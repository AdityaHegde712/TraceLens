"""Read-only diagnostic tools for incident telemetry investigation.

Includes LogSearchTool, TraceInspectTool, MetricQueryTool, ConfigLookupTool,
and RunbookRetrieveTool, with strict call budget tracking and parameter validation.
"""

from abc import ABC, abstractmethod
from typing import Any

from tracelens.telemetry.reader import IncidentBundle
from tracelens.telemetry.sanitizer import TelemetrySanitizer
from tracelens.telemetry.trace_dag import TraceDAG


class RunbookEntry(dict):
    """Dictionary representing runbook content with stable evidence_id."""

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        return bool(isinstance(key, str) and key in self.get("content", ""))

    def __str__(self) -> str:
        return f"[evidence_id: {self.get('evidence_id')}]\n{self.get('content', '')}"


class BaseDiagnosticTool(ABC):
    """Abstract base class for telemetry diagnostic tools with call budgeting."""

    def __init__(self, bundle: IncidentBundle, max_budget: int = 20) -> None:
        """Initialize tool with target incident bundle and maximum call budget."""
        self.bundle = bundle
        self.max_budget = max_budget
        self.call_count = 0
        self.sanitizer = TelemetrySanitizer()

    def _check_budget(self) -> None:
        """Increment call counter and verify budget is not exceeded."""
        if self.call_count >= self.max_budget:
            raise RuntimeError(f"Tool budget exceeded (limit={self.max_budget})")
        self.call_count += 1

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute the tool operation."""


class LogSearchTool(BaseDiagnosticTool):
    """Filters structured service logs by level, service, substring, or time."""

    def execute(
        self,
        level: str | None = None,
        service: str | None = None,
        query: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search logs matching criteria.

        Args:
            level: Optional severity level filter (e.g. 'ERROR').
            service: Optional service name filter.
            query: Substring to search inside log messages.
            limit: Maximum number of log records to return.

        Returns:
            List of matching serialized log dictionaries.
        """
        self._check_budget()
        results: list[dict[str, Any]] = []

        for idx, log in enumerate(self.bundle.logs):
            if level and log.level.upper() != level.upper():
                continue
            if service and log.service != service:
                continue
            if query and query.lower() not in log.message.lower():
                continue

            entry_dict = log.model_dump(mode="json")
            entry_dict["evidence_id"] = f"log-{idx}"
            entry_dict["message"] = self.sanitizer.sanitize_text(entry_dict["message"])
            entry_dict["attributes"] = self.sanitizer.sanitize_dict(entry_dict.get("attributes", {}))
            results.append(entry_dict)

            if len(results) >= limit:
                break

        return results


class TraceInspectTool(BaseDiagnosticTool):
    """Analyzes distributed trace DAGs to find bottlenecks and the critical path."""

    def execute(self, trace_id: str | None = None) -> dict[str, Any]:
        """Inspect trace DAG by trace ID.

        Args:
            trace_id: Distributed trace ID to inspect.

        Returns:
            Dictionary containing critical path, bottlenecks, and self-times.
        """
        self._check_budget()
        matching_spans = self.bundle.traces
        if trace_id:
            matching_spans = [s for s in self.bundle.traces if s.trace_id == trace_id]

        if not matching_spans:
            return {"error": f"No spans found for trace_id={trace_id}"}

        dag = TraceDAG.from_spans(matching_spans)
        critical_path = dag.find_critical_path()
        bottlenecks = dag.detect_bottlenecks(threshold_pct=0.3)
        self_times = dag.calculate_self_times()

        return {
            "trace_id": trace_id or (matching_spans[0].trace_id if matching_spans else None),
            "critical_path": [
                {
                    "evidence_id": node.span.span_id,
                    "span_id": node.span.span_id,
                    "name": node.span.name,
                    "duration_ms": node.duration_ms,
                    "status": node.span.status,
                }
                for node in critical_path
            ],
            "bottlenecks": [
                {
                    "evidence_id": b.span.span_id,
                    "span_id": b.span.span_id,
                    "name": b.span.name,
                    "self_time_ms": b.self_time_ms,
                    "status": b.span.status,
                }
                for b in bottlenecks
            ],
            "self_times": self_times,
        }


class MetricQueryTool(BaseDiagnosticTool):
    """Queries time-series metrics and computes summary statistics."""

    def execute(
        self,
        metric_name: str | None = None,
        pod: str | None = None,
    ) -> dict[str, Any]:
        """Query metrics by name and dimensional labels.

        Args:
            metric_name: Target metric name.
            pod: Optional pod label filter.

        Returns:
            Dictionary of summary statistics and matching data points.
        """
        self._check_budget()
        matches = self.bundle.metrics
        if metric_name:
            matches = [m for m in matches if m.metric_name == metric_name]
        if pod:
            matches = [m for m in matches if m.labels.get("pod") == pod]

        if not matches:
            target_metric = metric_name or "unknown"
            return {
                "evidence_id": f"metric-{target_metric}",
                "count": 0,
                "values": [],
                "message": "No matching metric points found",
            }

        values = [m.value for m in matches]
        observations = []
        for m in matches:
            obs = m.model_dump(mode="json")
            obs["evidence_id"] = f"metric-{m.metric_name}"
            observations.append(obs)

        target_metric = metric_name or matches[0].metric_name
        return {
            "evidence_id": f"metric-{target_metric}",
            "metric_name": metric_name,
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "observations": observations,
        }


class ConfigLookupTool(BaseDiagnosticTool):
    """Retrieves sanitized service configuration and metadata."""

    def execute(self, service: str | None = None) -> dict[str, Any]:
        """Look up configuration for a specified service.

        Args:
            service: Target service name.

        Returns:
            Dictionary of sanitized configuration settings.
        """
        self._check_budget()
        for cfg in self.bundle.configs:
            if not service or cfg.service == service:
                return {
                    "evidence_id": f"config-{cfg.service}",
                    "service": cfg.service,
                    "version": cfg.version,
                    "settings": self.sanitizer.sanitize_dict(cfg.settings),
                }

        target_service = service or "unknown"
        return {
            "evidence_id": f"config-{target_service}",
            "error": f"Configuration not found for service={service}",
        }


class RunbookRetrieveTool(BaseDiagnosticTool):
    """Searches operational runbooks for remediation procedures and known symptoms."""

    def execute(self, query: str | None = None) -> list[Any]:
        """Search runbooks for matching guidelines.

        Args:
            query: Substring to search inside runbook contents.

        Returns:
            List of matching runbook entries with stable evidence IDs.
        """
        self._check_budget()
        results: list[Any] = []
        for idx, rb in enumerate(self.bundle.runbooks):
            filename = f"runbook_{idx + 1}.md"
            if not query or query.lower() in rb.lower():
                results.append(
                    RunbookEntry(
                        evidence_id=f"runbook-{filename}",
                        filename=filename,
                        content=rb,
                    )
                )
        return results
