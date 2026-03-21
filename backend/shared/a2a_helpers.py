"""A2A protocol helpers: Agent Card loading, JSON-RPC utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import httpx

from shared.models import (
    AgentCard,
    JSONRPCRequest,
    JSONRPCResponse,
    MessagePart,
    A2AMessage,
    TaskState,
    new_id,
)

logger = logging.getLogger(__name__)


def load_agent_card(json_path: str | Path) -> AgentCard:
    """Load an AgentCard from a JSON file."""
    with open(json_path) as f:
        data = json.load(f)
    return AgentCard.model_validate(data)


async def fetch_agent_card(base_url: str, timeout: float = 5.0) -> Optional[AgentCard]:
    """Fetch an AgentCard from a remote agent's well-known endpoint."""
    url = f"{base_url}/.well-known/agent-card.json"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return AgentCard.model_validate(resp.json())
    except Exception as e:
        logger.warning(f"Failed to fetch agent card from {url}: {e}")
        return None


def build_jsonrpc_request(
    method: str,
    message_text: str = "",
    message_data: Optional[dict] = None,
    context_id: str = "",
    task_id: str = "",
    metadata: Optional[dict] = None,
) -> JSONRPCRequest:
    """Build a JSON-RPC 2.0 request for A2A communication."""
    parts: list[dict] = []
    if message_text:
        parts.append({"kind": "text", "text": message_text})
    if message_data:
        parts.append({"kind": "data", "data": message_data})

    params: dict = {
        "message": {
            "role": "user",
            "parts": parts,
            "contextId": context_id or new_id(),
            "taskId": task_id,
        },
        "configuration": {
            "acceptedOutputModes": ["text/plain", "application/json"],
            "historyLength": 0,
        },
    }
    if metadata:
        params["metadata"] = metadata

    return JSONRPCRequest(
        id=new_id(),
        method=method,
        params=params,
    )


async def send_a2a_message(
    agent_url: str,
    message_text: str = "",
    message_data: Optional[dict] = None,
    context_id: str = "",
    task_id: str = "",
    metadata: Optional[dict] = None,
    timeout: float = 120.0,
) -> JSONRPCResponse:
    """Send a JSON-RPC request to an A2A agent and return the response."""
    request = build_jsonrpc_request(
        method="SendMessage",
        message_text=message_text,
        message_data=message_data,
        context_id=context_id,
        task_id=task_id,
        metadata=metadata,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            agent_url,
            json=request.model_dump(),
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return JSONRPCResponse.model_validate(resp.json())


async def send_a2a_streaming(
    agent_url: str,
    message_text: str = "",
    message_data: Optional[dict] = None,
    context_id: str = "",
    task_id: str = "",
    metadata: Optional[dict] = None,
    timeout: float = 300.0,
):
    """Send a streaming JSON-RPC request and yield SSE events."""
    request = build_jsonrpc_request(
        method="SendStreamingMessage",
        message_text=message_text,
        message_data=message_data,
        context_id=context_id,
        task_id=task_id,
        metadata=metadata,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            agent_url,
            json=request.model_dump(),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip():
                        try:
                            yield json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse SSE data: {data_str[:100]}")
