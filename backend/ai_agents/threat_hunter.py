"""Agent 4: Proactive threat hunting for additional IOCs."""

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

HUNTER_LLM = None


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("threat_hunter")
    if HUNTER_LLM is not None:

        agent.llm = HUNTER_LLM
    context = {
        "alert_summary": raw_alert.get("rule_description", raw_alert.get("title", "")),
        "severity": raw_alert.get("severity", "unknown"),
        "source_ip": raw_alert.get("source_ip", "unknown"),
        "threat_analysis_summary": decision_package.get("threat_analysis", {}).get("summary", "")[:500],
        "mitre_id": decision_package.get("mitre_id", ""),
    }
    task = f"""
    Perform proactive threat hunting based on: {json.dumps(context)}

    Return JSON with: additional_iocs, lateral_movement_indicators, persistence_found, exfiltration_indicators, hunting_summary, recommended_log_sources
    """
    try:
        result = execute_agent_task(agent, task)
        hunt = parse_json(result)
    except Exception as e:
        logger.error(f"Threat hunting failed: {e}")
        hunt = {"additional_iocs": [], "lateral_movement_indicators": [], "persistence_found": False, "exfiltration_indicators": [], "hunting_summary": "Fallback mode", "recommended_log_sources": ["endpoint", "network", "authentication"]}

    # ── Cognitive Arsenal: live web intel on the MITRE technique ──
    try:
        from ai_tools import agent_reach_search
    except ImportError:
        from backend.ai_tools import agent_reach_search
    mitre_id = context.get("mitre_id") or ""
    if mitre_id:
        web = agent_reach_search(f"MITRE ATT&CK {mitre_id} detection hunting latest adversary TTPs", max_results=3)
        if web.get("ok"):
            hunt["external_intel"] = {
                "source": "agent_reach_web_search",
                "query": web.get("query"),
                "references": [
                    {"title": r.get("title"), "url": r.get("url"), "snippet": (r.get("snippet") or "")[:200]}
                    for r in web.get("results", [])
                ],
            }
            logger.info(f"Threat hunter enriched with {len(web['results'])} live reference(s) for {mitre_id}")

    log = {"agent": "threat_hunter", "message": f"Hunt complete: {len(hunt.get('additional_iocs', []))} new IOC(s)", "timestamp": datetime.utcnow().isoformat(), "level": "warning" if hunt.get("persistence_found") else "info"}

    return {"agent_logs": [log], "decision_package": {"threat_hunt_results": hunt}, "current_node": "forensics"}
