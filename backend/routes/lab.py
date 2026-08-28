"""Lab management endpoints: status, health checks, attack simulation, auto red-team."""

import asyncio
import logging
import random
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

try:
    from config import settings
    from state import ws_manager
    import state as app_state
except ImportError:
    from backend.config import settings
    from backend.state import ws_manager
    from backend import state as app_state

try:
    from routes.dashboard import process_alert_background
except ImportError:
    from backend.routes.dashboard import process_alert_background

logger = logging.getLogger("ageixaisoc.routes.lab")
router = APIRouter(tags=["lab"])

# ── Attack catalog: type -> {label, command template (target_ip injected)} ──
ATTACK_CATALOG = {
    "port_scan": {
        "label": "Port Scan (Nmap)",
        "command": "nmap -sV -A {target_ip}",
    },
    "ssh_brute_force": {
        "label": "SSH Brute Force (Hydra)",
        "command": "hydra -l admin -P /usr/share/wordlists/fasttrack.txt ssh://{target_ip} -t 4 -f -V",
    },
    "web_scan": {
        "label": "Web Vulnerability Scan (Nikto)",
        "command": "nikto -h http://{target_ip}",
    },
    "smb_enum": {
        "label": "SMB Enumeration (enum4linux)",
        "command": "enum4linux -a {target_ip}",
    },
    "nmap_windows": {
        "label": "Nmap Windows (default)",
        "command": "nmap -sV -A {target_ip}",
    },
    "full_scan": {
        "label": "Full Network Scan",
        "command": "nmap -sC -sU -p- {target_ip}",
    },
}

# ── Target catalog: name -> settings attribute holding the IP ──
TARGET_CATALOG = {
    "win10": "WIN10_IP",
    "metasploitable": "METASPLOITABLE_IP",
    "wazuh": "WAZUH_IP",
    "kali": "KALI_IP",
    "win_server": "AD_IP",
}


def resolve_target_ip(target: str) -> str:
    """Resolve a target name (win10/metasploitable/wazuh/kali/win_server) to its IP."""
    attr = TARGET_CATALOG.get(str(target).lower())
    if attr:
        return getattr(settings, attr)
    if target in ("192.168.56.2", "192.168.56.10", "192.168.56.20", "192.168.56.30", "192.168.56.40", "192.168.56.100"):
        return target  # raw IP passed directly
    raise HTTPException(status_code=400, detail=f"Unknown target: {target}")


# ── Attack → Wazuh-style alert mapping (custom rule IDs = AI-learned, live on Wazuh) ──
ATTACK_RULE_MAP = {
    "port_scan": {"rule_id": 100003, "description": "AI-learned: Suspicious port scan activity from external host", "severity": 10},
    "nmap_windows": {"rule_id": 100003, "description": "AI-learned: Suspicious port scan activity from external host", "severity": 10},
    "full_scan": {"rule_id": 100003, "description": "AI-learned: Suspicious port scan activity from external host", "severity": 10},
    "ssh_brute_force": {"rule_id": 100001, "description": "AI-learned: SSH brute force attempt detected", "severity": 10},
    "web_scan": {"rule_id": 100002, "description": "AI-learned: Web vulnerability scan detected", "severity": 9},
    "smb_enum": {"rule_id": 100004, "description": "AI-learned: SMB enumeration detected", "severity": 9},
}

TARGET_AGENT_MAP = {
    "win10": "win10-victim",
    "metasploitable": "metasploitable2",
    "wazuh": "wazuh-manager",
    "kali": "kali",
    "win_server": "win-server-dc",
}


def _build_attack_alert(attack_id: str, attack_type: str, target: str, target_ip: str) -> Dict[str, Any]:
    """Build a Wazuh-style alert from a launched attack so the SOC pipeline + HITL card run immediately."""
    meta = ATTACK_RULE_MAP.get(attack_type, ATTACK_RULE_MAP["port_scan"])
    return {
        "alert_id": attack_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "rule_id": meta["rule_id"],
        "rule_description": meta["description"],
        "severity": meta["severity"],
        "source_ip": settings.KALI_IP,
        "destination_ip": target_ip,
        "protocol": "TCP",
        "agent_name": TARGET_AGENT_MAP.get(target.lower(), target.lower()),
        "agent_ip": target_ip,
        "location": TARGET_AGENT_MAP.get(target.lower(), target.lower()),
        "raw": f"{attack_type} attack launched against {target_ip}",
        "decoded": {"mitre_id": []},
        "_processed_at": datetime.utcnow().isoformat(),
        "_source": "lab_attack",
    }


def _enqueue_pipeline(background_tasks, alert: Dict[str, Any]):
    """Kick the SOC pipeline for an attack alert (via BackgroundTasks or a direct task)."""
    if background_tasks is not None:
        background_tasks.add_task(process_alert_background, alert["alert_id"], alert)
    else:
        asyncio.get_running_loop().create_task(process_alert_background(alert["alert_id"], alert))


class AttackRequest(BaseModel):
    attack_type: str = "nmap_windows"
    target: str = "win10"
    parameters: Optional[Dict[str, Any]] = {}


class AttackResult(BaseModel):
    success: bool
    attack_id: str
    output: str
    timestamp: str


class TriggerAttackRequest(BaseModel):
    attack_type: str = "port_scan"
    target: str = "win10"
    custom_command: Optional[str] = None


def run_ssh_command(attack_type: str, target_ip: str, timeout: int = 120) -> tuple:
    """Execute the real SSH command for an attack type on Kali. Returns (cmd, exit_status, combined_output)."""
    import paramiko

    entry = ATTACK_CATALOG.get(attack_type)
    if entry:
        cmd = entry["command"].format(target_ip=target_ip)
    elif attack_type == "custom":
        cmd = "echo 'No custom command supplied'"
    else:
        cmd = f"echo 'Unknown attack type: {attack_type}'"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=settings.KALI_IP, username=settings.KALI_USER, password=settings.KALI_PASS, timeout=15)
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        combined = output + ("\n[STDERR]\n" + error if error else "")
        return cmd, exit_status, combined
    finally:
        ssh.close()


@router.get("/api/lab/status")
async def lab_status():
    return {
        "kali": {"ip": settings.KALI_IP, "status": "online", "last_seen": datetime.utcnow().isoformat(), "services": {"ssh": True}},
        "wazuh": {"ip": settings.WAZUH_IP, "status": "online", "last_seen": datetime.utcnow().isoformat(), "services": {"wazuh_manager": True, "elasticsearch": True, "kibana": True}},
        "fortigate": {"ip": settings.FORTIGATE_IP, "status": "online", "last_seen": datetime.utcnow().isoformat(), "services": {"firewall": True, "vpn": True}},
        "win10": {"ip": settings.WIN10_IP, "status": "online", "last_seen": datetime.utcnow().isoformat(), "services": {"wazuh_agent": True, "sysmon": True, "rdp": True}},
        "win_server": {"ip": settings.AD_IP, "status": "online", "last_seen": datetime.utcnow().isoformat(), "services": {"domain_controller": True, "ldap": True, "dns": True}},
        "metasploitable": {"ip": settings.METASPLOITABLE_IP, "status": "online", "last_seen": datetime.utcnow().isoformat(), "services": {"ssh": True, "http": True, "samba": True}},
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/api/lab/launch-attack")
async def launch_attack(attack: AttackRequest, background_tasks: BackgroundTasks = None):
    attack_id = f"ATK-{uuid.uuid4().hex[:8].upper()}"
    logger.info(f"Launching attack {attack_id}: {attack.attack_type} -> {attack.target}")

    target_ip = attack.parameters.get("target_ip") or resolve_target_ip(attack.target)

    # Notify ThreatMap the moment an attack is launched (real SSH about to run)
    await ws_manager.broadcast("attack_launched", {
        "attack_id": attack_id,
        "attack_type": attack.attack_type,
        "target": attack.target,
        "target_ip": target_ip,
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        cmd, exit_status, combined = await asyncio.to_thread(run_ssh_command, attack.attack_type, target_ip)

        result = AttackResult(success=exit_status == 0, attack_id=attack_id, output=combined, timestamp=datetime.utcnow().isoformat())

        await ws_manager.broadcast("attack_result", {
            "attack_id": attack_id, "attack_type": attack.attack_type,
            "target": attack.target, "target_ip": target_ip, "command": cmd,
            "success": result.success, "timestamp": result.timestamp,
        })

        # ── HITL card immediately: run the SOC pipeline on the attack itself ──
        _enqueue_pipeline(background_tasks, _build_attack_alert(attack_id, attack.attack_type, attack.target, target_ip))
        logger.info(f"Attack {attack_id} queued into SOC pipeline -> HITL review")
        return result

    except Exception as e:
        logger.error(f"Attack launch failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/api/lab/check-network")
async def check_network():
    import paramiko
    results = {}
    vms = {
        "kali": {"ip": settings.KALI_IP, "user": settings.KALI_USER, "pass": settings.KALI_PASS, "port": 22},
        "wazuh": {"ip": settings.WAZUH_IP, "user": settings.WAZUH_USER, "pass": settings.WAZUH_PASS, "port": 22},
        "fortigate": {"ip": settings.FORTIGATE_IP, "port": 443, "api_key": settings.FORTIGATE_API_KEY},
        "win10": {"ip": settings.WIN10_IP, "ping": True},
        "win_server": {"ip": settings.AD_IP, "ping": True},
        "metasploitable": {"ip": settings.METASPLOITABLE_IP, "user": "msfadmin", "pass": "msfadmin", "port": 22},
    }

    import httpx
    for vm_name, vm_config in vms.items():
        try:
            if vm_name == "fortigate":
                async with httpx.AsyncClient(timeout=5, verify=False) as client:
                    resp = await client.get(f"https://{vm_config['ip']}/api/v2/cmdb/system/status",
                                            headers={"Authorization": f"Bearer {vm_config.get('api_key', '')}"})
                    results[vm_name] = {"status": "online" if resp.status_code == 200 else "error", "response_code": resp.status_code, "latency_ms": resp.elapsed.total_seconds() * 1000}
            elif vm_config.get("ping"):
                import subprocess
                ping = subprocess.run(["ping", "-n", "1", vm_config["ip"]], capture_output=True, timeout=5)
                results[vm_name] = {"status": "online" if ping.returncode == 0 else "offline", "latency_ms": 0}
            else:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname=vm_config["ip"], username=vm_config.get("user", "root"), password=vm_config.get("pass", ""), timeout=5)
                ssh.close()
                results[vm_name] = {"status": "online", "latency_ms": 0}
        except Exception as e:
            results[vm_name] = {"status": "offline", "error": str(e)}

    return {"results": results, "timestamp": datetime.utcnow().isoformat(), "all_online": all(r.get("status") == "online" for r in results.values())}


@router.post("/api/trigger-attack")
async def trigger_attack(attack_data: TriggerAttackRequest, background_tasks: BackgroundTasks = None):
    attack_id = f"ATK-{uuid.uuid4().hex[:8].upper()}"
    target_ip = resolve_target_ip(attack_data.target)
    logger.info(f"Trigger attack {attack_id}: {attack_data.attack_type} -> {target_ip}")

    # Notify ThreatMap the moment an attack is launched
    await ws_manager.broadcast("attack_launched", {
        "attack_id": attack_id,
        "attack_type": attack_data.attack_type,
        "target": attack_data.target,
        "target_ip": target_ip,
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        if attack_data.custom_command:
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=settings.KALI_IP, username=settings.KALI_USER, password=settings.KALI_PASS, timeout=15)
            stdin, stdout, stderr = ssh.exec_command(attack_data.custom_command, timeout=120)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")
            ssh.close()
            cmd = attack_data.custom_command
            combined = output + ("\n[STDERR]\n" + error if error else "")
        else:
            cmd, exit_status, combined = await asyncio.to_thread(run_ssh_command, attack_data.attack_type, target_ip)

        success = exit_status == 0

        await ws_manager.broadcast("attack_result", {
            "attack_id": attack_id, "attack_type": attack_data.attack_type,
            "target": attack_data.target, "target_ip": target_ip, "command": cmd,
            "success": success, "timestamp": datetime.utcnow().isoformat(),
        })

        # ── HITL card immediately: run the SOC pipeline on the attack itself ──
        # (enqueued whenever the command executed — a real attack attempt occurred,
        #  even if the tool exits non-zero, e.g. brute force found no valid password)
        _enqueue_pipeline(background_tasks, _build_attack_alert(attack_id, attack_data.attack_type, attack_data.target, target_ip))
        logger.info(f"Attack {attack_id} queued into SOC pipeline -> HITL review")

        return {"attack_id": attack_id, "success": success, "output": combined[:5000], "command": cmd, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Trigger attack failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))


# ── Auto Red-Team Loop (OFF by default) ────────────────

_AUTO_LOOP_LOCK = asyncio.Lock()
AUTO_ATTACK_TYPES = ["port_scan", "ssh_brute_force", "web_scan", "smb_enum", "nmap_windows"]
AUTO_TARGETS = ["win10", "metasploitable", "wazuh"]


async def _auto_attack_loop():
    logger.info("Auto red-team loop started (60-120s randomized interval)")
    while True:
        if not app_state.auto_attack_enabled:
            await asyncio.sleep(1)
            continue
        delay = random.randint(60, 120)
        await asyncio.sleep(delay)
        if not app_state.auto_attack_enabled:
            continue
        atype = random.choice(AUTO_ATTACK_TYPES)
        target = random.choice(AUTO_TARGETS)
        logger.info(f"[AUTO] Launching {atype} -> {target}")
        try:
            await trigger_attack(TriggerAttackRequest(attack_type=atype, target=target))
        except Exception as e:
            logger.error(f"[AUTO] Attack failed: {e}")
        await ws_manager.broadcast("auto_attack", {"attack_type": atype, "target": target, "status": "fired", "timestamp": datetime.utcnow().isoformat()})


async def _ensure_auto_task():
    if app_state.auto_attack_task is None or app_state.auto_attack_task.done():
        app_state.auto_attack_task = asyncio.create_task(_auto_attack_loop())


@router.post("/api/lab/auto-attack/toggle")
async def toggle_auto_attack(enabled: bool = True):
    """Start/stop the periodic automatic red-team loop. OFF by default."""
    app_state.auto_attack_enabled = bool(enabled)
    if app_state.auto_attack_enabled:
        await _ensure_auto_task()
    logger.info(f"Auto red-team {'ENABLED' if app_state.auto_attack_enabled else 'DISABLED'}")
    await ws_manager.broadcast("auto_attack_toggle", {"enabled": app_state.auto_attack_enabled, "timestamp": datetime.utcnow().isoformat()})
    return {"enabled": app_state.auto_attack_enabled, "label": "Auto Red Team (safety: OFF by default)", "timestamp": datetime.utcnow().isoformat()}


@router.get("/api/lab/auto-attack/status")
async def auto_attack_status():
    return {
        "enabled": app_state.auto_attack_enabled,
        "task_running": app_state.auto_attack_task is not None and not app_state.auto_attack_task.done(),
        "interval_range_sec": [60, 120],
        "attack_types": AUTO_ATTACK_TYPES,
        "targets": AUTO_TARGETS,
        "timestamp": datetime.utcnow().isoformat(),
    }
