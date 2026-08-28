"""Agent 7: Blue Team detection validation — confirms whether a rule exists for the threat pattern."""

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

AD_ATTACK_PATTERNS = {
    "T1558": {"name": "Kerberoasting", "label": "AD Detection Logic — Rule-Based"},
    "T1550.002": {"name": "Pass-the-Hash", "label": "AD Detection Logic — Rule-Based"},
    "T1003.006": {"name": "DCSync", "label": "AD Detection Logic — Rule-Based"},
}

AD_TECHNIQUE_IDS = set(AD_ATTACK_PATTERNS.keys())

# Keyword-based fallback detection when the alert doesn't carry a mitre_id
AD_KEYWORDS = {
    "T1558": ["kerberoast", "tgs-", "service principal", "spn"],
    "T1550.002": ["pass-the-hash", "pth", "ntlm hash", "sekurlsa"],
    "T1003.006": ["dcsync", "replication", "getncchanges", "drsuapi"],
}


def check_ad_attack_pattern(mitre_id: str, raw_alert: dict) -> dict:
    """Rule-based AD attack detection (Kerberoasting, Pass-the-Hash, DCSync).
    NOT a full attack simulation — labeled 'AD Detection Logic — Rule-Based' in the UI.
    """
    if mitre_id and mitre_id in AD_TECHNIQUE_IDS:
        pattern = AD_ATTACK_PATTERNS[mitre_id]
        return {
            "ad_attack": True,
            "ad_technique": pattern["name"],
            "ad_label": pattern["label"],
            "ad_reasoning": f"Alert matches AD attack pattern for {pattern['name']} ({mitre_id}). "
                            f"Rule-based detection logic applied — not a full AD attack simulation.",
        }

    # Keyword fallback on alert text
    alert_text = " ".join(str(v) for v in (raw_alert or {}).values()).lower() if isinstance(raw_alert, dict) else str(raw_alert or "").lower()
    for tech_id, keywords in AD_KEYWORDS.items():
        if any(k in alert_text for k in keywords):
            pattern = AD_ATTACK_PATTERNS[tech_id]
            return {
                "ad_attack": True,
                "ad_technique": pattern["name"],
                "ad_label": pattern["label"],
                "ad_reasoning": f"Alert keywords match {pattern['name']} ({tech_id}). "
                                f"Rule-based detection logic applied — not a full AD attack simulation.",
            }
    return {"ad_attack": False, "ad_technique": None, "ad_label": None, "ad_reasoning": ""}


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("blue_team")
    mitre_id = decision_package.get("mitre_id", "")
    ad_check = check_ad_attack_pattern(mitre_id, raw_alert)

    # ── MITRE ATT&CK KB enrichment (real RAG lookup on the ingested STIX bundle) ──
    mitre_refs = []
    try:
        try:
            from rag_engine.rag_server import rag_server
        except ImportError:
            from backend.rag_engine.rag_server import rag_server
        hits = rag_server.search(
            f"{mitre_id} {decision_package.get('mitre_technique', '')} mitre attack technique",
            top_k=3,
        )
        mitre_refs = [
            {"technique_id": h.get("metadata", {}).get("technique_id", ""), "name": h.get("metadata", {}).get("name", ""), "text": (h.get("text", "") or "")[:400]}
            for h in hits
            if h.get("metadata", {}).get("kb") == "mitre_attack"
        ]
        if mitre_refs:
            logger.info(f"[BlueTeam] MITRE KB reference found for {mitre_id}: {mitre_refs[0].get('name', '')}")
    except Exception as e:
        logger.warning(f"[BlueTeam] MITRE KB lookup failed (non-fatal): {e}")

    if ad_check.get("ad_attack") and mitre_refs:
        ref = mitre_refs[0]
        ad_check["ad_reasoning"] += (
            f" MITRE KB reference: {ref.get('name', '')} ({ref.get('technique_id', '')}) "
            f"— {ref.get('text', '')[:200]}"
        )

    context = {
        "alert": raw_alert,
        "threat_analysis": decision_package.get("threat_analysis", {}),
        "mitre_id": mitre_id,
        "mitre_technique": decision_package.get("mitre_technique", ""),
        "red_team_validation": decision_package.get("red_team_validation", {}),
        "ad_attack_check": ad_check,
        "mitre_kb_references": mitre_refs,
    }
    task = f"""
    You are a Blue Team Detection Validator. Given the following alert and threat analysis,
    determine whether an existing Wazuh/SIEM detection rule would catch this attack pattern.

    Also consider the AD attack detection check. If 'ad_attack' is true, this alert matches
    a known Active Directory attack technique (Kerberoasting / Pass-the-Hash / DCSync).
    This is rule-based detection logic, NOT a full AD attack simulation.

    'mitre_kb_references' contains official MITRE ATT&CK technique descriptions retrieved
    from the RAG knowledge base — use them to assess detection coverage accurately.

    ```json
    {json.dumps(context, indent=2)}
    ```

    Return JSON with:
    - detection_confirmed (bool): true if existing Wazuh rules would detect this, false if a detection gap exists
    - reasoning (str): why detection is or isn't covered by existing rules
    - existing_rule_id (str or null): the rule ID that covers this, or null if no rule exists
    - ad_attack_confirmed (bool): true if this is an AD attack pattern
    - ad_technique (str or null): 'Kerberoasting', 'Pass-the-Hash', 'DCSync', or null
    """
    try:
        result = execute_agent_task(agent, task)
        blue = parse_json(result)
    except Exception as e:
        logger.error(f"Blue team validation failed: {e}")
        blue = {"detection_confirmed": False, "reasoning": f"Fallback: {e}", "existing_rule_id": None}

    # Merge AD detection into the result
    blue["ad_attack_check"] = ad_check
    if ad_check.get("ad_attack"):
        blue["ad_attack_confirmed"] = True
        blue["ad_technique"] = ad_check.get("ad_technique")
    else:
        blue.setdefault("ad_attack_confirmed", False)
        blue.setdefault("ad_technique", None)

    log_msg = f"Detection {'CONFIRMED' if blue.get('detection_confirmed') else 'GAP FOUND'} — {blue.get('reasoning', '')[:120]}"
    if ad_check.get("ad_attack"):
        log_msg += f" | AD: {ad_check.get('ad_technique')}"

    log = {
        "agent": "blue_team",
        "message": log_msg,
        "timestamp": datetime.utcnow().isoformat(),
        "level": "warning" if not blue.get("detection_confirmed") else "info",
    }

    return {"agent_logs": [log], "decision_package": {"blue_team_result": blue}, "current_node": "detection_engineer"}