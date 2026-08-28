import sys
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest


class TestGraphStructure:
    def test_graph_has_expected_nodes(self):
        from backend.orchestrator import soc_runner
        nodes = sorted(soc_runner.graph.nodes.keys())
        expected = sorted(["__start__", "threat_detection", "risk_scoring",
                           "recommendation", "threat_hunter", "forensics",
                           "red_team", "blue_team", "detection_engineer",
                           "gap_closure", "ueba", "osint", "master_synthesis"])
        assert nodes == expected

    def test_graph_is_compiled(self):
        from backend.orchestrator import soc_runner
        assert hasattr(soc_runner.graph, "astream")

    def test_runner_has_callbacks_list(self):
        from backend.orchestrator import soc_runner
        assert hasattr(soc_runner, "callbacks")
        assert isinstance(soc_runner.callbacks, list)

    def test_graph_has_6_pipeline_nodes(self):
        from backend.orchestrator import build_soc_graph
        graph = build_soc_graph()
        assert "threat_detection" in graph.nodes
        assert "red_team" in graph.nodes
