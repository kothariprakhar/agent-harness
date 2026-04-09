"""REST API routes for the Gateway."""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from shared.models import PipelineRequest, PipelineResult
from gateway.pipeline_runner import run_pipeline
from knowledge_base import store as kb_store
from knowledge_base.style_analyzer import analyze_style
from knowledge_base.composite_builder import build_composite

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    audience: str = "general"
    tone: str = "informative"
    use_knowledge_base: bool = False
    kb_tags: list[str] = []


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
        # Load composite style guide if KB is enabled
        style_guide_data: dict | None = None
        if req.use_knowledge_base:
            profiles = kb_store.get_all_style_profiles(
                tags=req.kb_tags if req.kb_tags else None
            )
            if profiles:
                guide = build_composite(profiles)
                style_guide_data = guide.model_dump()

        pipeline_req = PipelineRequest(
            prompt=req.prompt,
            audience=req.audience,
            tone=req.tone,
            use_knowledge_base=req.use_knowledge_base,
            kb_tags=req.kb_tags,
        )
        result = await run_pipeline(pipeline_req, style_guide=style_guide_data)
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


# ── Knowledge Base Endpoints ───────────────────────────────────────────────

@router.post("/kb/upload")
async def kb_upload(
    file: UploadFile = File(...),
    title: str = Form(""),
    tags: str = Form(""),
):
    """Upload an article to the knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    article = kb_store.save_article(
        filename=file.filename,
        file_content=content,
        title=title,
        tags=tag_list,
    )

    # Run style analysis (1 Gemini call)
    extracted_text = kb_store.get_extracted_text(article.id)
    if extracted_text:
        try:
            profile = await analyze_style(extracted_text)
            kb_store.save_style_profile(article.id, profile)
            article.style_profile = profile
        except Exception as e:
            logger.warning(f"Style analysis failed for {article.id}: {e}")

    return {"status": "uploaded", "article": article.model_dump()}


@router.get("/kb/articles")
async def kb_list_articles(tags: str = ""):
    """List all knowledge base articles."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    articles = kb_store.list_articles(tags=tag_list)
    return {"articles": [a.model_dump() for a in articles]}


@router.get("/kb/articles/{article_id}")
async def kb_get_article(article_id: str):
    """Get a knowledge base article with its style profile."""
    article = kb_store.get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"article": article.model_dump()}


@router.delete("/kb/articles/{article_id}")
async def kb_delete_article(article_id: str):
    """Delete an article from the knowledge base."""
    deleted = kb_store.delete_article(article_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"status": "deleted"}


@router.put("/kb/articles/{article_id}/tags")
async def kb_update_tags(article_id: str, tags: list[str]):
    """Update tags for an article."""
    article = kb_store.update_tags(article_id, tags)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"article": article.model_dump()}


@router.get("/kb/style-guide")
async def kb_get_style_guide(tags: str = ""):
    """Get the composite style guide from all (or tagged) articles."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    profiles = kb_store.get_all_style_profiles(tags=tag_list)
    guide = build_composite(profiles)
    return {"guide": guide.model_dump()}
