"""Build a composite style guide from multiple style profiles — pure Python, no LLM calls."""

from __future__ import annotations

from collections import Counter

from shared.models import CompositeStyleGuide, StyleProfile


def build_composite(profiles: list[StyleProfile]) -> CompositeStyleGuide:
    """Aggregate multiple StyleProfiles into a single CompositeStyleGuide."""
    if not profiles:
        return CompositeStyleGuide(
            full_style_prompt="No reference articles uploaded. Use your default writing style."
        )

    # Aggregate tone descriptors by frequency
    tone_counter: Counter[str] = Counter()
    for p in profiles:
        tone_counter.update(p.tone_descriptors)
    avg_tone = [t for t, _ in tone_counter.most_common(4)]

    # Determine dominant vocabulary level
    vocab_counter: Counter[str] = Counter()
    for p in profiles:
        if p.vocabulary_level:
            vocab_counter[p.vocabulary_level] += 1
    avg_vocabulary_level = vocab_counter.most_common(1)[0][0] if vocab_counter else "accessible"

    # Merge structural templates — pick the most common section types
    section_counter: Counter[str] = Counter()
    for p in profiles:
        section_counter.update(p.structural_template)
    # Keep sections that appear in at least 30% of articles
    threshold = max(1, len(profiles) * 0.3)
    structural_template = [
        s for s, count in section_counter.most_common(10) if count >= threshold
    ]
    if not structural_template:
        structural_template = [s for s, _ in section_counter.most_common(5)]

    # Merge formatting patterns
    fmt_counter: Counter[str] = Counter()
    for p in profiles:
        fmt_counter.update(p.formatting_patterns)
    formatting_rules = [f for f, count in fmt_counter.most_common(8) if count >= threshold]
    if not formatting_rules:
        formatting_rules = [f for f, _ in fmt_counter.most_common(4)]

    # Select best exemplary passages (up to 5, prefer diversity across articles)
    exemplary_passages: list[str] = []
    for p in profiles:
        for passage in p.exemplary_passages:
            if len(exemplary_passages) < 5 and passage not in exemplary_passages:
                exemplary_passages.append(passage)

    # Compute average metrics
    avg_sentence_len = sum(p.avg_sentence_length for p in profiles) / len(profiles)
    uses_citations = sum(1 for p in profiles if p.uses_citations) > len(profiles) / 2
    uses_subheadings = sum(1 for p in profiles if p.uses_subheadings) > len(profiles) / 2

    # Render the full style prompt
    full_style_prompt = _render_style_prompt(
        avg_tone=avg_tone,
        vocabulary_level=avg_vocabulary_level,
        sentence_style=_aggregate_sentence_style(profiles),
        structural_template=structural_template,
        formatting_rules=formatting_rules,
        exemplary_passages=exemplary_passages,
        avg_sentence_len=avg_sentence_len,
        uses_citations=uses_citations,
        uses_subheadings=uses_subheadings,
    )

    return CompositeStyleGuide(
        article_count=len(profiles),
        avg_tone=avg_tone,
        avg_vocabulary_level=avg_vocabulary_level,
        structural_template=structural_template,
        formatting_rules=formatting_rules,
        exemplary_passages=exemplary_passages,
        full_style_prompt=full_style_prompt,
    )


def _aggregate_sentence_style(profiles: list[StyleProfile]) -> str:
    styles = [p.sentence_style for p in profiles if p.sentence_style]
    if not styles:
        return "Varied sentence lengths."
    if len(styles) == 1:
        return styles[0]
    return "; ".join(styles[:3])


def _render_style_prompt(
    avg_tone: list[str],
    vocabulary_level: str,
    sentence_style: str,
    structural_template: list[str],
    formatting_rules: list[str],
    exemplary_passages: list[str],
    avg_sentence_len: float,
    uses_citations: bool,
    uses_subheadings: bool,
) -> str:
    lines = [
        f"**Tone & Voice**: Write in a {', '.join(avg_tone)} tone.",
        f"**Vocabulary Level**: {vocabulary_level} — match this register throughout.",
        f"**Sentence Style**: {sentence_style} (avg ~{avg_sentence_len:.0f} words/sentence).",
    ]

    if structural_template:
        lines.append(f"**Article Structure**: Follow this section pattern: {' -> '.join(structural_template)}")

    if formatting_rules:
        lines.append(f"**Formatting**: {'; '.join(formatting_rules)}")

    if uses_subheadings:
        lines.append("**Subheadings**: Use subheadings (### level) within major sections.")

    if uses_citations:
        lines.append("**Citations**: Use inline citations in the style of the reference articles.")

    if exemplary_passages:
        lines.append("\n**Reference Passages** (match this writing style):")
        for i, passage in enumerate(exemplary_passages[:3], 1):
            # Truncate long passages
            truncated = passage[:500] + "..." if len(passage) > 500 else passage
            lines.append(f"\n> Example {i}:\n> {truncated}")

    return "\n".join(lines)
