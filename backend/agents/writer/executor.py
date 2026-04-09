"""Writer agent executor: drafts and revises articles from research findings."""

from __future__ import annotations

import json
import logging
import re

from agents.base_agent import AgentExecutor
from agents.writer.prompts import WRITER_SYSTEM_PROMPT, WRITE_ARTICLE_PROMPT, REVISE_ARTICLE_PROMPT, STYLE_GUIDE_BLOCK
from shared.gemini_client import get_gemini_client
from shared.models import (
    ArticleDraft,
    Citation,
    ResearchFinding,
    ChartSpec,
    ConceptArtifact,
    CriticReport,
)

logger = logging.getLogger(__name__)


def _format_findings(findings: list[dict]) -> str:
    lines = []
    for i, f in enumerate(findings, 1):
        lines.append(
            f"[{i}] Claim: {f.get('claim', '')}\n"
            f"    Source: {f.get('source_title', '')} ({f.get('source_url', '')})\n"
            f"    Quote: \"{f.get('supporting_quote', '')}\"\n"
        )
    return "\n".join(lines) if lines else "(No research findings provided)"


def _format_charts(charts: list[dict]) -> str:
    if not charts:
        return "(No charts available)"
    lines = []
    for c in charts:
        lines.append(f"- {{{{chart:{c.get('chart_id', '')}}}}} — {c.get('title', '')} ({c.get('chart_type', '')})")
    return "\n".join(lines)


def _format_artifacts(artifacts: list[dict]) -> str:
    if not artifacts:
        return "(No interactive artifacts available)"
    lines = []
    for a in artifacts:
        lines.append(f"- {{{{artifact:{a.get('artifact_id', '')}}}}} — {a.get('title', '')}: {a.get('interactivity_description', '')}")
    return "\n".join(lines)


def _parse_article_output(text: str) -> ArticleDraft:
    """Parse the writer's output into an ArticleDraft."""
    # Try to extract JSON metadata block from the end
    citations: list[Citation] = []
    sections: list[str] = []
    markdown = text

    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        markdown = text[:json_match.start()].strip()
        try:
            meta = json.loads(json_match.group(1))
            for c in meta.get("citations", []):
                citations.append(Citation(
                    index=c.get("index", 0),
                    source_url=c.get("source_url", ""),
                    source_title=c.get("source_title", ""),
                    claim_text=c.get("claim_text", ""),
                ))
            sections = meta.get("sections", [])
        except (json.JSONDecodeError, TypeError):
            pass

    # Count words
    word_count = len(markdown.split())

    # Extract sections from headings if not in metadata
    if not sections:
        sections = re.findall(r"^#{1,3}\s+(.+)$", markdown, re.MULTILINE)

    return ArticleDraft(
        markdown=markdown,
        citations=citations,
        word_count=word_count,
        sections=sections,
    )


class WriterExecutor(AgentExecutor):
    async def execute(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> dict:
        client = get_gemini_client()

        topic = message_data.get("topic", message_text)
        audience = message_data.get("audience", "general")
        tone = message_data.get("tone", "informative")
        findings = message_data.get("research_findings", [])
        charts = message_data.get("chart_specs", [])
        artifacts = message_data.get("concept_artifacts", [])
        revision_feedback = message_data.get("revision_feedback")
        previous_draft = message_data.get("previous_draft")
        style_guide = message_data.get("style_guide")

        # Build system prompt — conditionally inject style guide
        system_prompt = WRITER_SYSTEM_PROMPT
        if style_guide and isinstance(style_guide, dict):
            style_text = style_guide.get("full_style_prompt", "")
            if style_text:
                system_prompt += STYLE_GUIDE_BLOCK.format(style_guide_text=style_text)

        if revision_feedback and previous_draft:
            # Revision pass
            issues_text = "\n".join(
                f"- [{issue.get('severity', 'warning')}] {issue.get('description', '')} "
                f"(Suggestion: {issue.get('suggestion', '')})"
                for issue in revision_feedback.get("issues", [])
            )
            suggestions_text = "\n".join(
                f"- {s}" for s in revision_feedback.get("suggestions", [])
            )

            prompt = REVISE_ARTICLE_PROMPT.format(
                previous_draft=previous_draft,
                issues_text=issues_text or "(none)",
                suggestions_text=suggestions_text or "(none)",
                findings_text=_format_findings(findings),
            )
        else:
            # First draft
            prompt = WRITE_ARTICLE_PROMPT.format(
                topic=topic,
                audience=audience,
                tone=tone,
                findings_text=_format_findings(findings),
                charts_text=_format_charts(charts),
                artifacts_text=_format_artifacts(artifacts),
            )

        resp = await client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            agent_name="writer",
            temperature=0.7,
        )

        draft = _parse_article_output(resp.text)

        return {
            "status": {
                "state": "COMPLETED",
                "message": f"Article drafted: {draft.word_count} words, {len(draft.sections)} sections",
            },
            "artifacts": [
                {
                    "parts": [{"kind": "data", "data": draft.model_dump()}],
                    "mimeType": "application/json",
                }
            ],
        }
