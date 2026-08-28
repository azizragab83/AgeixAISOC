"""
AgeixAISOC - LangGraph Orchestrator
Defines an 8-node StateGraph with Detection Gap Loop:
threat_detection → risk_scoring → recommendation → threat_hunter → forensics → red_team → blue_team
                                                                                              │
                                                                                  ┌───────────┤
                                                                                  ▼           ▼
                                                                          detection_engineer  END
                                                                                  │
                                                                                  ▼
                                                                           gap_closure → END
"""

import json
import logging
import operator
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END

try:
    from config import settings
except ImportError:
    from backend.config import settings

try:
    from ai_agents import (
        run_threat_detection,
        run_risk_scoring,
        run_recommendation,
        run_threat_hunter,
        run_forensics,
        run_red_team,
        run_blue_team,
        run_detection_eng,
        run_ueba,
        run_osint,
    )
except ImportError:
    from backend.ai_agents import (
        run_threat_detection,
        run_risk_scoring,
        run_recommendation,
        run_threat_hunter,
        run_forensics,
        run_red_team,
        run_blue_team,
        run_detection_eng,
        run_ueba,
        run_osint,
    )

try:
    from services.wazuh_deploy import deploy_sigma_rule_real, sigma_dict_to_wazuh_xml
except ImportError:
    from backend.services.wazuh_deploy import deploy_sigma_rule_real, sigma_dict_to_wazuh_xml

try:
    from ai_tools import run_master_tool_loop
except ImportError:
    from backend.ai_tools import run_master_tool_loop

try:
    from rag_memory import evaluate_learned_memory, apply_learned_memory_to_package
except ImportError:
    from backend.rag_memory import evaluate_learned_memory, apply_learned_memory_to_package

logger = logging.getLogger(__name__)


class AgentLog(TypedDict):
    agent: str
    message: str
    timestamp: str
    level: str


class DecisionPackage(TypedDict, total=False):
    alert_id: str
    raw_alert: Dict[str, Any]
    threat_analysis: Dict[str, Any]
    risk_score: float
    risk_level: str
    mitre_id: str
    mitre_technique: str
    recommendations: List[Dict[str, Any]]
    threat_hunt_results: Dict[str, Any]
    forensics_report: Dict[str, Any]
    red_team_validation: Dict[str, Any]
    blue_team_result: Dict[str, Any]
    gap_detected: bool
    sigma_rule: Optional[Dict[str, Any]]
    deployment_status: str
    decision_id: str
    status: str
    human_decision: Optional[str]
    executed_at: Optional[str]
    error: Optional[str]


def _merge_decision_packages(left: Optional[Dict], right: Optional[Dict]) -> Dict[str, Any]:
    """Reducer that deep-merges decision_package updates from parallel branches.

    Required because the 9-agent fan-out runs UEBA/OSINT concurrently with the
    core chain - without this reducer, the last-completing branch would clobber
    the others' outputs.
    """
    return {**(left or {}), **(right or {})}


def _last_write_wins(left: Any, right: Any) -> Any:
    """Reducer for keys written by parallel branches - last completed node wins."""
    return right if right is not None else left


class SOCState(TypedDict):
    alert_id: str
    raw_alert: Dict[str, Any]
    agent_logs: Annotated[List[AgentLog], operator.add]
    decision_package: Annotated[DecisionPackage, _merge_decision_packages]
    current_node: Annotated[str, _last_write_wins]
    errors: Annotated[List[str], operator.add]


def threat_detection_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[ThreatDetection] Processing alert {state['alert_id']}")
    result = run_threat_detection(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"]},
        "current_node": result["current_node"],
    }


def risk_scoring_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[RiskScoring] Scoring threat for alert {state['alert_id']}")
    result = run_risk_scoring(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"]},
        "current_node": result["current_node"],
    }


def recommendation_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[Recommendation] Generating SOAR actions for alert {state['alert_id']}")
    result = run_recommendation(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"]},
        "current_node": result["current_node"],
    }


def threat_hunter_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[ThreatHunter] Hunting for alert {state['alert_id']}")
    result = run_threat_hunter(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"]},
        "current_node": result["current_node"],
    }


def forensics_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[Forensics] Analyzing alert {state['alert_id']}")
    result = run_forensics(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"]},
        "current_node": result["current_node"],
    }


def red_team_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[RedTeam] Validating detection for alert {state['alert_id']}")
    agent_result = run_red_team(state["alert_id"], state["raw_alert"], state["decision_package"])

    decision_id = f"DEC-{state['alert_id']}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    base_package: DecisionPackage = {
        **state["decision_package"],
        **agent_result["decision_package"],
        "alert_id": state["alert_id"],
        "raw_alert": state["raw_alert"],
        "decision_id": decision_id,
        "status": "pending",
        "human_decision": None,
        "executed_at": None,
        "error": None,
    }

    log_entry: AgentLog = {
        "agent": "red_team",
        "message": f"Decision package {decision_id} created. Handing off to Blue Team for coverage check.",
        "timestamp": datetime.utcnow().isoformat(),
        "level": "success",
    }

    return {
        "agent_logs": agent_result["agent_logs"] + [log_entry],
        "decision_package": base_package,
        "current_node": "blue_team",
    }


def blue_team_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[BlueTeam] Checking detection coverage for alert {state['alert_id']}")
    result = run_blue_team(state["alert_id"], state["raw_alert"], state["decision_package"])
    gap_detected = not result["decision_package"].get("blue_team_result", {}).get("detection_confirmed", False)

    merged = {**state["decision_package"], **result["decision_package"], "gap_detected": gap_detected}
    if gap_detected:
        merged["deployment_status"] = "sigma_generation_pending"
    else:
        merged["deployment_status"] = "already_covered"

    return {
        "agent_logs": result["agent_logs"],
        "decision_package": merged,
        "current_node": "detection_engineer" if gap_detected else "__end__",
    }


def detection_engineer_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[DetectionEngineer] Generating Sigma rule for gap in alert {state['alert_id']}")
    result = run_detection_eng(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"], "deployment_status": "rule_generated"},
        "current_node": result["current_node"],
    }


def gap_closure_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[GapClosure] Deploying Sigma rule for alert {state['alert_id']}")
    dp = state["decision_package"]
    sigma_rule = dp.get("sigma_rule", {})
    rule_id = sigma_rule.get("rule_id", f"sigma-{state['alert_id'].lower()}")
    rule_content = sigma_dict_to_wazuh_xml(sigma_rule)

    rules_dir = Path(__file__).resolve().parent / "generated_rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    filepath = rules_dir / f"{rule_id}.xml"
    try:
        filepath.write_text(rule_content, encoding="utf-8")
        logger.info(f"Wazuh XML rule written to {filepath}")
        file_written = True
    except Exception as e:
        logger.error(f"Failed to write Wazuh XML rule file: {e}")
        file_written = False

    deploy_result = {"status": "file_write_failed", "message": "Could not write rule file"} if not file_written else {}
    if file_written:
        try:
            deploy_result = run_deploy_sigma_rule(
                rule_content, rule_id,
                settings.WAZUH_API_URL,
                settings.WAZUH_API_USER,
                settings.WAZUH_API_PASS,
                settings.WAZUH_API_KEY,
            )
        except Exception as e:
            logger.error(f"Sigma deploy call failed: {e}")
            deploy_result = {"status": "manual_review_required", "message": f"Deploy call failed: {e}", "rule_id": rule_id}

    deployment_status = deploy_result.get("status", "unknown")
    gap_closed = deployment_status == "deployed"

    sig_rule = dict(sigma_rule) if sigma_rule else None
    log_entry: AgentLog = {
        "agent": "gap_closure",
        "message": f"Rule {rule_id} — file={'written' if file_written else 'FAILED'}, wazuh={deployment_status}",
        "timestamp": datetime.utcnow().isoformat(),
        "level": "success" if gap_closed else "warning",
    }

    final_package = {
        **dp,
        "sigma_rule_generated": sig_rule,
        "deployment_status": deployment_status,
        "gap_closed": gap_closed,
        "new_rule_id": rule_id if deployment_status == "deployed" else None,
    }

    return {
        "agent_logs": [log_entry],
        "decision_package": final_package,
        "current_node": "__end__",
    }


def ueba_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[UEBA] Analyzing user behavior for alert {state['alert_id']}")
    result = run_ueba(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"]},
        "current_node": "master_synthesis",
    }


def osint_node(state: SOCState) -> Dict[str, Any]:
    logger.info(f"[OSINT] Enriching indicators for alert {state['alert_id']}")
    result = run_osint(state["alert_id"], state["raw_alert"], state["decision_package"])
    return {
        "agent_logs": result["agent_logs"],
        "decision_package": {**state["decision_package"], **result["decision_package"]},
        "current_node": "master_synthesis",
    }


def _call_master_brain(
    agent_outputs: Dict[str, Any],
    unified_risk: float,
    deterministic_summary: str,
    deterministic_narrative: str,
    deterministic_next: str,
) -> Dict[str, Any]:
    """Call the qwen2.5:14b Master Brain with all 9 agent outputs.

    Builds a massive structured prompt containing every agent's JSON output and
    asks the model to produce the final cognitive synthesis JSON:
      executive_summary / unified_risk_score / correlated_threat_narrative / predicted_next_move
    Returns the deterministic synthesis untouched if the LLM is unreachable.
    """
    import httpx

    prompt = f"""You are the Master Brain of an autonomous SOC. Synthesize the full evidence from 9 AI agents into one incident decision.

ALL AGENT OUTPUTS (JSON):
{json.dumps(agent_outputs, indent=2, default=str)}

IMPORTANT - HUMAN FEEDBACK MEMORY:
The "rag_memory" section above contains what human analysts previously decided for SIMILAR alerts
(queried from the learned_decisions vector store). If rag_memory.matched is true and kind is
"negative" (a past False Positive), you MUST lower unified_risk_score accordingly and mention the
analyst's prior verdict in correlated_threat_narrative. If kind is "positive", treat it as
corroborating evidence. If matched is false, ignore this section.

  IMPORTANT - EXTERNAL INTELLIGENCE INTEGRATION:
  Review the external intelligence gathered via Agent-Reach (deep web search), OSINT Arsenal
  (multi-source IOC enrichment), and Code Analysis (gstack). Integrate these external findings
  into your final correlated threat narrative and predicted next move.

IMPORTANT - EXTERNAL INTELLIGENCE:
The "external_intelligence" section contains LIVE data gathered autonomously by your Cognitive
Arsenal (web search results, IOC reputation enrichment from OSINT databases, page reads).
If findings show an IOC is known-malicious, RAISE unified_risk_score and cite the source in
correlated_threat_narrative. If enrichment shows a benign/legitimate service, LOWER risk and say why.
If findings are empty, ignore this section.

Return a JSON object ONLY with these exact keys:
{{
  "executive_summary": "2-sentence C-suite summary of the incident",
  "unified_risk_score": <float 0-100 final risk, lowered if RAG memory shows a past false positive>,
  "correlated_threat_narrative": "how network, endpoint, OSINT, UEBA, and human feedback memory connect",
  "predicted_next_move": "what the attacker will likely do next based on Forensics + Red Team"
}}"""

    timeout = 25
    base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434") or "http://localhost:11434"
    model = getattr(settings, "OLLAMA_MODEL_THREAT", "qwen2.5:14b") or "qwen2.5:14b"

    for path in ("/api/generate", "/api/chat"):
        try:
            payload = {"model": model, "stream": False}
            if path == "/api/chat":
                payload["messages"] = [{"role": "user", "content": prompt}]
            else:
                payload["prompt"] = prompt
            resp = httpx.post(f"{base_url}{path}", json=payload, timeout=timeout)
            if resp.status_code != 200:
                continue
            data = resp.json()
            raw = data.get("response") or (data.get("message") or {}).get("content") or ""
            if not raw:
                continue
            text = raw.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end + 1])
                logger.info("Master Brain (qwen2.5:14b) synthesis complete")
                return {
                    "executive_summary": str(parsed.get("executive_summary", deterministic_summary)),
                    "unified_risk_score": float(parsed.get("unified_risk_score", unified_risk)),
                    "correlated_threat_narrative": str(parsed.get("correlated_threat_narrative", deterministic_narrative)),
                    "predicted_next_move": str(parsed.get("predicted_next_move", deterministic_next)),
                }
        except Exception as e:
            logger.warning(f"Master Brain LLM call to {path} failed: {e}")

    logger.info("Master Brain LLM unreachable - using deterministic cognitive synthesis")
    return {
        "executive_summary": deterministic_summary,
        "unified_risk_score": unified_risk,
        "correlated_threat_narrative": deterministic_narrative,
        "predicted_next_move": deterministic_next,
    }


def master_synthesis_node(state: SOCState) -> Dict[str, Any]:
    """Master Brain: synthesize all 9 agent outputs into a single cognitive package."""
    logger.info(f"[MasterSynthesis] Synthesizing {len(state['agent_logs'])} agent outputs for alert {state['alert_id']}")
    dp = state["decision_package"]

    # Gather all JSON outputs from the 9 agents
    threat = dp.get("threat_analysis", {})
    risk = {
        "risk_score": dp.get("risk_score", 0),
        "risk_level": dp.get("risk_level", "unknown"),
        "priority_level": dp.get("priority_level", ""),
        "reasoning": dp.get("scoring_reasoning", ""),
    }
    recs = dp.get("recommendations", [])
    hunt = dp.get("threat_hunt_results", {})
    forensics = dp.get("forensics_report", {})
    red_team = dp.get("red_team_validation", {})
    ueba = dp.get("ueba_analysis", {})
    osint = dp.get("osint_analysis", {})
    blue_team = dp.get("blue_team_result", {})

    # ── RAG MEMORY: has a human already resolved a similar alert pattern? ──
    try:
        rag_memory = evaluate_learned_memory(state["alert_id"], state["raw_alert"])
    except Exception as e:
        logger.warning(f"Master Synthesis RAG memory check failed (non-fatal): {e}")
        rag_memory = None

    rag_memory_context = {
        "matched": bool(rag_memory and rag_memory.get("matched")),
        "kind": rag_memory.get("kind") if rag_memory else None,
        "confidence": round(float(rag_memory.get("confidence", 0)), 3) if rag_memory else 0.0,
        "note": rag_memory.get("note", "") if rag_memory else "",
    }

    # ── Reliable local synthesis (deterministic fallback) ──
    base_risk = float(risk.get("risk_score", 0) or 0)
    ueba_boost = int(ueba.get("ueba_risk_boost", 0) or 0)
    osint_boost = int(osint.get("osint_risk_boost", 0) or 0)
    unified_risk = min(100.0, base_risk + ueba_boost + osint_boost)

    # ── Learned-memory risk reduction: past False Positive lowers the score ──
    if rag_memory and rag_memory.get("action") == "lower_risk":
        unified_risk = round(min(100.0, unified_risk * 0.6), 1)

    # Correlated threat narrative built from real agent outputs
    # NOTE: initialized here because the narrative loop below references it;
    # the Cognitive Arsenal section further down populates it.
    external_intel: list = []
    narrative_parts = []
    if threat.get("threat_type"):
        narrative_parts.append(f"Threat detection identified {threat.get('threat_type')}")
    if osint.get("malicious_iocs"):
        narrative_parts.append(f"OSINT correlated {len(osint['malicious_iocs'])} malicious indicator(s) to known actor(s)")
    if ueba.get("anomaly_count"):
        narrative_parts.append(f"UEBA flagged {ueba['anomaly_count']} behavioral anomaly(ies)")
    if hunt.get("additional_iocs"):
        narrative_parts.append(f"Threat hunting uncovered {len(hunt['additional_iocs'])} additional IOCs")
    if forensics.get("root_cause"):
        narrative_parts.append(f"Forensics root cause: {forensics['root_cause']}")
    if rag_memory_context.get("matched"):
        narrative_parts.append(
            f"RAG memory: similar alert previously {rag_memory_context.get('kind')} by analyst "
            f"(confidence {rag_memory_context.get('confidence', 0):.0%}) - {rag_memory_context.get('note')}"
        )
    if external_intel:
        tool_names = [f.get("tool") for f in external_intel if isinstance(f, dict)]
        narrative_parts.append(
            f"Live intelligence gathered via Cognitive Arsenal ({', '.join(tool_names)}): "
            "external web/OSINT enrichment corroborates this assessment"
        )
    correlated_narrative = ". ".join(narrative_parts) if narrative_parts else "Agent outputs insufficient for correlation."

    # Predicted next move from forensics + red team
    predicted_parts = []
    red_next = red_team.get("next_likely_step") or red_team.get("predicted_next_step")
    if red_next:
        predicted_parts.append(str(red_next))
    if forensics.get("attack_timeline"):
        predicted_parts.append("Attacker will likely attempt lateral movement or persistence based on forensic timeline")
    predicted_next_move = "; ".join(predicted_parts) if predicted_parts else "No clear next-step prediction. Monitor host for privilege escalation."

    # 2-sentence executive summary
    summary = (
        f"An alert was confirmed as {threat.get('threat_type', 'a potential threat')} "
        f"with unified risk {unified_risk:.0f}/100 ({risk.get('risk_level', 'medium')}). "
        f"{correlated_narrative}"
    )

    # ── COGNITIVE ARSENAL: agentic external-intelligence gathering ──
    # The Master Brain itself decides which tools to call (web search / page
    # reads / IOC enrichment) before synthesizing. Fully guarded, never fatal.
    try:
        alert_summary = json.dumps({
            "alert_id": state["alert_id"],
            "raw_alert": state["raw_alert"],
            "threat_analysis": threat,
            "risk": risk,
            "osint": osint,
            "hunt_iocs": hunt.get("additional_iocs", []),
        }, indent=2, default=str)[:6000]
        rounds = int(getattr(settings, "ARSENAL_MASTER_ROUNDS", 3) or 3)
        external_intel = run_master_tool_loop(alert_summary, max_rounds=rounds)
        if external_intel:
            logger.info(
                f"[MasterSynthesis] Cognitive Arsenal gathered {len(external_intel)} "
                f"external intel finding(s): {[f.get('tool') for f in external_intel]}"
            )
    except Exception as e:
        logger.warning(f"Cognitive Arsenal loop failed (non-fatal): {e}")

    # Master Brain Cognitive Synthesis (qwen2.5:14b)
    agent_outputs = {
        "threat_detection": threat,
        "risk_scoring": risk,
        "recommendation": recs,
        "threat_hunter": hunt,
        "forensics": forensics,
        "red_team": red_team,
        "blue_team": blue_team,
        "ueba": ueba,
        "osint": osint,
        "rag_memory": rag_memory_context,
        "external_intelligence": {
            "source": "cognitive_arsenal (Agent-Reach web search + OSINT IOC enrichment)",
            "findings": external_intel,
        },
    }
    synthesis = _call_master_brain(
        agent_outputs=agent_outputs,
        unified_risk=unified_risk,
        deterministic_summary=summary,
        deterministic_narrative=correlated_narrative,
        deterministic_next=predicted_next_move,
    )

    master_package = {
        **dp,
        "master_synthesis": {
            **synthesis,
            "agent_outputs": agent_outputs,
        },
        "risk_score": round(float(synthesis.get("unified_risk_score", unified_risk)), 1),
        "risk_level": risk.get("risk_level", "medium"),
        "status": "pending",
    }

    log_entry: AgentLog = {
        "agent": "master_synthesis",
        "message": f"Master Brain synthesized {len(narrative_parts)} evidence streams. Unified risk: {unified_risk:.0f}/100",
        "timestamp": datetime.utcnow().isoformat(),
        "level": "success",
    }

    return {
        "agent_logs": [log_entry],
        "decision_package": master_package,
        "current_node": "decision_id_generation",
    }


def route_after_blue_team(state: SOCState) -> str:
    gap = state["decision_package"].get("gap_detected", False)
    if gap:
        logger.info(f"[Router] Gap detected → routing to detection_engineer")
        return "detection_engineer"
    logger.info(f"[Router] Already covered → routing to END")
    return "__end__"


def run_deploy_sigma_rule(rule_content: str, rule_id: str, api_url: str, api_user: str, api_pass: str, api_key: str) -> dict:
    import asyncio

    async def _deploy():
        return await deploy_sigma_rule_real(rule_content, rule_id, api_url, api_user, api_pass, api_key)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_deploy())
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(_deploy())).result()


def build_soc_graph() -> StateGraph:
    """9-agent COGNITIVE pipeline.

    Fan-out from threat_detection into THREE parallel branches:
      Branch A (core chain): risk_scoring -> recommendation -> threat_hunter
                             -> forensics -> red_team -> blue_team
      Branch B:              ueba   (independent behavioral analysis)
      Branch C:              osint  (independent intel enrichment)
    All branches JOIN at master_synthesis, which gathers every agent's JSON
    output, calls qwen2.5:14b (Master Brain), and emits the final package.
    """
    workflow = StateGraph(SOCState)

    workflow.add_node("threat_detection", threat_detection_node)
    workflow.add_node("risk_scoring", risk_scoring_node)
    workflow.add_node("recommendation", recommendation_node)
    workflow.add_node("threat_hunter", threat_hunter_node)
    workflow.add_node("forensics", forensics_node)
    workflow.add_node("red_team", red_team_node)
    workflow.add_node("blue_team", blue_team_node)
    workflow.add_node("detection_engineer", detection_engineer_node)
    workflow.add_node("gap_closure", gap_closure_node)
    workflow.add_node("ueba", ueba_node)
    workflow.add_node("osint", osint_node)
    workflow.add_node("master_synthesis", master_synthesis_node)

    workflow.set_entry_point("threat_detection")

    # ── PARALLEL FAN-OUT: three branches launch simultaneously ──
    workflow.add_edge("threat_detection", "risk_scoring")   # Branch A
    workflow.add_edge("threat_detection", "ueba")           # Branch B
    workflow.add_edge("threat_detection", "osint")          # Branch C

    # Branch A continues sequentially
    workflow.add_edge("risk_scoring", "recommendation")
    workflow.add_edge("recommendation", "threat_hunter")
    workflow.add_edge("threat_hunter", "forensics")
    workflow.add_edge("forensics", "red_team")
    workflow.add_edge("red_team", "blue_team")

    # Blue team gap loop rejoins synthesis after coverage check
    workflow.add_conditional_edges(
        "blue_team",
        route_after_blue_team,
        {
            "detection_engineer": "detection_engineer",
            "__end__": "master_synthesis",
        },
    )
    workflow.add_edge("detection_engineer", "gap_closure")
    workflow.add_edge("gap_closure", "master_synthesis")

    # ── PARALLEL JOIN: all branches converge on the Master Brain ──
    workflow.add_edge("ueba", "master_synthesis")
    workflow.add_edge("osint", "master_synthesis")
    workflow.add_edge("master_synthesis", END)

    return workflow.compile()


class SOCGraphRunner:
    """High-level runner for the SOC LangGraph pipeline."""

    def __init__(self):
        self.graph = build_soc_graph()
        self.callbacks = []

    def register_callback(self, callback):
        self.callbacks.append(callback)

    async def _notify_callbacks(self, event_type: str, data: Any):
        for callback in self.callbacks:
            try:
                await callback(event_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def run(self, alert_id: str, raw_alert: Dict[str, Any]) -> DecisionPackage:
        # ── MASTER BRAIN PRE-CHECK: Natural Adaptive Learning ──
        # Before generating a Decision Package, query the RAG learned_decisions
        # collection. If a similar alert was previously rejected by a human
        # (Negative Example), suppress it entirely when confidence > 90% or
        # lower the risk + append the analyst note when confidence >= 70%.
        try:
            learned_memory = evaluate_learned_memory(alert_id, raw_alert)
        except Exception as e:
            logger.warning(f"Master Brain learned-memory check failed (non-fatal): {e}")
            learned_memory = None

        if learned_memory and learned_memory.get("action") == "suppress":
            suppressed_pkg: DecisionPackage = {
                "alert_id": alert_id,
                "raw_alert": raw_alert,
                "decision_id": f"SUP-{alert_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "status": "suppressed_by_learned_memory",
                "human_decision": None,
                "executed_at": None,
                "error": None,
                "risk_score": 0.0,
                "risk_level": "informational",
                "notes": "Previously marked as False Positive by Analyst",
                "learned_memory": learned_memory,
                "created_at": datetime.utcnow().isoformat(),
            }
            logger.info(
                "Master Brain suppressed alert %s (learned FP, confidence=%.2f)",
                alert_id, learned_memory.get("confidence", 0),
            )
            await self._notify_callbacks("pipeline_complete", {
                "alert_id": alert_id,
                "decision_id": suppressed_pkg["decision_id"],
                "risk_score": 0,
                "risk_level": "informational",
                "timestamp": datetime.utcnow().isoformat(),
                "decision_package": suppressed_pkg,
                "suppressed_by_learned_memory": True,
            })
            return suppressed_pkg

        # ── Lower-risk learned memories are applied per-node via the state ──
        learned_hint = {}
        if learned_memory and learned_memory.get("action") == "lower_risk":
            learned_hint = learned_memory

        initial_state: SOCState = {
            "alert_id": alert_id,
            "raw_alert": raw_alert,
            "agent_logs": [],
            "decision_package": {"learned_memory_eval": learned_hint} if learned_hint else {},
            "current_node": "threat_detection",
            "errors": [],
        }

        await self._notify_callbacks("pipeline_start", {
            "alert_id": alert_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        config = {"configurable": {"thread_id": alert_id}}

        final_state = None
        async for event in self.graph.astream(initial_state, config):
            for node_name, node_state in event.items():
                if node_name == "__end__":
                    continue
                await self._notify_callbacks("node_transition", {
                    "alert_id": alert_id,
                    "node": node_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "logs": node_state.get("agent_logs", []),
                })
                final_state = node_state

        if final_state is None:
            raise RuntimeError(f"SOC pipeline did not complete for alert {alert_id}")

        decision_package = final_state.get("decision_package", {})

        # ── Apply learned-memory risk reduction AFTER the full pipeline ──
        if learned_hint:
            try:
                decision_package = apply_learned_memory_to_package(decision_package, learned_hint)
            except Exception as e:
                logger.warning(f"Apply learned memory to package failed (non-fatal): {e}")

        await self._notify_callbacks("pipeline_complete", {
            "alert_id": alert_id,
            "decision_id": decision_package.get("decision_id", ""),
            "risk_score": decision_package.get("risk_score", 0),
            "risk_level": decision_package.get("risk_level", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "decision_package": decision_package,
        })

        return decision_package


def _parse_agent_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    import re
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    return {"raw_output": text, "parse_error": "Could not parse JSON from agent output"}


soc_runner = SOCGraphRunner()
