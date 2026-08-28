"""Agent 1: Analyze raw Wazuh alert for threat indicators."""

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
    agent = get_agent("threat_detection")
    task = f"""
    Analyze the following Wazuh SIEM alert and identify all potential security threats:

    ```json
    {json.dumps(raw_alert, indent=2)}
    ```

    Return JSON with: is_threat, threat_type, severity, affected_assets, indicators, mitre_attack_id, mitre_technique, summary, confidence
    """
    try:
        result = execute_agent_task(agent, task)
        analysis = parse_json(result)
    except Exception as e:
        logger.error(f"Threat detection failed: {e}")
        analysis = {"is_threat": True, "threat_type": "unknown", "severity": "medium", "affected_assets": [], "indicators": [], "mitre_attack_id": "T1078", "mitre_technique": "Valid Accounts", "summary": f"Fallback: {e}", "confidence": 0.5}

    log = {"agent": "threat_detection", "message": f"Analysis: {analysis.get('threat_type', 'unknown')} (confidence: {analysis.get('confidence', 0):.2f})", "timestamp": datetime.utcnow().isoformat(), "level": "success" if analysis.get("is_threat") else "info"}

    return {"agent_logs": [log], "decision_package": {"threat_analysis": analysis, "mitre_id": analysis.get("mitre_attack_id", ""), "mitre_technique": analysis.get("mitre_technique", "")}, "current_node": "risk_scoring"}
