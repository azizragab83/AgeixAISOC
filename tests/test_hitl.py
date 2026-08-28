"""
HITL (Human-in-the-Loop) integration tests.
Tests n8n webhook SOAR execution with FortiGate fallback.
"""
import sys, os, asyncio
from unittest.mock import AsyncMock, MagicMock, patch

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest
from fastapi.testclient import TestClient


# ── Fixtures ─────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def decision_pkg():
    return {
        "decision_id": "DEC-test-001",
        "alert_id": "ALERT-001",
        "status": "pending",
        "risk_score": 85,
        "risk_level": "high",
        "mitre_id": "T1078",
        "mitre_technique": "Valid Accounts",
        "threat_analysis": {
            "threat_type": "brute_force",
            "summary": "SSH brute force detected",
        },
        "recommendations": [
            {"action_type": "block_ip", "target": "10.0.0.5", "priority": 1, "description": "Block attacking IP"},
        ],
        "raw_alert": {"source_ip": "10.0.0.5"},
        "forensics_report": {"timeline": [], "containment_steps": []},
    }


# ── execute_block_ip tests ──────────────────

class TestExecuteBlockIp:
    """Tests for execute_block_ip — n8n webhook with FortiGate fallback."""

    def test_n8n_success(self):
        async def run():
            from backend.state import ws_manager
            from backend.routes.hitl import execute_block_ip

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value = mock_instance

                with patch.object(ws_manager, "broadcast", AsyncMock()):
                    await execute_block_ip("10.0.0.5")

                mock_instance.post.assert_called_once()
                call_kwargs = mock_instance.post.call_args[1]
                assert call_kwargs["json"]["action"] == "block_ip"
                assert call_kwargs["json"]["src_ip"] == "10.0.0.5"
        asyncio.run(run())

    def test_n8n_fails_fortigate_fallback_success(self):
        async def run():
            from backend.state import ws_manager
            from backend.routes.hitl import execute_block_ip

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(side_effect=Exception("n8n unreachable"))
                mock_client.return_value.__aenter__.return_value = mock_instance

                with patch.object(ws_manager, "broadcast", AsyncMock()):
                    with patch("backend.fortigate_soar.block_ip_real", AsyncMock(return_value={"status": "success", "message": "IP blocked on FortiGate"})) as mock_fallback:
                        await execute_block_ip("10.0.0.5")
                        mock_fallback.assert_called_once_with("10.0.0.5")
        asyncio.run(run())

    def test_both_n8n_and_fortigate_fail(self):
        async def run():
            from backend.state import ws_manager
            from backend.routes.hitl import execute_block_ip

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(side_effect=Exception("n8n unreachable"))
                mock_client.return_value.__aenter__.return_value = mock_instance

                with patch.object(ws_manager, "broadcast", AsyncMock()):
                    with patch("backend.fortigate_soar.block_ip_real", AsyncMock(side_effect=Exception("FortiGate unreachable"))) as mock_fallback:
                        await execute_block_ip("10.0.0.5")
                        mock_fallback.assert_called_once_with("10.0.0.5")
        asyncio.run(run())


# ── forward_to_n8n tests ────────────────────

class TestForwardToN8n:

    def test_forward_success(self, decision_pkg):
        async def run():
            from backend.state import ws_manager
            from backend.routes.hitl import forward_to_n8n, settings

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = '{"status": "ok"}'
                mock_response.raise_for_status = MagicMock()
                mock_instance.post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value = mock_instance

                with patch.object(ws_manager, "broadcast", AsyncMock()):
                    with patch.object(settings, "N8N_WEBHOOK_URL", "http://n8n:5678/webhook/execute-soar"):
                        await forward_to_n8n(decision_pkg)

                mock_instance.post.assert_called_once()
                call_kwargs = mock_instance.post.call_args[1]
                sent = call_kwargs["json"]
                assert sent["decision_id"] == "DEC-test-001"
                assert sent["risk_level"] == "high"
                assert len(sent["actions"]) == 1
        asyncio.run(run())

    def test_forward_no_webhook_url(self, decision_pkg):
        async def run():
            from backend.routes.hitl import forward_to_n8n, settings

            with patch.object(settings, "N8N_WEBHOOK_URL", ""):
                with patch("httpx.AsyncClient") as mock_client:
                    await forward_to_n8n(decision_pkg)
                    mock_client.assert_not_called()
        asyncio.run(run())

    def test_forward_http_error(self, decision_pkg):
        async def run():
            import httpx
            from backend.state import ws_manager
            from backend.routes.hitl import forward_to_n8n, settings

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(side_effect=httpx.RequestError("Connection refused", request=MagicMock()))
                mock_client.return_value.__aenter__.return_value = mock_instance

                with patch.object(ws_manager, "broadcast", AsyncMock()):
                    with patch.object(settings, "N8N_WEBHOOK_URL", "http://n8n:5678/webhook/execute-soar"):
                        await forward_to_n8n(decision_pkg)

                mock_instance.post.assert_called_once()
        asyncio.run(run())


# ── POST /api/human-decision endpoint tests ──

class TestHumanDecisionEndpoint:

    def test_approve_with_block_ip(self, client, decision_pkg):
        from backend.state import pending_decisions
        pending_decisions["DEC-test-001"] = decision_pkg
        resp = client.post("/api/human-decision", json={
            "decision_id": "DEC-test-001",
            "action": "approved",
            "metadata": {"src_ip": "10.0.0.5"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["action"] == "approved"

    def test_reject_decision(self, client, decision_pkg):
        from backend.state import pending_decisions
        pending_decisions["DEC-test-002"] = {**decision_pkg, "decision_id": "DEC-test-002"}
        resp = client.post("/api/human-decision", json={
            "decision_id": "DEC-test-002",
            "action": "rejected",
            "analyst_notes": "Routine port scan from known scanner - false positive",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["action"] == "rejected"
        assert "False Positive" in data["message"]
        assert "auto-suppress" in data["message"]

    def test_invalid_decision_id(self, client):
        resp = client.post("/api/human-decision", json={
            "decision_id": "DEC-nonexistent",
            "action": "approved",
        })
        assert resp.status_code == 404

    def test_invalid_action(self, client, decision_pkg):
        from backend.state import pending_decisions
        pending_decisions["DEC-test-003"] = {**decision_pkg, "decision_id": "DEC-test-003"}
        resp = client.post("/api/human-decision", json={
            "decision_id": "DEC-test-003",
            "action": "invalid_action",
        })
        assert resp.status_code == 400

    def test_approve_no_recommendations(self, client):
        from backend.state import pending_decisions
        pending_decisions["DEC-test-004"] = {"decision_id": "DEC-test-004", "status": "pending", "recommendations": [], "raw_alert": {}}
        resp = client.post("/api/human-decision", json={
            "decision_id": "DEC-test-004",
            "action": "approved",
        })
        assert resp.status_code == 200
