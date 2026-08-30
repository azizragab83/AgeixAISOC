"""
AgeixAISOC - FastAPI Backend Server
Main entry point that includes all route modules.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from config import settings
    from state import ws_manager
    from orchestrator import soc_runner
except ImportError:
    from backend.config import settings
    from backend.state import ws_manager
    from backend.orchestrator import soc_runner

try:
    from routes import health_router, lab_router, hitl_router, dashboard_router, ws_router, rag_router, ti_router, toolkit_router, data_sources_router, chat_router, ioc_router
except ImportError:
    from backend.routes import health_router, lab_router, hitl_router, dashboard_router, ws_router, rag_router, ti_router, toolkit_router, data_sources_router, chat_router, ioc_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ageixaisoc")

# ── FastAPI App ──────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("AgeixAISOC Backend Starting...")
    logger.info(f"  API:     http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"  WS:      ws://{settings.API_HOST}:{settings.API_PORT}/ws/dashboard")
    logger.info(f"  Ollama:  {settings.OLLAMA_BASE_URL}")
    logger.info(f"  n8n:     {settings.N8N_WEBHOOK_URL}")
    logger.info(f"  Kali:    {settings.KALI_IP}")
    logger.info(f"  Wazuh:   {settings.WAZUH_IP}")
    logger.info(f"  FortiGate: {settings.FORTIGATE_IP}")
    logger.info(f"  Win10:   {settings.WIN10_IP}")
    logger.info(f"  AD:      {settings.AD_IP}")
    logger.info(f"  Meta:    {settings.METASPLOITABLE_IP}")
    logger.info("=" * 60)
    yield
    logger.info("AgeixAISOC Backend shutting down...")
    for connection in ws_manager.active_connections.copy():
        try:
            await connection.close(code=1001, reason="Server shutting down")
        except Exception:
            pass

app = FastAPI(
    title="AgeixAISOC - Autonomous SOC Platform",
    version="2.1.0",
    description="AI-powered Security Operations Center with LangGraph orchestration, "
                "CrewAI agents, WebSocket real-time dashboard, and n8n SOAR integration.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Orchestrator Callback -> WebSocket Bridge ──

async def orchestrator_callback(event_type: str, data: dict):
    if event_type == "node_transition":
        await ws_manager.broadcast("agent_log", {
            "alert_id": data.get("alert_id", ""),
            "node": data.get("node", ""),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
            "logs": data.get("logs", []),
        })
    elif event_type == "pipeline_complete":
        dp = data.get("decision_package", {})
        synthesis = dp.get("master_synthesis", {}) or {}
        await ws_manager.broadcast("decision_package", {
            "alert_id": data.get("alert_id", ""),
            "decision_id": dp.get("decision_id", ""),
            "risk_score": synthesis.get("unified_risk_score") or dp.get("risk_score", 0),
            "risk_level": dp.get("risk_level", "unknown"),
            "mitre_id": dp.get("mitre_id", ""),
            "mitre_technique": dp.get("mitre_technique", ""),
            "threat_type": dp.get("threat_analysis", {}).get("threat_type", "unknown"),
            "summary": synthesis.get("executive_summary") or dp.get("threat_analysis", {}).get("summary", ""),
            "executive_summary": synthesis.get("executive_summary", ""),
            "correlated_threat_narrative": synthesis.get("correlated_threat_narrative", ""),
            "predicted_next_move": synthesis.get("predicted_next_move", ""),
            "recommendations": dp.get("recommendations", []),
            "status": dp.get("status", "pending"),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
            "master_synthesis": synthesis,
            "decision_package": dp,
        })
    elif event_type == "pipeline_start":
        await ws_manager.broadcast("pipeline_status", {
            "alert_id": data.get("alert_id", ""),
            "status": "running",
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
        })

soc_runner.register_callback(orchestrator_callback)

# ── Include Routers ─────────────────────────

app.include_router(health_router)
app.include_router(lab_router)
app.include_router(hitl_router)
app.include_router(dashboard_router)
app.include_router(ws_router)
app.include_router(rag_router)
app.include_router(ti_router)
app.include_router(toolkit_router)
app.include_router(data_sources_router)
app.include_router(chat_router)
app.include_router(ioc_router)

# ── Background Tasks (Threat Intel refresh every 15 min + MITRE on startup) ──

import asyncio
import os

async def _threat_intel_refresh_loop():
    """Refresh threat intel every 15 minutes from the live Feodo Tracker feed."""
    try:
        from services.threat_intel import refresh_threat_intel
    except ImportError:
        from backend.services.threat_intel import refresh_threat_intel

    # Initial refresh 30s after startup
    await asyncio.sleep(30)
    await refresh_threat_intel()

    while True:
        await asyncio.sleep(900)  # 15 minutes
        await refresh_threat_intel()


async def _auto_learn_loop():
    """Continuous learning from live internet threat sources (startup + every 30 min)."""
    try:
        from services.auto_learner import auto_learn_loop
    except ImportError:
        from backend.services.auto_learner import auto_learn_loop
    await auto_learn_loop(interval_minutes=30)


async def _mitre_startup_ingest():
    """One-time MITRE ATT&CK STIX download + RAG ingest (cached to disk)."""
    try:
        from services.mitre_loader import ingest_mitre_attack
    except ImportError:
        from backend.services.mitre_loader import ingest_mitre_attack
    try:
        count = await asyncio.to_thread(ingest_mitre_attack)
        if count:
            logger.info(f"MITRE ATT&CK startup ingest complete: {count} techniques")
    except Exception as e:
        logger.warning(f"MITRE startup ingest skipped: {e}")


async def _ioc_ttl_expiry_loop():
    """
    IOC feed/expiry job: every 15 minutes, expire IOCs past their ttl_hours,
    unblock them from FortiGate/EDR/AV via the connectors, and mark them
    status=expired. Broadcasts ioc_update for each swept IOC.
    """
    try:
        from ioc_models import ioc_store
        from edr_connectors import unenforce_ioc_everywhere
    except ImportError:
        from backend.ioc_models import ioc_store
        from backend.edr_connectors import unenforce_ioc_everywhere

    await asyncio.sleep(60)  # let the app finish starting up
    while True:
        try:
            expired = ioc_store.find_expired()
            for ioc in expired:
                ioc.status = "expired"
                ioc_store.add_timeline_event(ioc, "TTL expired", "success", f"ttl_hours={ioc.ttl_hours}")
                ioc_store.update(ioc)
                try:
                    results = await unenforce_ioc_everywhere(ioc)
                    logger.info(f"[IOC TTL] unblocked {ioc.value}: {results}")
                except Exception as e:
                    logger.error(f"[IOC TTL] unblock failed for {ioc.value}: {e}")
                await ws_manager.broadcast("ioc_update", {
                    "ioc_id": ioc.id, "value": ioc.value, "status": "expired",
                    "reason": "ttl_expired", "timestamp": datetime.utcnow().isoformat(),
                })
            if expired:
                logger.info(f"[IOC TTL] swept {len(expired)} expired IOC(s)")
        except Exception as e:
            logger.error(f"[IOC TTL] sweep error: {e}")
        await asyncio.sleep(900)  # 15 minutes


@app.on_event("startup")
async def _start_background_tasks():
    asyncio.create_task(_threat_intel_refresh_loop())
    asyncio.create_task(_mitre_startup_ingest())
    asyncio.create_task(_auto_learn_loop())
    asyncio.create_task(_ioc_ttl_expiry_loop())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info",
    )