"""SSH bridge for executing commands on Kali Linux and other lab VMs."""

import logging
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)


class LabBridge:
    """SSH client abstraction for executing commands on lab VMs."""

    def __init__(self):
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self, hostname: str, username: str, password: str, port: int = 22, timeout: int = 15):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(hostname=hostname, port=port, username=username, password=password, timeout=timeout)
        logger.info(f"SSH connected to {username}@{hostname}:{port}")

    def execute(self, command: str, timeout: int = 120) -> dict:
        if not self._client:
            return {"success": False, "exit_code": -1, "stdout": "", "stderr": "Not connected"}
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout.read().decode("utf-8", errors="replace"),
            "stderr": stderr.read().decode("utf-8", errors="replace"),
        }

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def run_ssh_command(hostname: str, username: str, password: str, command: str, port: int = 22, timeout: int = 120) -> dict:
    """Convenience function: connect, execute, close."""
    bridge = LabBridge()
    try:
        bridge.connect(hostname, username, password, port)
        return bridge.execute(command, timeout)
    finally:
        bridge.close()
