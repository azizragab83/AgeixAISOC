"""CVE Loader — on-demand NVD API queries for CVEs mentioned in forensics output. Real, cached, scoped.

REAL DATA: Queries https://services.nvd.nist.gov/rest/json/cves/2.0 for specific CVE IDs
Cached in-memory to avoid repeated NVD calls. Ingested into 'cve_data' RAG collection.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx

logger = logging.getLogger(__name__)

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_cache: Dict[str, Dict[str, Any]] = {}

try:
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.rag_engine.rag_server import rag_server


def extract_cve_ids(text: str) -> List[str]:
    """Extract all CVE IDs (CVE-YYYY-NNNNN) from a text blob."""
    if not text:
        return []
    pattern = r"CVE-\d{4}-\d{4,7}"
    ids = re.findall(pattern, text, re.IGNORECASE)
    return list(dict.fromkeys([c.upper() for c in ids]))  # de-dup, preserve order


async def _fetch_cve(cve_id: str) -> Optional[Dict[str, Any]]:
    """Query NVD for a single CVE. Returns parsed record or None."""
    if cve_id in _cache:
        return _cache[cve_id]
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(NVD_API_URL, params={"cveId": cve_id})
            resp.raise_for_status()
            data = resp.json()
        vulns = data.get("vulnerabilities", [])
        if not vulns:
            _cache[cve_id] = {"cve_id": cve_id, "found": False}
            return _cache[cve_id]
        cve = vulns[0].get("cve", {})
        descriptions = cve.get("descriptions", [])
        en_desc = next((d.get("value", "") for d in descriptions if d.get("lang") == "en"), "")
        metrics = cve.get("metrics", {})
        cvss_v31 = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {}) if metrics.get("cvssMetricV31") else {}
        severity = cvss_v31.get("baseSeverity", "UNKNOWN")
        base_score = cvss_v31.get("baseScore", 0.0)
        published = cve.get("published", "")
        result = {
            "cve_id": cve_id,
            "found": True,
            "description": en_desc,
            "severity": severity,
            "base_score": base_score,
            "published": published,
            "fetched_at": datetime.utcnow().isoformat(),
        }
        _cache[cve_id] = result
        return result
    except Exception as e:
        logger.warning(f"NVD query failed for {cve_id}: {e}")
        return None


async def ingest_cves_for_forensics(forensics_text: str) -> int:
    """Extract CVE IDs from forensics output, query NVD, ingest into 'cve_data'. Returns count."""
    cve_ids = extract_cve_ids(forensics_text)
    if not cve_ids:
        return 0
    docs = []
    for cid in cve_ids[:5]:  # scope to max 5 CVEs per alert
        data = await _fetch_cve(cid)
        if data and data.get("found"):
            docs.append(data)
    if not docs:
        return 0
    rag_server.ingest(kb="cve_data", documents=docs)
    logger.info(f"Ingested {len(docs)} CVEs into 'cve_data' KB: {[d['cve_id'] for d in docs]}")
    return len(docs)