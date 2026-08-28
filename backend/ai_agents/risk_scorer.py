"""Agent 2: Assign quantitative risk score with MITRE severity, asset criticality, and threat intel reputation."""

import json
import logging
import os
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

# MITRE Technique -> severity weight
MITRE_SEVERITY = {
    "T1078": 30, "T1059": 20, "T1547": 10, "T1003": 20,
    "T1485": 30, "T1566": 20, "T1021": 20, "T1047": 10,
    "T1053": 10, "T1098": 10, "T1190": 30, "T1133": 20,
    "T1071": 10, "T1574": 20, "T1055": 20, "T1569": 10,
    "T1036": 10, "T1548": 10, "T1550": 10, "T1041": 20,
}

# CMDB: IP -> criticality weight — single source of truth in backend/data/cmdb.json
_CMDB_FALLBACK = {
    "192.168.56.20": "high",
    "192.168.56.30": "critical",
    "192.168.56.40": "low",
    "192.168.56.2": "critical",
    "192.168.56.10": "medium",
    "192.168.56.100": "critical",
}


def _load_cmdb() -> dict:
    """Load asset criticality from backend/data/cmdb.json. Falls back to built-in map if file missing."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cmdb.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assets = data.get("assets", {})
        if not assets:
            return dict(_CMDB_FALLBACK)
        return {ip: a.get("criticality", "medium") for ip, a in assets.items()}
    except Exception as e:
        logger.warning(f"Could not load {path}, using fallback CMDB: {e}")
        return dict(_CMDB_FALLBACK)


CMDB = _load_cmdb()

ASSET_CRITICALITY_WEIGHT = {
    "critical": 30,
    "high": 20,
    "medium": 10,
    "low": 5,
}

# Mock OSINT / known malicious IPs (simulated threat intel feed)
KNOWN_MALICIOUS_IPS = {
    "10.0.0.1", "185.220.101.0", "91.121.86.0", "51.75.144.0",
    "192.168.56.10",  # Kali in lab context for demos
}

FINANCIAL_IMPACT = {
    "P1-Critical": "$500k",
    "P2-High": "$100k",
    "P3-Medium": "$10k",
    "P4-Low": "$1k",
}

MITRE_CRITICAL = {"T1078", "T1485", "T1190"}
MITRE_HIGH = {"T1059", "T1003", "T1566", "T1021", "T1041", "T1574", "T1055"}
MITRE_MEDIUM = {"T1547", "T1047", "T1053", "T1098", "T1133", "T1036", "T1548", "T1550"}
MITRE_LOW = {"T1071", "T1569"}


def _get_mitre_severity(mitre_id: str) -> int:
    """Get the severity weight for a MITRE technique ID."""
    return MITRE_SEVERITY.get(mitre_id, 10)


def _get_asset_criticality(dst_ip: str) -> str:
    """Lookup asset criticality from the mock CMDB."""
    return CMDB.get(dst_ip, "medium")


def _check_threat_intel(src_ip: str) -> bool:
    """Check if the source IP appears in the simulated threat intel feed."""
    return src_ip in KNOWN_MALICIOUS_IPS


def _calculate_priority_level(risk_score: int) -> str:
    """Map risk score to priority level."""
    if risk_score >= 75:
        return "P1-Critical"
    elif risk_score >= 50:
        return "P2-High"
    elif risk_score >= 25:
        return "P3-Medium"
    else:
        return "P4-Low"


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("risk_scoring")
    threat = decision_package.get("threat_analysis", {})

    # Extract fields from raw_alert and threat analysis
    mitre_id = threat.get("mitre_id", "") or raw_alert.get("mitre_id", "")
    src_ip = raw_alert.get("source_ip", raw_alert.get("src_ip", ""))
    dst_ip = raw_alert.get("destination_ip", raw_alert.get("dst_ip", ""))

    # Factor 1: MITRE Technique severity
    mitre_score = _get_mitre_severity(mitre_id)

    # Factor 2: Asset criticality
    asset_crit = _get_asset_criticality(dst_ip)
    asset_score = ASSET_CRITICALITY_WEIGHT.get(asset_crit, 10)

    # Factor 3: Threat intel reputation
    intel_boost = 25 if _check_threat_intel(src_ip) else 0

    # Calculate raw risk score (capped at 100)
    raw_score = mitre_score + asset_score + intel_boost
    risk_score = min(100, raw_score)

    # Determine risk level
    if risk_score >= 75:
        risk_level = "critical"
    elif risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    priority_level = _calculate_priority_level(risk_score)
    financial_impact_estimate = FINANCIAL_IMPACT.get(priority_level, "$0")

    impact_score = min(10, round((mitre_score + asset_score) / 6, 1))
    likelihood_score = min(10, round((mitre_score + intel_boost) / 6, 1))

    reasoning_parts = []
    if mitre_id:
        reasoning_parts.append(f"MITRE {mitre_id} severity={mitre_score}")
    if dst_ip:
        reasoning_parts.append(f"Asset {dst_ip} criticality={asset_crit}({asset_score})")
    if intel_boost:
        reasoning_parts.append(f"Threat intel match +25 (src={src_ip})")
    reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Standard scoring"

    scoring = {
        "risk_score": float(risk_score),
        "risk_level": risk_level,
        "priority_level": priority_level,
        "financial_impact_estimate": financial_impact_estimate,
        "impact_score": float(impact_score),
        "likelihood_score": float(likelihood_score),
        "reasoning": reasoning,
        "mitre_severity_score": mitre_score,
        "asset_criticality": asset_crit,
        "asset_criticality_score": asset_score,
        "threat_intel_boost": intel_boost,
    }

    log = {
        "agent": "risk_scoring",
        "message": f"Score: {risk_score}/100 ({risk_level.upper()}) [{priority_level}] - {reasoning}",
        "timestamp": datetime.utcnow().isoformat(),
        "level": "warning" if risk_level in ("critical", "high") else "info",
    }

    return {
        "agent_logs": [log],
        "decision_package": {
            "risk_score": float(risk_score),
            "risk_level": risk_level,
            "priority_level": priority_level,
            "financial_impact_estimate": financial_impact_estimate,
            "impact_score": float(impact_score),
            "likelihood_score": float(likelihood_score),
            "scoring_reasoning": reasoning,
            "asset_criticality": asset_crit,
            "threat_intel_match": intel_boost > 0,
        },
        "current_node": "recommendation",
    }