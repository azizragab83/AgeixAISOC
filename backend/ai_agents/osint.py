"""Agent 9: OSINT - Open Source Intelligence Threat Enrichment.

Enriches alert indicators (IPs, hashes, domains) with threat-intel context:
reputation, known malware families, botnet feeds, and geopolitical attribution.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from agents import get_agent
except ImportError:
    from backend.agents import get_agent

try:
    from ai_agents._utils import execute_agent_task, parse_json
except ImportError:
    from backend.ai_agents._utils import execute_agent_task, parse_json

logger = logging.getLogger(__name__)

# Deterministic local intelligence engine (rips through known feeds)
KNOWN_MALICIOUS = {
    "185.220.101.0": {"family": "ANCHORPALM", "source": "Feodo Tracker", "reputation": "malicious"},
    "91.121.86.0": {"family": "Emotet", "source": "Feodo Tracker", "reputation": "malicious"},
    "51.75.144.0": {"family": "TrickBot", "source": "Feodo Tracker", "reputation": "malicious"},
}


def _intel_lookup(raw_alert: dict) -> dict:
    """Deterministic OSINT enrichment from local threat-intel cache + live feed."""
    import os
    from pathlib import Path
    ra = raw_alert or {}
    src_ip = ra.get("source_ip") or ra.get("src_ip", "")
    dst_ip = ra.get("destination_ip") or ra.get("dst_ip", "")
    iocs: List[str] = []
    reputations: List[dict] = []

    # Local cache file if available (services/threat_intel.py writes it)
    cache_path = Path(__file__).resolve().parent.parent / "data" / "threat_intel.json"
    feed = {}
    if cache_path.exists():
        try:
            feed = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            feed = {}

    for ip in (src_ip, dst_ip):
        if not ip:
            continue
        if ip in KNOWN_MALICIOUS:
            entry = KNOWN_MALICIOUS[ip]
            reputations.append({**entry, "indicator": ip})
            iocs.append(ip)
        if ip in feed:
            reputations.append({"indicator": ip, **feed[ip]})
            if feed[ip].get("reputation") == "malicious":
                iocs.append(ip)

    # Threat intel match from risk_scorer's KNOWN_MALICIOUS_IPS
    if src_ip in {"10.0.0.1", "185.220.101.0", "91.121.86.0", "51.75.144.0"}:
        label = KNOWN_MALICIOUS.get(src_ip, {}).get("family", "unknown")
        if src_ip not in [r["indicator"] for r in reputations]:
            reputations.append({
                "indicator": src_ip, "family": label, "source": "local_intel", "reputation": "malicious"
            })

    # ── Cognitive Arsenal: live IOC enrichment (Agent-Reach + OSINT arsenal) ──
    live_enrichment = {}
    try:
        from ai_tools import osint_arsenal_lookup
    except ImportError:
        from backend.ai_tools import osint_arsenal_lookup
    try:
        primary = src_ip or dst_ip
        if primary:
            live_enrichment = osint_arsenal_lookup(primary)
            urlhaus = live_enrichment.get("geo_asn") or {}
            abuse = (live_enrichment.get("abuseipdb") or {})
            known_bad = False
            for key in ("urlhaus", "urlhaus_payload"):
                block = live_enrichment.get(key) or {}
                if not isinstance(block, dict):
                    continue
                if block.get("known_malicious") or block.get("known_malware"):
                    known_bad = True
            vpn_or_hosting = bool(urlhaus.get("proxy_or_vpn")) or bool(urlhaus.get("hosting"))
            if known_bad:
                iocs.append(primary)
                reputations.append({
                    "indicator": primary,
                    "family": (live_enrichment.get("urlhaus_payload") or {}).get("signature") or "known-malicious",
                    "source": "urlhaus_live",
                    "reputation": "malicious",
                })
            elif vpn_or_hosting or abuse.get("confidence_of_abuse"):
                reputations.append({
                    "indicator": primary,
                    "family": "suspicious_infrastructure",
                    "source": "ip-api_live",
                    "reputation": "suspicious",
                })
    except Exception as exc:
        logger.warning(f"Cognitive Arsenal OSINT enrichment skipped (non-fatal): {exc}")

    method = "local_intel_cache+live_arsenal" if live_enrichment else "local_intel_cache"

    return {
        "indicators_reviewed": [i for i in (src_ip, dst_ip) if i],
        "reputation": reputations,
        "malicious_iocs": iocs,
        "threat_actor_cluster": list({r.get("family") for r in reputations if r.get("family")}),
        "live_enrichment": live_enrichment,
        "osint_risk_boost": min(25, len(iocs) * 12),
        "method": method,
    }


def run(alert_id: str, raw_alert: dict, decision_package: dict) -> dict:
    agent = get_agent("osint")
    task = f"""
Perform Open Source Intelligence (OSINT) analysis on indicators in this alert `{alert_id}`.

Alert:
```json
{json.dumps(raw_alert or {}, indent=2)}
```

Return JSON: {{indicators_reviewed (array), reputation (array of {{indicator, family, source, reputation}}), malicious_iocs (array), threat_actor, confidence (0-1)}}
"""
    try:
        result = execute_agent_task(agent, task)
        intel = parse_json(result)
        if not intel:
            raise ValueError("Empty OSINT result")
        intel["method"] = "llm"
    except Exception as e:
        logger.warning(f"OSINT LLM failed ({e}) - using local intel cache")
        intel = _intel_lookup(raw_alert)

    boost = int(intel.get("osint_risk_boost", 0) or 0)
    malicious = intel.get("malicious_iocs", []) or []
    log = {
        "agent": "osint",
        "message": f"OSINT: {len(malicious)} malicious indicator(s) found, actor: {intel.get('threat_actor') or intel.get('threat_intel_cluster') or 'unattributed'}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "warning" if malicious else "info",
    }

    return {
        "agent_logs": [log],
        "decision_package": {"osint_analysis": intel},
        "current_node": "master_synthesis",
    }