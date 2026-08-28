"""
AgeixAISOC — Cognitive Arsenal
==============================
External intelligence layer integrated from three open-source repos:

  1. Agent-Reach            -> agentic web reading/search (Jina Reader + DuckDuckGo)
  2. garrytan/gstack        -> analytical skill methodologies (gstack_skills/*.md)
  3. awesome-osint-arsenal  -> 753-tool OSINT catalog + IOC enrichment lookups

Every function degrades gracefully: no network / missing files / dead services
never crash the pipeline — callers always receive a well-formed dict.
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import httpx

try:
    from backend.config import settings
except ImportError:  # running as `uvicorn main:app` from inside backend/
    from config import settings

logger = logging.getLogger(__name__)

AI_TOOLS_DIR = Path(__file__).resolve().parent
SKILLS_DIR = AI_TOOLS_DIR / "gstack_skills"
OSINT_CATALOG_PATH = AI_TOOLS_DIR.parent / "data" / "osint_arsenal.json"

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgeixAISOC-CognitiveArsenal/1.0"
    )
}


def _timeout() -> float:
    return getattr(settings, "ARSENAL_TIMEOUT", 8.0)


# ---------------------------------------------------------------------------
# gstack skills
# ---------------------------------------------------------------------------

def gstack_list_skills() -> list:
    """List available distilled skills."""
    try:
        return sorted(p.stem for p in SKILLS_DIR.glob("*.md"))
    except Exception as exc:
        logger.warning("gstack_list_skills failed: %s", exc)
        return []


@lru_cache(maxsize=32)
def _load_skill_cached(name: str) -> str:
    return (SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")


def gstack_load_skill(name: str) -> dict:
    """Load a methodology skill by name. Returns {'ok', 'skill', 'content'}."""
    name = (name or "").strip().lower()
    try:
        content = _load_skill_cached(name)
        return {"ok": True, "skill": name, "content": content}
    except Exception:
        available = gstack_list_skills()
        return {"ok": False, "skill": name, "available": available, "content": ""}


# Heuristic scan patterns for the no-LLM code-analysis fallback.
_HEURISTICS = [
    ("obfuscated_powershell", re.compile(r"-enc(odedcommand)?\b", re.I), "Encoded PowerShell command"),
    ("download_cradle", re.compile(r"(iex|invoke-expression).*(downloadstring|webclient)|certutil.*urlcache", re.I), "Download cradle execution"),
    ("reverse_shell", re.compile(r"(/bin/(ba)?sh\s+-i|nc(\.exe)?\s+-e|socket\.connect)", re.I), "Reverse shell primitive"),
    ("mimikatz_ref", re.compile(r"(sekurlsa|mimikatz|lsadump::)", re.I), "Credential dumping tool reference"),
    ("base64_blob", re.compile(r"[A-Za-z0-9+/]{120,}={0,2}"), "Large base64 blob"),
    ("scheduled_persistence", re.compile(r"(schtasks\s+/create|new-scheduledtask)", re.I), "Scheduled-task persistence"),
    ("registry_run_key", re.compile(r"(currentversion\\\\?run|reg add.*run\b)", re.I), "Registry Run-key persistence"),
]


def _heuristic_code_scan(snippet: str) -> dict:
    hits = []
    for name, rx, label in _HEURISTICS:
        if rx.search(snippet):
            hits.append({"indicator": name, "detail": label})
    verdict = "unknown"
    if hits:
        verdict = "malicious" if len(hits) >= 2 else "suspicious"
    elif snippet.strip():
        verdict = "benign"
    return {
        "risk_verdict": verdict,
        "summary": (
            f"Heuristic scan flagged {len(hits)} indicator(s): "
            + "; ".join(h["detail"] for h in hits)
            if hits else "No suspicious primitives found by heuristic scan."
        ),
        "indicators": [h["indicator"] for h in hits],
    }


def gstack_analyze_code(snippet: str, language: str = "auto") -> dict:
    """Analyze a script/command payload with the local coder model, applying the
    gstack investigate skill. Falls back to a deterministic heuristic scan."""
    snippet = (snippet or "").strip()
    if not snippet:
        return {"ok": False, "language": language,
                "analysis": {"risk_verdict": "unknown", "summary": "Empty payload.", "indicators": []}}

    skill = gstack_load_skill("investigate")
    methodology = skill.get("content", "")[:1500]

    prompt = (
        "You are a malware analyst. Analyze this payload extracted from a security alert.\n\n"
        f"METHODOLOGY:\n{methodology}\n\nPAYLOAD ({language}):\n```\n{snippet[:2000]}\n```"
        '\n\nReturn ONLY JSON: {"risk_verdict": "malicious|suspicious|benign", '
        '"summary": "one paragraph explaining what it does and why", '
        '"indicators": ["observable IOC strings or techniques"]}'
    )

    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL_CODER", "qwen2.5-coder:7b")
    try:
        r = httpx.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 400},
            },
            timeout=60.0,
        )
        r.raise_for_status()
        parsed = _extract_json_block(r.json().get("response", ""))
        if parsed and parsed.get("risk_verdict"):
            return {
                "ok": True,
                "language": language,
                "model": model,
                "analysis": {
                    "risk_verdict": parsed.get("risk_verdict", "unknown"),
                    "summary": str(parsed.get("summary", ""))[:600],
                    "indicators": list(parsed.get("indicators", []))[:10],
                },
            }
    except Exception as exc:
        logger.warning("gstack_analyze_code LLM failed (%s) - using heuristics", exc)

    return {
        "ok": True,
        "language": language,
        "model": "heuristic_fallback",
        "analysis": _heuristic_code_scan(snippet),
    }


# ---------------------------------------------------------------------------
# Agent Reach — agentic web reading & search
# ---------------------------------------------------------------------------

def agent_reach_read(url: str, max_chars: int = 4000) -> dict:
    """Read a page through Jina Reader (r.jina.ai); fall back to direct fetch."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    # 1) Jina Reader — clean markdown extraction, no API key needed.
    try:
        r = httpx.get(
            f"https://r.jina.ai/{url}",
            headers=_HTTP_HEADERS,
            timeout=max(_timeout(), 12.0),
            follow_redirects=True,
        )
        if r.status_code == 200 and r.text.strip():
            text = r.text[:max_chars]
            return {"ok": True, "url": url, "source": "jina_reader", "content": text}
    except Exception as exc:
        logger.debug("jina reader failed for %s: %s", url, exc)
    # 2) Direct fetch + crude tag strip.
    try:
        r = httpx.get(url, headers=_HTTP_HEADERS, timeout=_timeout(), follow_redirects=True)
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text or "", flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return {
            "ok": bool(text),
            "url": url,
            "source": "direct",
            "content": text[:max_chars],
        }
    except Exception as exc:
        logger.warning("agent_reach_read failed for %s: %s", url, exc)
        return {"ok": False, "url": url, "source": "none", "content": "", "error": str(exc)}


_DDGO_RESULT_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S
)
_DDGO_SNIPPET_RE = re.compile(
    r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', re.S
)


def _clean_ddgo_href(href: str) -> str:
    href = unquote(href)
    if href.startswith("//duckduckgo.com/l/") or "/l/?" in href:
        parsed = urlparse(href if href.startswith("http") else "https:" + href)
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return qs["uddg"][0]
    return href


def agent_reach_search(query: str, max_results: int = 5) -> dict:
    """Agentic web search via DuckDuckGo HTML endpoint (no API key)."""
    query = (query or "").strip()
    if not query:
        return {"ok": False, "query": query, "results": []}
    try:
        r = httpx.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=_HTTP_HEADERS,
            timeout=max(_timeout(), 12.0),
            follow_redirects=True,
        )
        body = r.text
        titles = [(m.group(1), re.sub(r"<.*?>", "", m.group(2)).strip())
                  for m in _DDGO_RESULT_RE.finditer(body)]
        snippets = [re.sub(r"<.*?>|&#x27;|&quot;", " ", m.group(1)).strip()
                    for m in _DDGO_SNIPPET_RE.finditer(body)]
        results = []
        for i, (href, title) in enumerate(titles[:max_results]):
            results.append({
                "title": title,
                "url": _clean_ddgo_href(href),
                "snippet": snippets[i] if i < len(snippets) else "",
            })
        ok = len(results) > 0
        return {"ok": ok, "query": query, "results": results}
    except Exception as exc:
        logger.warning("agent_reach_search failed for '%s': %s", query, exc)
        return {"ok": False, "query": query, "results": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# OSINT Arsenal — catalog + IOC enrichment
# ---------------------------------------------------------------------------

_IOC_TYPE_RES = [
    ("ipv4", re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")),
    ("hash", re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")),
    ("email", re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")),
    ("url", re.compile(r"^https?://", re.I)),
]


def osint_detect_type(ioc: str) -> str:
    ioc = (ioc or "").strip()
    for label, rx in _IOC_TYPE_RES:
        if rx.match(ioc):
            return label
    if "." in ioc and not ioc.startswith("http"):
        return "domain"
    return "unknown"


@lru_cache(maxsize=1)
def load_osint_catalog() -> list:
    try:
        data = json.loads(OSINT_CATALOG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("osint catalog unavailable: %s", exc)
        return []


def osint_arsenal_suggest(query: str, limit: int = 5) -> dict:
    """Keyword-search the 753-tool OSINT catalog."""
    catalog = load_osint_catalog()
    terms = [t.lower() for t in re.split(r"[\s,_;-]+", (query or "").lower()) if t]
    scored = []
    for entry in catalog:
        hay = json.dumps(entry, ensure_ascii=False).lower() if isinstance(entry, dict) else str(entry).lower()
        score = sum(1 for t in terms if t in hay)
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    tools = []
    for _, e in scored[:limit]:
        tools.append({
            "name": e.get("name") or e.get("Name"),
            "description": (e.get("description") or e.get("Description") or "")[:200],
            "category": e.get("category") or e.get("Category") or "",
            "url": e.get("url") or e.get("Url") or e.get("link") or "",
        })
    return {"ok": bool(tools), "query": query, "catalog_size": len(catalog), "tools": tools}


def _enrich_ip(ip: str) -> dict:
    out = {}
    try:
        r = httpx.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,country,city,isp,org,as,proxy,hosting,mobile"},
            timeout=_timeout(),
        )
        if r.status_code == 200:
            d = r.json()
            out["geo_asn"] = {
                "country": d.get("country"), "city": d.get("city"),
                "isp": d.get("isp"), "org": d.get("org"), "as": d.get("as"),
                "proxy_or_vpn": bool(d.get("proxy")), "hosting": bool(d.get("hosting")),
            }
    except Exception as exc:
        logger.debug("ip-api failed for %s: %s", ip, exc)
    api_key = getattr(settings, "ABUSEIPDB_API_KEY", "") or ""
    if api_key:
        try:
            r = httpx.get(
                "https://api.abuseipdb.com/api/v2/check",
                params={"ipAddress": ip, "maxAgeInDays": 90},
                headers={"Key": api_key, "Accept": "application/json"},
                timeout=_timeout(),
            )
            if r.status_code == 200:
                d = r.json().get("data", {})
                out["abuseipdb"] = {
                    "confidence_of_abuse": d.get("abuseConfidenceScore"),
                    "total_reports": d.get("totalReports"),
                    "is_tor": d.get("isTor"),
                }
        except Exception as exc:
            logger.debug("abuseipdb failed for %s: %s", ip, exc)
    return out


def _enrich_domain_or_url(target: str, kind: str) -> dict:
    endpoint = "https://urlhaus-api.abuse.ch/v1/host/" if kind == "domain" \
        else "https://urlhaus-api.abuse.ch/v1/url/"
    field = "host" if kind == "domain" else "url"
    out = {}
    try:
        r = httpx.post(endpoint, data={field: target}, timeout=max(_timeout(), 12.0))
        if r.status_code == 200:
            d = r.json()
            if d.get("query_status") == "ok":
                out["urlhaus"] = {
                    "known_malicious": True,
                    "url_count": d.get("url_count"),
                    "tags": d.get("tags"),
                    "blacklists": d.get("blacklists"),
                }
            elif d.get("query_status") == "no_results":
                out["urlhaus"] = {"known_malicious": False}
    except Exception as exc:
        logger.debug("urlhaus failed for %s: %s", target, exc)
    return out


def _enrich_hash(h: str) -> dict:
    out = {}
    try:
        r = httpx.post(
            "https://urlhaus-api.abuse.ch/v1/payload/",
            data={"sha256": h.lower()} if len(h) == 64 else {"md5": h.lower()},
            timeout=max(_timeout(), 12.0),
        )
        if r.status_code == 200:
            d = r.json()
            if d.get("query_status") == "ok":
                out["urlhaus_payload"] = {
                    "known_malware": True,
                    "file_type": d.get("file_type"),
                    "signature": d.get("signature"),
                    "virustotal": d.get("virustotal", {}).get("result") if isinstance(d.get("virustotal"), dict) else None,
                }
            elif d.get("query_status") == "no_results":
                out["urlhaus_payload"] = {"known_malware": False}
    except Exception as exc:
        logger.debug("urlhaus payload failed: %s", exc)
    return out


def osint_arsenal_lookup(ioc: str) -> dict:
    """Enrich an IOC using free no-key sources (+ optional keyed ones)."""
    ioc = (ioc or "").strip()
    kind = osint_detect_type(ioc)
    enrichment: dict = {"ioc": ioc, "type": kind}
    if kind == "ipv4":
        enrichment.update(_enrich_ip(ioc))
    elif kind in ("domain", "url"):
        enrichment.update(_enrich_domain_or_url(ioc, kind))
    elif kind == "hash":
        enrichment.update(_enrich_hash(ioc))
    suggestions = osint_arsenal_suggest(f"{kind} {ioc}", limit=3)
    enrichment["recommended_osint_tools"] = suggestions.get("tools", [])
    return enrichment


# ---------------------------------------------------------------------------
# Master Brain tool registry + ReAct-style loop
# ---------------------------------------------------------------------------

MASTER_TOOLS = {
    "web_search": {
        "fn": agent_reach_search,
        "args": ["query"],
        "desc": "Search the public web for threat intel about an actor/malware/CVE.",
    },
    "read_page": {
        "fn": agent_reach_read,
        "args": ["url"],
        "desc": "Read a specific webpage (report, advisory, blog) and extract its text.",
    },
    "enrich_ioc": {
        "fn": osint_arsenal_lookup,
        "args": ["ioc"],
        "desc": "Reputation-enrich an IP/domain/URL/hash (geo/ASN/VPN, known-malware DBs).",
    },
    "suggest_osint_tools": {
        "fn": osint_arsenal_suggest,
        "args": ["query"],
        "desc": "Recommend specialized OSINT tools from a 753-tool catalog.",
    },
    "analyze_code": {
        "fn": gstack_analyze_code,
        "args": ["snippet"],
        "desc": "Analyze a suspicious script/command payload for malicious behavior.",
    },
    "list_skills": {
        "fn": gstack_list_skills,
        "args": [],
        "desc": "List analytical methodology skills available.",
    },
    "load_skill": {
        "fn": lambda name: gstack_load_skill(name),
        "args": ["name"],
        "desc": "Load an analytical methodology (investigate/review/cso) to structure reasoning.",
    },
}


def get_master_tools_manifest() -> str:
    lines = []
    for name, spec in MASTER_TOOLS.items():
        args = ", ".join(f"{a}:str" for a in spec["args"])
        lines.append(f"- {name}({args}): {spec['desc']}")
    return "\n".join(lines)


def _dispatch(tool_name: str, args: dict):
    """Execute one registered tool safely."""
    spec = MASTER_TOOLS.get(tool_name)
    if spec is None:
        return {"ok": False, "error": f"unknown tool '{tool_name}'"}
    kwargs = {}
    for a in spec["args"]:
        v = args.get(a)
        if v is None:
            return {"ok": False, "error": f"missing arg '{a}' for '{tool_name}'"}
        kwargs[a] = v
    try:
        return spec["fn"](**kwargs)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _extract_json_block(text: str):
    """Pull first JSON object out of an LLM response."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    raw = m.group(0)
    for candidate in (raw, raw.replace("\n", " ")):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def run_master_tool_loop(context_summary: str, max_rounds: int = 3) -> list:
    """
    Agentic loop for the Master Brain: given incident context, the LLM decides
    which external intelligence tools to call (web search / page reads / IOC
    enrichment / skill loading) and we execute them. Returns collected findings.

    Fully guarded: any failure returns [] and the pipeline continues normally.
    """
    if not getattr(settings, "ARSENAL_ENABLED", True):
        return []

    findings = []
    transcript = []
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    system_prompt = (
        "You are the Master Brain of an AI Security Operations Center.\n"
        "You can call external intelligence tools before making your decision.\n\n"
        "AVAILABLE TOOLS:\n" + get_master_tools_manifest() +
        "\n\nRULES:\n"
        "- Respond with ONLY one JSON object, no other text.\n"
        '- To call a tool: {"thought": "...", "tool": "<name>", "args": {...}}\n'
        '- When you have enough intel: {"thought": "...", "done": true}\n'
        "- Maximum value calls: enrich suspicious IPs/domains, search web for "
        "unfamiliar malware/CVE names. Do NOT call more than "
        f"{max_rounds} tools."
    )

    for _ in range(max(1, max_rounds)):
        messages = [{"role": "system", "content": system_prompt}]
        user_content = context_summary
        if transcript:
            user_content += "\n\nPREVIOUS TOOL RESULTS:\n" + json.dumps(transcript[-3:], ensure_ascii=False)[:3000]
            user_content += "\n\nDecide: call another tool, or finish with done:true."
        messages.append({"role": "user", "content": user_content})

        try:
            r = httpx.post(
                f"{base_url}/api/chat",
                json={
                    "model": settings.OLLAMA_MODEL_THREAT,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2, "num_predict": 300},
                },
                timeout=45.0,
            )
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "")
        except Exception as exc:
            logger.warning("master tool-loop LLM call failed: %s", exc)
            break

        action = _extract_json_block(content)
        if not action:
            break
        if action.get("done"):
            break
        tool_name = action.get("tool")
        args = action.get("args") if isinstance(action.get("args"), dict) else {}
        result = _dispatch(tool_name, args)
        entry = {"tool": tool_name, "args": args, "result": result}
        transcript.append(entry)
        if tool_name == "read_page" and result.get("content"):
            findings.append({
                "tool": tool_name,
                "url": result.get("url"),
                "excerpt": result.get("content", "")[:800],
            })
        elif result.get("ok"):
            slim = {k: v for k, v in result.items() if k != "content"}
            findings.append({"tool": tool_name, **slim})

    return findings


__all__ = [
    "gstack_list_skills", "gstack_load_skill", "gstack_analyze_code",
    "agent_reach_read", "agent_reach_search",
    "osint_detect_type", "load_osint_catalog",
    "osint_arsenal_suggest", "osint_arsenal_lookup",
    "MASTER_TOOLS", "get_master_tools_manifest",
    "run_master_tool_loop",
]

# ---------------------------------------------------------------------------
# Agent Tool Assignments (compatibility layer for agents.py)
# ---------------------------------------------------------------------------

try:
    from crewai.tools import tool as _mk_crewai_tool
except ImportError:
    _mk_crewai_tool = None


def _as_crewai_tool(fn):
    return _mk_crewai_tool(fn) if _mk_crewai_tool else fn


COGNITIVE_ARSENAL = {
    "agent_reach_search": _as_crewai_tool(agent_reach_search),
    "gstack_analyze_code": _as_crewai_tool(gstack_analyze_code),
    "osint_arsenal_lookup": _as_crewai_tool(osint_arsenal_lookup),
}

AGENT_TOOL_ASSIGNMENTS = {
    "threat_hunter": ["agent_reach_search", "osint_arsenal_lookup"],
    "forensics": ["gstack_analyze_code"],
    "osint": ["agent_reach_search", "gstack_analyze_code", "osint_arsenal_lookup"],
    "detection_engineer": ["gstack_analyze_code"],
}


def get_cognitive_tools(agent_name: str) -> list:
    """Return the list of cognitive tools assigned to a given agent."""
    names = AGENT_TOOL_ASSIGNMENTS.get(agent_name, [])
    return [COGNITIVE_ARSENAL[n] for n in names if n in COGNITIVE_ARSENAL]