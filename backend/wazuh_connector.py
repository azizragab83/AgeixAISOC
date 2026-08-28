"""Wazuh API connector — fetch alerts and agent status."""

import logging
from typing import Any, Dict, List, Optional

import httpx

try:
    from config import settings
except ImportError:
    from backend.config import settings

logger = logging.getLogger(__name__)


class WazuhConnector:
    """Client for the Wazuh REST API (port 55000)."""

    def __init__(self, base_url: str = None, username: str = None, password: str = None):
        wazuh_port = getattr(settings, 'WAZUH_API_PORT', 55000)
        self.base_url = (base_url or f"https://{settings.WAZUH_IP}:{wazuh_port}").rstrip("/")
        self.username = username or settings.WAZUH_USER or "wazuh-wui"
        self.password = password or settings.WAZUH_PASS or "wazuh-wui"
        self._token: Optional[str] = None

    async def _get_token(self) -> Optional[str]:
        if self._token:
            return self._token
        try:
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                resp = await client.post(
                    f"{self.base_url}/security/user/authenticate",
                    auth=(self.username, self.password),
                )
                if resp.status_code == 200:
                    self._token = resp.json().get("data", {}).get("token")
                    return self._token
                logger.error(f"Wazuh auth failed: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Wazuh auth error: {e}")
        return None

    async def _get(self, path: str, params: dict = None) -> dict:
        token = await self._get_token()
        if not token:
            return {"error": "Wazuh authentication failed"}
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                resp = await client.get(
                    f"{self.base_url}{path}",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                return resp.json() if resp.status_code == 200 else {"error": f"Wazuh API: {resp.status_code}", "detail": resp.text[:500]}
        except Exception as e:
            return {"error": str(e)}

    async def get_alerts(self, limit: int = 50, severity: str = None) -> List[Dict[str, Any]]:
        params = {"limit": limit, "sort": "-timestamp"}
        if severity:
            try:
                params["rule.level"] = severity
            except Exception:
                pass
        result = await self._get("/security/alerts", params)
        return result.get("data", {}).get("affected_items", []) if "data" in result else []

    async def get_agents(self) -> List[Dict[str, Any]]:
        result = await self._get("/agents")
        return result.get("data", {}).get("affected_items", []) if "data" in result else []

    async def get_agent_status(self, agent_id: str = "all") -> dict:
        result = await self._get(f"/agents/{agent_id if agent_id != 'all' else ''}")
        return result.get("data", {}) if "data" in result else result

    async def health_check(self) -> dict:
        token = await self._get_token()
        return {"connected": token is not None, "base_url": self.base_url}


wazuh = WazuhConnector()
