"""MITRE ATT&CK STIX loader — downloads real enterprise-attack bundle once, caches to disk, ingests into RAG.

REAL DATA: Downloads from https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json
Cached to backend/data/mitre_attack_cache.json after first download.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)

MITRE_STIX_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "mitre_attack_cache.json")

try:
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.rag_engine.rag_server import rag_server


def load_downloaded_bundle() -> Dict[str, Any]:
    """Return the STIX bundle from cache. If missing, download + cache it once."""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            logger.info(f"MITRE ATT&CK bundle loaded from cache: {CACHE_PATH}")
            return json.load(f)

    logger.info("Downloading MITRE ATT&CK Enterprise STIX bundle (one-time)...")
    try:
        resp = httpx.get(MITRE_STIX_URL, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        bundle = resp.json()
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(bundle, f)
        logger.info(f"MITRE ATT&CK bundle cached ({len(bundle.get('objects', []))} objects)")
        return bundle
    except Exception as e:
        logger.error(f"MITRE download failed: {e}")
        return {"objects": []}


def extract_techniques(bundle: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract attack-pattern objects (techniques) with id/name/tactic/description."""
    techniques = []
    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        external = obj.get("external_references", [])
        mitre_id = next((e.get("external_id", "") for e in external if e.get("source_name") == "mitre-attack"), "")
        if not mitre_id:
            continue

        kill_chain = obj.get("kill_chain_phases", [])
        tactic = ""
        for kc in kill_chain:
            if kc.get("kill_chain_name") == "mitre-attack":
                tactic = kc.get("phase_name", "")
                break

        techniques.append({
            "id": mitre_id,
            "name": obj.get("name", ""),
            "tactic": tactic,
            "description": obj.get("description", ""),
        })
    # De-dup by ID
    seen = set()
    deduped = []
    for t in techniques:
        if t["id"] not in seen:
            seen.add(t["id"])
            deduped.append(t)
    return deduped


def ingest_mitre_attack() -> int:
    """Download/extract/ingest MITRE techniques into the 'mitre_attack' RAG collection. Returns count."""
    bundle = load_downloaded_bundle()
    techniques = extract_techniques(bundle)
    if not techniques:
        logger.warning("No MITRE techniques extracted — check network/cache.")
        return 0

    docs = [{
        "technique_id": t["id"],
        "name": t["name"],
        "tactic": t["tactic"],
        "description": t["description"],
    } for t in techniques]

    rag_server.ingest(kb="mitre_attack", documents=docs)
    logger.info(f"Ingested {len(docs)} MITRE techniques into 'mitre_attack' KB")
    return len(docs)