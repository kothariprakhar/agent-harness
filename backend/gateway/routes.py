"""REST API routes for the Gateway."""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.models import PipelineRequest, PipelineResult
from gateway.pipeline_runner import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    audience: str = "general"
    tone: str = "informative"


class GenerateResponse(BaseModel):
    status: str
    message: str
    result: dict | None = None


# Store for completed pipeline results (in-memory for demo)
_results: dict[str, PipelineResult] = {}
_counter = 0


@router.post("/generate")
async def generate_article(req: GenerateRequest) -> GenerateResponse:
    """Start the research-to-article pipeline."""
    global _counter
    try:
        pipeline_req = PipelineRequest(
            prompt=req.prompt,
            audience=req.audience,
            tone=req.tone,
        )
        result = await run_pipeline(pipeline_req)
        _counter += 1
        result_id = str(_counter)
        _results[result_id] = result

        return GenerateResponse(
            status="completed",
            message=f"Article generated: {result.article.word_count} words, "
                    f"quality score: {result.evaluation.overall_score:.1%}",
            result={"id": result_id, **result.model_dump()},
        )
    except Exception as e:
        logger.exception(f"Generate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{result_id}")
async def get_result(result_id: str) -> dict:
    """Get a previously generated pipeline result."""
    result = _results.get(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result.model_dump()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "gateway"}
