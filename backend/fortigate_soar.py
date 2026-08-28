import logging
import httpx

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

async def block_ip_real(src_ip: str) -> dict:
    if not settings.FORTIGATE_API_KEY:
        logger.warning("FortiGate API key not configured. Cannot block IP directly.")
        return {"status": "failed", "message": "FortiGate API key not configured"}

    url = f"https://{settings.FORTIGATE_IP}/api/v2/cmdb/firewall/address"
    payload = {
        "name": f"blocked-{src_ip.replace('.', '-')}",
        "subnet": [src_ip, "255.255.255.255"],
    }

    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.FORTIGATE_API_KEY}"},
            )
            if resp.status_code == 200:
                logger.info(f"FortiGate: IP {src_ip} blocked successfully")
                return {"status": "success", "message": f"IP {src_ip} blocked on FortiGate"}
            else:
                logger.error(f"FortiGate API error: {resp.status_code} - {resp.text[:200]}")
                return {"status": "failed", "message": f"FortiGate API returned {resp.status_code}"}
    except Exception as e:
        logger.error(f"FortiGate connection failed: {e}")
        return {"status": "failed", "message": str(e)}
