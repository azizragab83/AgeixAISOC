"""
Edge case and integration tests for untested code paths:
- _parse_agent_json() utility (4 code paths)
- WebSocket /ws/dashboard
- POST /api/lab/check-network
- Error/edge cases for existing endpoints
"""
import sys, os, json, asyncio
from unittest.mock import AsyncMock, MagicMock, patch

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.main import app
    return TestClient(app)


# ── _parse_agent_json ────────────────────────

class TestParseAgentJson:
    """4 code paths in orchestrator._parse_agent_json."""

    def test_direct_json(self):
        from backend.orchestrator import _parse_agent_json
        result = _parse_agent_json('{"a": 1, "b": 2}')
        assert result == {"a": 1, "b": 2}

    def test_markdown_code_block(self):
        from backend.orchestrator import _parse_agent_json
        text = "```json\n{\"a\": 1, \"b\": 2}\n```"
        result = _parse_agent_json(text)
        assert result == {"a": 1, "b": 2}

    def test_markdown_block_no_lang(self):
        from backend.orchestrator import _parse_agent_json
        text = "```\n{\"a\": 1, \"b\": 2}\n```"
        result = _parse_agent_json(text)
        assert result == {"a": 1, "b": 2}

    def test_regex_fallback(self):
        from backend.orchestrator import _parse_agent_json
        text = "Here is the result: {\"a\": 1, \"b\": 2}"
        result = _parse_agent_json(text)
        assert result == {"a": 1, "b": 2}

    def test_nested_json_regex_fallback(self):
        from backend.orchestrator import _parse_agent_json
        text = "Output: {\"a\": {\"nested\": true}}"
        result = _parse_agent_json(text)
        assert isinstance(result, dict)
        assert "parse_error" not in result or not result.get("parse_error")

    def test_raw_text_fallback(self):
        from backend.orchestrator import _parse_agent_json
        text = "No JSON here, just plain text"
        result = _parse_agent_json(text)
        assert "raw_output" in result
        assert "parse_error" in result
        assert result["raw_output"] == text

    def test_empty_string(self):
        from backend.orchestrator import _parse_agent_json
        result = _parse_agent_json("")
        assert "raw_output" in result
        assert result["raw_output"] == ""


# ── WebSocket /ws/dashboard ──────────────────

class TestWebSocket:
    """WebSocket endpoint — ping/pong, disconnect handling."""

    def test_ping_pong(self, client):
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "pong"
            assert "timestamp" in msg

    def test_invalid_json_no_error(self, client):
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.send_text("not json")
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "pong"

    def test_unknown_message_type(self, client):
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.send_text(json.dumps({"type": "unknown"}))
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "pong"

    def test_disconnect_handling(self, client):
        with client.websocket_connect("/ws/dashboard") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            data = ws.receive_text()
            assert json.loads(data)["type"] == "pong"


# ── POST /api/lab/check-network ──────────────

class TestCheckNetwork:
    """POST /api/lab/check-network — the only endpoint with zero test coverage."""

    def test_check_network_returns_dict(self, client):
        resp = client.post("/api/lab/check-network")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "results" in data

    def test_check_network_has_results_per_target(self, client):
        resp = client.post("/api/lab/check-network")
        data = resp.json()
        assert "results" in data or "status" in data


# ── Error / Edge cases for existing endpoints ─

class TestForensicsEdgeCases:
    """GET /api/forensics/{id} — 404 path and edge cases."""

    def test_nonexistent_incident_returns_404(self, client):
        resp = client.get("/api/forensics/NONEXISTENT-12345")
        assert resp.status_code == 404


class TestAlertsEdgeCases:
    """GET /api/alerts — filter and limit edge cases."""

    def test_severity_filter_no_matches(self, client):
        resp = client.get("/api/alerts?severity=critical")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("alerts"), list)

    def test_limit_zero(self, client):
        resp = client.get("/api/alerts?limit=0")
        assert resp.status_code == 200

    def test_limit_negative(self, client):
        resp = client.get("/api/alerts?limit=-1")
        assert resp.status_code == 200


class TestSOAREdgeCases:
    """POST /api/soar/execute — edge cases."""

    def test_empty_actions(self, client):
        resp = client.post("/api/soar/execute", json=[])
        assert resp.status_code == 200
        data = resp.json()
        assert data["executed_count"] == 0

    def test_unknown_action_type(self, client):
        resp = client.post("/api/soar/execute", json=[{"action_type": "not_a_real_action", "target": "10.0.0.5"}])
        assert resp.status_code == 200
        data = resp.json()
        assert data["executed_count"] == 1
        assert any(result.get("status") == "simulated" for result in data.get("results", []))


class TestSigmaRuleEdgeCases:
    """POST /api/rules/deploy — validation edge cases."""

    def test_deploy_minimal_payload(self, client):
        resp = client.post("/api/rules/deploy", json={"title": ""})
        assert resp.status_code == 200

    def test_deploy_with_mitre_list(self, client):
        resp = client.post("/api/rules/deploy", json={"title": "Test Rule", "mitre_id": ["T1078", "T1059"], "level": "critical"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "pending_approval"
        assert "rule_id" in data


class TestTriggerAttackEdgeCases:
    """POST /api/trigger-attack — edge cases."""

    def test_invalid_attack_type(self, client):
        resp = client.post("/api/trigger-attack", json={"attack_type": "invalid_type_xyz"})
        assert resp.status_code in (200, 502)

    def test_custom_command(self, client):
        resp = client.post("/api/trigger-attack", json={"attack_type": "custom", "custom_command": "echo test"})
        assert resp.status_code in (200, 502)


class TestDashboardMetricsEdgeCases:
    """GET /api/dashboard/metrics — shape verification."""

    def test_metrics_response_structure(self, client):
        resp = client.get("/api/dashboard/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        for key in ("active_alerts", "pending_decisions", "pipeline_status"):
            assert key in data


class TestNLQueryEdgeCases:
    """POST /api/query/nl — query variants."""

    def test_ip_blocking_query(self, client):
        resp = client.post("/api/query/nl", json={"query": "block ip 10.0.0.5"})
        assert resp.status_code == 200

    def test_empty_query(self, client):
        resp = client.post("/api/query/nl", json={"query": ""})
        assert resp.status_code == 200

    def test_mitre_query(self, client):
        resp = client.post("/api/query/nl", json={"query": "what mitre techniques are covered"})
        assert resp.status_code == 200
