"""Threat Intelligence endpoints — MITRE ATT&CK coverage based on real alert data."""

import logging
import os
import re
from datetime import datetime

from fastapi import APIRouter

try:
    from state import pending_decisions, decision_history
except ImportError:
    from backend.state import pending_decisions, decision_history

logger = logging.getLogger("ageixaisoc.routes.ti")
router = APIRouter(tags=["ti"])

MITRE_FRAMEWORK = [
    {"id": "T1078", "name": "Valid Accounts", "tactic": "Defense Evasion"},
    {"id": "T1059", "name": "Command & Scripting", "tactic": "Execution"},
    {"id": "T1547", "name": "Boot/Logon Autostart", "tactic": "Persistence"},
    {"id": "T1003", "name": "OS Credential Dumping", "tactic": "Credential Access"},
    {"id": "T1485", "name": "Data Destruction", "tactic": "Impact"},
    {"id": "T1566", "name": "Phishing", "tactic": "Initial Access"},
    {"id": "T1021", "name": "Remote Services", "tactic": "Lateral Movement"},
    {"id": "T1047", "name": "WMI", "tactic": "Execution"},
    {"id": "T1053", "name": "Scheduled Task", "tactic": "Privilege Escalation"},
    {"id": "T1098", "name": "Account Manipulation", "tactic": "Persistence"},
    {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
    {"id": "T1133", "name": "External Remote Services", "tactic": "Initial Access"},
    {"id": "T1071", "name": "Application Layer Protocol", "tactic": "Command & Control"},
    {"id": "T1574", "name": "Hijack Execution Flow", "tactic": "Persistence"},
    {"id": "T1055", "name": "Process Injection", "tactic": "Defense Evasion"},
    {"id": "T1569", "name": "System Services", "tactic": "Execution"},
    {"id": "T1036", "name": "Masquerading", "tactic": "Defense Evasion"},
    {"id": "T1548", "name": "Abuse Elevation Control", "tactic": "Privilege Escalation"},
    {"id": "T1550", "name": "Use Alternate Auth Material", "tactic": "Lateral Movement"},
    {"id": "T1041", "name": "Exfiltration Over C2", "tactic": "Exfiltration"},
]


def _all_packages():
    """Every decision package ever produced: pending + resolved history."""
    seen = set()
    for pkg in list(pending_decisions.values()) + list(decision_history):
        did = pkg.get("decision_id") or pkg.get("alert_id") or id(pkg)
        if did in seen:
            continue
        seen.add(did)
        yield pkg


def _technique_ids_covered_by_rules() -> set:
    """MITRE techniques referenced by AI-generated rules in generated_rules/."""
    covered = set()
    rules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_rules")
    if not os.path.exists(rules_dir):
        return covered
    for f in os.listdir(rules_dir):
        if not f.endswith(".xml"):
            continue
        try:
            content = open(os.path.join(rules_dir, f), "r", encoding="utf-8").read()
        except Exception:
            continue
        for mid in re.findall(r"<id>(T\d+(?:\.\d+)?)</id>", content):
            base = mid.split(".")[0]
            covered.add(mid)
            covered.add(base)
    return covered


@router.get("/api/ti/coverage")
async def ti_coverage():
    observed_ids = set()
    for pkg in _all_packages():
        mid = pkg.get("mitre_id", "")
        if mid:
            observed_ids.add(str(mid))
        ta = pkg.get("threat_analysis", {}) or {}
        tmid = ta.get("mitre_attack_id", "")
        if tmid:
            observed_ids.add(str(tmid))
        raw = pkg.get("raw_alert", {}) or {}
        decoded = raw.get("decoded", {}) or {}
        for dmid in (decoded.get("mitre_id") or []):
            observed_ids.add(str(dmid))

    # Normalize sub-techniques to base technique (T1550.002 → T1550) for framework matching
    normalized = set()
    for mid in observed_ids:
        normalized.add(mid.split(".")[0] if "." in mid else mid)
    observed_ids = normalized

    covered_ids = _technique_ids_covered_by_rules()

    techniques = []
    covered_count = 0
    observed_count = 0
    for t in MITRE_FRAMEWORK:
        observed = t["id"] in observed_ids
        covered = t["id"] in covered_ids
        status = "covered" if covered else ("observed" if observed else "unmonitored")
        if observed:
            observed_count += 1
        if covered:
            covered_count += 1
        techniques.append({**t, "coverage": 100 if covered else (50 if observed else 0), "observed": observed, "covered": covered, "status": status})

    total = len(MITRE_FRAMEWORK)
    coverage_pct = round((covered_count / total) * 100) if total else 0

    iocs = []
    for pkg in _all_packages():
        src_ip = pkg.get("raw_alert", {}).get("source_ip", "")
        if src_ip and src_ip != "unknown":
            iocs.append(src_ip)
        hunt = pkg.get("threat_hunt_results", {}) or {}
        for ioc in hunt.get("additional_iocs", []):
            if isinstance(ioc, str):
                iocs.append(ioc)

    return {
        "techniques": techniques,
        "coverage_pct": coverage_pct,
        "covered": covered_count,
        "observed_count": observed_count,
        "total": total,
        "observed": list(observed_ids),
        "covered_techniques": list(covered_ids),
        "iocs": list(set(iocs)),
        "timestamp": datetime.utcnow().isoformat(),
    }
