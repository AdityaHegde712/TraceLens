"""Specification tests for TraceLens data models.

Strict TDD suite: All models and their behavioral constraints are locked here.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from tracelens.models.telemetry import (
    ConfigMetadata,
    IncidentManifest,
    LogEntry,
    MetricPoint,
    TraceSpan,
)
from tracelens.models.triage import (
    EvidenceLink,
    EvidencePolarity,
    Hypothesis,
    NextCheckProposal,
    TriageReport,
)


class TestTelemetryModels:
    """Locked assertions for telemetry data models."""

    def test_log_entry_valid(self):
        entry = LogEntry(
            timestamp=datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc),
            level="ERROR",
            service="retrieval-service",
            message="Vector index connection timed out",
            attributes={"retry_count": 3, "db_host": "milvus.internal"},
            trace_id="tr-1001",
            span_id="sp-2001",
        )
        assert entry.service == "retrieval-service"
        assert entry.level == "ERROR"
        assert entry.trace_id == "tr-1001"
        assert entry.attributes["retry_count"] == 3
        # String timestamps should also parse or be accepted
        dumped = entry.model_dump()
        assert dumped["trace_id"] == "tr-1001"

    def test_log_entry_defaults_and_optionals(self):
        entry = LogEntry(
            timestamp="2026-10-15T12:00:00Z",
            level="INFO",
            service="api-gateway",
            message="Health check passed",
        )
        assert entry.attributes == {}
        assert entry.trace_id is None
        assert entry.span_id is None

    def test_log_entry_validation_failure(self):
        with pytest.raises(ValidationError):
            # Missing required fields: timestamp, level, service, message
            LogEntry()  # type: ignore

    def test_trace_span_valid(self):
        span = TraceSpan(
            trace_id="tr-550",
            span_id="sp-01",
            parent_span_id=None,
            name="POST /v1/chat/completions",
            start_time_ms=1000.0,
            end_time_ms=1500.0,
            attributes={"http.status_code": 200},
            status="ok",
        )
        assert span.trace_id == "tr-550"
        assert span.end_time_ms - span.start_time_ms == 500.0
        assert span.parent_span_id is None
        assert span.status == "ok"

    def test_trace_span_defaults(self):
        span = TraceSpan(
            trace_id="tr-550",
            span_id="sp-02",
            name="db_query",
            start_time_ms=1100.0,
            end_time_ms=1250.0,
            status="error",
        )
        assert span.attributes == {}
        assert span.parent_span_id is None

    def test_trace_span_validation_failure(self):
        with pytest.raises(ValidationError):
            TraceSpan(trace_id="tr-1")  # type: ignore

    def test_metric_point_valid(self):
        point = MetricPoint(
            timestamp="2026-10-15T12:05:00Z",
            metric_name="rag_query_latency_ms",
            value=842.5,
            labels={"endpoint": "/query", "status": "200"},
        )
        assert point.metric_name == "rag_query_latency_ms"
        assert point.value == 842.5
        assert point.labels["endpoint"] == "/query"

    def test_metric_point_defaults(self):
        point = MetricPoint(
            timestamp="2026-10-15T12:05:00Z",
            metric_name="system_cpu_usage",
            value=0.74,
        )
        assert point.labels == {}

    def test_config_metadata_valid(self):
        config = ConfigMetadata(
            service="embedding-service",
            version="v2.4.1",
            settings={"batch_size": 32, "model": "text-embedding-3-small"},
        )
        assert config.service == "embedding-service"
        assert config.version == "v2.4.1"
        assert config.settings["batch_size"] == 32

    def test_incident_manifest_valid(self):
        manifest = IncidentManifest(
            incident_id="INC-404",
            title="Spike in 504 Gateway Timeouts",
            symptom="P99 latency jumped from 200ms to 4500ms on /query",
            start_time="2026-10-15T10:00:00Z",
            end_time="2026-10-15T11:00:00Z",
            ground_truth_root_cause="Milvus vector DB node OOM killed due to large batch size",
            services_involved=["api-gateway", "retrieval-service", "vector-db"],
        )
        assert manifest.incident_id == "INC-404"
        assert len(manifest.services_involved) == 3
        assert "vector-db" in manifest.services_involved


class TestTriageModels:
    """Locked assertions for incident triage and evidence grounding models."""

    def test_evidence_polarity_enum(self):
        assert EvidencePolarity.SUPPORT.value == "support"
        assert EvidencePolarity.REFUTE.value == "refute"
        assert EvidencePolarity.NEUTRAL.value == "neutral"

    def test_evidence_link_valid(self):
        link = EvidenceLink(
            evidence_id="ev-001",
            source_type="log",
            polarity=EvidencePolarity.SUPPORT,
            description="Out of memory log entry in vector db worker pod",
            relevance_score=0.95,
        )
        assert link.evidence_id == "ev-001"
        assert link.source_type == "log"
        assert link.polarity == EvidencePolarity.SUPPORT
        assert link.relevance_score == 0.95

    def test_evidence_link_invalid_source_type(self):
        with pytest.raises(ValidationError):
            EvidenceLink(
                evidence_id="ev-002",
                source_type="invalid_source",  # type: ignore
                polarity=EvidencePolarity.REFUTE,
                description="Invalid source test",
                relevance_score=0.5,
            )

    def test_hypothesis_valid(self):
        ev1 = EvidenceLink(
            evidence_id="ev-001",
            source_type="log",
            polarity=EvidencePolarity.SUPPORT,
            description="OOM log in vector-db",
            relevance_score=0.9,
        )
        ev2 = EvidenceLink(
            evidence_id="ev-002",
            source_type="metric",
            polarity=EvidencePolarity.REFUTE,
            description="Network bandwidth was well below threshold",
            relevance_score=0.7,
        )
        hypo = Hypothesis(
            hypothesis_id="hyp-1",
            title="Vector DB Out of Memory Crash",
            description="High batch ingestion query triggered worker kill",
            confidence=0.88,
            evidence_links=[ev1, ev2],
            refutation_count=1,
            support_count=1,
        )
        assert hypo.hypothesis_id == "hyp-1"
        assert len(hypo.evidence_links) == 2
        assert hypo.confidence == 0.88
        assert hypo.support_count == 1
        assert hypo.refutation_count == 1

    def test_hypothesis_defaults(self):
        hypo = Hypothesis(
            hypothesis_id="hyp-2",
            title="Network partition",
            description="Temporary packet loss between gateway and LLM provider",
            confidence=0.15,
        )
        assert hypo.evidence_links == []
        assert hypo.refutation_count == 0
        assert hypo.support_count == 0

    def test_next_check_proposal_valid(self):
        proposal = NextCheckProposal(
            check_id="chk-10",
            target_source="metric",
            query_or_action="container_memory_working_set_bytes{pod=~'vector-db.*'}",
            expected_information_gain=0.85,
            rationale="Verify whether pod memory hit cgroup limit at incident onset",
        )
        assert proposal.check_id == "chk-10"
        assert proposal.target_source == "metric"
        assert proposal.expected_information_gain == 0.85

    def test_triage_report_diagnosed(self):
        report = TriageReport(
            incident_id="INC-404",
            reported_symptom="504 timeout spike",
            status="diagnosed",
            primary_root_cause="Milvus OOM crash",
            confidence=0.92,
            hypotheses=[
                Hypothesis(
                    hypothesis_id="hyp-1",
                    title="Milvus OOM",
                    description="OOM crash",
                    confidence=0.92,
                    support_count=2,
                )
            ],
            recommended_next_check=None,
            abstention_reason=None,
        )
        assert report.status == "diagnosed"
        assert report.primary_root_cause == "Milvus OOM crash"
        assert report.confidence == 0.92

    def test_triage_report_abstained(self):
        report = TriageReport(
            incident_id="INC-500",
            reported_symptom="Intermittent token generation pauses",
            status="abstained",
            primary_root_cause=None,
            confidence=0.2,
            hypotheses=[],
            recommended_next_check=NextCheckProposal(
                check_id="chk-11",
                target_source="log",
                query_or_action="grep 'rate_limit' /var/log/llm-gateway.log",
                expected_information_gain=0.9,
                rationale="Insufficient evidence to distinguish between rate limiting and upstream network delay",
            ),
            abstention_reason="Confidence below threshold (0.2 < 0.6) and conflicting metrics",
        )
        assert report.status == "abstained"
        assert report.abstention_reason is not None
        assert report.recommended_next_check is not None
        assert report.primary_root_cause is None

    def test_triage_report_invalid_status(self):
        with pytest.raises(ValidationError):
            TriageReport(
                incident_id="INC-999",
                reported_symptom="Unknown",
                status="resolved",  # type: ignore (only diagnosed, abstained, inconclusive allowed)
                confidence=0.5,
            )
