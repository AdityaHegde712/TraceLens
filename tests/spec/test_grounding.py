"""Specification tests for the TraceLens Grounding Verifier and Next-Check Selector.

Strict TDD suite locking behavior for:
1. Grounding Verifier: Bipartite graph construction, net confidence calculation,
   conflict detection, abstention rules, and GroundingAssessment structure.
2. Next-Check Selector: Hypothesis entropy calculation, information gain evaluation,
   and optimal check selection to resolve diagnostic ambiguity.
"""

import pytest

from tracelens.grounding.discriminator import (
    NextCheckSelector,
    calculate_entropy,
)
from tracelens.grounding.verifier import (
    GroundingAssessment,
    GroundingVerifier,
)
from tracelens.models.triage import (
    EvidenceLink,
    EvidencePolarity,
    Hypothesis,
    NextCheckProposal,
)


class TestGroundingVerifier:
    """Locked assertions for dual-polarity evidence grounding and conflict verification."""

    def test_bipartite_graph_construction(self):
        verifier = GroundingVerifier()
        h1 = Hypothesis(
            hypothesis_id="H1",
            title="Milvus OOM",
            description="Out of memory in milvus pod",
            confidence=0.5,
            evidence_links=[
                EvidenceLink(
                    evidence_id="ev-1",
                    source_type="log",
                    polarity=EvidencePolarity.SUPPORT,
                    description="OOMKilled log message",
                    relevance_score=0.9,
                ),
                EvidenceLink(
                    evidence_id="ev-2",
                    source_type="metric",
                    polarity=EvidencePolarity.REFUTE,
                    description="CPU usage normal",
                    relevance_score=0.4,
                ),
            ],
        )

        assessment = verifier.verify([h1])
        assert isinstance(assessment, GroundingAssessment)
        assert "H1" in assessment.bipartite_graph
        graph_entry = assessment.bipartite_graph["H1"]

        assert graph_entry["supporting"] == ["ev-1"]
        assert graph_entry["refuting"] == ["ev-2"]
        assert pytest.approx(graph_entry["support_weight"]) == 0.9
        assert pytest.approx(graph_entry["refute_weight"]) == 0.4

    def test_net_confidence_calculation(self):
        """Formula: C(H) = max(0, min(1, (W_sup - lambda * W_ref) / (W_sup + W_ref)))
        With lambda = 1.0:
        W_sup = 0.8 + 0.8 = 1.6
        W_ref = 0.4
        W_total = 2.0
        C(H) = (1.6 - 1.0 * 0.4) / 2.0 = 1.2 / 2.0 = 0.60
        """
        verifier = GroundingVerifier(refutation_lambda=1.0, min_confidence_threshold=0.5)
        h = Hypothesis(
            hypothesis_id="H1",
            title="Index build contention",
            description="High lock contention",
            confidence=0.0,
            evidence_links=[
                EvidenceLink(
                    evidence_id="ev-1",
                    source_type="log",
                    polarity=EvidencePolarity.SUPPORT,
                    description="Lock wait timeout",
                    relevance_score=0.8,
                ),
                EvidenceLink(
                    evidence_id="ev-2",
                    source_type="trace",
                    polarity=EvidencePolarity.SUPPORT,
                    description="Span latency 4500ms on index_lock",
                    relevance_score=0.8,
                ),
                EvidenceLink(
                    evidence_id="ev-3",
                    source_type="metric",
                    polarity=EvidencePolarity.REFUTE,
                    description="Disk IO within normal envelope",
                    relevance_score=0.4,
                ),
            ],
        )

        assessment = verifier.verify([h])
        evaluated_h = assessment.hypotheses[0]

        assert pytest.approx(evaluated_h.confidence) == 0.60
        assert evaluated_h.support_count == 2
        assert evaluated_h.refutation_count == 1
        assert assessment.status == "diagnosed"
        assert assessment.primary_root_cause == "Index build contention"

    def test_abstention_on_contradictory_evidence(self):
        """If refuting weight >= 0.5 * supporting weight, verifier must abstain."""
        verifier = GroundingVerifier(contradiction_ratio_threshold=0.5)
        h = Hypothesis(
            hypothesis_id="H-conflict",
            title="Network partition",
            description="Upstream connection drop",
            confidence=0.0,
            evidence_links=[
                EvidenceLink(
                    evidence_id="ev-1",
                    source_type="log",
                    polarity=EvidencePolarity.SUPPORT,
                    description="Connection reset by peer",
                    relevance_score=0.8,
                ),
                EvidenceLink(
                    evidence_id="ev-2",
                    source_type="metric",
                    polarity=EvidencePolarity.REFUTE,
                    description="Zero packet loss recorded across interface",
                    relevance_score=0.5,  # 0.5 >= 0.5 * 0.8 (0.4) -> conflict!
                ),
            ],
        )

        assessment = verifier.verify([h])
        assert assessment.status == "abstained"
        assert assessment.primary_root_cause is None
        assert "Contradictory evidence" in (assessment.abstention_reason or "")

    def test_abstention_on_insufficient_evidence_weight(self):
        """If total evidence weight is below min_evidence_weight, verifier must abstain."""
        verifier = GroundingVerifier(min_evidence_weight=1.5)
        h = Hypothesis(
            hypothesis_id="H-sparse",
            title="Config mismatch",
            description="Wrong chunk size",
            confidence=0.0,
            evidence_links=[
                EvidenceLink(
                    evidence_id="ev-1",
                    source_type="config",
                    polarity=EvidencePolarity.SUPPORT,
                    description="chunk_size set to 256",
                    relevance_score=0.3,
                )
            ],
        )

        assessment = verifier.verify([h])
        assert assessment.status == "abstained"
        assert assessment.primary_root_cause is None
        assert "below threshold" in (assessment.abstention_reason or "")

    def test_inconclusive_on_competing_hypotheses(self):
        """When top two hypotheses have indistinguishable confidence, declare inconclusive."""
        verifier = GroundingVerifier(min_evidence_weight=0.5, ambiguity_margin=0.05)
        h1 = Hypothesis(
            hypothesis_id="H1",
            title="Cause A",
            description="High GC pause",
            confidence=0.0,
            evidence_links=[
                EvidenceLink(
                    evidence_id="ev-1",
                    source_type="metric",
                    polarity=EvidencePolarity.SUPPORT,
                    description="JVM GC latency spike",
                    relevance_score=0.9,
                )
            ],
        )
        h2 = Hypothesis(
            hypothesis_id="H2",
            title="Cause B",
            description="DB lock timeout",
            confidence=0.0,
            evidence_links=[
                EvidenceLink(
                    evidence_id="ev-2",
                    source_type="log",
                    polarity=EvidencePolarity.SUPPORT,
                    description="DB lock wait timeout",
                    relevance_score=0.9,
                )
            ],
        )

        assessment = verifier.verify([h1, h2])
        assert assessment.status == "inconclusive"
        assert assessment.primary_root_cause is None
        assert "competing hypotheses" in (assessment.abstention_reason or "").lower()


class TestNextCheckSelector:
    """Locked assertions for information-gain check selection and entropy reduction."""

    def test_calculate_entropy_equiprobable(self):
        """Two equiprobable hypotheses: H = - 2 * (0.5 * log2(0.5)) = 1.0 bit."""
        entropy = calculate_entropy([0.5, 0.5])
        assert pytest.approx(entropy) == 1.0

    def test_calculate_entropy_deterministic(self):
        """Single certain hypothesis: H = 0.0 bit."""
        entropy = calculate_entropy([1.0, 0.0])
        assert pytest.approx(entropy) == 0.0

    def test_select_optimal_check_maximizes_gain(self):
        selector = NextCheckSelector()
        h1 = Hypothesis(
            hypothesis_id="H1",
            title="Milvus OOM",
            description="OOM crash",
            confidence=0.5,
        )
        h2 = Hypothesis(
            hypothesis_id="H2",
            title="Rate limit throttling",
            description="HTTP 429 throttling",
            confidence=0.5,
        )

        check_low = NextCheckProposal(
            check_id="chk-low",
            target_source="config",
            query_or_action="cat /etc/hosts",
            expected_information_gain=0.1,
            rationale="Low value check",
        )
        check_high = NextCheckProposal(
            check_id="chk-high",
            target_source="metric",
            query_or_action="container_memory_working_set_bytes{pod=~'milvus.*'}",
            expected_information_gain=0.88,
            rationale="Directly distinguishes OOM crash from API throttling",
        )

        selected = selector.select_optimal_check([h1, h2], [check_low, check_high])
        assert selected is not None
        assert selected.check_id == "chk-high"
        assert selected.expected_information_gain == 0.88

    def test_select_optimal_check_empty_candidates(self):
        selector = NextCheckSelector()
        h1 = Hypothesis(hypothesis_id="H1", title="A", description="A", confidence=0.5)
        selected = selector.select_optimal_check([h1], [])
        assert selected is None
