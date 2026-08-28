"""Natural Adaptive Learning memory for AgeixAISOC.

Every human HITL decision (approve/reject) is ingested as a Positive or
Negative Example into the learned_decisions ChromaDB collection. The Master
Brain queries this memory before processing new alerts to auto-suppress or
lower risk scores on similar False-Positive patterns.
"""

import logging
from typing import Any, Dict

try:
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.rag_engine.rag_server import rag_server

logger = logging.getLogger("ageixaisoc.rag_memory")

LEARNED_KB = "learned_decisions"
DISTANCE_TO_CONFIDENCE = lambda d: max(0.0, min(1.0, 1.0 - float(d)))
SUPPRESS_CONFIDENCE = 0.90
LOWER_RISK_CONFIDENCE = 0.70
MIN_CONFIDENCE = 0.55


def _extract_pattern_keys(raw_alert: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the searchable pattern keys from a raw alert (Wazuh-style)."""
    ra = raw_alert or {}
    mitre = ra.get("mitre_id", "") or (ra.get("decoded") or {}).get("mitre_id", [])
    if isinstance(mitre, list):
        mitre = ",".join(str(m) for m in mitre)
    src_ip = ra.get("source_ip") or ra.get("src_ip", "")
    dst_ip = ra.get("destination_ip") or ra.get("dst_ip", "")
    rule_id = ra.get("rule_id", "")
    rule_desc = ra.get("rule_description") or ra.get("description", "")
    summary = ra.get("summary", "")
    location = ra.get("location", "")
    return {
        "mitre_id": str(mitre or ""),
        "source_ip": str(src_ip or ""),
        "destination_ip": str(dst_ip or ""),
        "rule_id": str(rule_id or ""),
        "rule_description": str(rule_desc or ""),
        "summary": str(summary or ""),
        "location": str(location or ""),
    }


def _build_memory_text(kind: str, pattern: Dict[str, Any], analyst_notes: str) -> str:
    """Build a natural-language text blob for embedding + search."""
    parts = [
        f"{kind} example for alert pattern",
        f"mitre: {pattern.get('mitre_id', '')}",
        f"src: {pattern.get('source_ip', '')}",
        f"dst: {pattern.get('destination_ip', '')}",
        f"rule: {pattern.get('rule_id', '')}",
        f"description: {pattern.get('rule_description', '')}",
        f"summary: {pattern.get('summary', '')}",
        f"location: {pattern.get('location', '')}",
    ]
    if analyst_notes:
        parts.append(f"analyst notes: {analyst_notes}")
    return " | ".join(p for p in parts if p and p.split(":", 1)[-1].strip())


def _normalize(action: str) -> str:
    """Normalize analyst action string -> 'positive' | 'negative'."""
    a = (action or "").strip().lower()
    if a in ("approved", "approve", "positive", "accepted", "true"):
        return "positive"
    if a in ("rejected", "reject", "negative", "false_positive", "fp", "dismissed"):
        return "negative"
    return "negative"


def ingest_example(
    decision_id, alert_id, raw_alert, decision_package,
    action, analyst_notes="", record_status="Closed (False Positive)",
):
    """Store a human decision into the learned_decisions KB.

    Returns dict with 'ingested' (bool), 'doc_id' (optional), 'kind'
    ('positive'|'negative'), and 'error' on failure.
    """
    from datetime import datetime
    kind = _normalize(action)
    pattern = _extract_pattern_keys(raw_alert)
    text = _build_memory_text(kind, pattern, analyst_notes)

    memory_doc = {
        "decision_id": decision_id,
        "alert_id": alert_id,
        "action": action,
        "kind": kind,
        "analyst_notes": analyst_notes,
        "record_status": record_status,
        "pattern": pattern,
        "captured_at": datetime.utcnow().isoformat(),
        "danger_summary": (decision_package.get("threat_analysis") or {}).get("summary", ""),
        "risk_score": decision_package.get("risk_score", 0),
        "risk_level": decision_package.get("risk_level", "unknown"),
        "mitre_id": decision_package.get("mitre_id") or pattern.get("mitre_id") or "",
        "decision_package_summary": {
            k: v for k, v in decision_package.items()
            if k not in ("raw_alert", "decision_id", "status", "human_decision", "executed_at")
        },
    }

    try:
        doc_ids = rag_server.ingest(kb=LEARNED_KB, documents=[memory_doc])
        if doc_ids:
            logger.info(
                "Adaptive memory: %s example for alert %s stored in learned_decisions "
                "(decision %s)",
                kind, alert_id, decision_id,
            )
            return {"ingested": True, "doc_id": doc_ids[0], "kind": kind}
        logger.warning("Adaptive memory: rag_server returned no doc ids for %s", decision_id)
        return {"ingested": False, "doc_id": None, "kind": kind}
    except Exception as e:
        logger.error("Adaptive memory ingest failed for decision %s: %s", decision_id, e)
        return {"ingested": False, "doc_id": None, "kind": kind, "error": str(e)}


def evaluate_learned_memory(alert_id: str, raw_alert: Dict[str, Any]) -> Dict[str, Any]:
    """Master-Brain pre-check: does learned memory recognize this alert?

    Searches the learned_decisions KB for the most similar previously
    resolved pattern. Returns a recommendation dict (never raises):

        matched, kind, confidence, action ('suppress'|'lower_risk'|'none'),
        note, matches (top docs), source_file_id
    """
    pattern = _extract_pattern_keys(raw_alert)
    if not any(pattern.values()):
        return {"matched": False, "kind": None, "confidence": 0.0,
                "action": "none", "note": "", "matches": []}

    query_text = _build_memory_text("pattern", pattern, "")
    try:
        docs = rag_server.search_kb(LEARNED_KB, query_text, top_k=3)
    except Exception as e:
        logger.warning("learned_decisions search failed (%s) — treating as no-memory", e)
        docs = []

    memory_mode = getattr(rag_server, "_initialized", None) == "memory"

    best_negative = None
    best_negative_conf = 0.0
    best_positive = None
    best_positive_conf = 0.0

    for doc in docs:
        metadata = doc.get("metadata") or {}
        distance = doc.get("distance", 1.0)
        if memory_mode:
            # search_kb memory-mode returns keyword-overlap similarity in [0,1]
            # where higher = more similar.
            confidence = float(distance)
        else:
            # ChromaDB cosine distance: smaller = closer. Convert to confidence.
            confidence = DISTANCE_TO_CONFIDENCE(distance)

        kind = metadata.get("kind") or _normalize(metadata.get("action", ""))
        if kind == "negative" and confidence > best_negative_conf:
            best_negative = doc
            best_negative_conf = confidence
        elif kind == "positive" and confidence > best_positive_conf:
            best_positive = doc
            best_positive_conf = confidence

    if best_negative_conf >= SUPPRESS_CONFIDENCE:
        return {
            "matched": True, "kind": "negative", "confidence": best_negative_conf,
            "action": "suppress",
            "note": "Previously marked as False Positive by Analyst",
            "matches": [best_negative], "source_file_id": best_negative.get("id", ""),
        }
    if best_negative_conf >= LOWER_RISK_CONFIDENCE:
        return {
            "matched": True, "kind": "negative", "confidence": best_negative_conf,
            "action": "lower_risk",
            "note": "Previously marked as False Positive by Analyst",
            "matches": [best_negative], "source_file_id": best_negative.get("id", ""),
        }
    if best_positive_conf >= LOWER_RISK_CONFIDENCE:
        return {
            "matched": True, "kind": "positive", "confidence": best_positive_conf,
            "action": "none", "note": "Similar alert previously approved — keep risk score",
            "matches": [best_positive], "source_file_id": best_positive.get("id", ""),
        }

    return {
        "matched": False, "kind": None,
        "confidence": max(best_negative_conf, best_positive_conf),
        "action": "none", "note": "", "matches": docs,
        "source_file_id": (best_negative or best_positive or {}).get("id", ""),
    }


def apply_learned_memory_to_package(
    decision_package: Dict[str, Any],
    memory_eval: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply the learned-memory recommendation to a decision package."""
    pkg = dict(decision_package)
    action = memory_eval.get("action", "none")
    if action == "suppress":
        pkg["status"] = "suppressed_by_learned_memory"
        pkg["human_decision"] = None
        pkg["risk_level"] = "informational"
        pkg["learned_memory"] = memory_eval
    elif action == "lower_risk":
        current = float(pkg.get("risk_score", 0) or 0)
        adjusted = max(0.0, current * 0.5)
        pkg["risk_score"] = round(adjusted, 1)
        if adjusted < 25:
            pkg["risk_level"] = "low"
        elif adjusted < 50:
            pkg["risk_level"] = "medium"
        notes = list(pkg.get("analyst_notes", []) or [])
        if memory_eval.get("note") not in notes:
            notes = notes + [memory_eval["note"]]
        pkg["analyst_notes"] = notes
        pkg["learned"] = memory_eval
    return pkg
