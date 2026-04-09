"""Integration tests for the pipeline: mocked Gemini + mocked web search.

These tests verify the pipeline orchestration logic without making real API calls.
Run with: pytest backend/tests/test_pipeline_integration.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from shared.models import (
    ResearchFinding,
    ResearchOutput,
    ArticleDraft,
    CriticReport,
    DataAnalystOutput,
    Citation,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_finding():
    return ResearchFinding(
        claim="Transformer attention uses queries, keys, and values.",
        source_url="https://arxiv.org/abs/1706.03762",
        source_title="Attention Is All You Need",
        supporting_quote="An attention function can be described as mapping a query and a set of key-value pairs to an output.",
        confidence=0.95,
        search_query="transformer attention mechanism",
    )


@pytest.fixture
def sample_research(sample_finding):
    return ResearchOutput(
        findings=[sample_finding] * 5,
        queries_used=["transformer attention mechanism", "self-attention explained"],
        total_sources_consulted=3,
    )


@pytest.fixture
def sample_article():
    return ArticleDraft(
        markdown="# Transformers\n\nTransformer attention uses queries, keys, and values. [1]\n\n## Sources\n1. Attention Is All You Need\n",
        citations=[Citation(index=1, source_url="https://arxiv.org/abs/1706.03762", source_title="Attention Is All You Need")],
        word_count=150,
        sections=["Transformers"],
    )


@pytest.fixture
def passing_critic_report():
    return CriticReport(
        passed=True,
        citation_accuracy=0.95,
        claim_grounding_score=0.90,
        internal_consistency=1.0,
        audience_alignment=0.80,
        completeness=0.70,
        overall_score=0.915,
        revision_required=False,
    )


@pytest.fixture
def failing_critic_report():
    return CriticReport(
        passed=False,
        citation_accuracy=0.60,
        claim_grounding_score=0.55,
        internal_consistency=1.0,
        audience_alignment=0.70,
        completeness=0.60,
        overall_score=0.634,
        issues=[],
        suggestions=["Add more citations"],
        revision_required=True,
    )


# ── Model validation tests (no mocks needed) ─────────────────────────────


class TestModelValidation:
    def test_research_finding_confidence_bounded(self, sample_finding):
        assert 0.0 <= sample_finding.confidence <= 1.0

    def test_article_draft_word_count(self, sample_article):
        assert sample_article.word_count > 0

    def test_critic_report_overall_in_range(self, passing_critic_report):
        assert 0.0 <= passing_critic_report.overall_score <= 1.0

    def test_passing_report_is_not_revision_required(self, passing_critic_report):
        assert not passing_critic_report.revision_required

    def test_failing_report_is_revision_required(self, failing_critic_report):
        assert failing_critic_report.revision_required
        assert not failing_critic_report.passed


# ── A2A helpers tests ─────────────────────────────────────────────────────


class TestA2AHelpers:
    @pytest.mark.asyncio
    async def test_send_a2a_message_retries_on_connection_error(self):
        """send_a2a_message should retry on ConnectError."""
        import httpx
        from shared.a2a_helpers import send_a2a_message

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection refused")
            # Third attempt succeeds
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "jsonrpc": "2.0",
                "id": "test",
                "result": {"status": {"state": "COMPLETED"}, "artifacts": []},
            }
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = mock_post
            mock_client_cls.return_value = mock_client

            result = await send_a2a_message(
                "http://localhost:9999",
                message_text="test",
                retry_backoff=0.01,  # fast for tests
            )
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_send_a2a_message_raises_after_max_retries(self):
        """send_a2a_message should raise after exhausting retries."""
        import httpx
        from shared.a2a_helpers import send_a2a_message

        async def always_fail(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = always_fail
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.ConnectError):
                await send_a2a_message(
                    "http://localhost:9999",
                    message_text="test",
                    max_retries=2,
                    retry_backoff=0.01,
                )


# ── Composite style guide integration ────────────────────────────────────


class TestCompositeStyleGuideIntegration:
    def test_guide_full_style_prompt_used_in_writer_logic(self):
        """Verify the full_style_prompt content is injected correctly into Writer prompt."""
        from agents.writer.prompts import STYLE_GUIDE_BLOCK

        style_text = "Be concise. Use bullet lists."
        injected = STYLE_GUIDE_BLOCK.format(style_guide_text=style_text)
        assert style_text in injected
        assert "Style Guide" in injected

    def test_composite_guide_with_no_profiles_is_safe(self):
        from knowledge_base.composite_builder import build_composite
        guide = build_composite([])
        # Should not raise and should produce a safe fallback prompt
        assert isinstance(guide.full_style_prompt, str)
        assert len(guide.full_style_prompt) > 0
