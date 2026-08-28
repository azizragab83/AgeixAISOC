"""Agent 5b (alt): Sigma rule generation — Detection Gap Engine."""

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

FALLBACK_RULE = {
    "title": "AI-generated detection rule",
    "rule_id": "sigma-ai-generated",
    "description": "Auto-generated rule for detected gap",
    "logsource": {"category": "process_creation", "product": "windows"},
    "detection": {"selection": {"EventID": 4688}, "condition": "selection"},
    "level": "medium",
    "mitre_id": ["T1078"],
    "false_positives": ["Unknown"],
    "status": "experimental",
}


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("detection_engineer")
    context = {
        "alert": raw_alert,
        "threat_analysis": decision_package.get("threat_analysis", {}),
        "mitre_id": decision_package.get("mitre_id", ""),
        "blue_team_reasoning": decision_package.get("blue_team_result", {}).get("reasoning", "Detection gap identified — no existing rule covers this pattern."),
    }
    task = f"""
    Generate a Sigma detection rule to close this detection gap:

    ```json
    {json.dumps(context, indent=2)}
    ```

    The Blue Team confirmed this pattern is NOT covered by existing rules.
    Generate a new Sigma rule that would detect it.

    Return JSON with: title, rule_id, description, logsource (category, product, service), detection (selection, condition), level, mitre_id list, false_positives, status
    """
    rule = FALLBACK_RULE.copy()
    rule["rule_id"] = f"sigma-{alert_id.lower()}"
    rule["mitre_id"] = [decision_package.get("mitre_id", "T1078") if decision_package.get("mitre_id") else "T1078"]

    try:
        result = execute_agent_task(agent, task)
        parsed = parse_json(result)
    except Exception as e:
        logger.error(f"Sigma generation failed: {e}")
        parsed = {}
    if not parsed:
        logger.warning("detection_eng LLM parse failed, using fallback rule template.")
    else:
        rule = parsed

    log = {"agent": "detection_engineer", "message": f"Sigma rule generated: {rule.get('title', 'Untitled')}", "timestamp": datetime.utcnow().isoformat(), "level": "info"}

    return {"agent_logs": [log], "decision_package": {"sigma_rule": rule}, "current_node": "gap_closure"}
