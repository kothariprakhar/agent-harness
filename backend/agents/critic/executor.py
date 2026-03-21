"""Critic agent executor: evaluates articles for hallucination and quality."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from agents.base_agent import AgentExecutor
from agents.critic.prompts import (
    CRITIC_SYSTEM_PROMPT,
    EXTRACT_CLAIMS_PROMPT,
    VERIFY_CITATION_PROMPT,
    CHECK_CONSISTENCY_PROMPT,
    EVALUATE_AUDIENCE_PROMPT,
    EVALUATE_COMPLETENESS_PROMPT,
)
from shared.gemini_client import get_gemini_client
from shared.models import CriticReport, CriticIssue, TaskState, new_id
from shared.config import (
    CITATION_ACCURACY_THRESHOLD,
    CLAIM_GROUNDING_THRESHOLD,
    INTERNAL_CONSISTENCY_THRESHOLD,
    AUDIENCE_ALIGNMENT_THRESHOLD,
    COMPLETENESS_THRESHOLD,
    OVERALL_SCORE_THRESHOLD,
)

logger = logging.getLogger(__name__)


def _safe_json_parse(text: str) -> dict | list | None:
    """Parse JSON from LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


class CriticExecutor(AgentExecutor):
    async def execute(
        self,
        message_text: str,
        message_data: dict,
        task_id: str,
        context_id: str,
        metadata: dict,
    ) -> dict:
        client = get_gemini_client()

        article_markdown = message_data.get("article_markdown", message_text)
        citations = message_data.get("citations", [])
        research_findings = message_data.get("research_findings", [])
        topic = message_data.get("topic", "")
        audience = message_data.get("audience", "general")
        sections = message_data.get("sections", [])
        word_count = message_data.get("word_count", 0)

        issues: list[CriticIssue] = []
        all_suggestions: list[str] = []

        # ── 1. Extract claims ───────────────────────────────────────────
        claims_resp = await client.generate(
            prompt=EXTRACT_CLAIMS_PROMPT.format(article_text=article_markdown[:6000]),
            system_prompt=CRITIC_SYSTEM_PROMPT,
            agent_name="critic",
            temperature=0.2,
        )
        claims = _safe_json_parse(claims_resp.text)
        if not isinstance(claims, list):
            claims = []

        # ── 2. Citation accuracy ────────────────────────────────────────
        cited_claims = [c for c in claims if c.get("citation_index") is not None]
        supported_count = 0

        # Build citation -> finding mapping
        finding_by_url: dict[str, dict] = {}
        for f in research_findings:
            url = f.get("source_url", "")
            if url:
                finding_by_url[url] = f

        citation_by_index: dict[int, dict] = {}
        for c in citations:
            citation_by_index[c.get("index", 0)] = c

        for claim_obj in cited_claims[:15]:  # Cap to avoid rate limit exhaustion
            idx = claim_obj.get("citation_index")
            citation = citation_by_index.get(idx, {})
            source_url = citation.get("source_url", "")
            finding = finding_by_url.get(source_url)

            if not finding:
                issues.append(CriticIssue(
                    severity="error",
                    location=claim_obj.get("location", ""),
                    description=f"Citation [{idx}] references a source not in research findings",
                    suggestion="Remove this claim or find supporting research",
                ))
                continue

            verify_resp = await client.generate(
                prompt=VERIFY_CITATION_PROMPT.format(
                    claim=claim_obj.get("claim", ""),
                    quote=finding.get("supporting_quote", ""),
                    source_title=finding.get("source_title", ""),
                    source_url=source_url,
                ),
                system_prompt=CRITIC_SYSTEM_PROMPT,
                agent_name="critic",
                temperature=0.1,
            )
            verdict = _safe_json_parse(verify_resp.text)
            if isinstance(verdict, dict) and verdict.get("verdict") == "SUPPORTS":
                supported_count += 1
            else:
                verdict_str = verdict.get("verdict", "UNKNOWN") if isinstance(verdict, dict) else "PARSE_ERROR"
                explanation = verdict.get("explanation", "") if isinstance(verdict, dict) else ""
                issues.append(CriticIssue(
                    severity="warning" if verdict_str == "INSUFFICIENT" else "error",
                    location=claim_obj.get("location", ""),
                    description=f"Citation [{idx}] - {verdict_str}: {explanation}",
                    suggestion="Strengthen or replace this citation",
                ))

        citation_accuracy = supported_count / max(len(cited_claims), 1)

        # ── 3. Claim grounding score ────────────────────────────────────
        uncited_claims = [c for c in claims if c.get("citation_index") is None]
        for uc in uncited_claims:
            issues.append(CriticIssue(
                severity="warning",
                location=uc.get("location", ""),
                description=f"Uncited factual claim: \"{uc.get('claim', '')[:80]}\"",
                suggestion="Add a citation or mark as [UNGROUNDED]",
            ))

        total_claims = len(claims)
        grounded_claims = len(cited_claims)  # cited = grounded (simplified)
        claim_grounding = grounded_claims / max(total_claims, 1)

        # ── 4. Internal consistency ─────────────────────────────────────
        internal_consistency = 1.0
        # Check pairs of quantitative claims for contradictions
        quant_claims = [c for c in claims if c.get("is_quantitative")]
        if len(quant_claims) >= 2:
            # Check a sample of pairs (max 5 pairs to conserve rate limit)
            pairs_checked = 0
            for i in range(min(len(quant_claims) - 1, 3)):
                for j in range(i + 1, min(len(quant_claims), i + 3)):
                    consistency_resp = await client.generate(
                        prompt=CHECK_CONSISTENCY_PROMPT.format(
                            claim_a=quant_claims[i].get("claim", ""),
                            location_a=quant_claims[i].get("location", ""),
                            claim_b=quant_claims[j].get("claim", ""),
                            location_b=quant_claims[j].get("location", ""),
                        ),
                        system_prompt=CRITIC_SYSTEM_PROMPT,
                        agent_name="critic",
                        temperature=0.1,
                    )
                    result = _safe_json_parse(consistency_resp.text)
                    if isinstance(result, dict) and result.get("verdict") == "CONTRADICTORY":
                        internal_consistency = 0.0
                        issues.append(CriticIssue(
                            severity="error",
                            location=f"{quant_claims[i].get('location', '')} vs {quant_claims[j].get('location', '')}",
                            description=f"Contradiction: {result.get('explanation', '')}",
                            suggestion="Resolve the contradiction between these claims",
                        ))
                    pairs_checked += 1

        # ── 5. Audience alignment ───────────────────────────────────────
        audience_resp = await client.generate(
            prompt=EVALUATE_AUDIENCE_PROMPT.format(
                audience=audience,
                article_excerpt=article_markdown[:3000],
            ),
            system_prompt=CRITIC_SYSTEM_PROMPT,
            agent_name="critic",
            temperature=0.3,
        )
        audience_result = _safe_json_parse(audience_resp.text)
        audience_alignment = 0.7
        if isinstance(audience_result, dict):
            audience_alignment = float(audience_result.get("overall", 0.7))
            for s in audience_result.get("suggestions", []):
                all_suggestions.append(s)

        # ── 6. Completeness ─────────────────────────────────────────────
        completeness_resp = await client.generate(
            prompt=EVALUATE_COMPLETENESS_PROMPT.format(
                topic=topic,
                sections=json.dumps(sections),
                num_sources=len(set(f.get("source_url", "") for f in research_findings)),
                word_count=word_count,
            ),
            system_prompt=CRITIC_SYSTEM_PROMPT,
            agent_name="critic",
            temperature=0.3,
        )
        completeness_result = _safe_json_parse(completeness_resp.text)
        completeness = 0.6
        if isinstance(completeness_result, dict):
            completeness = float(completeness_result.get("score", 0.6))
            for s in completeness_result.get("suggestions", []):
                all_suggestions.append(s)
            for aspect in completeness_result.get("missing_aspects", []):
                all_suggestions.append(f"Consider covering: {aspect}")

        # ── Compute overall score and pass/fail ─────────────────────────
        overall = (
            citation_accuracy * 0.30
            + claim_grounding * 0.30
            + internal_consistency * 0.20
            + audience_alignment * 0.10
            + completeness * 0.10
        )

        passed = (
            citation_accuracy >= CITATION_ACCURACY_THRESHOLD
            and claim_grounding >= CLAIM_GROUNDING_THRESHOLD
            and internal_consistency >= INTERNAL_CONSISTENCY_THRESHOLD
            and audience_alignment >= AUDIENCE_ALIGNMENT_THRESHOLD
            and completeness >= COMPLETENESS_THRESHOLD
            and overall >= OVERALL_SCORE_THRESHOLD
        )

        report = CriticReport(
            passed=passed,
            citation_accuracy=round(citation_accuracy, 3),
            claim_grounding_score=round(claim_grounding, 3),
            internal_consistency=round(internal_consistency, 3),
            audience_alignment=round(audience_alignment, 3),
            completeness=round(completeness, 3),
            overall_score=round(overall, 3),
            issues=[CriticIssue(**i.model_dump()) for i in issues],
            suggestions=all_suggestions,
            revision_required=not passed,
        )

        state = "COMPLETED" if passed else "INPUT_REQUIRED"
        message = (
            f"Article {'PASSED' if passed else 'FAILED'} evaluation. "
            f"Overall: {overall:.1%} | Citations: {citation_accuracy:.1%} | "
            f"Grounding: {claim_grounding:.1%} | Consistency: {internal_consistency:.1%}"
        )

        return {
            "status": {"state": state, "message": message},
            "artifacts": [
                {
                    "parts": [{"kind": "data", "data": report.model_dump()}],
                    "mimeType": "application/json",
                }
            ],
        }
