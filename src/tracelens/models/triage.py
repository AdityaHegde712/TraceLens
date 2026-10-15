"""Triage and evidence grounding data models for TraceLens.

Provides schemas for structured hypotheses, evidence polarity links,
information-gain check proposals, and calibrated triage reports.
"""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class EvidencePolarity(str, Enum):
    """Polarity of evidence relative to an incident hypothesis."""

    SUPPORT = "support"
    REFUTE = "refute"
    NEUTRAL = "neutral"


class EvidenceLink(BaseModel):
    """An individual grounding link connecting telemetry evidence to a hypothesis."""

    model_config = ConfigDict(extra="ignore")

    evidence_id: str = Field(
        ...,
        description="Unique identifier for the evidence artifact or telemetry chunk.",
    )
    source_type: Literal["log", "trace", "metric", "config"] = Field(
        ...,
        description="Telemetry source category: 'log', 'trace', 'metric', or 'config'.",
    )
    polarity: EvidencePolarity = Field(
        ...,
        description="Whether this evidence supports, refutes, or is neutral towards hypothesis.",
    )
    description: str = Field(
        ...,
        description="Human-readable citation or excerpt explaining relevance.",
    )
    relevance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Calibrated relevance score between 0.0 and 1.0.",
    )


class Hypothesis(BaseModel):
    """A candidate explanation for the incident root cause."""

    model_config = ConfigDict(extra="ignore")

    hypothesis_id: str = Field(
        ...,
        description="Unique identifier for the hypothesis.",
    )
    title: str = Field(
        ...,
        description="Concise summary title of the suspected root cause.",
    )
    description: str = Field(
        ...,
        description="Detailed causal mechanism and propagation description.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Model confidence score between 0.0 and 1.0.",
    )
    evidence_links: list[EvidenceLink] = Field(
        default_factory=list,
        description="Grounded telemetry citations supporting or refuting this hypothesis.",
    )
    refutation_count: int = Field(
        default=0,
        ge=0,
        description="Count of refuting evidence links.",
    )
    support_count: int = Field(
        default=0,
        ge=0,
        description="Count of supporting evidence links.",
    )


class NextCheckProposal(BaseModel):
    """Active diagnostic proposal recommending the next telemetry query."""

    model_config = ConfigDict(extra="ignore")

    check_id: str = Field(
        ...,
        description="Unique identifier for the diagnostic check action.",
    )
    target_source: str = Field(
        ...,
        description="Target telemetry silo or system (e.g. 'log', 'metric', 'trace', 'config').",
    )
    query_or_action: str = Field(
        ...,
        description="Concrete PromQL query, log grep expression, or span inspection query.",
    )
    expected_information_gain: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Estimated uncertainty reduction score between 0.0 and 1.0.",
    )
    rationale: str = Field(
        ...,
        description="Reasoning explaining why this check distinguishes competing hypotheses.",
    )


class TriageReport(BaseModel):
    """Complete incident triage diagnosis report with grounded evidence or abstention."""

    model_config = ConfigDict(extra="ignore")

    incident_id: str = Field(
        ...,
        description="Identifier of the incident being diagnosed.",
    )
    reported_symptom: str = Field(
        ...,
        description="Primary alert or symptom that initiated triage.",
    )
    status: Literal["diagnosed", "abstained", "inconclusive"] = Field(
        ...,
        description="Final triage verdict: 'diagnosed', 'abstained', or 'inconclusive'.",
    )
    primary_root_cause: str | None = Field(
        default=None,
        description="Top-ranked root cause diagnosis, or None if abstained/inconclusive.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Calibrated overall diagnosis confidence score between 0.0 and 1.0.",
    )
    hypotheses: list[Hypothesis] = Field(
        default_factory=list,
        description="List of evaluated hypotheses with grounded evidence links.",
    )
    recommended_next_check: NextCheckProposal | None = Field(
        default=None,
        description="Next diagnostic check when status is abstained or inconclusive.",
    )
    abstention_reason: str | None = Field(
        default=None,
        description="Explicit explanation if system abstained from diagnosing.",
    )
