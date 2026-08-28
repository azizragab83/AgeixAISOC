"""Health check endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter

try:
    from config import settings
except ImportError:
    from backend.config import settings

logger = logging.getLogger("ageixaisoc.routes.health")
router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.1.0",
        "ollama_configured": bool(settings.OLLAMA_BASE_URL),
        "kali_configured": bool(settings.KALI_IP),
        "wazuh_configured": bool(settings.WAZUH_IP),
        "fortigate_configured": bool(settings.FORTIGATE_IP),
        "win10_configured": bool(settings.WIN10_IP),
        "ad_configured": bool(settings.AD_IP),
        "metasploitable_configured": bool(settings.METASPLOITABLE_IP),
        "n8n_configured": bool(settings.N8N_WEBHOOK_URL),
    }


@router.get("/api/health/tools")
async def tools_health_check():
    """Live health check for all connected SOC tools — real connectivity tests."""
    import httpx
    results = {}

    # ── Ollama: GET /api/tags ──
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            results["ollama"] = {
                "status": "online" if resp.status_code == 200 else "offline",
                "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                "label": "🟢 Live — real health check",
            }
    except Exception as e:
        results["ollama"] = {"status": "offline", "error": str(e)[:100], "label": "🟢 Live — real health check"}

    # ── n8n: GET /healthz (standard n8n health endpoint) ──
    n8n_base = settings.N8N_WEBHOOK_URL.replace("/webhook/execute-soar", "")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{n8n_base}/healthz")
            results["n8n"] = {
                "status": "online" if resp.status_code == 200 else "offline",
                "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                "label": "🟢 Live — real health check",
            }
    except Exception as e:
        results["n8n"] = {"status": "offline", "error": str(e)[:100], "label": "🟢 Live — real health check"}

    # ── FortiGate: API status check ──
    try:
        async with httpx.AsyncClient(timeout=5, verify=False) as client:
            resp = await client.get(
                f"https://{settings.FORTIGATE_IP}/api/v2/monitor/system/status",
                headers={"Authorization": f"Bearer {settings.FORTIGATE_API_KEY}"},
            )
            results["fortigate"] = {
                "status": "online" if resp.status_code in (200, 401) else "offline",
                "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                "label": "🟢 Live — real health check",
            }
    except Exception as e:
        results["fortigate"] = {"status": "offline", "error": str(e)[:100], "label": "🟢 Live — real health check"}

    # ── Wazuh: API connectivity check ──
    try:
        async with httpx.AsyncClient(timeout=5, verify=False) as client:
            resp = await client.get(f"https://{settings.WAZUH_IP}:55000/security/user/authenticate")
            results["wazuh"] = {
                "status": "online" if resp.status_code in (200, 401) else "offline",
                "latency_ms": int(resp.elapsed.total_seconds() * 1000),
                "label": "🟢 Live — real health check",
            }
    except Exception as e:
        results["wazuh"] = {"status": "offline", "error": str(e)[:100], "label": "🟢 Live — real health check"}

    return {"tools": results, "timestamp": datetime.utcnow().isoformat()}