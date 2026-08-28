"""Threat Intel refresh — live feed from abuse.ch Feodo Tracker (no API key needed).

LIVE FEED (15 min refresh): Pulls https://feodotracker.abuse.ch/downloads/ipblocklist.csv
Ingests known C2 IPs into the 'threat_intel' RAG collection. Tracks last_refresh timestamp.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Dict, List, Any

import httpx

logger = logging.getLogger(__name__)

FEODO_URL = "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"
last_refresh: str = ""
ingested_count: int = 0

try:
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.rag_engine.rag_server import rag_server


async def refresh_threat_intel(max_ips: int = 500) -> Dict[str, Any]:
    """Fetch Feodo Tracker IP blocklist, ingest into 'threat_intel' KB. Returns status dict."""
    global last_refresh, ingested_count

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(FEODO_URL)
            resp.raise_for_status()
            text = resp.text
    except Exception as e:
        logger.warning(f"Feodo Tracker fetch failed: {e}")
        return {"status": "failed", "error": str(e), "last_refresh": last_refresh}

    # Feodo CSV has comment lines (#) + a header row
    rows = []
    for line in text.splitlines():
        if line.startswith("#") or line.startswith("Firstseen"):
            continue
        parts = line.split(",")
        if len(parts) >= 3:
            rows.append({
                "first_seen": parts[0].strip(),
                "ip": parts[1].strip(),
                "port": parts[2].strip() if len(parts) > 2 else "",
                "malware": parts[3].strip() if len(parts) > 3 else "",
            })

    if not rows:
        logger.warning("Feodo Tracker returned 0 rows (empty feed).")
        return {"status": "empty", "last_refresh": last_refresh}

    scoped = rows[:max_ips]
    docs = [{
        "_label": "Live Threat Intel Feed — abuse.ch Feodo Tracker (15min refresh)",
        **r,
    } for r in scoped]

    import asyncio
    await asyncio.to_thread(rag_server.ingest, "threat_intel", docs)
    ingested_count = len(docs)
    last_refresh = datetime.utcnow().isoformat()
    logger.info(f"Threat intel refreshed: ingested {len(docs)} C2 IPs into 'threat_intel' KB")
    return {"status": "ok", "ingested": len(docs), "last_refresh": last_refresh}


def get_threat_intel_status() -> Dict[str, Any]:
    """Return current threat intel status (for UI badge)."""
    return {
        "source": "Feodo Tracker (abuse.ch)",
        "label": "Live Feed (15min refresh)",
        "last_refresh": last_refresh if last_refresh else None,
        "ingested_count": ingested_count,
    }