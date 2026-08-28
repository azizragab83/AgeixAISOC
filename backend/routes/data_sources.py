"""Data source routes — CMDB, Compliance, RAG knowledge sources, alert-reduction & gap-closure stats."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException

try:
    from config import settings
    from state import pending_decisions, ws_manager
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.config import settings
    from backend.state import pending_decisions, ws_manager
    from backend.rag_engine.rag_server import rag_server

logger = logging.getLogger("ageixaisoc.routes.data_sources")
router = APIRouter(tags=["data-sources"])

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# ── Background ingestion counters (real pipeline statistics) ──
_alert_reduction = {
    "raw_alerts_today": 0,
    "alerts_reached_hitl": 0,
    "date": datetime.utcnow().strftime("%Y-%m-%d"),
}
_gap_closure = {
    "gaps_detected": 0,
    "gaps_closed": 0,
    "rules_deployed": 0,
}


def register_raw_alert_ingestion():
    """Call when a raw Wazuh alert enters the webhook."""
    _alert_reduction["raw_alerts_today"] += 1


def register_hitl_reached():
    """Call when a decision package reaches pending_decisions (i.e. reached HITL)."""
    _alert_reduction["alerts_reached_hitl"] += 1


def register_gap_detected():
    _gap_closure["gaps_detected"] += 1


def register_gap_closed():
    _gap_closure["gaps_closed"] += 1
    _gap_closure["rules_deployed"] += 1


# ── Auto-resolved (is_threat: false — filtered by AI before HITL) ──
_auto_resolved: int = 0


def register_auto_resolved():
    global _auto_resolved
    _auto_resolved += 1


# ── Pipeline time registry (real MTTD / MTTR computation) ──
# decision_id -> {"alert_received_at": iso, "pipeline_completed_at": iso}
_pipeline_times: Dict[str, Dict[str, str]] = {}
# decision_id -> iso of human resolution
_resolved_times: Dict[str, str] = {}


def register_pipeline_completed(decision_id: str, alert_received_at: Optional[str]):
    """Call when a pipeline run completes and reaches HITL."""
    _pipeline_times[decision_id] = {
        "alert_received_at": alert_received_at or datetime.utcnow().isoformat(),
        "pipeline_completed_at": datetime.utcnow().isoformat(),
    }


def register_resolved(decision_id: str):
    """Call when an analyst approves/rejects a decision (resolution time)."""
    _resolved_times[decision_id] = datetime.utcnow().isoformat()


def _mean_minutes(timestamps: List[float]) -> Optional[float]:
    if not timestamps:
        return None
    return round(sum(timestamps) / len(timestamps), 1)


def compute_mttd_mttr() -> Dict[str, Any]:
    """Real MTTD/MTTR from actual pipeline run timestamps. Returns None when no data yet."""
    mttd_samples = []
    for t in _pipeline_times.values():
        try:
            received = datetime.fromisoformat(t["alert_received_at"])
            completed = datetime.fromisoformat(t["pipeline_completed_at"])
            mttd_samples.append((completed - received).total_seconds() / 60)
        except (ValueError, TypeError):
            continue

    mttr_samples = []
    for decision_id, resolved_at in _resolved_times.items():
        pipeline = _pipeline_times.get(decision_id)
        if not pipeline:
            continue
        try:
            completed = datetime.fromisoformat(pipeline["pipeline_completed_at"])
            resolved = datetime.fromisoformat(resolved_at)
            mttr_samples.append((resolved - completed).total_seconds() / 60)
        except (ValueError, TypeError):
            continue

    return {
        "mttd_min": _mean_minutes(mttd_samples),
        "mttr_min": _mean_minutes(mttr_samples),
        "mttd_samples": len(mttd_samples),
        "mttr_samples": len(mttr_samples),
        "label": "Live — computed from actual pipeline run timestamps",
    }


# ── CMDB (Static Config) ───────────────────────

@router.get("/api/cmdb/assets")
async def get_cmdb_assets():
    """Return the asset criticality map from backend/data/cmdb.json."""
    path = os.path.join(DATA_DIR, "cmdb.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="CMDB data file not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        **data,
        "label": data.get("_label", "Static Config — Not Live Discovery"),
        "trust_level": "⚪ Static Reference — Mock CMDB, not live discovery",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── NIST CSF / ISO 27001 Compliance (Static Mapping) ──────

@router.get("/api/compliance/mapping/{mitre_id}")
async def get_compliance_mapping(mitre_id: str):
    """Return NIST CSF + ISO 27001 controls for a MITRE technique (static reference)."""
    path = os.path.join(DATA_DIR, "compliance_mappings.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Compliance mappings file not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mitre_upper = mitre_id.upper()
    mapping = data.get("mapping", {}).get(mitre_upper)
    if not mapping:
        raise HTTPException(
            status_code=404,
            detail=f"No compliance mapping for {mitre_upper}. Available: {sorted(data['mapping'].keys())}"
        )
    return {
        "mitre_id": mitre_upper,
        "label": "Framework Reference — Static Mapping",
        **mapping,
    }


# ── RAG Knowledge Source Status ────────────────

@router.get("/api/knowledge-sources")
async def knowledge_sources_status():
    """Return the status of all RAG knowledge bases with trust-level labels."""
    kbs = rag_server.list_knowledge_bases()
    sources = []
    for kb in kbs:
        labels = {
            "past_incidents": "🟢 Live — populated from pipeline runs",
            "threat_intel": "🟢 Live — Feodo Tracker (15min refresh)",
            "sigma_rules": "🟢 Live — auto-generated by gap loop",
            "cve_data": "🟡 Cached — on-demand NVD lookups",
            "mitre_attack": "🟡 Cached — real MITRE STIX bundle",
            "learned_decisions": "🟢 Live — HITL analyst decisions",
            "cve_kev": "🟡 Cached — known exploited vulnerabilities",
        }
        sources.append({
            "id": kb["id"],
            "name": kb["name"],
            "description": kb["description"],
            "label": labels.get(kb["id"], "⚪ Static Reference"),
            "doc_count": rag_server.count_kb(kb["id"]),
        })
    return {"sources": sources, "timestamp": datetime.utcnow().isoformat()}


# ── Alert Reduction Stats (proves AI filters noise) ──

@router.get("/api/dashboard/alert-reduction-stats")
async def alert_reduction_stats():
    """Compare raw alerts ingested vs alerts that reached HITL. Proves noise filtering."""
    raw = _alert_reduction["raw_alerts_today"]
    hitl = _alert_reduction["alerts_reached_hitl"]
    reduction_pct = round(((raw - hitl) / raw) * 100, 1) if raw else 0.0
    return {
        "raw_alerts_today": raw,
        "alerts_reached_hitl": hitl,
        "auto_resolved_by_ai": _auto_resolved,
        "noise_filtered": raw - hitl,
        "reduction_pct": reduction_pct,
        "label": "Live — computed from actual pipeline runs",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Gap Closure Stats ──────────────────────────

@router.get("/api/dashboard/gap-closure-stats")
async def gap_closure_stats():
    """Count gaps detected vs closed from the Detection Gap Loop."""
    gaps = _gap_closure["gaps_detected"]
    closed = _gap_closure["gaps_closed"]
    open_gaps = gaps - closed

    sigma_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_rules")
    rules_on_disk = 0
    if os.path.exists(sigma_dir):
        rules_on_disk = len([f for f in os.listdir(sigma_dir) if f.endswith(".xml")])

    return {
        "gaps_detected": gaps,
        "gaps_closed": closed,
        "gaps_open": open_gaps,
        "rules_on_disk": rules_on_disk,
        "label": "Live — computed from gap loop + generated_rules/",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── MITRE ATT&CK Ingest ────────────────────────

@router.post("/api/knowledge/mitre/refresh")
async def refresh_mitre_attack():
    """Trigger one-time MITRE ATT&CK STIX download + RAG ingest."""
    try:
        from services.mitre_loader import ingest_mitre_attack
    except ImportError:
        from backend.services.mitre_loader import ingest_mitre_attack
    import asyncio
    count = await asyncio.to_thread(ingest_mitre_attack)
    if count == 0:
        raise HTTPException(status_code=502, detail="MITRE download failed — check connectivity or cache.")
    return {"status": "ok", "ingested": count, "label": "🟡 Cached — real MITRE STIX bundle", "timestamp": datetime.utcnow().isoformat()}


# ── Threat Intel Refresh ───────────────────────

@router.post("/api/knowledge/threat-intel/refresh")
async def refresh_threat_intel():
    """Trigger a Feodo Tracker pull + RAG ingest now."""
    try:
        from services.threat_intel import refresh_threat_intel
    except ImportError:
        from backend.services.threat_intel import refresh_threat_intel
    result = await refresh_threat_intel()
    return {"label": "🟢 Live — Feodo Tracker (15min refresh)", **result}


@router.get("/api/knowledge/threat-intel/status")
async def threat_intel_status():
    try:
        from services.threat_intel import get_threat_intel_status
    except ImportError:
        from backend.services.threat_intel import get_threat_intel_status
    return get_threat_intel_status()


# ── CVE Ingest (on-demand from forensics) ──────

@router.post("/api/knowledge/cve/ingest")
async def ingest_cves(body: Dict[str, Any]):
    """Ingest CVEs extracted from a forensics text blob / incident id."""
    forensics_text = body.get("text", "")
    try:
        from services.cve_loader import ingest_cves_for_forensics
    except ImportError:
        from backend.services.cve_loader import ingest_cves_for_forensics
    count = await ingest_cves_for_forensics(forensics_text)
    return {"status": "ok" if count else "no_cves", "ingested": count, "label": "🟡 Cached — on-demand NVD lookups"}