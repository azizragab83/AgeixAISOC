"""
IOC Management API routes.

Endpoints:
  POST /api/ioc/from-sigma-block   — ingest IOC after a FortiGate block is confirmed
  GET  /api/ioc                    — list/filter IOCs (virtualized table feed)
  GET  /api/ioc/stats              — badge counters (active / enforced / pending)
  GET  /api/ioc/{ioc_id}           — full record incl. lifecycle timeline
  POST /api/ioc/{ioc_id}/enforce-edr — manual EDR/AV enforcement fan-out
  POST /api/ioc/{ioc_id}/whitelist — whitelist with required justification
  POST /api/ioc/{ioc_id}/expire    — force-expire + unblock everywhere
  POST /api/ioc/expire-sweep       — run the TTL expiry sweep now (also scheduled)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

try:
    from state import ws_manager
except ImportError:
    from backend.state import ws_manager

try:
    from ioc_models import ioc_store, IOC, IOCTimelineEvent
    from edr_connectors import enforce_ioc_everywhere, unenforce_ioc_everywhere
except ImportError:
    from backend.ioc_models import ioc_store, IOC, IOCTimelineEvent
    from backend.edr_connectors import enforce_ioc_everywhere, unenforce_ioc_everywhere

logger = logging.getLogger("ageixaisoc.routes.ioc")
router = APIRouter(tags=["ioc"])


# ── Request models ───────────────────────────────────────────────────────────

class SigmaBlockIngest(BaseModel):
    """Payload fired right after a FortiGate block is confirmed by SOAR."""
    sigma_rule_id: str = ""
    wazuh_alert_id: str = ""
    ip: str = ""
    domain: str = ""
    file_hash: str = ""                  # sha256 or md5 (auto-detected)
    mitre_technique: str = ""
    confidence: int = Field(default=70, ge=0, le=100)
    severity: str = "high"
    analyst_decision_id: str = ""
    approved_by: str = "system"
    ttl_hours: int = Field(default=72, ge=1, le=8760)


class WhitelistRequest(BaseModel):
    justification: str = Field(min_length=3, description="Required justification for the audit trail")
    analyst: str = "unknown"


class EnforceResult(BaseModel):
    ioc_id: str
    value: str
    blocked_on: List[str]
    results: Dict[str, Any]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _detect_type(value: str) -> Optional[str]:
    v = value.strip().lower()
    if v.count(".") == 3 and all(p.isdigit() for p in v.split(".")):
        return "ip"
    if len(v) == 64 and all(c in "0123456789abcdef" for c in v):
        return "hash_sha256"
    if len(v) == 32 and all(c in "0123456789abcdef" for c in v):
        return "hash_md5"
    if "." in v and " " not in v:
        return "domain"
    return None


def _seed_timeline(ioc: IOC, sigma_rule_id: str, alert_id: str, decision_id: str):
    """Pre-populate the kill-chain timeline for the frontend drawer."""
    now = datetime.utcnow().isoformat()
    ioc.timeline = [
        IOCTimelineEvent(step="Sigma rule fired", status="success",
                         detail=f"Rule {sigma_rule_id or 'unknown'}", timestamp=now),
        IOCTimelineEvent(step="Wazuh alert ingested", status="success",
                         detail=f"Alert {alert_id or 'unknown'}", timestamp=now),
        IOCTimelineEvent(step="Core Brain recommendation", status="success",
                         detail="block_ip recommended", timestamp=now),
        IOCTimelineEvent(step="Human approval", status="success",
                         detail=f"Decision {decision_id or 'n/a'} approved by {ioc.approved_by}", timestamp=now),
        IOCTimelineEvent(step="FortiGate block", status="success",
                         detail=f"IP blocked at perimeter", timestamp=now),
        IOCTimelineEvent(step="EDR/AV push", status="pending",
                         detail="Awaiting endpoint enforcement", timestamp=now),
    ]


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/api/ioc/from-sigma-block")
async def ioc_from_sigma_block(payload: SigmaBlockIngest, background_tasks: BackgroundTasks):
    """
    Called internally right after a FortiGate block is confirmed (n8n webhook
    callback or direct FastAPI call). Creates/updates the IOC record (dedupe
    by value), sets blocked_on=["fortigate"], then auto-triggers EDR
    enforcement as a background task.
    """
    value = (payload.ip or payload.domain or payload.file_hash or "").strip()
    if not value:
        raise HTTPException(status_code=422, detail="One of ip / domain / file_hash is required")

    ioc_type = _detect_type(value)
    if not ioc_type:
        raise HTTPException(status_code=422, detail=f"Cannot determine IOC type for value: {value}")

    now = datetime.utcnow().isoformat()
    ioc = ioc_store.get_by_value(value)
    if ioc:
        # Update existing record (dedupe by value)
        ioc.last_seen = now
        ioc.source_sigma_rule_id = payload.sigma_rule_id or ioc.source_sigma_rule_id
        ioc.source_alert_id = payload.wazuh_alert_id or ioc.source_alert_id
        ioc.source_decision_id = payload.analyst_decision_id or ioc.source_decision_id
        ioc.mitre_technique = payload.mitre_technique or ioc.mitre_technique
        ioc.confidence = max(ioc.confidence, payload.confidence)
        ioc.approved_by = payload.approved_by or ioc.approved_by
        if ioc.status == "expired":
            ioc.status = "active"
        if "fortigate" not in ioc.blocked_on:
            ioc.blocked_on.append("fortigate")
        ioc_store.add_timeline_event(ioc, "FortiGate block (re-confirmed)", "success", f"Decision {payload.analyst_decision_id}")
        ioc = ioc_store.update(ioc)
        created = False
    else:
        ioc = IOC(
            type=ioc_type,
            value=value,
            source_sigma_rule_id=payload.sigma_rule_id,
            source_alert_id=payload.wazuh_alert_id,
            source_decision_id=payload.analyst_decision_id,
            confidence=payload.confidence,
            severity=payload.severity,
            status="active",
            blocked_on=["fortigate"],
            mitre_technique=payload.mitre_technique,
            approved_by=payload.approved_by,
            ttl_hours=payload.ttl_hours,
        )
        _seed_timeline(ioc, payload.sigma_rule_id, payload.wazuh_alert_id, payload.analyst_decision_id)
        ioc = ioc_store.upsert(ioc)
        created = True

    # Auto-enforce on EDR/AV in the background (fault-tolerant fan-out)
    background_tasks.add_task(_auto_enforce, ioc.id)

    await ws_manager.broadcast("ioc_update", {
        "ioc_id": ioc.id, "value": ioc.value, "type": ioc.type,
        "status": ioc.status, "blocked_on": ioc.blocked_on,
        "created": created, "timestamp": now,
    })

    return {
        "status": "success", "ioc_id": ioc.id, "value": ioc.value,
        "type": ioc.type, "created": created, "blocked_on": ioc.blocked_on,
        "edr_enforcement": "scheduled",
    }


async def _auto_enforce(ioc_id: str):
    """Background task: push IOC to all EDR/AV connectors + broadcast progress."""
    ioc = ioc_store.get(ioc_id)
    if not ioc:
        return
    try:
        await enforce_ioc_everywhere(ioc, broadcast_fn=ws_manager.broadcast)
    except Exception as e:
        logger.error(f"Auto EDR enforcement failed for {ioc.value}: {e}")


@router.get("/api/ioc")
async def list_iocs(
    type: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    mitre: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 500,
):
    items = ioc_store.list(ioc_type=type, status=status, severity=severity,
                           mitre=mitre, search=search, limit=limit)
    return {"total": len(items), "items": [i.model_dump() for i in items]}


@router.get("/api/ioc/stats")
async def ioc_stats():
    stats = ioc_store.stats()
    stats["timestamp"] = datetime.utcnow().isoformat()
    return stats


@router.get("/api/ioc/{ioc_id}")
async def get_ioc(ioc_id: str):
    ioc = ioc_store.get(ioc_id)
    if not ioc:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")
    return ioc.model_dump()


@router.post("/api/ioc/{ioc_id}/enforce-edr")
async def enforce_edr(ioc_id: str):
    """Manual trigger: push this IOC to every configured EDR/AV connector now."""
    ioc = ioc_store.get(ioc_id)
    if not ioc:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")
    if ioc.status != "active":
        raise HTTPException(status_code=409, detail=f"IOC is {ioc.status}; only active IOCs can be enforced")

    results = await enforce_ioc_everywhere(ioc, broadcast_fn=ws_manager.broadcast)
    return EnforceResult(ioc_id=ioc.id, value=ioc.value,
                         blocked_on=ioc.blocked_on, results=results).model_dump()


@router.post("/api/ioc/{ioc_id}/whitelist")
async def whitelist_ioc(ioc_id: str, req: WhitelistRequest, background_tasks: BackgroundTasks):
    """Whitelist an IOC (with required justification) and unblock everywhere."""
    ioc = ioc_store.get(ioc_id)
    if not ioc:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")

    ioc.status = "whitelisted"
    ioc.approved_by = req.analyst
    ioc_store.add_timeline_event(ioc, "Whitelisted", "success",
                                 f"by {req.analyst}: {req.justification}")
    ioc_store.update(ioc)

    background_tasks.add_task(_unblock_background, ioc.id)

    await ws_manager.broadcast("ioc_update", {
        "ioc_id": ioc.id, "value": ioc.value, "status": "whitelisted",
        "timestamp": datetime.utcnow().isoformat(),
    })
    return {"status": "success", "ioc_id": ioc.id, "message": f"IOC {ioc.value} whitelisted; unblocking in background"}


@router.post("/api/ioc/{ioc_id}/expire")
async def force_expire(ioc_id: str, background_tasks: BackgroundTasks):
    """Force-expire an IOC and remove all blocks (FortiGate + EDR + AV)."""
    ioc = ioc_store.get(ioc_id)
    if not ioc:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")

    ioc.status = "expired"
    ioc_store.add_timeline_event(ioc, "Force expired", "success", "manual expiry by analyst")
    ioc_store.update(ioc)

    background_tasks.add_task(_unblock_background, ioc.id)

    await ws_manager.broadcast("ioc_update", {
        "ioc_id": ioc.id, "value": ioc.value, "status": "expired",
        "timestamp": datetime.utcnow().isoformat(),
    })
    return {"status": "success", "ioc_id": ioc.id, "message": f"IOC {ioc.value} expired; unblocking in background"}


async def _unblock_background(ioc_id: str):
    ioc = ioc_store.get(ioc_id)
    if not ioc:
        return
    try:
        results = await unenforce_ioc_everywhere(ioc)
        logger.info(f"Unblock sweep for {ioc.value}: {results}")
    except Exception as e:
        logger.error(f"Unblock sweep failed for {ioc.value}: {e}")


@router.post("/api/ioc/expire-sweep")
async def expire_sweep(background_tasks: BackgroundTasks):
    """Run the TTL expiry sweep now (also runs automatically every 15 min)."""
    expired = ioc_store.find_expired()
    swept = []
    for ioc in expired:
        ioc.status = "expired"
        ioc_store.add_timeline_event(ioc, "TTL expired", "success", f"ttl_hours={ioc.ttl_hours}")
        ioc_store.update(ioc)
        background_tasks.add_task(_unblock_background, ioc.id)
        swept.append({"ioc_id": ioc.id, "value": ioc.value})
    return {"status": "success", "swept": len(swept), "items": swept}