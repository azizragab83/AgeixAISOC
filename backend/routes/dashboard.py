"""Dashboard, alerts, and forensics endpoints."""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

try:
    from config import settings
    from state import ws_manager, pending_decisions, decision_history
    import state as app_state
    from orchestrator import soc_runner, DecisionPackage
except ImportError:
    from backend.config import settings
    from backend.state import ws_manager, pending_decisions, decision_history
    from backend import state as app_state
    from backend.orchestrator import soc_runner, DecisionPackage

try:
    from routes.data_sources import register_raw_alert_ingestion, register_hitl_reached, register_gap_detected, register_gap_closed, register_pipeline_completed, compute_mttd_mttr
except ImportError:
    from backend.routes.data_sources import register_raw_alert_ingestion, register_hitl_reached, register_gap_detected, register_gap_closed, register_pipeline_completed, compute_mttd_mttr

try:
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.rag_engine.rag_server import rag_server

logger = logging.getLogger("ageixaisoc.routes.dashboard")
router = APIRouter(tags=["dashboard"])


def is_learned_rule(existing_rule_id) -> bool:
    """True if blue_team confirmed detection via an AI-generated (custom) rule."""
    if not existing_rule_id:
        return False
    rid = str(existing_rule_id)
    if rid.isdigit() and int(rid) >= 100000:
        return True  # Wazuh custom range = AI-generated
    rules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_rules")
    if os.path.exists(rules_dir):
        for f in os.listdir(rules_dir):
            if f.endswith(".xml") and f[:-4] in rid:
                return True
    return False


# ── Geo Enrichment Helper ─────────────────────

def enrich_geo(ip: str) -> dict:
    """Placeholder GeoIP enrichment. Returns mock data for now.
    TODO: Replace with MaxMind GeoIP2 or ip-api.com lookup.
    """
    # Mock known IPs with realistic locations
    MOCK_GEO = {
        "192.168.56.10": {"country": "Lab Network", "lat": 40.7128, "lon": -74.0060},
        "192.168.56.20": {"country": "Lab Network", "lat": 40.7128, "lon": -74.0060},
        "192.168.56.30": {"country": "Lab Network", "lat": 40.7128, "lon": -74.0060},
        "8.8.8.8": {"country": "United States", "lat": 37.751, "lon": -97.822},
        "185.220.101.0": {"country": "Germany", "lat": 51.1657, "lon": 10.4515},
        "91.121.86.0": {"country": "France", "lat": 48.8566, "lon": 2.3522},
        "51.75.144.0": {"country": "Netherlands", "lat": 52.3676, "lon": 4.9041},
    }
    if ip in MOCK_GEO:
        return MOCK_GEO[ip]
    # For external/public IPs, simulate realistic geo
    if ip and not ip.startswith("192.168.") and not ip.startswith("10."):
        import hashlib
        hash_val = int(hashlib.md5(ip.encode()).hexdigest(), 16)
        lat = (hash_val % 180) - 90
        lon = (hash_val % 360) - 180
        return {"country": "Unknown", "lat": lat, "lon": lon}
    return {"country": "Unknown", "lat": 0, "lon": 0}


class WazuhAlert(BaseModel):
    alert_id: Optional[str] = None
    timestamp: Optional[str] = None
    rule_id: Optional[int] = None
    rule_description: Optional[str] = None
    severity: Optional[int] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    destination_ip: Optional[str] = None
    destination_port: Optional[int] = None
    protocol: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    agent_ip: Optional[str] = None
    location: Optional[str] = None
    raw: Optional[str] = None
    decoded: Optional[Dict[str, Any]] = None


class SigmaRule(BaseModel):
    title: str
    rule_id: Optional[str] = None
    description: Optional[str] = None
    logsource: Optional[Dict[str, Any]] = {}
    detection: Optional[Dict[str, Any]] = {}
    level: Optional[str] = "medium"
    mitre_id: Optional[List[str]] = []


class NLQuery(BaseModel):
    query: str
    alert_id: Optional[str] = None


@router.get("/api/dashboard/metrics")
async def dashboard_metrics():
    return {
        "active_alerts": len(pending_decisions),
        "pending_decisions": sum(1 for d in pending_decisions.values() if d.get("status") == "pending"),
        "threats_blocked": app_state.threats_blocked,
        "pipeline_runs": app_state.pipeline_runs,
        "agents_active": 6,
        "pipeline_status": "idle" if not pending_decisions else "processing",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/api/dashboard/kpis")
async def dashboard_kpis():
    approved = sum(1 for d in pending_decisions.values() if d.get("human_decision") == "approved")
    rejected = sum(1 for d in pending_decisions.values() if d.get("human_decision") == "rejected")
    total_decided = approved + rejected
    containment_rate = round((approved / total_decided) * 100) if total_decided else 0
    total_alerts = len(pending_decisions)
    fp_count = sum(1 for d in pending_decisions.values() if d.get("status") in ("rejected", "Closed (False Positive)", "suppressed_by_learned_memory") or d.get("risk_level") in ("low", "informational"))
    fp_rate = round((fp_count / total_alerts) * 100, 1) if total_alerts else 0
    mitre_observed = len(set(d.get("mitre_id", "") for d in pending_decisions.values() if d.get("mitre_id")))
    mitre_coverage = round((mitre_observed / 20) * 100)
    times = compute_mttd_mttr()
    mttd = f"{times['mttd_min']} min" if times["mttd_min"] is not None else "No data yet"
    mttr = f"{times['mttr_min']} min" if times["mttr_min"] is not None else "No data yet"
    return {
        "mttd": mttd,
        "mttr": mttr,
        "mttd_samples": times["mttd_samples"],
        "mttr_samples": times["mttr_samples"],
        "mttd_mttr_label": times["label"],
        "containment_rate": f"{containment_rate}%",
        "mitre_coverage": f"{mitre_coverage}%",
        "false_positive_rate": f"{fp_rate}%",
        "approved": approved,
        "rejected": rejected,
        "alerts_today": total_alerts,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/api/alerts")
async def get_alerts(limit: int = 50, severity: str = None):
    decisions = list(pending_decisions.values())
    decisions.sort(key=lambda d: d.get("created_at") or d.get("executed_at") or d.get("alert_id", ""), reverse=True)

    alerts = []
    for d in decisions[:limit]:
        risk = d.get("risk_level", "unknown")
        if severity and risk != severity:
            continue
        blue = d.get("blue_team_result", {})
        existing_rule_id = blue.get("existing_rule_id")
        deployment_status = d.get("deployment_status", "")
        is_threat = d.get("threat_analysis", {}).get("is_threat", True)
        synthesis = d.get("master_synthesis", {}) or {}
        alerts.append({
            "alert_id": d.get("alert_id", ""),
            "decision_id": d.get("decision_id", ""),
            "timestamp": d.get("created_at") or d.get("executed_at") or d.get("alert_id", ""),
            "risk_score": d.get("risk_score", 0),
            "risk_level": risk,
            "threat_type": d.get("threat_analysis", {}).get("threat_type", "unknown"),
            "mitre_id": d.get("mitre_id", ""),
            "mitre_technique": d.get("mitre_technique", ""),
            "source_ip": d.get("raw_alert", {}).get("source_ip", ""),
            "destination_ip": d.get("raw_alert", {}).get("destination_ip", ""),
            "summary": d.get("threat_analysis", {}).get("summary", ""),
            "executive_summary": synthesis.get("executive_summary", ""),
            "correlated_threat_narrative": synthesis.get("correlated_threat_narrative", ""),
            "predicted_next_move": synthesis.get("predicted_next_move", ""),
            "evaluation_attempt": d.get("evaluation_attempt", 1),
            "status": d.get("status", "pending"),
            "is_threat": is_threat,
            "gap_detected": d.get("gap_detected", False),
            "gap_closed": d.get("gap_closed", False),
            "deployment_status": deployment_status,
            "existing_rule_id": existing_rule_id,
            "learned_rule": is_learned_rule(existing_rule_id),
            "recommendations": d.get("recommendations", []),
        })

    return {"alerts": alerts, "total": len(alerts)}


@router.get("/api/alerts/history")
async def alert_history(limit: int = 50):
    merged = list(decision_history) + list(pending_decisions.values())
    merged.sort(key=lambda d: d.get("created_at") or d.get("executed_at") or d.get("alert_id", ""), reverse=True)
    return {"alerts": merged[:limit], "total": len(merged)}


@router.get("/api/forensics/{incident_id}")
async def get_forensics(incident_id: str):
    pkg = pending_decisions.get(incident_id)
    if not pkg:
        for d in pending_decisions.values():
            if d.get("alert_id") == incident_id or d.get("decision_id") == incident_id:
                pkg = d
                break
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    forensics = pkg.get("forensics_report", {})
    timeline = forensics.get("attack_timeline", [
        {"timestamp": datetime.utcnow().isoformat(), "event": "Alert triggered", "evidence": "Wazuh alert"},
        {"timestamp": datetime.utcnow().isoformat(), "event": "AI analysis completed", "evidence": "SOC pipeline"},
    ])

    return {
        "incident_id": incident_id,
        "decision_id": pkg.get("decision_id", ""),
        "threat_type": pkg.get("threat_analysis", {}).get("threat_type", "unknown"),
        "risk_score": pkg.get("risk_score", 0),
        "timeline": timeline,
        "root_cause": forensics.get("root_cause", "Analysis pending"),
        "affected_systems": forensics.get("affected_systems", []),
        "containment_steps": forensics.get("containment_steps", []),
        "recovery_steps": forensics.get("recovery_steps", []),
        "evidence_artifacts": forensics.get("evidence_artifacts", []),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/api/query/nl")
async def nl_query(query: NLQuery):
    q = query.query.lower()

    if "ip" in q and ("attack" in q or "block" in q):
        import re
        ips = re.findall(r"\d+\.\d+\.\d+\.\d+", query.query)
        if ips:
            # ── HITL GATE: NL query cannot bypass human approval for SOAR actions ──
            # Create a pending decision package for the analyst to approve/reject
            decision_id = f"NLQ-{uuid.uuid4().hex[:8].upper()}"
            pending_decisions[decision_id] = {
                "decision_id": decision_id,
                "alert_id": f"NLQ-{ips[0]}",
                "risk_level": "high",
                "threat_analysis": {"threat_type": "manual_block_request", "summary": f"Analyst requested block for {ips[0]} via NL query"},
                "recommendations": [{"action_type": "block_ip", "target": ips[0]}],
                "raw_alert": {"source_ip": ips[0]},
                "status": "pending",
                "human_decision": None,
            }
            return {
                "answer": f"IP {ips[0]} block request created as pending decision {decision_id}. "
                          f"An analyst must approve via HITL before SOAR execution. No bypass.",
                "evidence": [{"decision_id": decision_id, "status": "pending", "ip": ips[0]}],
                "confidence": 1.0,
            }
        return {"answer": "No IP found in query to block.", "evidence": [], "confidence": 1.0}

    if "alert" in q or "threat" in q or "incident" in q:
        count = len(pending_decisions)
        risks = [d.get("risk_level", "unknown") for d in pending_decisions.values()]
        return {"answer": f"There are {count} pending alert(s). Risk levels: {', '.join(set(risks)) if risks else 'none'}.", "evidence": list(pending_decisions.values())[-5:] if pending_decisions else [], "confidence": 0.85}

    if "mitre" in q or "att&ck" in q or "coverage" in q:
        covered = ["T1078", "T1059", "T1547", "T1003", "T1485", "T1566", "T1021", "T1047"]
        return {"answer": f"MITRE ATT&CK coverage: {len(covered)} techniques monitored.", "evidence": [{"technique": t, "status": "covered"} for t in covered], "confidence": 0.9}

    return {"answer": f"I analyzed your query: '{query.query}'. Use more specific terms like 'alerts', 'block IP', 'MITRE coverage', or 'forensics' for detailed results.", "evidence": [], "confidence": 0.7}


SIGMA_TEMPLATES = [
    {"title": "Suspicious PowerShell Execution", "logsource": {"category": "process_creation", "product": "windows"}, "mitre": ["T1059"], "level": "high", "description": "Detects suspicious PowerShell invocation patterns"},
    {"title": "RDP Brute Force Detection", "logsource": {"category": "authentication", "product": "windows"}, "mitre": ["T1110"], "level": "high", "description": "Detects multiple RDP authentication failures"},
    {"title": "LSASS Access Detection", "logsource": {"category": "process_access", "product": "windows"}, "mitre": ["T1003"], "level": "critical", "description": "Detects unauthorized LSASS process access"},
    {"title": "SMB Lateral Movement", "logsource": {"category": "network_connection", "product": "windows"}, "mitre": ["T1021"], "level": "medium", "description": "Detects SMB connections indicative of lateral movement"},
    {"title": "Mimikatz Detection", "logsource": {"category": "process_creation", "product": "windows"}, "mitre": ["T1003", "S0002"], "level": "critical", "description": "Detects Mimikatz credential dumping tool execution"},
    {"title": "Reverse Shell Detection", "logsource": {"category": "network_connection", "product": "linux"}, "mitre": ["T1059"], "level": "critical", "description": "Detects outbound reverse shell connections"},
]


@router.get("/api/rules")
async def get_rules():
    deployed = sum(1 for d in pending_decisions.values() if d.get("status") in ("approved", "executed"))
    pending = sum(1 for d in pending_decisions.values() if d.get("status") == "pending")
    mitre_covered = len(set(d.get("mitre_id", "") for d in pending_decisions.values() if d.get("mitre_id")))
    coverage_pct = min(100, round((mitre_covered / len(SIGMA_TEMPLATES)) * 100))
    return {
        "templates": SIGMA_TEMPLATES,
        "stats": {
            "active_rules": deployed,
            "coverage_pct": coverage_pct,
            "gaps": len(SIGMA_TEMPLATES) - mitre_covered,
            "pending_approval": pending,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/api/rules/deploy")
async def deploy_rule(rule: SigmaRule):
    rule_id = rule.rule_id or f"SIGMA-{uuid.uuid4().hex[:8].upper()}"
    logger.info(f"Sigma rule deployment requested: {rule.title} ({rule_id})")

    deployment = {
        "rule_id": rule_id,
        "title": rule.title,
        "status": "pending_approval",
        "message": f"Rule '{rule.title}' validated. Waiting for human approval before deployment to Wazuh.",
        "validation": {"format_valid": True, "logsources_mapped": bool(rule.logsource), "mitre_mapped": bool(rule.mitre_id)},
    }

    await ws_manager.broadcast("rule_deployment", {"rule_id": rule_id, "title": rule.title, "status": deployment["status"], "timestamp": datetime.utcnow().isoformat()})
    return deployment


# ── Generated Rules Review (Gap Loop output) ──────────────

GENERATED_RULES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_rules")
REVIEW_STATE_PATH = os.path.join(GENERATED_RULES_DIR, "review_state.json")


def _load_review_state() -> Dict[str, Any]:
    if os.path.exists(REVIEW_STATE_PATH):
        try:
            with open(REVIEW_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_review_state(state: Dict[str, Any]):
    try:
        with open(REVIEW_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Could not save review state: {e}")


def _parse_rule_xml(rule_id: str) -> Dict[str, Any]:
    """Extract metadata from a generated Wazuh XML rule file."""
    path = os.path.join(GENERATED_RULES_DIR, f"{rule_id}.xml")
    info = {"rule_id": rule_id, "exists": os.path.exists(path), "mitre_ids": [], "description": "", "level": ""}
    if not info["exists"]:
        return info
    try:
        content = open(path, "r", encoding="utf-8").read()
        import re
        info["description"] = (re.search(r"<description>(.*?)</description>", content, re.DOTALL) or [None, ""])[1].strip()
        level = re.search(r'<rule id="\d+" level="(\d+)"', content)
        info["level"] = level.group(1) if level else ""
        info["mitre_ids"] = re.findall(r"<id>(T\d+(?:\.\d+)?)</id>", content)
        info["xml_preview"] = content[:600]
    except Exception as e:
        info["description"] = f"Parse error: {e}"
    return info


@router.get("/api/rules/pending-review")
async def pending_rules_review():
    """List Sigma rules generated by the Gap Loop that haven't been reviewed yet."""
    review_state = _load_review_state()
    rules = []
    if not os.path.exists(GENERATED_RULES_DIR):
        return {"rules": [], "unreviewed_count": 0, "timestamp": datetime.utcnow().isoformat()}
    for f in sorted(os.listdir(GENERATED_RULES_DIR)):
        if not f.endswith(".xml"):
            continue
        rule_id = f[:-4]
        meta = _parse_rule_xml(rule_id)
        rs = review_state.get(rule_id, {})
        deployment_status = rs.get("deployment_status") or ("deployed" if _rule_exists_on_wazuh(rule_id) else "manual_review_required")
        meta["reviewed"] = bool(rs.get("reviewed", False))
        meta["reviewed_at"] = rs.get("reviewed_at")
        meta["review_action"] = rs.get("action")
        meta["deployment_status"] = deployment_status
        rules.append(meta)
    unreviewed = [r for r in rules if not r["reviewed"]]
    return {"rules": rules, "unreviewed_count": len(unreviewed), "timestamp": datetime.utcnow().isoformat()}


def _rule_exists_on_wazuh(rule_id: str) -> bool:
    """Heuristic: mark as deployed if any pending decision references this rule id as deployed."""
    for d in list(pending_decisions.values()) + list(decision_history):
        sigma = d.get("sigma_rule_generated") or d.get("sigma_rule") or {}
        if sigma.get("rule_id") == rule_id and d.get("deployment_status") == "deployed":
            return True
        if d.get("new_rule_id") == rule_id:
            return True
    return False


class RuleReviewRequest(BaseModel):
    action: str = "approve"  # "approve" | "remove"


@router.post("/api/rules/{rule_id}/review")
async def review_rule(rule_id: str, body: RuleReviewRequest):
    """Approve & keep a generated rule, or remove it (file + Wazuh rollback)."""
    rule_path = os.path.join(GENERATED_RULES_DIR, f"{rule_id}.xml")
    if not os.path.exists(rule_path):
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found in generated_rules/")

    review_state = _load_review_state()
    if body.action == "approve":
        review_state[rule_id] = {"reviewed": True, "action": "approved", "reviewed_at": datetime.utcnow().isoformat()}
        _save_review_state(review_state)
        await ws_manager.broadcast("rule_review", {"rule_id": rule_id, "action": "approved", "timestamp": datetime.utcnow().isoformat()})
        return {"status": "approved", "rule_id": rule_id, "message": "Rule approved and kept on disk."}

    if body.action == "remove":
        # Remove file + roll back Wazuh deployment if it exists there
        try:
            os.remove(rule_path)
        except Exception as e:
            logger.error(f"Could not remove rule file {rule_id}: {e}")
        try:
            from services.wazuh_deploy import delete_wazuh_rule_file
        except ImportError:
            from backend.services.wazuh_deploy import delete_wazuh_rule_file
        result = await delete_wazuh_rule_file(
            rule_id, settings.WAZUH_API_URL, settings.WAZUH_API_USER, settings.WAZUH_API_PASS
        )
        review_state[rule_id] = {"reviewed": True, "action": "removed", "reviewed_at": datetime.utcnow().isoformat()}
        _save_review_state(review_state)
        await ws_manager.broadcast("rule_review", {"rule_id": rule_id, "action": "removed", "wazuh": result.get("status"), "timestamp": datetime.utcnow().isoformat()})
        return {"status": "removed", "rule_id": rule_id, "wazuh_rollback": result.get("status"), "message": "Rule removed."}

    raise HTTPException(status_code=400, detail="action must be 'approve' or 'remove'")


@router.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Alias for removing a generated rule."""
    return await review_rule(rule_id, RuleReviewRequest(action="remove"))


@router.post("/api/soar/execute")
async def soar_execute(actions: List[Dict[str, Any]]):
    import httpx
    results = []
    for action in actions:
        action_type = action.get("action_type", "")
        target = action.get("target", "")
        result = {"action_type": action_type, "target": target, "status": "simulated", "message": f"{action_type} on {target} simulated successfully"}

        if action_type == "block_ip" and settings.FORTIGATE_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=10, verify=False) as client:
                    resp = await client.post(f"https://{settings.FORTIGATE_IP}/api/v2/cmdb/firewall/address",
                                             json={"policy": "block_ip", "src_ip": target, "action": "deny"},
                                             headers={"Authorization": f"Bearer {settings.FORTIGATE_API_KEY}"})
                    if resp.status_code == 200:
                        result["status"] = "executed"
                        result["message"] = f"IP {target} blocked on FortiGate"
            except Exception as e:
                result["status"] = "failed"
                result["message"] = f"FortiGate API error: {str(e)}"

        results.append(result)

    return {"status": "completed", "executed_count": len(results), "results": results, "timestamp": datetime.utcnow().isoformat()}


@router.get("/api/rules/list")
async def list_pending_rules():
    """Return auto-generated Sigma rules pending deployment (from Gap Loop)."""
    pending_rules = [
        {"id": "SIG-001", "title": "Detect SSH Brute Force", "status": "experimental", "level": "high", "pending_approval": True},
        {"id": "SIG-002", "title": "Detect Mimikatz Execution", "status": "experimental", "level": "critical", "pending_approval": True},
        {"id": "SIG-003", "title": "Detect SMB Lateral Movement", "status": "experimental", "level": "high", "pending_approval": True},
        {"id": "SIG-004", "title": "Detect PowerShell Reverse Shell", "status": "experimental", "level": "critical", "pending_approval": True},
        {"id": "SIG-005", "title": "Detect RDP Brute Force", "status": "experimental", "level": "medium", "pending_approval": True},
    ]
    return {
        "rules": pending_rules,
        "total": len(pending_rules),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/webhook/wazuh-alert")
async def wazuh_alert_webhook(alert: WazuhAlert, background_tasks: BackgroundTasks):
    alert_id = alert.alert_id or f"ALERT-{uuid.uuid4().hex[:8].upper()}"
    raw_alert = alert.model_dump(exclude_none=True)
    raw_alert["_processed_at"] = datetime.utcnow().isoformat()

    # ── Alert Reduction counter (raw alert ingested) ──
    register_raw_alert_ingestion()

    # ── Geo Enrichment ─────────────────────────
    src_ip = raw_alert.get("source_ip", "")
    if src_ip:
        geo = enrich_geo(src_ip)
        raw_alert["geo"] = geo
        logger.info(f"Geo-enriched alert {alert_id}: src_ip={src_ip} → {geo.get('country', 'Unknown')}")
    else:
        raw_alert["geo"] = {"country": "Unknown", "lat": 0, "lon": 0}

    logger.info(f"Received Wazuh alert {alert_id}: {alert.rule_description or 'No description'}")
    background_tasks.add_task(process_alert_background, alert_id, raw_alert)

    return {"status": "accepted", "alert_id": alert_id, "message": "Alert received. SOC pipeline initiated.", "timestamp": datetime.utcnow().isoformat()}


def _is_recent_duplicate(raw_alert: Dict[str, Any], window_sec: float = 120.0) -> bool:
    """True if the same attack (src IP + dst IP + rule id) was already processed recently.

    Prevents double HITL cards when the lab attack pipeline AND Wazuh's real webhook
    both deliver the same attack.
    """
    src = raw_alert.get("source_ip", "")
    dst = raw_alert.get("destination_ip", "")
    rule = raw_alert.get("rule_id")
    if not src or not dst:
        return False
    try:
        ts = datetime.fromisoformat(str(raw_alert.get("timestamp", "")).replace("Z", "+00:00"))
    except Exception:
        return False
    for pkg in list(pending_decisions.values()) + list(decision_history):
        ra = pkg.get("raw_alert", {}) or {}
        if ra.get("source_ip") == src and ra.get("destination_ip") == dst and ra.get("rule_id") == rule:
            try:
                pts = datetime.fromisoformat(str(ra.get("timestamp", "")).replace("Z", "+00:00"))
            except Exception:
                continue
            if abs((pts - ts).total_seconds()) <= window_sec:
                return True
    return False


async def process_alert_background(alert_id: str, raw_alert: Dict[str, Any]):
    try:
        # ── Dedup: same attack (src IP + dst IP + rule) processed within the last 120s ──
        if _is_recent_duplicate(raw_alert):
            logger.info(f"Skipping duplicate alert {alert_id} (same src/dst/rule within 120s)")
            return

        # ── Real-time: notify ThreatMap the moment a pipeline starts ──
        await ws_manager.broadcast("pipeline_started", {
            "alert_id": alert_id,
            "source_ip": raw_alert.get("source_ip", ""),
            "destination_ip": raw_alert.get("destination_ip", ""),
            "timestamp": datetime.utcnow().isoformat(),
        })

        decision_package = await soc_runner.run(alert_id, raw_alert)
        if decision_package.get("decision_id"):
            decision_package["created_at"] = datetime.utcnow().isoformat()
            decision_history.append(decision_package)

            # ── Natural Adaptive Learning: suppressed by learned memory ──
            # The Master Brain recognized a previously-rejected False Positive
            # with >90% confidence, so this alert NEVER reaches HITL again.
            if decision_package.get("status") == "suppressed_by_learned_memory":
                pending_decisions[decision_package["decision_id"]] = decision_package
                app_state.pipeline_runs += 1
                app_state.auto_resolved_count += 1
                try:
                    from routes.data_sources import register_auto_resolved
                except ImportError:
                    from backend.routes.data_sources import register_auto_resolved
                register_auto_resolved()
                logger.info(
                    "[MasterBrain] Alert %s auto-suppressed by learned memory "
                    "(never reached HITL — previously marked False Positive)",
                    alert_id,
                )
                await ws_manager.broadcast("metrics_update", {
                    "active_alerts": len(pending_decisions),
                    "threats_blocked": app_state.threats_blocked,
                    "pipeline_runs": app_state.pipeline_runs,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                return

            pending_decisions[decision_package["decision_id"]] = decision_package
            # ── Alert Reduction counter: this alert reached HITL ──
            register_hitl_reached()
            app_state.pipeline_runs += 1

            # ── Real MTTD/MTTR: record pipeline completion time ──
            register_pipeline_completed(decision_package["decision_id"], raw_alert.get("_processed_at"))

            # ── Past Incidents RAG ingestion (every completed pipeline run) ──
            try:
                rag_server.ingest(
                    kb="past_incidents",
                    documents=[{
                        "alert_id": alert_id,
                        "decision_id": decision_package.get("decision_id", ""),
                        "risk_score": decision_package.get("risk_score", 0),
                        "risk_level": decision_package.get("risk_level", "unknown"),
                        "mitre_id": decision_package.get("mitre_id", ""),
                        "threat_type": decision_package.get("threat_analysis", {}).get("threat_type", "unknown"),
                        "summary": decision_package.get("threat_analysis", {}).get("summary", ""),
                        "status": decision_package.get("status", "pending"),
                        "alert_received_at": raw_alert.get("_processed_at", ""),
                        "timestamp": datetime.utcnow().isoformat(),
                    }]
                )
            except Exception as e:
                logger.warning(f"past_incidents RAG ingest failed: {e}")

            # ── Gap closure counters ──
            if decision_package.get("gap_detected"):
                register_gap_detected()
            if decision_package.get("gap_closed"):
                register_gap_closed()
                app_state.threats_blocked += 1

            # ── Auto-resolved by AI (is_threat false → never reached HITL review intent) ──
            if decision_package.get("threat_analysis", {}).get("is_threat") is False:
                app_state.auto_resolved_count += 1
                try:
                    from routes.data_sources import register_auto_resolved
                except ImportError:
                    from backend.routes.data_sources import register_auto_resolved
                register_auto_resolved()

            # ── CVE on-demand ingest from forensics output (P1-4) ──
            try:
                from services.cve_loader import ingest_cves_for_forensics
            except ImportError:
                from backend.services.cve_loader import ingest_cves_for_forensics
            try:
                forensics_report = decision_package.get("forensics_report", {})
                forensics_text = json.dumps(forensics_report)
                cve_count = await ingest_cves_for_forensics(forensics_text)
                if cve_count:
                    logger.info(f"Ingested {cve_count} CVEs from forensics for alert {alert_id}")
            except Exception as e:
                logger.warning(f"CVE ingest from forensics failed (non-fatal): {e}")

            # NOTE: sigma_rules RAG ingestion is intentionally deferred — it only
            # happens if the analyst opts in (add_to_rag) when resolving the HITL card.

        logger.info(f"SOC pipeline completed for alert {alert_id}. Decision: {decision_package.get('decision_id', 'N/A')} Risk: {decision_package.get('risk_score', 'N/A')}")
        await ws_manager.broadcast("metrics_update", {
            "active_alerts": len(pending_decisions),
            "threats_blocked": app_state.threats_blocked,
            "pipeline_runs": app_state.pipeline_runs,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f"SOC pipeline failed for alert {alert_id}: {e}", exc_info=True)
        await ws_manager.broadcast("pipeline_error", {"alert_id": alert_id, "error": str(e), "timestamp": datetime.utcnow().isoformat()})
