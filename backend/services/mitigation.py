"""Mitigation service — FortiGate blocking and SOAR action execution."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def block_ip(src_ip: str, fortigate_ip: str, api_key: str) -> dict:
    """Block an IP on FortiGate via REST API."""
    import httpx

    if not api_key:
        logger.warning("FortiGate API key not configured. Cannot block IP.")
        return {"status": "failed", "message": "FortiGate API key not configured"}

    url = f"https://{fortigate_ip}/api/v2/cmdb/firewall/address"
    payload = {"name": f"blocked-{src_ip.replace('.', '-')}", "subnet": [src_ip, "255.255.255.255"]}

    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.post(url, json=payload, headers={"Authorization": f"Bearer {api_key}"})
            if resp.status_code in (200, 201):
                logger.info(f"FortiGate: IP {src_ip} blocked successfully")
                return {"status": "success", "message": f"IP {src_ip} blocked on FortiGate"}
            logger.error(f"FortiGate API error: {resp.status_code} - {resp.text[:200]}")
            return {"status": "failed", "message": f"FortiGate returned {resp.status_code}"}
    except Exception as e:
        logger.error(f"FortiGate connection failed: {e}")
        return {"status": "failed", "message": str(e)}


async def execute_n8n_webhook(webhook_url: str, payload: dict, timeout: int = 10) -> dict:
    """Send a payload to the n8n SOAR webhook."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            logger.info(f"n8n webhook responded: {resp.status_code}")
            return {"status": "success", "response_code": resp.status_code, "body": resp.text[:500]}
    except Exception as e:
        logger.warning(f"n8n webhook failed: {e}")
        return {"status": "failed", "error": str(e)}
