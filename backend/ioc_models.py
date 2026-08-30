"""
IOC (Indicator of Compromise) data model and persistent store.

First-class IOC records created when a Sigma rule fires in Wazuh and the
resulting FortiGate IP block is approved by a human analyst. Stored as JSON
on disk (consistent with the project's data/*.json pattern) — swap for
SQLModel/Postgres later without changing the API surface.
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("ageixaisoc.ioc")

IOCType = Literal["ip", "domain", "hash_sha256", "hash_md5"]
IOCStatus = Literal["active", "expired", "whitelisted"]
EnforcementLayer = Literal["fortigate", "edr", "av"]


class IOCTimelineEvent(BaseModel):
    """One step in the IOC's lifecycle (Sigma fired -> ... -> EDR push)."""
    step: str
    status: Literal["pending", "success", "failed", "skipped"] = "pending"
    detail: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class IOC(BaseModel):
    id: str = Field(default_factory=lambda: f"ioc-{uuid.uuid4().hex[:12]}")
    type: IOCType
    value: str
    source_sigma_rule_id: str = ""
    source_alert_id: str = ""            # Wazuh alert id
    source_decision_id: str = ""         # HITL decision id
    first_seen: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_seen: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: int = 50                 # 0-100
    severity: str = "medium"             # critical | high | medium | low
    status: IOCStatus = "active"
    blocked_on: List[EnforcementLayer] = []
    mitre_technique: str = ""
    approved_by: str = ""                # analyst name
    ttl_hours: int = 72                  # auto-expire
    timeline: List[IOCTimelineEvent] = []
    enrichment: Dict[str, Any] = {}      # OTX / OSINT cross-check results

    def is_expired(self) -> bool:
        if self.status != "active":
            return False
        try:
            expires = datetime.fromisoformat(self.last_seen) + timedelta(hours=self.ttl_hours)
            return datetime.utcnow() >= expires
        except Exception:
            return False


class IOCStore:
    """Thread-safe JSON-file-backed IOC store with dedupe by value."""

    def __init__(self, path: str = None):
        base = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(base, "data", "iocs.json")
        self._lock = threading.RLock()
        self._iocs: Dict[str, IOC] = {}   # keyed by value (dedupe)
        self._load()

    # ── Persistence ─────────────────────────────
    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for item in raw:
                    ioc = IOC(**item)
                    self._iocs[ioc.value] = ioc
                logger.info(f"IOC store loaded: {len(self._iocs)} records from {self.path}")
        except Exception as e:
            logger.warning(f"IOC store load failed (starting empty): {e}")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump([ioc.model_dump() for ioc in self._iocs.values()], f, indent=2)
            os.replace(tmp, self.path)
        except Exception as e:
            logger.error(f"IOC store save failed: {e}")

    # ── CRUD ────────────────────────────────────
    def upsert(self, ioc: IOC) -> IOC:
        """Create or update (dedupe by value). Returns the stored record."""
        with self._lock:
            existing = self._iocs.get(ioc.value)
            if existing:
                existing.last_seen = ioc.first_seen
                existing.source_alert_id = ioc.source_alert_id or existing.source_alert_id
                existing.source_decision_id = ioc.source_decision_id or existing.source_decision_id
                existing.source_sigma_rule_id = ioc.source_sigma_rule_id or existing.source_sigma_rule_id
                existing.mitre_technique = ioc.mitre_technique or existing.mitre_technique
                existing.approved_by = ioc.approved_by or existing.approved_by
                existing.confidence = max(existing.confidence, ioc.confidence)
                if ioc.severity in ("critical", "high") and existing.severity not in ("critical",):
                    existing.severity = ioc.severity
                if "fortigate" in ioc.blocked_on and "fortigate" not in existing.blocked_on:
                    existing.blocked_on.append("fortigate")
                self._save()
                return existing
            self._iocs[ioc.value] = ioc
            self._save()
            return ioc

    def get(self, ioc_id: str) -> Optional[IOC]:
        with self._lock:
            for ioc in self._iocs.values():
                if ioc.id == ioc_id:
                    return ioc
        return None

    def get_by_value(self, value: str) -> Optional[IOC]:
        with self._lock:
            return self._iocs.get(value)

    def list(
        self,
        ioc_type: str = None,
        status: str = None,
        severity: str = None,
        mitre: str = None,
        search: str = None,
        limit: int = 500,
    ) -> List[IOC]:
        with self._lock:
            items = list(self._iocs.values())
        if ioc_type:
            items = [i for i in items if i.type == ioc_type]
        if status:
            items = [i for i in items if i.status == status]
        if severity:
            items = [i for i in items if i.severity == severity]
        if mitre:
            items = [i for i in items if mitre.lower() in i.mitre_technique.lower()]
        if search:
            s = search.lower()
            items = [i for i in items if s in i.value.lower() or s in i.mitre_technique.lower()]
        items.sort(key=lambda i: i.last_seen, reverse=True)
        return items[:limit]

    def update(self, ioc: IOC) -> IOC:
        with self._lock:
            self._iocs[ioc.value] = ioc
            self._save()
        return ioc

    def add_timeline_event(self, ioc: IOC, step: str, status: str, detail: str = ""):
        ioc.timeline.append(IOCTimelineEvent(step=step, status=status, detail=detail))
        self.update(ioc)

    def stats(self) -> dict:
        with self._lock:
            items = list(self._iocs.values())
        active = [i for i in items if i.status == "active"]
        return {
            "total": len(items),
            "active": len(active),
            "expired": len([i for i in items if i.status == "expired"]),
            "whitelisted": len([i for i in items if i.status == "whitelisted"]),
            "enforced_edr": len([i for i in active if "edr" in i.blocked_on]),
            "pending_enforcement": len([i for i in active if "edr" not in i.blocked_on]),
            "by_type": {
                t: len([i for i in items if i.type == t])
                for t in ("ip", "domain", "hash_sha256", "hash_md5")
            },
        }

    def find_expired(self) -> List[IOC]:
        with self._lock:
            items = list(self._iocs.values())
        return [i for i in items if i.is_expired()]


# Singleton store
ioc_store = IOCStore()