import sys
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_health_has_status_key(self, client):
        r = client.get("/api/health")
        data = r.json()
        assert data["status"] == "healthy"

    def test_health_has_version(self, client):
        r = client.get("/api/health")
        assert "version" in r.json()


class TestLabEndpoints:
    def test_lab_status(self, client):
        r = client.get("/api/lab/status")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_lab_status_has_device_keys(self, client):
        r = client.get("/api/lab/status")
        data = r.json()
        assert len(data) > 0


class TestDashboardEndpoints:
    def test_metrics(self, client):
        r = client.get("/api/dashboard/metrics")
        assert r.status_code == 200

    def test_alerts(self, client):
        r = client.get("/api/alerts")
        assert r.status_code == 200

    def test_alerts_history(self, client):
        r = client.get("/api/alerts/history")
        assert r.status_code == 200

    def test_forensics_unknown(self, client):
        r = client.get("/api/forensics/nonexistent")
        assert r.status_code in (200, 404)


class TestPostEndpoints:
    def test_query_nl(self, client):
        r = client.post("/api/query/nl", json={"query": "show me critical alerts"})
        assert r.status_code == 200

    def test_rules_deploy(self, client):
        payload = {"title": "Test Rule", "mitre_id": ["T1078"], "level": "high"}
        r = client.post("/api/rules/deploy", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "rule_id" in data

    def test_soar_execute(self, client):
        payload = [{"action_type": "block_ip", "target": "10.0.0.5"}]
        r = client.post("/api/soar/execute", json=payload)
        assert r.status_code == 200

    def test_human_decision_unknown(self, client):
        payload = {"decision_id": "pytest-999", "action": "approved"}
        r = client.post("/api/human-decision", json=payload)
        assert r.status_code in (200, 404)

    def test_trigger_attack(self, client):
        r = client.post("/api/trigger-attack", json={"attack_type": "brute_force"})
        assert r.status_code == 200

    def test_launch_attack(self, client):
        r = client.post("/api/lab/launch-attack", json={"attack_type": "port_scan", "target": "192.168.56.20"})
        assert r.status_code == 200


class TestRAGEndpoints:
    def test_rag_stats(self, client):
        r = client.get("/api/rag/stats")
        assert r.status_code == 200
        data = r.json()
        assert "collections" in data
        assert "total_documents" in data

    def test_rag_search(self, client):
        r = client.post("/api/rag/search", json={"query": "critical alert", "top_k": 3})
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert data["query"] == "critical alert"

    def test_rag_search_with_kb_filter(self, client):
        r = client.post("/api/rag/search", json={"query": "threat actor", "kb_filter": "threat_intel"})
        assert r.status_code == 200

    def test_rag_ingest(self, client):
        r = client.post("/api/rag/ingest", json={"text": "Test document for ingestion", "kb_name": "learned_decisions"})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "doc_id" in data

    def test_rag_ingest_invalid_kb(self, client):
        r = client.post("/api/rag/ingest", json={"text": "test", "kb_name": "nonexistent"})
        assert r.status_code == 400


class TestWebhook:
    def test_wazuh_webhook(self, client):
        payload = {
            "rule_id": 1001,
            "rule_description": "Test rule",
            "severity": 10,
            "source_ip": "10.0.0.5",
            "agent_name": "test-agent",
        }
        r = client.post("/webhook/wazuh-alert", json=payload)
        assert r.status_code in (200, 202)
        data = r.json()
        assert data["status"] == "accepted"
