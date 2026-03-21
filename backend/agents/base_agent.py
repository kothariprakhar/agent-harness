"""Base A2A-compliant agent: FastAPI app with Agent Card serving, JSON-RPC endpoints, SSE streaming."""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from shared.models import (
    AgentCard,
    JSONRPCRequest,
    JSONRPCResponse,
    TaskState,
    TaskStatus,
    TokenUsage,
    new_id,
)

logger = logging.getLogger(__name__)


class AgentExecutor(ABC):
    """Interface that each agent implements."""

    @abstractmethod
    async def execute(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> dict:
        """
        Process a task and return the result.

        Returns a dict with:
          - "status": TaskStatus dict
          - "artifacts": list of artifact dicts
          - "usage": TokenUsage dict (optional)
        """
        ...

    async def execute_streaming(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> AsyncGenerator[dict, None]:
        """
        Process a task with streaming status updates.
        Yields dicts that are SSE event payloads.
        Default implementation wraps execute() with WORKING -> COMPLETED.
        """
        # Emit WORKING status
        yield self._make_event(task_id, context_id, TaskState.WORKING, "Processing...")

        try:
            result = await self.execute(
                message_text, message_data, task_id, context_id, metadata
            )
            # Emit final result
            yield {
                "jsonrpc": "2.0",
                "id": new_id(),
                "result": {
                    "taskId": task_id,
                    "contextId": context_id,
                    "status": result.get("status", {"state": "COMPLETED", "message": "Done"}),
                    "artifacts": result.get("artifacts", []),
                },
            }
        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            yield self._make_event(task_id, context_id, TaskState.FAILED, str(e))

    @staticmethod
    def _make_event(
        task_id: str, context_id: str, state: TaskState, message: str
    ) -> dict:
        return {
            "jsonrpc": "2.0",
            "id": new_id(),
            "result": {
                "taskId": task_id,
                "contextId": context_id,
                "status": {"state": state.value, "message": message},
                "artifacts": [],
            },
        }


def create_agent_app(
    agent_card_path: str | Path,
    executor: AgentExecutor,
    agent_name: str = "agent",
) -> FastAPI:
    """Factory: creates a FastAPI app with A2A-compliant endpoints."""

    app = FastAPI(title=f"{agent_name} Agent")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load agent card
    with open(agent_card_path) as f:
        agent_card_data = json.load(f)
    agent_card = AgentCard.model_validate(agent_card_data)

    @app.get("/.well-known/agent-card.json")
    async def get_agent_card():
        return JSONResponse(content=agent_card.model_dump())

    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": agent_name}

    @app.post("/")
    async def handle_jsonrpc(request: Request):
        """JSON-RPC 2.0 dispatcher for A2A protocol."""
        body = await request.json()
        method = body.get("method", "")
        req_id = body.get("id", new_id())
        params = body.get("params", {})

        message = params.get("message", {})
        message_text = ""
        message_data = {}
        for part in message.get("parts", []):
            if part.get("kind") == "text":
                message_text += part.get("text", "")
            elif part.get("kind") == "data":
                message_data.update(part.get("data", {}))

        context_id = message.get("contextId", new_id())
        task_id = message.get("taskId", "") or new_id()
        metadata = params.get("metadata", {})

        if method == "SendMessage":
            try:
                result = await executor.execute(
                    message_text, message_data, task_id, context_id, metadata
                )
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "taskId": task_id,
                        "contextId": context_id,
                        "status": result.get("status", {"state": "COMPLETED", "message": "Done"}),
                        "artifacts": result.get("artifacts", []),
                    },
                })
            except Exception as e:
                logger.exception(f"SendMessage failed: {e}")
                return JSONResponse(content={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(e)},
                })

        elif method == "SendStreamingMessage":
            async def event_generator():
                async for event in executor.execute_streaming(
                    message_text, message_data, task_id, context_id, metadata
                ):
                    yield {"data": json.dumps(event)}

            return EventSourceResponse(event_generator())

        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            })

    return app
