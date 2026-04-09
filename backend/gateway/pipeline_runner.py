"""Pipeline runner: invokes the Orchestrator and relays events to WebSocket clients."""

from __future__ import annotations

import logging
import time

from shared.a2a_helpers import send_a2a_message
from shared.config import ORCHESTRATOR_PORT
from shared.models import PipelineEvent, PipelineRequest, PipelineResult
from gateway.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

ORCHESTRATOR_URL = f"http://localhost:{ORCHESTRATOR_PORT}"


async def run_pipeline(
    request: PipelineRequest,
    style_guide: dict | None = None,
) -> PipelineResult:
    """Run the full research-to-article pipeline via the Orchestrator agent."""

    await ws_manager.emit_event("pipeline_started", {
        "prompt": request.prompt,
        "audience": request.audience,
        "tone": request.tone,
        "use_knowledge_base": request.use_knowledge_base,
    })

    message_data: dict = {
        "prompt": request.prompt,
        "audience": request.audience,
        "tone": request.tone,
    }
    if style_guide:
        message_data["style_guide"] = style_guide

    try:
        response = await send_a2a_message(
            agent_url=ORCHESTRATOR_URL,
            message_text=request.prompt,
            message_data=message_data,
            timeout=600.0,  # 10 min max for full pipeline
        )

        resp_dict = response.model_dump()
        result_data = resp_dict.get("result", {})
        status = result_data.get("status", {})

        # Extract pipeline result from artifacts
        artifacts = result_data.get("artifacts", [])
        pipeline_data = {}
        if artifacts:
            parts = artifacts[0].get("parts", [])
            for part in parts:
                if part.get("kind") == "data":
                    pipeline_data = part.get("data", {})
                    break

        if pipeline_data:
            pipeline_result = PipelineResult.model_validate(pipeline_data)
        else:
            pipeline_result = PipelineResult()

        await ws_manager.emit_event("pipeline_complete", {
            "status": status.get("state", "COMPLETED"),
            "message": status.get("message", ""),
            "total_time": pipeline_result.total_time_seconds,
        })

        return pipeline_result

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        await ws_manager.emit_event("pipeline_error", {"error": str(e)})
        raise
