"""Agent 3: Generate SOAR playbook recommendations."""

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


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("recommendation")
    context = {"threat_analysis": decision_package.get("threat_analysis", {}), "risk_score": decision_package.get("risk_score", 0), "risk_level": decision_package.get("risk_level", ""), "mitre_id": decision_package.get("mitre_id", ""), "mitre_technique": decision_package.get("mitre_technique", "")}
    task = f"""
    Generate executable SOAR playbook recommendations:

    ```json
    {json.dumps(context, indent=2)}
    ```

    Return JSON array of actions. Each: action_id, action_type (block_ip/isolate_endpoint/update_firewall_rule/notify_admin/collect_forensics), target, priority (1-5), description, mitre_mapping, parameters
    """
    try:
        result = execute_agent_task(agent, task)
        recs = parse_json(result)
        if isinstance(recs, dict) and "actions" in recs:
            recs = recs["actions"]
        elif isinstance(recs, dict):
            recs = [recs]
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        recs = [{"action_id": "fallback-001", "action_type": "block_ip", "target": raw_alert.get("source_ip", "unknown"), "priority": 1, "description": f"Block source IP from alert {alert_id}", "mitre_mapping": decision_package.get("mitre_id", "T1078"), "parameters": {"duration_hours": 24}}]

    log = {"agent": "recommendation", "message": f"Generated {len(recs)} SOAR action(s)", "timestamp": datetime.utcnow().isoformat(), "level": "info"}

    return {"agent_logs": [log], "decision_package": {"recommendations": recs}, "current_node": "threat_hunter"}
