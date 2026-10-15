"""Information-gain hypothesis discriminator and next-check selector.

Computes Shannon entropy across competing hypothesis probability distributions
and ranks candidate telemetry checks to identify the action maximizing expected
information gain.
"""

import math

from tracelens.models.triage import Hypothesis, NextCheckProposal


def calculate_entropy(probabilities: list[float]) -> float:
    """Calculate Shannon entropy in bits for a discrete probability distribution.

    Args:
        probabilities: List of non-negative probabilities.

    Returns:
        Shannon entropy in bits (H >= 0.0). Returns 0.0 for empty or deterministic distributions.
    """
    valid_probs = [p for p in probabilities if p > 0.0]
    total = sum(valid_probs)
    if total <= 0.0:
        return 0.0

    # Normalize distribution to sum to 1.0
    normalized = [p / total for p in valid_probs]
    entropy = -sum(p * math.log2(p) for p in normalized)
    return max(0.0, entropy)


class NextCheckSelector:
    """Selects the diagnostic inspection check that minimizes posterior hypothesis uncertainty."""

    def calculate_hypothesis_distribution(self, hypotheses: list[Hypothesis]) -> list[float]:
        """Convert hypothesis confidence scores to a normalized probability distribution.

        Args:
            hypotheses: List of candidate hypotheses.

        Returns:
            List of normalized probability values.
        """
        confidences = [max(0.001, h.confidence) for h in hypotheses]
        total = sum(confidences)
        if total <= 0.0:
            return [1.0 / len(hypotheses)] * len(hypotheses) if hypotheses else []
        return [c / total for c in confidences]

    def rank_candidate_checks(
        self,
        hypotheses: list[Hypothesis],
        candidate_checks: list[NextCheckProposal],
    ) -> list[tuple[NextCheckProposal, float]]:
        """Rank candidate checks by expected information gain.

        Args:
            hypotheses: Competing incident hypotheses.
            candidate_checks: Candidate telemetry queries/actions.

        Returns:
            List of (NextCheckProposal, score) tuples sorted in descending order of information gain.
        """
        if not candidate_checks:
            return []

        distribution = self.calculate_hypothesis_distribution(hypotheses)
        current_entropy = calculate_entropy(distribution)

        ranked: list[tuple[NextCheckProposal, float]] = []
        for check in candidate_checks:
            # Expected gain is weighted by current ambiguity entropy
            score = check.expected_information_gain * (1.0 + current_entropy)
            ranked.append((check, score))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    def select_optimal_check(
        self,
        hypotheses: list[Hypothesis],
        candidate_checks: list[NextCheckProposal],
    ) -> NextCheckProposal | None:
        """Select the single best candidate check maximizing expected information gain.

        Args:
            hypotheses: Current active hypotheses.
            candidate_checks: Candidate inspection proposals.

        Returns:
            Selected NextCheckProposal or None if candidate_checks is empty.
        """
        ranked = self.rank_candidate_checks(hypotheses, candidate_checks)
        if not ranked:
            return None
        return ranked[0][0]
