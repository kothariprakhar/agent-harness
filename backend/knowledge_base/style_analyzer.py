"""Style analysis via a single Gemini call per article."""

from __future__ import annotations

import logging
import re

from shared.gemini_client import get_gemini_client
from shared.models import StyleProfile

logger = logging.getLogger(__name__)

STYLE_ANALYSIS_PROMPT = """\
Analyze the writing style of the following article. Extract a detailed style profile.

Article text (excerpt):
{article_text}

Analyze and return:
1. tone_descriptors: 2-4 adjectives describing the tone (e.g., "analytical", "conversational", "authoritative")
2. sentence_style: brief description of sentence patterns (e.g., "Short, punchy sentences with occasional long explanatory ones")
3. vocabulary_level: one of "technical", "accessible", "academic", "casual"
4. formatting_patterns: list of formatting habits (e.g., "uses bullet lists", "bold key terms", "numbered steps")
5. structural_template: ordered list of section types used (e.g., ["Hook introduction", "Problem statement", "Analysis with examples", "Key takeaways", "Conclusion"])
6. exemplary_passages: 2-3 representative paragraphs copied verbatim from the article that best showcase the writing style
7. uses_citations: whether the article uses inline citations or references
8. uses_subheadings: whether the article uses subheadings within sections

Return as structured JSON matching the schema.
"""


def compute_structural_metrics(text: str) -> dict:
    """Compute structural metrics from text using pure Python (no LLM)."""
    sentences = re.split(r'[.!?]+\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    headings = re.findall(r'^#{1,6}\s+.+$', text, re.MULTILINE)

    avg_sentence_length = (
        sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    )

    return {
        "avg_sentence_length": round(avg_sentence_length, 1),
        "avg_section_count": len(headings),
    }


async def analyze_style(article_text: str) -> StyleProfile:
    """Analyze an article's style using one Gemini call with structured output."""
    client = get_gemini_client()

    # Truncate to first 6000 chars to stay within reasonable token limits
    excerpt = article_text[:6000]

    response = await client.generate(
        prompt=STYLE_ANALYSIS_PROMPT.format(article_text=excerpt),
        system_prompt="You are a writing style analyst. Return structured JSON.",
        agent_name="knowledge_base",
        response_schema=StyleProfile,
        temperature=0.3,
    )

    if response.parsed and isinstance(response.parsed, StyleProfile):
        profile = response.parsed
    else:
        logger.warning("Failed to parse style profile from Gemini, using defaults")
        profile = StyleProfile()

    # Overlay Python-computed structural metrics
    metrics = compute_structural_metrics(article_text)
    profile.avg_sentence_length = metrics["avg_sentence_length"]
    profile.avg_section_count = metrics["avg_section_count"]

    return profile
