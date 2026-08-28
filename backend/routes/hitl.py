"""Human-in-the-Loop decision endpoint with n8n webhook + FortiGate fallback."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

try:
    from config import settings
    from state import ws_manager, pending_decisions, decision_history
    import state as app_state
except ImportError:
    from backend.config import settings
    from backend.state import ws_manager, pending_decisions, decision_history
    from backend import state as app_state

try:
    from rag_engine.rag_server import rag_server
except ImportError:
    from backend.rag_engine.rag_server import rag_server

try:
    import rag_memory
except ImportError:
    from backend import rag_memory

try:
    from routes.data_sources import register_resolved
except ImportError:
    from backend.routes.data_sources import register_resolved

logger = logging.getLogger("ageixaisoc.routes.hitl")
router = APIRouter(tags=["hitl"])


class HumanDecision(BaseModel):
    decision_id: str
    action: str
    analyst_notes: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = {}
    add_to_rag: Optional[bool] = False


@router.post("/api/human-decision")
async def human_decision(decision: HumanDecision, background_tasks: BackgroundTasks):
    decision_pkg = pending_decisions.get(decision.decision_id)
    if not decision_pkg:
        raise HTTPException(status_code=404, detail=f"Decision {decision.decision_id} not found or already processed.")

    logger.info(f"Human decision received: {decision.decision_id} -> {decision.action}")

    if decision.action == "approved":
        decision_pkg["status"] = "approved"
        decision_pkg["human_decision"] = "approved"
        decision_pkg["executed_at"] = datetime.utcnow().isoformat()

        recommendations = decision_pkg.get("recommendations", [])
        src_ip = decision.metadata.get("src_ip") or decision_pkg.get("raw_alert", {}).get("source_ip", "")

        block_actions = 0
        for rec in recommendations:
            if rec.get("action_type") == "block_ip":
                ip_to_block = rec.get("target") or src_ip
                if ip_to_block and ip_to_block != "unknown":
                    background_tasks.add_task(execute_block_ip, ip_to_block)
                    block_actions += 1
        if block_actions:
            app_state.threats_blocked += block_actions

        # ── Adaptive Learning: ingest approval as a Positive Example ──
        try:
            rag_memory.ingest_example(
                decision_id=decision.decision_id,
                alert_id=decision_pkg.get("alert_id", decision.decision_id),
                raw_alert=decision_pkg.get("raw_alert", {}),
                decision_package=decision_pkg,
                action="approved",
                analyst_notes=decision.analyst_notes,
                record_status="Approved — SOAR dispatched",
            )
        except Exception as e:
            logger.warning(f"Adaptive memory positive-example ingest failed: {e}")

        # ── Trigger the n8n SOAR webhook with the full decision package ──
        try:
            background_tasks.add_task(forward_to_n8n, decision_pkg)
        except Exception as e:
            logger.warning(f"n8n forward scheduling failed: {e}")

        result_message = "Decision approved. AI learned from your approval and SOAR actions were dispatched."
    elif decision.action == "rejected":
        decision_pkg["status"] = "Closed (False Positive)"
        decision_pkg["human_decision"] = "rejected"
        decision_pkg["executed_at"] = datetime.utcnow().isoformat()

        # ── Natural Adaptive Learning: ingest as a Negative Example (False Positive) ──
        try:
            ingest_result = rag_memory.ingest_example(
                decision_id=decision.decision_id,
                alert_id=decision_pkg.get("alert_id", decision.decision_id),
                raw_alert=decision_pkg.get("raw_alert", {}),
                decision_package=decision_pkg,
                action="rejected",
                analyst_notes=decision.analyst_notes,
                record_status="Closed (False Positive)",
            )
            logger.info(
                "Adaptive memory: rejection learned for %s (ingested=%s, kind=%s)",
                decision.decision_id, ingest_result.get("ingested"), ingest_result.get("kind"),
            )
        except Exception as e:
            logger.warning(f"Adaptive memory negative-example ingest failed: {e}")

        result_message = "Decision rejected. Marked as False Positive — AI will auto-suppress similar alerts in the future."
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {decision.action}. Must be 'approved' or 'rejected'.")

    await ws_manager.broadcast("decision_result", {
        "decision_id": decision.decision_id, "action": decision.action,
        "timestamp": datetime.utcnow().isoformat(), "status": decision_pkg["status"],
    })

    # ── Natural Adaptive Learning notification to analyst ──
    if decision.action == "rejected":
        await ws_manager.broadcast("ai_learning", {
            "message": "🧠 AI has learned from your feedback. Future similar alerts will be auto-suppressed.",
            "decision_id": decision.decision_id,
            "status": decision_pkg["status"],
            "timestamp": datetime.utcnow().isoformat(),
        })

    register_resolved(decision.decision_id)
    pending_decisions.pop(decision.decision_id, None)

    # ── RAG opt-in: only store what the analyst explicitly approves for AI memory ──
    if decision.add_to_rag:
        try:
            rag_server.ingest(
                kb="learned_decisions",
                documents=[{
                    "alert_id": decision.decision_id,
                    "action": decision.action,
                    "analyst_notes": decision.analyst_notes,
                    "timestamp": datetime.utcnow().isoformat(),
                    "decision_package": {k: v for k, v in decision_pkg.items() if k != "raw_alert"},
                }]
            )
            logger.info(f"Learned decision {decision.decision_id} ingested into RAG (learned_decisions KB)")
        except Exception as e:
            logger.warning(f"Failed to ingest decision into RAG: {e}")

        # Sigma rule generated by the Gap Loop — also opt-in
        sigma_rule = decision_pkg.get("sigma_rule_generated") or decision_pkg.get("sigma_rule")
        if sigma_rule:
            try:
                rag_server.ingest(
                    kb="sigma_rules",
                    documents=[{
                        "rule_id": sigma_rule.get("rule_id", ""),
                        "title": sigma_rule.get("title", ""),
                        "level": sigma_rule.get("level", "medium"),
                        "mitre_id": sigma_rule.get("mitre_id", []),
                        "description": sigma_rule.get("description", ""),
                        "deployment_status": decision_pkg.get("deployment_status", "unknown"),
                        "timestamp": datetime.utcnow().isoformat(),
                    }]
                )
                logger.info(f"Sigma rule {sigma_rule.get('rule_id', '')} ingested into RAG (sigma_rules KB, analyst opt-in)")
            except Exception as e:
                logger.warning(f"sigma_rules RAG ingest failed: {e}")

    await ws_manager.broadcast("metrics_update", {
        "active_alerts": len(pending_decisions),
        "threats_blocked": app_state.threats_blocked,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {"status": "success", "decision_id": decision.decision_id, "action": decision.action, "message": result_message, "timestamp": datetime.utcnow().isoformat()}


async def execute_block_ip(src_ip: str):
    n8n_url = "http://localhost:5678/webhook/execute-soar"
    payload = {"action": "block_ip", "src_ip": src_ip}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(n8n_url, json=payload)
            response.raise_for_status()
            logger.info(f"n8n webhook executed block_ip for {src_ip}: {response.status_code}")
            await ws_manager.broadcast("soar_execution", {"action": "block_ip", "src_ip": src_ip, "status": "executing", "source": "n8n", "timestamp": datetime.utcnow().isoformat()})
            return
    except Exception as e:
        logger.warning(f"n8n webhook failed for block_ip ({src_ip}): {e}. Falling back to direct FortiGate API.")

    try:
        try:
            from fortigate_soar import block_ip_real
        except ImportError:
            from backend.fortigate_soar import block_ip_real
        result = await block_ip_real(src_ip)
        logger.info(f"FortiGate fallback result for {src_ip}: {result}")
        await ws_manager.broadcast("soar_execution", {"action": "block_ip", "src_ip": src_ip, "status": result.get("status", "failed"), "source": "fortigate_direct", "message": result.get("message", ""), "timestamp": datetime.utcnow().isoformat()})
    except Exception as e2:
        logger.error(f"FortiGate fallback also failed for {src_ip}: {e2}")


async def forward_to_n8n(decision_pkg: dict):
    webhook_url = settings.N8N_WEBHOOK_URL
    if not webhook_url:
        logger.warning("n8n webhook URL not configured. Skipping SOAR execution.")
        return

    payload = {
        "decision_id": decision_pkg.get("decision_id", ""),
        "alert_id": decision_pkg.get("alert_id", ""),
        "risk_score": decision_pkg.get("risk_score", 0),
        "risk_level": decision_pkg.get("risk_level", "unknown"),
        "mitre_id": decision_pkg.get("mitre_id", ""),
        "mitre_technique": decision_pkg.get("mitre_technique", ""),
        "threat_summary": decision_pkg.get("threat_analysis", {}).get("summary", ""),
        "actions": decision_pkg.get("recommendations", []),
        "forensics": decision_pkg.get("forensics_report", {}),
        "iocs": decision_pkg.get("threat_hunt_results", {}).get("additional_iocs", []),
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"n8n webhook responded: {response.status_code} - {response.text[:200]}")
            await ws_manager.broadcast("soar_execution", {"decision_id": decision_pkg.get("decision_id", ""), "status": "executing", "webhook_url": webhook_url, "response_status": response.status_code, "timestamp": datetime.utcnow().isoformat()})
    except Exception as e:
        # Catch ALL failures (connection errors AND HTTP status errors such as
        # n8n returning 404 when the execute-soar workflow is not registered)
        # so a SOAR delivery problem never crashes the decision flow.
        logger.error(f"Failed to forward to n8n webhook: {e}")
        await ws_manager.broadcast("soar_execution", {"decision_id": decision_pkg.get("decision_id", ""), "status": "failed", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
