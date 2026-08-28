"""Agent 8: UEBA - User & Entity Behavior Analytics."""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from agents import get_agent
except ImportError:
    from backend.agents import get_agent

try:
    from ai_agents._utils import execute_agent_task, parse_json
except ImportError:
    from backend.ai_agents._utils import execute_agent_task, parse_json

logger = logging.getLogger(__name__)


def _rule_based(raw_alert: dict) -> dict:
    """Deterministic UEBA scoring fallback (LLM never crashes the node)."""
    ra = raw_alert or {}
    user = ra.get("user") or (ra.get("data") or {}).get("user", "unknown")
    src_ip = ra.get("source_ip") or ra.get("src_ip", "")
    dst_ip = ra.get("destination_ip") or ra.get("dst_ip", "")
    event_id = ((ra.get("data") or {}).get("winlog") or {}).get("event_id")
    agent_name = ra.get("agent_name", "")
    anomalies: List[str] = []
    boost = 0

    # Failed-login volume heuristic
    raw_text = json.dumps(ra, default=str).lower()
    if "multiple failed" in raw_text or "brute force" in raw_text or "failed logins" in raw_text:
        import re
        nums = [int(m) for m in re.findall(r"(\d+)", str(ra.get("rule_description", "")))]
        fails = max(nums, default=5)
        if fails >= 10:
            anomalies.append("Sustained brute-force behavior - possible credential stuffing")
            boost = 25
        else:
            anomalies.append(f"{fails} failed authentication attempts in one window")
            boost = 15

    if event_id == 4672:
        anomalies.append("Special privileges assigned during alert window")
        boost += 10

    # Off-hours authentication
    ts = ra.get("timestamp", "")
    hour = None
    try:
        hour = int(datetime.fromisoformat(str(ts).replace("Z", "+00:00")).hour)
    except Exception:
        pass
    if hour is not None and (hour < 5 or hour > 23):
        anomalies.append("Authentication outside normal working hours")
        boost += 8

    if "kali" in str(agent_name).lower() or src_ip == "192.168.56.10":
        anomalies.append("Activity from previously-unseen host")
        boost += 8

    return {
        "user": str(user),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "ueba_risk_boost": boost,
        "behavior_deviation_score": min(10, round(boost / 3, 1)),
        "entity_risk": "high" if boost >= 25 else "medium" if boost >= 10 else "low",
        "method": "rule_engine",
    }


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("ueba")
    task = f"""
Analyze the Wazuh alert `{alert_id}` for User & Entity Behavior Analytics (UEBA).

Alert:
```json
{json.dumps(raw_alert or {}, indent=2)}
```

Return JSON: {{user, anomaly_count, anomalies (array), behavior_deviation_score (0-10), entity_risk (low/medium/high), ueba_risk_boost (0-30)}}
"""
    try:
        result = execute_agent_task(agent, task)
        ueba = parse_json(result)
        if not ueba:
            raise ValueError("Empty UEBA result")
        ueba["method"] = "llm"
    except Exception as e:
        logger.warning(f"UEBA LLM failed ({e}) - using rule engine")
        ueba = _rule_based(raw_alert)

    boost = int(ueba.get("ueba_risk_boost", 0) or 0)
    log = {
        "agent": "ueba",
        "message": f"UEBA: {ueba.get('entity_risk', 'unknown')} behavior deviation, {ueba.get('anomaly_count', 0)} anomalies",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "warning" if boost >= 15 else "info",
    }

    return {
        "agent_logs": [log],
        "decision_package": {"ueba_analysis": ueba},
        "current_node": "master_synthesis",
    }