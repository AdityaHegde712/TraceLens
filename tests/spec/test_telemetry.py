"""Specification tests for the TraceLens telemetry engine.

Strict TDD suite locking behavior for:
1. Sanitizer: SHA-256 masking of credentials and verifiable canary token detection.
2. Trace DAG: Tree assembly, self-time calculation, critical path, bottleneck detection, cycle handling.
3. Reader: Incident bundle loader reading logs, traces, metrics, configs, and runbooks.
"""

import json
from pathlib import Path
import pytest

from tracelens.models.telemetry import (
    TraceSpan,
)
from tracelens.telemetry.reader import IncidentBundle, IncidentReader
from tracelens.telemetry.sanitizer import (
    TelemetrySanitizer,
    detect_canary_leak,
    generate_canary,
)
from tracelens.telemetry.trace_dag import TraceDAG


# =====================================================================
# 1. Sanitizer Tests
# =====================================================================

class TestTelemetrySanitizer:
    """Locked assertions for credential masking and canary leak detection."""

    def test_generate_canary_format(self):
        canary = generate_canary()
        assert canary.startswith("TL-CANARY-")
        # UUID is 36 chars: 8-4-4-4-12 -> total length 10 + 36 = 46
        assert len(canary) == 46

    def test_canary_leak_detection(self):
        canary = generate_canary()
        clean_text = "Standard operation completed successfully."
        leaked_text = f"Error communicating with provider using canary token {canary} in payload."

        assert not detect_canary_leak(clean_text, canary)
        assert detect_canary_leak(leaked_text, canary)

    def test_sanitize_canary_token(self):
        sanitizer = TelemetrySanitizer()
        canary = generate_canary()
        text = f"Leaked prompt session with canary: {canary}"
        sanitized = sanitizer.sanitize_text(text)

        # Canary must be masked
        assert canary not in sanitized
        assert "[REDACTED_CANARY:" in sanitized
        # Leak detection on sanitized text must now return False
        assert not detect_canary_leak(sanitized, canary)

    def test_sanitize_openai_and_generic_api_tokens(self):
        sanitizer = TelemetrySanitizer()
        secret = "sk-proj-abc1234567890abcdefghijklmnopqrstuvwxyz"
        text = f"Failed to authenticate with OpenAI API key {secret} on endpoint."
        sanitized = sanitizer.sanitize_text(text)

        assert secret not in sanitized
        assert "[REDACTED_SECRET:" in sanitized

    def test_sanitize_authorization_headers(self):
        sanitizer = TelemetrySanitizer()
        auth_header = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        text = f"HTTP request outgoing headers: {auth_header} to upstream."
        sanitized = sanitizer.sanitize_text(text)

        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "[REDACTED_AUTH:" in sanitized

    def test_sanitize_database_connection_strings(self):
        sanitizer = TelemetrySanitizer()
        db_url = "postgresql://rag_admin:SuperSecretPass123!@postgres.internal.cluster:5432/vectors"
        text = f"Connection pool failed for connection string: {db_url}"
        sanitized = sanitizer.sanitize_text(text)

        assert "SuperSecretPass123!" not in sanitized
        assert "rag_admin" not in sanitized
        assert "[REDACTED_URI:" in sanitized

    def test_sanitize_dict_recursively(self):
        sanitizer = TelemetrySanitizer()
        raw = {
            "api_key": "sk-secretkey999999999999999",
            "nested": {
                "db_conn": "mysql://user:mypass@db.host:3306/db",
                "canary": generate_canary(),
                "status": "active",
            },
            "count": 42,
        }
        sanitized = sanitizer.sanitize_dict(raw)
        assert "sk-secretkey999999999999999" not in str(sanitized)
        assert "mypass" not in str(sanitized)
        assert "[REDACTED" in sanitized["api_key"]
        assert sanitized["nested"]["status"] == "active"
        assert sanitized["count"] == 42


# =====================================================================
# 2. Trace DAG Tests
# =====================================================================

class TestTraceDAG:
    """Locked assertions for tree construction, self-time, and bottleneck detection."""

    @pytest.fixture
    def sample_spans(self) -> list[TraceSpan]:
        """Hierarchical trace tree:
        root (span-1, duration=1000ms: 0..1000)
          ├── child1: embedding (span-2, duration=300ms: 50..350)
          └── child2: vector_retrieval (span-3, duration=600ms: 350..950)
                └── grandchild: milvus_rpc (span-4, duration=500ms: 400..900)
        """
        return [
            TraceSpan(
                trace_id="trace-01",
                span_id="span-1",
                parent_span_id=None,
                name="POST /v1/chat",
                start_time_ms=0.0,
                end_time_ms=1000.0,
            ),
            TraceSpan(
                trace_id="trace-01",
                span_id="span-2",
                parent_span_id="span-1",
                name="embed_query",
                start_time_ms=50.0,
                end_time_ms=350.0,
            ),
            TraceSpan(
                trace_id="trace-01",
                span_id="span-3",
                parent_span_id="span-1",
                name="vector_search",
                start_time_ms=350.0,
                end_time_ms=950.0,
            ),
            TraceSpan(
                trace_id="trace-01",
                span_id="span-4",
                parent_span_id="span-3",
                name="milvus_query_rpc",
                start_time_ms=400.0,
                end_time_ms=900.0,
            ),
        ]

    def test_dag_tree_assembly(self, sample_spans):
        dag = TraceDAG.from_spans(sample_spans)
        assert len(dag.root_spans) == 1
        root = dag.root_spans[0]
        assert root.span.span_id == "span-1"
        assert len(root.children) == 2

        child_ids = {c.span.span_id for c in root.children}
        assert child_ids == {"span-2", "span-3"}

        vec_search = next(c for c in root.children if c.span.span_id == "span-3")
        assert len(vec_search.children) == 1
        assert vec_search.children[0].span.span_id == "span-4"

    def test_self_time_calculation(self, sample_spans):
        """Self-time: delta t = duration - sum(children_durations).

        - span-1: duration=1000. Children: span-2 (300) + span-3 (600) = 900. Self-time = 100ms.
        - span-2: duration=300. Children: none. Self-time = 300ms.
        - span-3: duration=600. Children: span-4 (500). Self-time = 100ms.
        - span-4: duration=500. Children: none. Self-time = 500ms.
        """
        dag = TraceDAG.from_spans(sample_spans)
        self_times = dag.calculate_self_times()

        assert pytest.approx(self_times["span-1"]) == 100.0
        assert pytest.approx(self_times["span-2"]) == 300.0
        assert pytest.approx(self_times["span-3"]) == 100.0
        assert pytest.approx(self_times["span-4"]) == 500.0

    def test_critical_path_identification(self, sample_spans):
        """Critical path should follow the longest latency path from root to leaf:
        span-1 (1000ms) -> span-3 (600ms) -> span-4 (500ms).
        """
        dag = TraceDAG.from_spans(sample_spans)
        critical_path = dag.find_critical_path()
        path_ids = [node.span.span_id for node in critical_path]

        assert path_ids == ["span-1", "span-3", "span-4"]

    def test_bottleneck_detection(self, sample_spans):
        """Identify spans whose self-time consumes a high proportion of trace time.
        With total duration = 1000ms:
        - span-4 has self_time = 500ms (50% of total trace duration).
        - threshold_pct = 0.4 should identify span-4.
        """
        dag = TraceDAG.from_spans(sample_spans)
        bottlenecks = dag.detect_bottlenecks(threshold_pct=0.4)

        assert len(bottlenecks) == 1
        assert bottlenecks[0].span.span_id == "span-4"

    def test_cycle_detection_and_resilience(self):
        """Cyclical traces should not cause infinite recursion."""
        cycle_spans = [
            TraceSpan(
                trace_id="tr-cycle",
                span_id="span-A",
                parent_span_id="span-B",
                name="op_A",
                start_time_ms=0.0,
                end_time_ms=100.0,
            ),
            TraceSpan(
                trace_id="tr-cycle",
                span_id="span-B",
                parent_span_id="span-A",
                name="op_B",
                start_time_ms=10.0,
                end_time_ms=90.0,
            ),
        ]
        # Should gracefully handle cycles without crashing
        dag = TraceDAG.from_spans(cycle_spans)
        assert dag is not None
        # Should be able to compute self-times and critical path without recursion error
        self_times = dag.calculate_self_times()
        assert len(self_times) == 2


# =====================================================================
# 3. Incident Reader Tests
# =====================================================================

class TestIncidentReader:
    """Locked assertions for loading incident telemetry bundles from files."""

    @pytest.fixture
    def incident_dir(self, tmp_path: Path) -> Path:
        """Create a mock incident bundle directory."""
        inc_dir = tmp_path / "INC-101"
        inc_dir.mkdir()

        # Manifest
        manifest_data = {
            "incident_id": "INC-101",
            "title": "Milvus Vector DB OOM Crash",
            "symptom": "High latency and 504 errors on /query endpoint",
            "start_time": "2026-10-15T12:00:00Z",
            "end_time": "2026-10-15T12:30:00Z",
            "ground_truth_root_cause": "OOM due to memory leak during index build",
            "services_involved": ["retrieval-service", "milvus-db"],
        }
        (inc_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        # Logs
        logs_data = [
            {
                "timestamp": "2026-10-15T12:05:00Z",
                "level": "ERROR",
                "service": "milvus-db",
                "message": "Out of memory: Killed process 412 (milvus-server)",
                "attributes": {"exit_code": 137},
                "trace_id": "tr-001",
                "span_id": "sp-001",
            }
        ]
        (inc_dir / "logs.json").write_text(json.dumps(logs_data), encoding="utf-8")

        # Traces
        traces_data = [
            {
                "trace_id": "tr-001",
                "span_id": "sp-001",
                "parent_span_id": None,
                "name": "POST /query",
                "start_time_ms": 100.0,
                "end_time_ms": 600.0,
                "attributes": {"status": "504"},
                "status": "error",
            }
        ]
        (inc_dir / "traces.json").write_text(json.dumps(traces_data), encoding="utf-8")

        # Metrics
        metrics_data = [
            {
                "timestamp": "2026-10-15T12:05:00Z",
                "metric_name": "container_memory_usage_bytes",
                "value": 16106127360.0,
                "labels": {"pod": "milvus-db-0"},
            }
        ]
        (inc_dir / "metrics.json").write_text(json.dumps(metrics_data), encoding="utf-8")

        # Configs
        configs_data = [
            {
                "service": "milvus-db",
                "version": "v2.4.0",
                "settings": {"cache_size_gb": 16, "index_type": "HNSW"},
            }
        ]
        (inc_dir / "config.json").write_text(json.dumps(configs_data), encoding="utf-8")

        # Runbooks
        runbooks_dir = inc_dir / "runbooks"
        runbooks_dir.mkdir()
        (runbooks_dir / "milvus_oom_mitigation.md").write_text(
            "# Runbook: Milvus OOM\nCheck pod memory limit and restart worker.",
            encoding="utf-8",
        )

        return inc_dir

    def test_load_bundle_complete(self, incident_dir: Path):
        bundle = IncidentReader.load_bundle(incident_dir)
        assert isinstance(bundle, IncidentBundle)

        # Assert manifest
        assert bundle.manifest.incident_id == "INC-101"
        assert bundle.manifest.services_involved == ["retrieval-service", "milvus-db"]

        # Assert logs
        assert len(bundle.logs) == 1
        assert bundle.logs[0].level == "ERROR"
        assert "Out of memory" in bundle.logs[0].message

        # Assert traces
        assert len(bundle.traces) == 1
        assert bundle.traces[0].name == "POST /query"

        # Assert metrics
        assert len(bundle.metrics) == 1
        assert bundle.metrics[0].value == 16106127360.0

        # Assert configs
        assert len(bundle.configs) == 1
        assert bundle.configs[0].version == "v2.4.0"

        # Assert runbooks
        assert len(bundle.runbooks) == 1
        assert "Milvus OOM" in bundle.runbooks[0]

    def test_load_bundle_missing_optional_files(self, tmp_path: Path):
        """Bundles with only manifest.json should load gracefully with empty lists."""
        sparse_dir = tmp_path / "sparse-incident"
        sparse_dir.mkdir()

        manifest_data = {
            "incident_id": "INC-SPARSE",
            "title": "Sparse Incident",
            "symptom": "Degraded latency",
            "start_time": "2026-10-15T00:00:00Z",
            "ground_truth_root_cause": "Unknown",
        }
        (sparse_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        bundle = IncidentReader.load_bundle(sparse_dir)
        assert bundle.manifest.incident_id == "INC-SPARSE"
        assert bundle.logs == []
        assert bundle.traces == []
        assert bundle.metrics == []
        assert bundle.configs == []
        assert bundle.runbooks == []
