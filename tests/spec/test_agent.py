"""Specification tests for the TraceLens Bounded ReAct Agent and CLI.

Strict TDD suite locking behavior for:
1. LLM Backends: Abstract base, Mock, Ollama, and OpenAI adapters.
2. Read-Only Diagnostic Tools: Filtering, trace DAG inspection, metrics quantiles,
   sanitized config retrieval, runbook lookup, and call budget enforcement.
3. Bounded ReAct Loop: FSM states, mutation refusal guard, loop repetition guard,
   bounded step budget, and grounded TriageReport synthesis.
4. CLI Commands: Triage and inspect entry points.
"""

import pytest

from tracelens.agent.llm_backend import (
    LLMBackend,
    MockLLMBackend,
    OllamaBackend,
    OpenAIBackend,
)
from tracelens.agent.react_loop import (
    AgentState,
    BoundedReActAgent,
)
from tracelens.agent.tools import (
    ConfigLookupTool,
    LogSearchTool,
    MetricQueryTool,
    RunbookRetrieveTool,
    TraceInspectTool,
)
from tracelens.cli import build_parser, main
from tracelens.models.telemetry import (
    ConfigMetadata,
    IncidentManifest,
    LogEntry,
    MetricPoint,
    TraceSpan,
)
from tracelens.telemetry.reader import IncidentBundle


@pytest.fixture
def sample_bundle() -> IncidentBundle:
    """Fixture providing a rich IncidentBundle for testing tools and agent."""
    manifest = IncidentManifest(
        incident_id="INC-300",
        title="Vector DB Worker Crash",
        symptom="504 gateway timeout on /search",
        start_time="2026-10-15T10:00:00Z",
        end_time="2026-10-15T10:30:00Z",
        ground_truth_root_cause="Milvus node OOM killed during index compaction",
        services_involved=["gateway", "retrieval", "milvus-db"],
    )
    logs = [
        LogEntry(
            timestamp="2026-10-15T10:05:00Z",
            level="INFO",
            service="gateway",
            message="Incoming request POST /search",
            trace_id="tr-100",
            span_id="sp-1",
        ),
        LogEntry(
            timestamp="2026-10-15T10:06:00Z",
            level="ERROR",
            service="milvus-db",
            message="Out of memory: Kill process 501 (milvus-compaction) score 850",
            trace_id="tr-100",
            span_id="sp-2",
        ),
        LogEntry(
            timestamp="2026-10-15T10:06:30Z",
            level="ERROR",
            service="retrieval",
            message="Upstream RPC timeout to milvus-db:19530",
            trace_id="tr-100",
            span_id="sp-3",
        ),
    ]
    traces = [
        TraceSpan(
            trace_id="tr-100",
            span_id="sp-1",
            parent_span_id=None,
            name="POST /search",
            start_time_ms=0.0,
            end_time_ms=2000.0,
            status="error",
        ),
        TraceSpan(
            trace_id="tr-100",
            span_id="sp-3",
            parent_span_id="sp-1",
            name="retrieval_query",
            start_time_ms=100.0,
            end_time_ms=1900.0,
            status="error",
        ),
        TraceSpan(
            trace_id="tr-100",
            span_id="sp-2",
            parent_span_id="sp-3",
            name="milvus_compaction",
            start_time_ms=200.0,
            end_time_ms=1800.0,
            status="error",
        ),
    ]
    metrics = [
        MetricPoint(
            timestamp="2026-10-15T10:04:00Z",
            metric_name="container_memory_bytes",
            value=8000000000.0,
            labels={"pod": "milvus-db-0"},
        ),
        MetricPoint(
            timestamp="2026-10-15T10:06:00Z",
            metric_name="container_memory_bytes",
            value=16500000000.0,
            labels={"pod": "milvus-db-0"},
        ),
    ]
    configs = [
        ConfigMetadata(
            service="milvus-db",
            version="v2.4.1",
            settings={
                "api_key": "sk-secret123456789",
                "max_memory_gb": 16,
                "compaction_enabled": True,
            },
        )
    ]
    runbooks = [
        "# Milvus OOM Troubleshooting\nWhen milvus-db crashes with exit code 137, inspect compaction memory limit."
    ]

    return IncidentBundle(
        manifest=manifest,
        logs=logs,
        traces=traces,
        metrics=metrics,
        configs=configs,
        runbooks=runbooks,
    )


# =====================================================================
# 1. LLM Backend Tests
# =====================================================================

class TestLLMBackend:
    """Locked assertions for LLM backend adapters."""

    def test_mock_backend_deterministic(self):
        backend = MockLLMBackend(default_response="Diagnosed: Milvus OOM")
        resp = backend.generate("Analyze the incident logs")
        assert resp == "Diagnosed: Milvus OOM"
        assert len(backend.history) == 1

    def test_mock_backend_sequential_responses(self):
        backend = MockLLMBackend(responses=["Step 1: Check logs", "Step 2: Check metrics"])
        assert backend.generate("Prompt 1") == "Step 1: Check logs"
        assert backend.generate("Prompt 2") == "Step 2: Check metrics"
        # Falls back to default when responses exhausted
        assert "Step" in backend.generate("Prompt 3")

    def test_ollama_backend_interface(self):
        backend = OllamaBackend(model="llama3:8b", base_url="http://localhost:11434")
        assert isinstance(backend, LLMBackend)
        assert backend.model == "llama3:8b"

    def test_openai_backend_interface(self):
        backend = OpenAIBackend(model="gpt-4o-mini", api_key="sk-test", base_url="https://api.openai.com/v1")
        assert isinstance(backend, LLMBackend)
        assert backend.model == "gpt-4o-mini"


# =====================================================================
# 2. Diagnostic Tools Tests
# =====================================================================

class TestDiagnosticTools:
    """Locked assertions for read-only diagnostic tools."""

    def test_log_search_tool_filtering(self, sample_bundle):
        tool = LogSearchTool(sample_bundle)
        # Search by service
        milvus_logs = tool.execute(service="milvus-db")
        assert len(milvus_logs) == 1
        assert "Out of memory" in milvus_logs[0]["message"]

        # Search by level
        error_logs = tool.execute(level="ERROR")
        assert len(error_logs) == 2

        # Search by substring
        query_logs = tool.execute(query="Incoming request")
        assert len(query_logs) == 1

    def test_trace_inspect_tool(self, sample_bundle):
        tool = TraceInspectTool(sample_bundle)
        result = tool.execute(trace_id="tr-100")
        assert result["trace_id"] == "tr-100"
        assert "critical_path" in result
        assert "bottlenecks" in result
        assert len(result["critical_path"]) == 3
        assert result["bottlenecks"][0]["span_id"] == "sp-2"

    def test_metric_query_tool(self, sample_bundle):
        tool = MetricQueryTool(sample_bundle)
        result = tool.execute(metric_name="container_memory_bytes")
        assert result["count"] == 2
        assert result["min"] == 8000000000.0
        assert result["max"] == 16500000000.0
        assert result["avg"] == 12250000000.0

    def test_config_lookup_tool_sanitization(self, sample_bundle):
        tool = ConfigLookupTool(sample_bundle)
        result = tool.execute(service="milvus-db")
        assert result["service"] == "milvus-db"
        assert result["version"] == "v2.4.1"
        # Secret api_key must be sanitized
        settings_str = str(result["settings"])
        assert "sk-secret123456789" not in settings_str
        assert "[REDACTED" in settings_str

    def test_runbook_retrieve_tool(self, sample_bundle):
        tool = RunbookRetrieveTool(sample_bundle)
        results = tool.execute(query="exit code 137")
        assert len(results) == 1
        assert "Milvus OOM Troubleshooting" in results[0]

    def test_tool_call_budget_enforcement(self, sample_bundle):
        tool = LogSearchTool(sample_bundle, max_budget=2)
        tool.execute()
        tool.execute()
        with pytest.raises(RuntimeError, match="Tool budget exceeded"):
            tool.execute()


# =====================================================================
# 3. Bounded ReAct Loop Tests
# =====================================================================

class TestBoundedReActLoop:
    """Locked assertions for ReAct execution, FSM states, and safety bounds."""

    def test_fsm_mutation_refusal(self, sample_bundle):
        """Mutating or dangerous user prompts must be refused immediately."""
        backend = MockLLMBackend()
        agent = BoundedReActAgent(sample_bundle, llm=backend)

        dangerous_symptoms = [
            "Please restart the milvus service immediately",
            "Drop database test and re-index",
            "Delete pod milvus-db-0 and reboot",
        ]

        for symptom in dangerous_symptoms:
            report = agent.run(symptom=symptom)
            assert agent.state == AgentState.MUTATION_REFUSED
            assert report.status == "abstained"
            assert "Mutating operation refused" in (report.abstention_reason or "")

    def test_fsm_loop_detection_guard(self, sample_bundle):
        """Repeated identical tool calls (> 2) must interrupt and force synthesis."""
        # LLM keeps outputting the exact same tool call
        looping_output = '{"thought": "Check logs", "action": "log_search", "args": {"service": "milvus-db"}}'
        backend = MockLLMBackend(default_response=looping_output)
        agent = BoundedReActAgent(sample_bundle, llm=backend, max_steps=10)

        report = agent.run(symptom="504 gateway timeout")
        assert report is not None
        # Agent must terminate or force synthesis before reaching step 10
        assert agent.step_count <= 4
        assert agent.state in (AgentState.TERMINATED, AgentState.ABSTAINED)

    def test_fsm_max_step_budget(self, sample_bundle):
        """Agent must never exceed max_steps."""
        step_outputs = [
            '{"thought": "Search gateway logs", "action": "log_search", "args": {"service": "gateway"}}',
            '{"thought": "Search retrieval logs", "action": "log_search", "args": {"service": "retrieval"}}',
            '{"thought": "Query metrics", "action": "metric_query", "args": {"metric_name": "container_memory_bytes"}}',
            '{"thought": "Check config", "action": "config_lookup", "args": {"service": "milvus-db"}}',
            '{"thought": "Check runbooks", "action": "runbook_retrieve", "args": {"query": "milvus"}}',
        ]
        backend = MockLLMBackend(responses=step_outputs)
        agent = BoundedReActAgent(sample_bundle, llm=backend, max_steps=3)

        agent.run(symptom="504 gateway timeout")
        assert agent.step_count == 3
        assert agent.state in (AgentState.TERMINATED, AgentState.ABSTAINED)

    def test_complete_triage_flow_diagnosed(self, sample_bundle):
        """A normal triage workflow finishes with a grounded TriageReport."""
        responses = [
            '{"thought": "Search for error logs in milvus", "action": "log_search", "args": {"level": "ERROR", "service": "milvus-db"}}',
            '{"thought": "Found OOM log, inspect memory metrics", "action": "metric_query", "args": {"metric_name": "container_memory_bytes"}}',
            """{
                "thought": "Evidence confirms OOM during compaction.",
                "action": "finish",
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "title": "Milvus Compaction OOM",
                        "description": "Milvus pod killed by cgroup OOM during compaction",
                        "evidence_links": [
                            {
                                "evidence_id": "ev-log-1",
                                "source_type": "log",
                                "polarity": "support",
                                "description": "Out of memory kill process 501",
                                "relevance_score": 0.95
                            },
                            {
                                "evidence_id": "ev-metric-1",
                                "source_type": "metric",
                                "polarity": "support",
                                "description": "Memory reached 16.5GB hitting 16GB limit",
                                "relevance_score": 0.9
                            }
                        ]
                    }
                ]
            }""",
        ]
        backend = MockLLMBackend(responses=responses)
        agent = BoundedReActAgent(sample_bundle, llm=backend, max_steps=5)

        report = agent.run(symptom="504 gateway timeout")
        assert report.status == "diagnosed"
        assert report.primary_root_cause == "Milvus Compaction OOM"
        assert report.confidence >= 0.8
        assert len(report.hypotheses) == 1


# =====================================================================
# 4. CLI Tests
# =====================================================================

class TestCLI:
    """Locked assertions for the CLI interface."""

    def test_build_parser_options(self):
        parser = build_parser()
        # Subcommands exist
        args = parser.parse_args(["triage", "./data/incidents/INC-1", "--mock", "--model", "test-model"])
        assert args.command == "triage"
        assert args.incident_dir == "./data/incidents/INC-1"
        assert args.mock is True
        assert args.model == "test-model"

        inspect_args = parser.parse_args(["inspect", "./data/incidents/INC-1"])
        assert inspect_args.command == "inspect"
        assert inspect_args.incident_dir == "./data/incidents/INC-1"

    def test_cli_inspect_execution(self, tmp_path, sample_bundle):
        inc_dir = tmp_path / "INC-TEST"
        from tracelens.telemetry.reader import IncidentReader
        IncidentReader.save_bundle(sample_bundle, inc_dir)

        exit_code = main(["inspect", str(inc_dir)])
        assert exit_code == 0

    def test_cli_triage_execution_with_mock(self, tmp_path, sample_bundle):
        inc_dir = tmp_path / "INC-TEST"
        from tracelens.telemetry.reader import IncidentReader
        IncidentReader.save_bundle(sample_bundle, inc_dir)

        exit_code = main(["triage", str(inc_dir), "--mock"])
        assert exit_code == 0
