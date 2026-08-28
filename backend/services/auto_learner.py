"""Auto-Learner — continuous learning from live internet threat sources.

Downloads data from multiple FREE no-key sources and ingests into the RAG
knowledge base so the platform continuously learns:

  1. abuse.ch Feodo Tracker   -> C2 IP blocklist (CSV)
  2. abuse.ch URLhaus         -> malicious URL feed (CSV)
  3. CISA KEV                 -> Known Exploited Vulnerabilities (JSON)
  4. MITRE ATT&CK             -> techniques via mitre_loader (STIX)
  5. OpenPhish free feed      -> phishing URLs

Runs at startup + every 30 minutes. Fully guarded: any source failure never
crashes the pipeline. Status exposed via /api/knowledge/threat-intel/status.
"""

import asyncio
import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

try:
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.rag_engine.rag_server import rag_server

# ── Sources (all free, no API keys) ──────────────────────────────────────────

SOURCES = {
    "feodo_c2": {
        "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.csv",
        "label": "abuse.ch Feodo Tracker — C2 IPs",
        "kb": "threat_intel",
    },
    "urlhaus": {
        "url": "https://urlhaus.abuse.ch/downloads/text_recent/",
        "label": "abuse.ch URLhaus — Malicious URLs",
        "kb": "threat_intel",
    },
    "cisa_kev": {
        "url": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        "label": "CISA KEV — Known Exploited Vulnerabilities",
        "kb": "cve_kev",
    },
    "openphish": {
        "url": "https://openphish.com/feed.txt",
        "label": "OpenPhish — Phishing URLs",
        "kb": "threat_intel",
    },
}

# ── State ────────────────────────────────────────────────────────────────────

learning_status: Dict[str, Any] = {
    "last_run": None,
    "sources": {},
    "total_learned": 0,
    "running": False,
}


# ── Fetchers ─────────────────────────────────────────────────────────────────

def _fetch_feodo(text: str, max_docs: int) -> List[dict]:
    docs = []
    for line in text.splitlines():
        if line.startswith("#") or line.startswith("Firstseen"):
            continue
        parts = line.split(",")
        if len(parts) >= 3:
            docs.append({
                "type": "c2_ip",
                "ip": parts[1].strip(),
                "port": parts[2].strip() if len(parts) > 2 else "",
                "malware": parts[3].strip() if len(parts) > 3 else "",
                "first_seen": parts[0].strip(),
                "source": "feodo_tracker",
            })
    return docs[:max_docs]


def _fetch_urlhaus(text: str, max_docs: int) -> List[dict]:
    docs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split('","')
        if parts:
            url = parts[0].strip('"')
            docs.append({
                "type": "malicious_url",
                "url": url[:500],
                "source": "urlhaus",
            })
    return docs[:max_docs]


def _fetch_cisa_kev(text: str, max_docs: int) -> List[dict]:
    docs = []
    try:
        data = json.loads(text)
        for vuln in data.get("vulnerabilities", []):
            docs.append({
                "type": "exploited_vulnerability",
                "cve_id": vuln.get("cveID", ""),
                "vendor": vuln.get("vendorProject", ""),
                "product": vuln.get("product", ""),
                "description": (vuln.get("shortDescription", "") or "")[:400],
                "date_added": vuln.get("dateAdded", ""),
                "known_ransomware": vuln.get("knownRansomwareCampaignUse", ""),
                "source": "cisa_kev",
            })
    except json.JSONDecodeError as e:
        logger.warning(f"CISA KEV JSON parse failed: {e}")
    return docs[:max_docs]


def _fetch_openphish(text: str, max_docs: int) -> List[dict]:
    docs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        docs.append({
            "type": "phishing_url",
            "url": line[:500],
            "source": "openphish",
        })
    return docs[:max_docs]


FETCHERS = {
    "feodo_c2": _fetch_feodo,
    "urlhaus": _fetch_urlhaus,
    "cisa_kev": _fetch_cisa_kev,
    "openphish": _fetch_openphish,
}


# ── Core learning loop ───────────────────────────────────────────────────────

def _learn_from_source(source_name: str, max_docs: int = 300) -> Dict[str, Any]:
    """Download one source and ingest into RAG. Returns per-source status."""
    src = SOURCES[source_name]
    result = {"source": source_name, "label": src["label"], "status": "failed", "learned": 0}

    try:
        resp = httpx.get(src["url"], timeout=30, follow_redirects=True)
        resp.raise_for_status()
        docs = FETCHERS[source_name](resp.text, max_docs)
        if docs:
            rag_server.ingest(src["kb"], docs)
            result["status"] = "ok"
            result["learned"] = len(docs)
            logger.info(f"AutoLearner: learned {len(docs)} items from {src['label']}")
        else:
            result["status"] = "empty"
    except Exception as e:
        logger.warning(f"AutoLearner: {source_name} failed: {e}")
        result["error"] = str(e)[:200]

    return result


def run_learning_cycle(max_per_source: int = 300) -> Dict[str, Any]:
    """Run one full learning cycle across all sources (blocking)."""
    if learning_status.get("running"):
        return {"status": "already_running", **learning_status}

    learning_status["running"] = True
    total = 0
    try:
        for source_name in SOURCES:
            result = _learn_from_source(source_name, max_per_source)
            learning_status["sources"][source_name] = result
            total += result.get("learned", 0)
        learning_status["total_learned"] = learning_status.get("total_learned", 0) + total
        learning_status["last_run"] = datetime.utcnow().isoformat()
        logger.info(f"AutoLearner cycle complete: learned {total} new items")
    finally:
        learning_status["running"] = False

    return {"status": "ok", "learned_this_cycle": total, **learning_status}


async def run_learning_cycle_async(max_per_source: int = 300) -> Dict[str, Any]:
    """Async wrapper — runs the blocking cycle in a thread."""
    return await asyncio.to_thread(run_learning_cycle, max_per_source)


# ── Background loop (started from main.py lifespan) ─────────────────────────

async def auto_learn_loop(interval_minutes: int = 30):
    """Background task: learn at startup, then every N minutes."""
    # Initial learning 20s after startup
    await asyncio.sleep(20)
    try:
        await run_learning_cycle_async()
    except Exception as e:
        logger.warning(f"AutoLearner initial cycle failed: {e}")

    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            await run_learning_cycle_async()
        except Exception as e:
            logger.warning(f"AutoLearner cycle failed: {e}")


def get_learning_status() -> Dict[str, Any]:
    """Return current learning status (for UI)."""
    return {
        "enabled": True,
        "sources": [
            {"name": k, "label": v["label"], "kb": v["kb"]}
            for k, v in SOURCES.items()
        ],
        **learning_status,
    }