import sys
import os

# Add project root so imports like "backend.main" work
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_agent_execute():
    """Mock all CrewAI agent execute_task calls to return valid JSON instantly."""
    mock_agent = MagicMock()

    def fake_execute(task, context=None, tools=None):
        raise Exception("Mocked agent failure")
    mock_agent.execute_task = fake_execute

    with patch("backend.agents.get_agent", return_value=mock_agent):
        yield


SAMPLE_ALERT = {
    "alert_id": "test-alert-001",
    "timestamp": "2026-07-22T10:00:00Z",
    "rule": {"id": 1001, "level": 12, "description": "Multiple failed logins"},
    "agent": {"id": "001", "name": "win10-victim"},
    "data": {
        "src_ip": "10.0.0.5",
        "dst_ip": "192.168.56.20",
        "user": "administrator",
        "winlog": {"event_id": 4625, "logon_type": 3},
    },
    "source_ip": "10.0.0.5",
    "description": "Multiple failed logins from 10.0.0.5",
    "severity": "high",
}


@pytest.fixture
def sample_alert():
    return dict(SAMPLE_ALERT)


@pytest.fixture
def client():
    from backend.main import app
    with TestClient(app) as c:
        yield c
