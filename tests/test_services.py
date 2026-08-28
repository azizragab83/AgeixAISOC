import sys
import os
import asyncio

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pytest


class TestFortigateSoar:
    def test_block_ip_real_imports(self):
        from backend.fortigate_soar import block_ip_real
        assert callable(block_ip_real)

    def test_block_ip_real_returns_dict(self):
        from backend.fortigate_soar import block_ip_real
        result = asyncio.run(block_ip_real("10.0.0.5"))
        assert isinstance(result, dict)
        assert any(k in result for k in ("success", "error", "status", "message"))


class TestMitigation:
    def test_block_ip_imports(self):
        from backend.services.mitigation import block_ip
        assert callable(block_ip)

    def test_block_ip_returns_dict(self):
        from backend.services.mitigation import block_ip
        from backend.config import settings
        result = asyncio.run(block_ip("10.0.0.5", settings.FORTIGATE_IP, settings.FORTIGATE_API_KEY))
        assert isinstance(result, dict)

    def test_execute_n8n_webhook_imports(self):
        from backend.services.mitigation import execute_n8n_webhook
        assert callable(execute_n8n_webhook)

    def test_execute_n8n_webhook_returns_dict(self):
        from backend.services.mitigation import execute_n8n_webhook
        from backend.config import settings
        actions = [{"action_type": "block_ip", "target": "10.0.0.5"}]
        result = asyncio.run(execute_n8n_webhook(settings.N8N_WEBHOOK_URL, actions))
        assert isinstance(result, dict)


class TestLabBridge:
    def test_run_ssh_command_imports(self):
        from backend.lab_bridge import run_ssh_command
        assert callable(run_ssh_command)

    def test_run_ssh_command_returns_dict(self):
        from backend.lab_bridge import run_ssh_command
        result = run_ssh_command("192.168.56.10", "aziz", "8394", "echo test", timeout=2)
        assert isinstance(result, dict)


class TestWazuhConnector:
    def test_connector_imports(self):
        from backend.wazuh_connector import WazuhConnector
        assert WazuhConnector

    def test_connector_init(self):
        from backend.wazuh_connector import WazuhConnector
        wc = WazuhConnector("192.168.56.30", "wazuh", "wazuh")
        assert "192.168.56.30" in wc.base_url
