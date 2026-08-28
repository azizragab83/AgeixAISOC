import sys
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest


AGENT_MODULES = [
    ("threat_detection", "threat_detection"),
    ("risk_scorer", "risk_scoring"),
    ("recommender", "recommendation"),
    ("threat_hunter", "threat_hunter"),
    ("forensics_agent", "forensics"),
    ("red_team", "red_team"),
    ("detection_eng", "forensics"),
]

REQUIRED_KEYS = {"agent_logs", "decision_package", "current_node"}

ALERT = {
    "alert_id": "UT-001",
    "raw_alert": {"src_ip": "10.0.0.5", "rule": {"level": 12}},
    "decision_package": {},
}


def _import_run(module_name):
    mod = __import__(f"backend.ai_agents.{module_name}", fromlist=["run"])
    return mod.run


class TestAgentFallbacks:
    @pytest.mark.parametrize("module,agent_name", AGENT_MODULES)
    def test_run_returns_dict_with_required_keys(self, module, agent_name):
        run_fn = _import_run(module)
        result = run_fn("UT-001", ALERT["raw_alert"], ALERT["decision_package"])
        assert isinstance(result, dict)
        assert REQUIRED_KEYS.issubset(result.keys()), f"missing keys: {REQUIRED_KEYS - result.keys()}"

    @pytest.mark.parametrize("module,agent_name", AGENT_MODULES)
    def test_run_agent_logs_is_list(self, module, agent_name):
        run_fn = _import_run(module)
        result = run_fn("UT-001", ALERT["raw_alert"], ALERT["decision_package"])
        assert isinstance(result["agent_logs"], list)
        assert len(result["agent_logs"]) >= 1

    @pytest.mark.parametrize("module,agent_name", AGENT_MODULES)
    def test_run_decision_package_is_dict(self, module, agent_name):
        run_fn = _import_run(module)
        result = run_fn("UT-001", ALERT["raw_alert"], ALERT["decision_package"])
        assert isinstance(result["decision_package"], dict)

    @pytest.mark.parametrize("module,agent_name,expected_node", [
        ("threat_detection", "threat_detection", "risk_scoring"),
        ("risk_scorer", "risk_scoring", "recommendation"),
        ("recommender", "recommendation", "threat_hunter"),
        ("threat_hunter", "threat_hunter", "forensics"),
        ("forensics_agent", "forensics", "red_team"),
        ("red_team", "red_team", "__end__"),
    ])
    def test_run_current_node(self, module, agent_name, expected_node):
        run_fn = _import_run(module)
        result = run_fn("UT-001", ALERT["raw_alert"], ALERT["decision_package"])
        assert result["current_node"] == expected_node


class TestThreatDetection:
    def test_analysis_keys_present(self):
        run_fn = _import_run("threat_detection")
        result = run_fn("UT-001", ALERT["raw_alert"], {})
        dp = result["decision_package"]
        assert "threat_analysis" in dp
        analysis = dp["threat_analysis"]
        for key in ("is_threat", "threat_type", "severity", "confidence"):
            assert key in analysis

    def test_mitre_id_set(self):
        run_fn = _import_run("threat_detection")
        result = run_fn("UT-001", ALERT["raw_alert"], {})
        dp = result["decision_package"]
        assert dp.get("mitre_id") or dp.get("mitre_attack_id")


class TestRiskScoring:
    def test_score_fields_present(self):
        run_fn = _import_run("risk_scorer")
        dp = {"threat_analysis": {"is_threat": True, "severity": "high"}}
        result = run_fn("UT-001", ALERT["raw_alert"], dp)
        rdp = result["decision_package"]
        for key in ("risk_score", "risk_level"):
            assert key in rdp


class TestRecommender:
    def test_recommendations_list(self):
        run_fn = _import_run("recommender")
        dp = {"threat_analysis": {}, "risk_score": 65, "mitre_id": "T1078"}
        result = run_fn("UT-001", ALERT["raw_alert"], dp)
        assert "recommendations" in result["decision_package"]
        recs = result["decision_package"]["recommendations"]
        assert isinstance(recs, list)
        assert len(recs) >= 1


class TestThreatHunter:
    def test_hunt_results_present(self):
        run_fn = _import_run("threat_hunter")
        dp = {"threat_analysis": {}, "mitre_id": "T1078"}
        result = run_fn("UT-001", ALERT["raw_alert"], dp)
        assert "threat_hunt_results" in result["decision_package"]


class TestForensics:
    def test_forensics_report_present(self):
        run_fn = _import_run("forensics_agent")
        dp = {"threat_analysis": {}, "threat_hunt_results": {}, "mitre_id": "T1078"}
        result = run_fn("UT-001", ALERT["raw_alert"], dp)
        assert "forensics_report" in result["decision_package"]
        report = result["decision_package"]["forensics_report"]
        for key in ("root_cause", "affected_systems", "containment_steps"):
            assert key in report


class TestRedTeam:
    def test_validation_present(self):
        run_fn = _import_run("red_team")
        dp = {
            "threat_analysis": {},
            "risk_score": 65,
            "recommendations": [],
            "threat_hunt_results": {},
            "forensics_report": {},
        }
        result = run_fn("UT-001", ALERT["raw_alert"], dp)
        assert "red_team_validation" in result["decision_package"]
        v = result["decision_package"]["red_team_validation"]
        for key in ("detection_quality", "red_team_score", "validation_summary"):
            assert key in v
