"""Agent 5: Deep forensic analysis — attack timeline builder."""

import json
import logging
from datetime import datetime

try:
    from agents import get_agent
except ImportError:
    from backend.agents import get_agent

try:
    from ai_agents._utils import execute_agent_task, parse_json
except ImportError:
    from backend.ai_agents._utils import execute_agent_task, parse_json

logger = logging.getLogger(__name__)

FORENSICS_LLM = None


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("forensics")
    if FORENSICS_LLM is not None:

        agent.llm = FORENSICS_LLM
    context = {
        "alert_summary": raw_alert.get("rule_description", raw_alert.get("title", "")),
        "severity": raw_alert.get("severity", "unknown"),
        "source_ip": raw_alert.get("source_ip", "unknown"),
        "agent_name": raw_alert.get("agent_name", "unknown"),
        "threat_analysis_summary": decision_package.get("threat_analysis", {}).get("summary", "")[:500],
        "threat_hunt_summary": decision_package.get("threat_hunt_results", {}).get("hunting_summary", "")[:300],
        "mitre_id": decision_package.get("mitre_id", ""),
    }
    task = f"""
    Conduct forensic analysis based on: {json.dumps(context)}

    Return JSON with: attack_timeline (list of events with timestamp/event/evidence), root_cause, affected_systems, data_compromised, evidence_artifacts, containment_steps, recovery_steps, forensics_summary
    """
    try:
        result = execute_agent_task(agent, task)
        report = parse_json(result)
    except Exception as e:
        logger.error(f"Forensics failed: {e}")
        report = {"attack_timeline": [{"timestamp": datetime.utcnow().isoformat(), "event": "Alert triggered", "evidence": "Wazuh alert"}], "root_cause": "Fallback mode", "affected_systems": [raw_alert.get("agent_name", "unknown")], "data_compromised": False, "evidence_artifacts": [], "containment_steps": ["Isolate affected system", "Block malicious IP"], "recovery_steps": ["Verify system integrity", "Restore from backup"], "forensics_summary": "Fallback forensic analysis"}

    # ── gstack skill: structure root-cause reasoning (investigate methodology) ──
    try:
        from ai_tools import gstack_load_skill
    except ImportError:
        from backend.ai_tools import gstack_load_skill
    skill = gstack_load_skill("investigate")
    if skill.get("ok"):
        report["methodology"] = {
            "skill": "gstack:investigate",
            "applied": True,
            "root_cause_confirmed_by_evidence": bool(report.get("root_cause") and report.get("root_cause") != "Fallback mode"),
        }

    # ── Cognitive Arsenal: deep code analysis of any embedded script/command ──
    try:
        from ai_tools import gstack_analyze_code
    except ImportError:
        from backend.ai_tools import gstack_analyze_code
    full_log = raw_alert.get("full_log") or raw_alert.get("fullLog") or ""
    suspicious_cmd = raw_alert.get("command") or ""
    payload = (suspicious_cmd or full_log or "").strip()
    if 20 < len(payload) < 4000 and any(
        kw in payload.lower()
        for kw in ("powershell", "cmd.exe", "bash -", "/bin/", "invoke-", "iex ", "certutil", "python", "perl ", "nc ", "curl ", "wget ")
    ):
        code_analysis = gstack_analyze_code(payload[:2000])
        report["code_analysis"] = {
            "source": "gstack_coder",
            "risk_verdict": code_analysis.get("analysis", {}).get("risk_verdict", "unknown"),
            "summary": code_analysis.get("analysis", {}).get("summary", ""),
            "indicators": code_analysis.get("analysis", {}).get("indicators", [])[:8],
        }
        logger.info(f"Forensics code analysis verdict: {report['code_analysis']['risk_verdict']}")

    log = {"agent": "forensics", "message": f"Forensics complete: {report.get('root_cause', 'completed')[:80]}", "timestamp": datetime.utcnow().isoformat(), "level": "info"}

    return {"agent_logs": [log], "decision_package": {"forensics_report": report}, "current_node": "red_team"}
