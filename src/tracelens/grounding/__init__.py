"""Evidence grounding, dual-polarity verification, and information gain discriminators."""

from tracelens.grounding.discriminator import (
    NextCheckSelector,
    calculate_entropy,
)
from tracelens.grounding.verifier import (
    GroundingAssessment,
    GroundingVerifier,
)

__all__ = [
    "GroundingAssessment",
    "GroundingVerifier",
    "NextCheckSelector",
    "calculate_entropy",
]
