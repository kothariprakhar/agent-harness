"""Unit tests for knowledge_base.composite_builder"""

import pytest
from shared.models import StyleProfile
from knowledge_base.composite_builder import build_composite, _render_style_prompt


def _make_profile(**kwargs) -> StyleProfile:
    defaults = dict(
        tone_descriptors=["analytical"],
        sentence_style="Medium-length sentences.",
        vocabulary_level="technical",
        formatting_patterns=["uses bullet lists"],
        structural_template=["Introduction", "Analysis", "Conclusion"],
        exemplary_passages=["This is an example passage."],
        avg_sentence_length=18.0,
        avg_section_count=3,
        uses_citations=True,
        uses_subheadings=True,
    )
    defaults.update(kwargs)
    return StyleProfile(**defaults)


def test_empty_profiles_returns_fallback():
    guide = build_composite([])
    assert guide.article_count == 0
    assert "No reference articles" in guide.full_style_prompt


def test_single_profile():
    profile = _make_profile()
    guide = build_composite([profile])
    assert guide.article_count == 1
    assert "analytical" in guide.avg_tone
    assert guide.avg_vocabulary_level == "technical"
    assert "Introduction" in guide.structural_template
    assert len(guide.exemplary_passages) >= 1
    assert "analytical" in guide.full_style_prompt


def test_multiple_profiles_aggregates_tone():
    profiles = [
        _make_profile(tone_descriptors=["analytical", "clear"]),
        _make_profile(tone_descriptors=["analytical", "concise"]),
        _make_profile(tone_descriptors=["conversational"]),
    ]
    guide = build_composite(profiles)
    # "analytical" appears in 2/3 profiles — should be top tone
    assert guide.avg_tone[0] == "analytical"
    assert guide.article_count == 3


def test_vocabulary_level_majority_vote():
    profiles = [
        _make_profile(vocabulary_level="technical"),
        _make_profile(vocabulary_level="technical"),
        _make_profile(vocabulary_level="accessible"),
    ]
    guide = build_composite(profiles)
    assert guide.avg_vocabulary_level == "technical"


def test_structural_template_threshold():
    # Section must appear in >= 30% of articles
    profiles = [
        _make_profile(structural_template=["Hook", "Analysis", "Conclusion"]),
        _make_profile(structural_template=["Hook", "Analysis", "Conclusion"]),
        _make_profile(structural_template=["Analysis", "Conclusion"]),
    ]
    guide = build_composite(profiles)
    # All appear in >=2/3 articles (67%), so all should be included
    assert "Analysis" in guide.structural_template
    assert "Conclusion" in guide.structural_template
    assert "Hook" in guide.structural_template


def test_exemplary_passages_capped_at_5():
    profiles = [
        _make_profile(exemplary_passages=[f"Passage {i}" for i in range(4)])
        for _ in range(3)
    ]
    guide = build_composite(profiles)
    assert len(guide.exemplary_passages) <= 5


def test_full_style_prompt_not_empty():
    guide = build_composite([_make_profile()])
    assert len(guide.full_style_prompt) > 50
    assert "Tone" in guide.full_style_prompt


def test_render_style_prompt_includes_subheadings():
    prompt = _render_style_prompt(
        avg_tone=["clear"],
        vocabulary_level="accessible",
        sentence_style="Short.",
        structural_template=["Intro", "Body"],
        formatting_rules=[],
        exemplary_passages=[],
        avg_sentence_len=15.0,
        uses_citations=False,
        uses_subheadings=True,
    )
    assert "Subheadings" in prompt or "subheadings" in prompt


def test_render_style_prompt_includes_citations():
    prompt = _render_style_prompt(
        avg_tone=["academic"],
        vocabulary_level="academic",
        sentence_style="Complex.",
        structural_template=[],
        formatting_rules=[],
        exemplary_passages=[],
        avg_sentence_len=25.0,
        uses_citations=True,
        uses_subheadings=False,
    )
    assert "Citations" in prompt or "citation" in prompt.lower()
