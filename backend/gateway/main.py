"""Gateway API: browser-facing REST + WebSocket hub."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway.websocket_manager import sio
from gateway.routes import router
from shared.config import GATEWAY_PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

app = FastAPI(title="AgentHarness Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Mount Socket.IO
socket_app = socketio.ASGIApp(sio, other_app=app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=GATEWAY_PORT)
