"""Shared state for the AgeixAISOC application."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("ageixaisoc.state")


class ConnectionManager:
    """Manages WebSocket connections for real-time dashboard streaming."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        message = json.dumps({"type": event_type, **data}, default=str)
        async with self._lock:
            dead = []
            for conn in self.active_connections:
                try:
                    await conn.send_text(message)
                except WebSocketDisconnect:
                    dead.append(conn)
                except Exception as e:
                    logger.error(f"WebSocket send error: {e}")
                    dead.append(conn)
            for d in dead:
                self.active_connections.remove(d)


ws_manager = ConnectionManager()
pending_decisions: Dict[str, Any] = {}
decision_history: List[Dict[str, Any]] = []

# Real running counters (survive HITL pops — drive KPIs & coverage)
threats_blocked: int = 0          # successful SOAR block actions (HITL-approved or gap-closed)
pipeline_runs: int = 0            # total completed pipeline runs this process lifetime
auto_resolved_count: int = 0      # alerts filtered by AI (is_threat: false, never reached HITL)

# Auto red-team task control (OFF by default — safety)
auto_attack_enabled: bool = False
auto_attack_task: Optional[asyncio.Task] = None
