"""WebSocket connection manager for real-time pipeline events."""

from __future__ import annotations

import json
import logging
from typing import Any

import socketio

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


class WebSocketManager:
    """Manages WebSocket connections and broadcasts pipeline events."""

    def __init__(self, server: socketio.AsyncServer):
        self.server = server
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.event
        async def connect(sid, environ):
            logger.info(f"Client connected: {sid}")

        @self.server.event
        async def disconnect(sid):
            logger.info(f"Client disconnected: {sid}")

    async def emit_event(self, event_type: str, data: Any):
        """Broadcast a pipeline event to all connected clients."""
        await self.server.emit("pipeline_event", {
            "type": event_type,
            "data": data if isinstance(data, dict) else {"message": str(data)},
        })

    async def emit_pipeline_event(self, event: dict):
        """Broadcast a PipelineEvent dict."""
        await self.server.emit("pipeline_event", event)


ws_manager = WebSocketManager(sio)
