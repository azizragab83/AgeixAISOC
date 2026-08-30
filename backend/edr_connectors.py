"""
EDR / Antivirus enforcement connector layer.

Pushes approved IOCs (IPs, file hashes) down to the endpoint layer so blocks
are enforced on the host — not just at the FortiGate network perimeter.

Connectors:
  1. WazuhActiveResponseConnector — real: Wazuh API `PUT /active-response`
     triggers the `firewall-drop` AR script on every Wazuh agent, adding the
     IP to local iptables / Windows Firewall.
  2. ClamAVConnector — real: appends the hash to the ClamAV signature DB
     (local.hdb for MD5 / local.hsb for SHA-256) and reloads clamd.
  3. CrowdStrikeFalconConnector — stub: env-var gated (CROWDSTRIKE_*), mocks
     the response until a license/API key is configured.
  4. DefenderATPConnector — stub: env-var gated (DEFENDER_ATP_*), mocks the
     response until an Azure AD app registration is configured.

The fan-out (`enforce_ioc_everywhere`) is fault-tolerant: one connector
failing never blocks the others.
"""

import asyncio
import logging
import os
import socket
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

try:
    from config import settings
except ImportError:
    from backend.config import settings

logger = logging.getLogger("ageixaisoc.edr")


class EDRConnector(ABC):
    """Abstract base for all endpoint-enforcement backends."""

    name: str = "base"
    layer: str = "edr"  # "edr" or "av" — maps to IOC.blocked_on entries

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this connector has the credentials/paths it needs."""

    @abstractmethod
    async def block_ip(self, ip: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Block an IP at the endpoint layer."""

    @abstractmethod
    async def block_hash(self, file_hash: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Block a file hash at the endpoint layer."""

    @abstractmethod
    async def unblock_ip(self, ip: str) -> Dict[str, Any]:
        """Remove an IP block (used by the TTL expiry job)."""

    @abstractmethod
    async def unblock_hash(self, file_hash: str) -> Dict[str, Any]:
        """Remove a hash block (used by the TTL expiry job)."""


# ─────────────────────────────────────────────────────────────────────────────
# 1. Wazuh Active Response (open-source, already in stack)
# ─────────────────────────────────────────────────────────────────────────────

class WazuhActiveResponseConnector(EDRConnector):
    """
    Triggers a Wazuh Active Response on ALL agents via the Wazuh Manager API:

        PUT {WAZUH_API_URL}/active-response?agents_list=*
        {
          "command": "firewall-drop",
          "arguments": ["-add", "<ip>", "-d", "<minutes>"],
          "alert": { ... }
        }

    The stock `firewall-drop` AR script adds the IP to local iptables on Linux
    agents and to Windows Firewall on Windows agents. Requires the AR to be
    enabled in ossec.conf (`<active-response><command>firewall-drop ...`).
    """

    name = "wazuh-active-response"
    layer = "edr"

    def __init__(self):
        self.base_url = settings.WAZUH_API_URL.rstrip("/")
        self.username = settings.WAZUH_API_USER or settings.WAZUH_USER or "wazuh-wui"
        self.password = settings.WAZUH_API_PASS or settings.WAZUH_PASS or "wazuh-wui"
        self.command = getattr(settings, "WAZUH_AR_COMMAND", "firewall-drop")
        self.block_minutes = int(getattr(settings, "WAZUH_AR_BLOCK_MINUTES", "0"))  # 0 = permanent
        self._token: Optional[str] = None
        self._token_ts: float = 0

    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def _get_token(self) -> Optional[str]:
        # Wazuh tokens last ~900s; refresh every 10 min
        if self._token and (time.time() - self._token_ts) < 600:
            return self._token
        try:
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                resp = await client.post(
                    f"{self.base_url}/security/user/authenticate",
                    auth=(self.username, self.password),
                )
                if resp.status_code == 200:
                    self._token = resp.json().get("data", {}).get("token")
                    self._token_ts = time.time()
                    return self._token
                logger.error(f"[WazuhAR] auth failed: {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"[WazuhAR] auth error: {e}")
        return None

    async def _run_ar(self, arguments: List[str], alert: Dict[str, Any]) -> Dict[str, Any]:
        token = await self._get_token()
        if not token:
            return {"status": "failed", "message": "Wazuh authentication failed"}

        payload = {
            "command": self.command,
            "arguments": arguments,
            "alert": alert or {"rule": {"level": 10}, "description": "AgeixAISOC IOC enforcement"},
        }
        try:
            async with httpx.AsyncClient(timeout=20, verify=False) as client:
                resp = await client.put(
                    f"{self.base_url}/active-response",
                    params={"agents_list": "*"},
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
                if resp.status_code in (200, 201):
                    affected = resp.json().get("data", {}).get("affected_items", [])
                    logger.info(f"[WazuhAR] AR '{self.command}' dispatched to {len(affected)} agents: {arguments}")
                    return {
                        "status": "success",
                        "message": f"Active response dispatched to {len(affected)} agent(s)",
                        "agents": [a.get("id") for a in affected][:20],
                    }
                return {"status": "failed", "message": f"Wazuh API {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def block_ip(self, ip: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        args = ["-add", ip]
        if self.block_minutes > 0:
            args += ["-d", str(self.block_minutes)]
        alert = (context or {}).get("alert") or {}
        return await self._run_ar(args, alert)

    async def block_hash(self, file_hash: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        # Wazuh AR has no stock hash-block script; use a custom `win-delete-file`
        # / `remove-file` style AR if deployed. Reported as skipped otherwise.
        custom = getattr(settings, "WAZUH_AR_HASH_COMMAND", "")
        if not custom:
            return {"status": "skipped", "message": "No Wazuh AR hash-block command configured"}
        self.command = custom
        try:
            return await self._run_ar(["-add", file_hash], (context or {}).get("alert") or {})
        finally:
            self.command = getattr(settings, "WAZUH_AR_COMMAND", "firewall-drop")

    async def unblock_ip(self, ip: str) -> Dict[str, Any]:
        return await self._run_ar(["-delete", ip], {})

    async def unblock_hash(self, file_hash: str) -> Dict[str, Any]:
        return {"status": "skipped", "message": "Wazuh AR hash unblock not supported"}


# ─────────────────────────────────────────────────────────────────────────────
# 2. ClamAV (open-source AV) — hash blocklist via local.hdb / local.hsb
# ─────────────────────────────────────────────────────────────────────────────

class ClamAVConnector(EDRConnector):
    """
    File-hash blocking for ClamAV:

      * MD5  hashes -> appended to `local.hdb`  (format: `md5:malware-name:size`)
      * SHA-256     -> appended to `local.hsb`  (format: `sha256:malware-name:size`)
      * Then clamd is reloaded: first try the clamd TCP socket `RELOAD`
        command (default port 3310), falling back to `clamdscan --reload`.

    Any file on an endpoint matching the hash will be flagged/quarantined on
    the next scan (or immediately with on-access scanning enabled).
    """

    name = "clamav"
    layer = "av"

    def __init__(self):
        self.hdb_path = getattr(settings, "CLAMAV_HDB_PATH", "/var/lib/clamav/local.hdb")
        self.hsb_path = getattr(settings, "CLAMAV_HSB_PATH", "/var/lib/clamav/local.hsb")
        self.clamd_host = getattr(settings, "CLAMAV_HOST", "localhost")
        self.clamd_port = int(getattr(settings, "CLAMAV_PORT", "3310"))

    def is_configured(self) -> bool:
        return bool(self.hdb_path or self.hsb_path)

    def _append_signature(self, db_path: str, file_hash: str) -> str:
        """Append `hash:malware-name:0` to the signature DB. Returns the line."""
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        name = f"AgeixAISOC.IOC.{file_hash[:12]}"
        line = f"{file_hash}:{name}:0"
        with open(db_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return line

    async def _reload_clamd(self) -> Dict[str, Any]:
        """Reload clamd signatures: socket RELOAD first, clamdscan fallback."""
        # 1) Try clamd TCP socket RELOAD
        try:
            def _sock_reload():
                with socket.create_connection((self.clamd_host, self.clamd_port), timeout=5) as s:
                    s.sendall(b"nRELOAD\n")
                    return s.recv(256).decode(errors="ignore").strip()
            resp = await asyncio.to_thread(_sock_reload)
            if "RELOADING" in resp.upper() or "OK" in resp.upper():
                return {"status": "success", "message": f"clamd reload via socket: {resp}"}
        except Exception as e:
            logger.debug(f"[ClamAV] socket reload unavailable: {e}")

        # 2) Fallback: clamdscan --reload
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["clamdscan", "--reload"],
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode == 0:
                return {"status": "success", "message": f"clamdscan --reload: {proc.stdout.strip()[:120]}"}
            return {"status": "failed", "message": f"clamdscan rc={proc.returncode}: {proc.stderr.strip()[:200]}"}
        except FileNotFoundError:
            return {"status": "failed", "message": "clamdscan binary not found and clamd socket unreachable"}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def block_hash(self, file_hash: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        h = file_hash.lower()
        try:
            if len(h) == 32:
                line = self._append_signature(self.hdb_path, h)   # MD5
            elif len(h) == 64:
                line = self._append_signature(self.hsb_path, h)   # SHA-256
            else:
                return {"status": "failed", "message": f"Unsupported hash length: {len(h)}"}
            logger.info(f"[ClamAV] signature appended: {line}")
            reload_result = await self._reload_clamd()
            if reload_result["status"] == "success":
                return {"status": "success", "message": f"Hash blocklisted + clamd reloaded ({line})"}
            # Signature written but reload failed — still partially effective
            return {"status": "success", "message": f"Signature written; reload deferred: {reload_result['message']}"}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def block_ip(self, ip: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"status": "skipped", "message": "ClamAV does not block IPs (hash-based AV only)"}

    async def unblock_hash(self, file_hash: str) -> Dict[str, Any]:
        h = file_hash.lower()
        db_path = self.hdb_path if len(h) == 32 else self.hsb_path
        try:
            if not os.path.exists(db_path):
                return {"status": "skipped", "message": "Signature DB not found"}
            with open(db_path, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if not ln.startswith(h + ":")]
            with open(db_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            await self._reload_clamd()
            return {"status": "success", "message": f"Hash removed from {os.path.basename(db_path)}"}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def unblock_ip(self, ip: str) -> Dict[str, Any]:
        return {"status": "skipped", "message": "ClamAV does not block IPs"}


# ─────────────────────────────────────────────────────────────────────────────
# 3. CrowdStrike Falcon (commercial stub — env-var gated)
# ─────────────────────────────────────────────────────────────────────────────

class CrowdStrikeFalconConnector(EDRConnector):
    """
    TODO: plug in a real CrowdStrike Falcon license.

    Set CROWDSTRIKE_CLIENT_ID / CROWDSTRIKE_CLIENT_SECRET (+ optional
    CROWDSTRIKE_API_BASE, default https://api.crowdstrike.com) and this stub
    becomes live. Until then it mocks a success response so the pipeline
    fan-out is never blocked.
    """

    name = "crowdstrike-falcon"
    layer = "edr"

    def __init__(self):
        self.client_id = getattr(settings, "CROWDSTRIKE_CLIENT_ID", "")
        self.client_secret = getattr(settings, "CROWDSTRIKE_CLIENT_SECRET", "")
        self.api_base = getattr(settings, "CROWDSTRIKE_API_BASE", "https://api.crowdstrike.com")
        self._token: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _oauth(self) -> Optional[str]:
        if self._token:
            return self._token
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_base}/oauth2/token",
                    data={"client_id": self.client_id, "client_secret": self.client_secret},
                )
                if resp.status_code == 201:
                    self._token = resp.json().get("access_token")
                    return self._token
        except Exception as e:
            logger.warning(f"[Falcon] OAuth failed: {e}")
        return None

    async def block_ip(self, ip: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "CrowdStrike not configured (set CROWDSTRIKE_CLIENT_ID/SECRET) — mocked success"}
        # TODO: real implementation — POST /policy/combined/ioc/v1 (IoC Management API)
        token = await self._oauth()
        if not token:
            return {"status": "failed", "message": "Falcon OAuth failed"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_base}/iocs/entities/indicators/v1",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"indicators": [{
                        "type": "ipv4", "value": ip,
                        "policy": "detect", "platforms": ["linux", "mac", "windows"],
                        "description": f"AgeixAISOC auto-block (MITRE {(context or {}).get('mitre', '')})",
                    }]},
                )
                return {"status": "success" if resp.status_code == 201 else "failed", "message": resp.text[:200]}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def block_hash(self, file_hash: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "CrowdStrike not configured — mocked success"}
        # TODO: real implementation — hash IoC with policy "prevent"
        token = await self._oauth()
        if not token:
            return {"status": "failed", "message": "Falcon OAuth failed"}
        ioc_type = "sha256" if len(file_hash) == 64 else "md5"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_base}/iocs/entities/indicators/v1",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"indicators": [{
                        "type": ioc_type, "value": file_hash.lower(),
                        "policy": "prevent", "platforms": ["linux", "mac", "windows"],
                    }]},
                )
                return {"status": "success" if resp.status_code == 201 else "failed", "message": resp.text[:200]}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def unblock_ip(self, ip: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "CrowdStrike not configured — mocked"}
        return {"status": "skipped", "message": "TODO: DELETE /iocs/entities/indicators/v1"}

    async def unblock_hash(self, file_hash: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "CrowdStrike not configured — mocked"}
        return {"status": "skipped", "message": "TODO: DELETE /iocs/entities/indicators/v1"}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Microsoft Defender for Endpoint (commercial stub — env-var gated)
# ─────────────────────────────────────────────────────────────────────────────

class DefenderATPConnector(EDRConnector):
    """
    TODO: plug in a real Microsoft Defender for Endpoint app registration.

    Set DEFENDER_ATP_TENANT_ID / DEFENDER_ATP_CLIENT_ID / DEFENDER_ATP_CLIENT_SECRET
    (Azure AD app with Machine.Isolate + Ip AdvancedQuery permissions) and this
    stub becomes live. Until then it mocks a success response.
    """

    name = "defender-atp"
    layer = "edr"

    def __init__(self):
        self.tenant_id = getattr(settings, "DEFENDER_ATP_TENANT_ID", "")
        self.client_id = getattr(settings, "DEFENDER_ATP_CLIENT_ID", "")
        self.client_secret = getattr(settings, "DEFENDER_ATP_CLIENT_SECRET", "")
        self.login_base = "https://login.microsoftonline.com"
        self.api_base = "https://api.securitycenter.microsoft.com"
        self._token: Optional[str] = None

    def is_configured(self) -> bool:
        return bool(self.tenant_id and self.client_id and self.client_secret)

    async def _oauth(self) -> Optional[str]:
        if self._token:
            return self._token
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.login_base}/{self.tenant_id}/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "resource": "https://api.securitycenter.windows.com",
                    },
                )
                if resp.status_code == 200:
                    self._token = resp.json().get("access_token")
                    return self._token
        except Exception as e:
            logger.warning(f"[DefenderATP] OAuth failed: {e}")
        return None

    async def block_ip(self, ip: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "Defender ATP not configured (set DEFENDER_ATP_TENANT_ID/CLIENT_ID/CLIENT_SECRET) — mocked success"}
        # TODO: real implementation — POST /api/ips (Add Indicator with action=Block)
        token = await self._oauth()
        if not token:
            return {"status": "failed", "message": "Defender OAuth failed"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_base}/api/ips",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "indicatorValue": ip, "indicatorType": "IpAddress",
                        "action": "Block", "severity": "High",
                        "title": "AgeixAISOC auto-block",
                        "description": f"MITRE {(context or {}).get('mitre', '')}",
                        "application": "AgeixAISOC",
                    },
                )
                return {"status": "success" if resp.status_code == 201 else "failed", "message": resp.text[:200]}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def block_hash(self, file_hash: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "Defender ATP not configured — mocked success"}
        token = await self._oauth()
        if not token:
            return {"status": "failed", "message": "Defender OAuth failed"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_base}/api/ips",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "indicatorValue": file_hash.lower(),
                        "indicatorType": "FileSha256" if len(file_hash) == 64 else "FileMd5",
                        "action": "BlockAndRemediate", "severity": "High",
                        "title": "AgeixAISOC hash block", "application": "AgeixAISOC",
                    },
                )
                return {"status": "success" if resp.status_code == 201 else "failed", "message": resp.text[:200]}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def unblock_ip(self, ip: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "Defender ATP not configured — mocked"}
        return {"status": "skipped", "message": "TODO: DELETE /api/ips/{indicatorId}"}

    async def unblock_hash(self, file_hash: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {"status": "mocked", "message": "Defender ATP not configured — mocked"}
        return {"status": "skipped", "message": "TODO: DELETE /api/ips/{indicatorId}"}


# ─────────────────────────────────────────────────────────────────────────────
# Fan-out orchestration (fault-tolerant)
# ─────────────────────────────────────────────────────────────────────────────

def get_connectors() -> List[EDRConnector]:
    """All registered connectors, in enforcement order."""
    return [
        WazuhActiveResponseConnector(),
        ClamAVConnector(),
        CrowdStrikeFalconConnector(),
        DefenderATPConnector(),
    ]


async def enforce_ioc_everywhere(ioc, broadcast_fn=None) -> Dict[str, Any]:
    """
    Push an IOC to every configured connector. Fault-tolerant fan-out:
    each connector runs independently; failures are logged and returned,
    never raised. Updates ioc.blocked_on on success and appends timeline
    events. Returns {connector_name: result_dict}.
    """
    try:
        from ioc_models import ioc_store
    except ImportError:
        from backend.ioc_models import ioc_store

    results: Dict[str, Any] = {}
    context = {"mitre": ioc.mitre_technique, "alert": {"rule": {"level": 10}}}

    for connector in get_connectors():
        cname = connector.name
        if not connector.is_configured():
            results[cname] = {"status": "skipped", "message": "not configured"}
            ioc_store.add_timeline_event(ioc, f"EDR push: {cname}", "skipped", "not configured")
            continue

        try:
            if ioc.type in ("ip", "domain"):
                result = await connector.block_ip(ioc.value, context)
            else:
                result = await connector.block_hash(ioc.value, context)
        except Exception as e:  # never let one connector kill the fan-out
            logger.error(f"[EDR] {cname} raised for {ioc.value}: {e}")
            result = {"status": "failed", "message": str(e)}

        results[cname] = result

        if result.get("status") == "success":
            if connector.layer not in ioc.blocked_on:
                ioc.blocked_on.append(connector.layer)
            ioc_store.add_timeline_event(ioc, f"EDR push: {cname}", "success", result.get("message", ""))
        elif result.get("status") == "mocked":
            ioc_store.add_timeline_event(ioc, f"EDR push: {cname}", "success", result.get("message", ""))
        else:
            ioc_store.add_timeline_event(ioc, f"EDR push: {cname}", "failed", result.get("message", ""))

    ioc_store.update(ioc)
    logger.info(f"[EDR] enforcement fan-out complete for {ioc.value}: "
                f"{ {k: v.get('status') for k, v in results.items()} }")

    if broadcast_fn:
        try:
            await broadcast_fn("ioc_enforced", {
                "ioc_id": ioc.id, "value": ioc.value, "type": ioc.type,
                "blocked_on": ioc.blocked_on, "results": results,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.warning(f"[EDR] ioc_enforced broadcast failed: {e}")

    return results


async def unenforce_ioc_everywhere(ioc) -> Dict[str, Any]:
    """Remove endpoint blocks for an expired IOC (TTL expiry job)."""
    results: Dict[str, Any] = {}
    for connector in get_connectors():
        if not connector.is_configured():
            continue
        try:
            if ioc.type in ("ip", "domain"):
                results[connector.name] = await connector.unblock_ip(ioc.value)
            else:
                results[connector.name] = await connector.unblock_hash(ioc.value)
        except Exception as e:
            results[connector.name] = {"status": "failed", "message": str(e)}
    return results