"""System and task prompts for the Critic agent."""

CRITIC_SYSTEM_PROMPT = """\
You are a strict article quality evaluator. You assess articles for factual accuracy, \
citation quality, internal consistency, audience alignment, and completeness. \
You provide quantified scores and specific, actionable feedback.

You are the hallucination prevention layer. Be thorough and critical.
"""

EXTRACT_CLAIMS_PROMPT = """\
Extract all factual claims from the following article. A factual claim is any statement \
that asserts something as true about the world (not opinions, not hedged statements).

Article:
{article_text}

Return a JSON array of objects, each with:
- "claim": the factual statement
- "location": the section/paragraph where it appears (e.g., "Introduction, paragraph 2")
- "citation_index": the [n] citation number if present, or null if uncited
- "is_quantitative": true if the claim involves specific numbers/data

Return ONLY valid JSON.
"""

VERIFY_CITATION_PROMPT = """\
Determine whether the following source quote supports the given claim.

Claim: "{claim}"
Source quote: "{quote}"
Source: {source_title} ({source_url})

Does the quote SUPPORT, CONTRADICT, or provide INSUFFICIENT evidence for the claim?
Also rate how strong the support is (0.0-1.0).

Return JSON: {{"verdict": "SUPPORTS"|"CONTRADICTS"|"INSUFFICIENT", "strength": 0.0-1.0, "explanation": "..."}}
Return ONLY valid JSON.
"""

CHECK_CONSISTENCY_PROMPT = """\
Check whether these two claims from the same article are consistent with each other.

Claim A (from {location_a}): "{claim_a}"
Claim B (from {location_b}): "{claim_b}"

Are they CONSISTENT, CONTRADICTORY, or UNRELATED?
If contradictory, explain the contradiction.

Return JSON: {{"verdict": "CONSISTENT"|"CONTRADICTORY"|"UNRELATED", "explanation": "..."}}
Return ONLY valid JSON.
"""

EVALUATE_AUDIENCE_PROMPT = """\
Evaluate whether this article is appropriately written for the target audience.

Target audience: {audience}
Article excerpt (first 1000 words):
{article_excerpt}

Score the following (0.0-1.0):
1. vocabulary_appropriateness: Are technical terms appropriate for this audience?
2. explanation_depth: Are concepts explained at the right level?
3. engagement: Is the writing engaging for this audience?

Return JSON: {{"vocabulary_appropriateness": 0.0-1.0, "explanation_depth": 0.0-1.0, "engagement": 0.0-1.0, "overall": 0.0-1.0, "suggestions": ["..."]}}
Return ONLY valid JSON.
"""

EVALUATE_COMPLETENESS_PROMPT = """\
Given the original research topic and the article, evaluate how completely the article covers the topic.

Topic: "{topic}"
Article sections: {sections}
Number of unique sources cited: {num_sources}
Article word count: {word_count}

Score completeness (0.0-1.0) based on:
- Coverage of key aspects
- Depth of treatment
- Breadth of perspectives
- Adequate use of available sources

Return JSON: {{"score": 0.0-1.0, "missing_aspects": ["..."], "suggestions": ["..."]}}
Return ONLY valid JSON.
"""
