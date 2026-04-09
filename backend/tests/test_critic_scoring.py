"""Unit tests for critic scoring logic (no LLM calls — tests pure computation)."""

import pytest
from shared.models import CriticReport, CriticIssue


def _make_report(**kwargs) -> CriticReport:
    defaults = dict(
        passed=False,
        citation_accuracy=0.9,
        claim_grounding_score=0.85,
        internal_consistency=1.0,
        audience_alignment=0.75,
        completeness=0.65,
        overall_score=0.0,
        style_match=0.0,
        issues=[],
        suggestions=[],
        revision_required=True,
    )
    defaults.update(kwargs)
    return CriticReport(**defaults)


def _compute_overall(r: CriticReport) -> float:
    return (
        r.citation_accuracy * 0.30
        + r.claim_grounding_score * 0.30
        + r.internal_consistency * 0.20
        + r.audience_alignment * 0.10
        + r.completeness * 0.10
    )


class TestCriticReportModel:
    def test_scores_bounded_between_0_and_1(self):
        r = _make_report(citation_accuracy=0.95, claim_grounding_score=0.80)
        assert 0.0 <= r.citation_accuracy <= 1.0
        assert 0.0 <= r.claim_grounding_score <= 1.0

    def test_invalid_score_raises(self):
        with pytest.raises(Exception):
            CriticReport(citation_accuracy=1.5)  # exceeds max

    def test_style_match_defaults_to_zero(self):
        r = _make_report()
        assert r.style_match == 0.0

    def test_issues_list_default_empty(self):
        r = _make_report()
        assert r.issues == []


class TestOverallScoreComputation:
    def test_perfect_scores_give_1_0(self):
        r = _make_report(
            citation_accuracy=1.0,
            claim_grounding_score=1.0,
            internal_consistency=1.0,
            audience_alignment=1.0,
            completeness=1.0,
        )
        assert round(_compute_overall(r), 5) == 1.0

    def test_zero_scores_give_0_0(self):
        r = _make_report(
            citation_accuracy=0.0,
            claim_grounding_score=0.0,
            internal_consistency=0.0,
            audience_alignment=0.0,
            completeness=0.0,
        )
        assert _compute_overall(r) == 0.0

    def test_weights_sum_to_1(self):
        weights = [0.30, 0.30, 0.20, 0.10, 0.10]
        assert sum(weights) == pytest.approx(1.0)

    def test_citation_and_grounding_dominate(self):
        # High citation + grounding, low everything else → still decent overall
        r = _make_report(
            citation_accuracy=1.0,
            claim_grounding_score=1.0,
            internal_consistency=0.0,
            audience_alignment=0.0,
            completeness=0.0,
        )
        overall = _compute_overall(r)
        assert overall == pytest.approx(0.60)

    def test_consistency_zero_fails_regardless_of_others(self):
        # Even with perfect other scores, consistency=0 → overall = 0.80 max
        r = _make_report(
            citation_accuracy=1.0,
            claim_grounding_score=1.0,
            internal_consistency=0.0,
            audience_alignment=1.0,
            completeness=1.0,
        )
        overall = _compute_overall(r)
        # 0.30 + 0.30 + 0.0 + 0.10 + 0.10 = 0.80
        assert overall == pytest.approx(0.80)

    def test_passing_threshold_requires_0_80(self):
        # Construct scores that hover just above/below 0.80
        r_pass = _make_report(
            citation_accuracy=0.90,
            claim_grounding_score=0.90,
            internal_consistency=1.0,
            audience_alignment=0.75,
            completeness=0.65,
        )
        r_fail = _make_report(
            citation_accuracy=0.75,
            claim_grounding_score=0.75,
            internal_consistency=1.0,
            audience_alignment=0.70,
            completeness=0.60,
        )
        assert _compute_overall(r_pass) >= 0.80
        assert _compute_overall(r_fail) < 0.80


class TestCriticIssue:
    def test_default_severity_is_warning(self):
        issue = CriticIssue(description="Something off")
        assert issue.severity == "warning"

    def test_error_severity(self):
        issue = CriticIssue(severity="error", description="Citation not found")
        assert issue.severity == "error"
