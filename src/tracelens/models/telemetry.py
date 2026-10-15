"""Telemetry data models for TraceLens.

Provides schemas for structured logs, distributed trace spans, metrics,
service configurations, and incident manifests.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class LogEntry(BaseModel):
    """Structured log record emitted by a service."""

    model_config = ConfigDict(extra="ignore")

    timestamp: datetime | str = Field(
        ...,
        description="Timestamp when the log was generated.",
    )
    level: str = Field(
        ...,
        description="Log severity level (e.g., INFO, WARN, ERROR, DEBUG).",
    )
    service: str = Field(
        ...,
        description="Service or component name emitting the log.",
    )
    message: str = Field(
        ...,
        description="Human-readable log message.",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata key-value pairs.",
    )
    trace_id: str | None = Field(
        default=None,
        description="Associated distributed trace ID, if correlated.",
    )
    span_id: str | None = Field(
        default=None,
        description="Associated span ID, if correlated.",
    )


class TraceSpan(BaseModel):
    """Distributed tracing span representing an operation execution window."""

    model_config = ConfigDict(extra="ignore")

    trace_id: str = Field(
        ...,
        description="Distributed trace identifier across service boundaries.",
    )
    span_id: str = Field(
        ...,
        description="Unique identifier for this specific execution span.",
    )
    parent_span_id: str | None = Field(
        default=None,
        description="Span ID of parent operation, or None if root span.",
    )
    name: str = Field(
        ...,
        description="Operation or endpoint name (e.g. POST /v1/chat/completions).",
    )
    start_time_ms: float = Field(
        ...,
        description="Epoch timestamp in milliseconds when span started.",
    )
    end_time_ms: float = Field(
        ...,
        description="Epoch timestamp in milliseconds when span ended.",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Span attributes and tags (e.g. http.status_code, db.system).",
    )
    status: str = Field(
        default="ok",
        description="Span completion status (e.g., 'ok', 'error', 'unset').",
    )


class MetricPoint(BaseModel):
    """Individual timeseries metric observation."""

    model_config = ConfigDict(extra="ignore")

    timestamp: datetime | str = Field(
        ...,
        description="Observation timestamp.",
    )
    metric_name: str = Field(
        ...,
        description="Prometheus/OpenTelemetry metric name.",
    )
    value: float = Field(
        ...,
        description="Numeric observed metric value.",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Dimensional metric labels (e.g., method, endpoint, pod).",
    )


class ConfigMetadata(BaseModel):
    """Snapshot of service configuration and runtime environment."""

    model_config = ConfigDict(extra="ignore")

    service: str = Field(
        ...,
        description="Name of the service owning the configuration.",
    )
    version: str = Field(
        ...,
        description="Software release version or commit hash.",
    )
    settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Active runtime configuration parameters.",
    )


class IncidentManifest(BaseModel):
    """Manifest describing a reproduced or benchmarked incident."""

    model_config = ConfigDict(extra="ignore")

    incident_id: str = Field(
        ...,
        description="Unique benchmark incident identifier.",
    )
    title: str = Field(
        ...,
        description="Short human-readable incident headline.",
    )
    symptom: str = Field(
        ...,
        description="Reported alert, user symptom, or SLO degradation.",
    )
    start_time: datetime | str = Field(
        ...,
        description="Estimated start time of the incident condition.",
    )
    end_time: datetime | str | None = Field(
        default=None,
        description="Resolved or boundary end time of the incident.",
    )
    ground_truth_root_cause: str = Field(
        ...,
        description="Ground-truth verified root cause explanation.",
    )
    services_involved: list[str] = Field(
        default_factory=list,
        description="List of services affected or implicated in the incident.",
    )
