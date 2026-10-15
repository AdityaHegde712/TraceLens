"""Dual-polarity evidence grounding verifier.

Constructs bipartite graphs connecting candidate hypotheses to supporting
and refuting evidence, scores net confidence with refutation penalties,
and enforces calibrated abstention policies against contradictions.
"""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

from tracelens.models.triage import EvidencePolarity, Hypothesis


class GroundingAssessment(BaseModel):
    """Structured assessment result produced by GroundingVerifier."""

    model_config = ConfigDict(extra="ignore")

    status: Literal["diagnosed", "abstained", "inconclusive"] = Field(
        ...,
        description="Verdict status: 'diagnosed', 'abstained', or 'inconclusive'.",
    )
    primary_root_cause: str | None = Field(
        default=None,
        description="Diagnosed primary root cause title or explanation.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Calibrated net confidence score in [0.0, 1.0].",
    )
    hypotheses: list[Hypothesis] = Field(
        default_factory=list,
        description="Evaluated hypotheses with updated confidence and counts.",
    )
    bipartite_graph: dict[str, Any] = Field(
        default_factory=dict,
        description="Bipartite graph mapping hypothesis IDs to supporting/refuting evidence.",
    )
    abstention_reason: str | None = Field(
        default=None,
        description="Explicit reasoning when verifier abstains or returns inconclusive.",
    )


class GroundingVerifier:
    """Verifies candidate hypotheses against grounded telemetry citations."""

    def __init__(
        self,
        refutation_lambda: float = 1.5,
        contradiction_ratio_threshold: float = 0.5,
        min_confidence_threshold: float = 0.6,
        min_evidence_weight: float = 1.0,
        ambiguity_margin: float = 0.05,
    ) -> None:
        """Initialize grounding verifier with calibration parameters.

        Args:
            refutation_lambda: Penalty multiplier for refuting evidence.
            contradiction_ratio_threshold: Ratio W_ref / W_sup triggering conflict abstention.
            min_confidence_threshold: Minimum net confidence needed to diagnose.
            min_evidence_weight: Minimum total evidence weight (W_sup + W_ref) required.
            ambiguity_margin: Confidence delta below which competing top hypotheses are ambiguous.
        """
        self.refutation_lambda = refutation_lambda
        self.contradiction_ratio_threshold = contradiction_ratio_threshold
        self.min_confidence_threshold = min_confidence_threshold
        self.min_evidence_weight = min_evidence_weight
        self.ambiguity_margin = ambiguity_margin

    def verify(self, hypotheses: list[Hypothesis]) -> GroundingAssessment:
        """Evaluate hypotheses, compute net confidences, and enforce abstention rules.

        Args:
            hypotheses: List of candidate hypotheses with attached EvidenceLinks.

        Returns:
            GroundingAssessment containing diagnosis status, confidence, and bipartite graph.
        """
        if not hypotheses:
            return GroundingAssessment(
                status="abstained",
                abstention_reason="No candidate hypotheses provided",
            )

        bipartite_graph: dict[str, Any] = {}
        evaluated_hypotheses: list[Hypothesis] = []

        for h in hypotheses:
            supporting = [
                e for e in h.evidence_links if e.polarity == EvidencePolarity.SUPPORT
            ]
            refuting = [
                e for e in h.evidence_links if e.polarity == EvidencePolarity.REFUTE
            ]

            w_sup = sum(e.relevance_score for e in supporting)
            w_ref = sum(e.relevance_score for e in refuting)
            w_total = w_sup + w_ref

            if w_total > 0.0:
                net_score = (w_sup - self.refutation_lambda * w_ref) / w_total
                net_conf = max(0.0, min(1.0, net_score))
            else:
                net_conf = 0.0

            # Update hypothesis counts and calibrated confidence
            h.confidence = net_conf
            h.support_count = len(supporting)
            h.refutation_count = len(refuting)
            evaluated_hypotheses.append(h)

            bipartite_graph[h.hypothesis_id] = {
                "supporting": [e.evidence_id for e in supporting],
                "refuting": [e.evidence_id for e in refuting],
                "support_weight": w_sup,
                "refute_weight": w_ref,
                "total_weight": w_total,
            }

        # Rank hypotheses by confidence descending, then by total supporting weight
        evaluated_hypotheses.sort(
            key=lambda hyp: (
                hyp.confidence,
                bipartite_graph[hyp.hypothesis_id]["support_weight"],
            ),
            reverse=True,
        )

        top_h = evaluated_hypotheses[0]
        top_info = bipartite_graph[top_h.hypothesis_id]
        top_w_sup = top_info["support_weight"]
        top_w_ref = top_info["refute_weight"]
        top_w_total = top_info["total_weight"]

        # Rule 1: Insufficient total evidence weight
        if top_w_total < self.min_evidence_weight:
            return GroundingAssessment(
                status="abstained",
                confidence=top_h.confidence,
                hypotheses=evaluated_hypotheses,
                bipartite_graph=bipartite_graph,
                abstention_reason=(
                    f"Total evidence weight ({top_w_total:.2f}) below threshold "
                    f"({self.min_evidence_weight:.2f})"
                ),
            )

        # Rule 2: Contradictory evidence (refuting weight >= ratio * supporting weight)
        if top_w_sup > 0 and top_w_ref >= self.contradiction_ratio_threshold * top_w_sup:
            return GroundingAssessment(
                status="abstained",
                confidence=top_h.confidence,
                hypotheses=evaluated_hypotheses,
                bipartite_graph=bipartite_graph,
                abstention_reason=(
                    f"Contradictory evidence detected: refuting weight ({top_w_ref:.2f}) >= "
                    f"{self.contradiction_ratio_threshold} * supporting weight ({top_w_sup:.2f})"
                ),
            )

        # Rule 3: Low net confidence
        if top_h.confidence < self.min_confidence_threshold:
            return GroundingAssessment(
                status="abstained",
                confidence=top_h.confidence,
                hypotheses=evaluated_hypotheses,
                bipartite_graph=bipartite_graph,
                abstention_reason=(
                    f"Confidence {top_h.confidence:.2f} below threshold "
                    f"{self.min_confidence_threshold:.2f}"
                ),
            )

        # Rule 4: Ambiguous competing hypotheses
        if len(evaluated_hypotheses) > 1:
            second_h = evaluated_hypotheses[1]
            if (
                abs(top_h.confidence - second_h.confidence) <= self.ambiguity_margin
                and second_h.confidence >= self.min_confidence_threshold
            ):
                return GroundingAssessment(
                    status="inconclusive",
                    confidence=top_h.confidence,
                    hypotheses=evaluated_hypotheses,
                    bipartite_graph=bipartite_graph,
                    abstention_reason=(
                        "Ambiguous competing hypotheses with indistinguishable confidence"
                    ),
                )

        # Rule 5: Successfully diagnosed
        return GroundingAssessment(
            status="diagnosed",
            primary_root_cause=top_h.title,
            confidence=top_h.confidence,
            hypotheses=evaluated_hypotheses,
            bipartite_graph=bipartite_graph,
        )
