"""Incident telemetry bundle loader and persistence reader.

Parses standardized JSON bundles containing incident manifests, logs, traces,
metrics, service configurations, and markdown operational runbooks.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path

from tracelens.models.telemetry import (
    ConfigMetadata,
    IncidentManifest,
    LogEntry,
    MetricPoint,
    TraceSpan,
)


@dataclass
class IncidentBundle:
    """In-memory representation of an incident dataset bundle."""

    manifest: IncidentManifest
    logs: list[LogEntry] = field(default_factory=list)
    traces: list[TraceSpan] = field(default_factory=list)
    metrics: list[MetricPoint] = field(default_factory=list)
    configs: list[ConfigMetadata] = field(default_factory=list)
    runbooks: list[str] = field(default_factory=list)


class IncidentReader:
    """Reader and serializer for reproducible incident bundles."""

    @classmethod
    def load_bundle(cls, dir_path: Path | str) -> IncidentBundle:
        """Load an incident bundle from a directory.

        Args:
            dir_path: Directory containing manifest.json and associated telemetry files.

        Returns:
            An IncidentBundle populated with parsed Pydantic telemetry models.
        """
        path = Path(dir_path)
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Incident bundle directory not found: {path}")

        # 1. Manifest (required)
        manifest_file = path / "manifest.json"
        if not manifest_file.exists():
            manifest_file = path / "incident.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"No manifest.json or incident.json found in {path}")

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest = IncidentManifest.model_validate(manifest_data)

        # 2. Logs (optional)
        logs: list[LogEntry] = []
        logs_file = path / "logs.json"
        if logs_file.exists():
            raw_logs = json.loads(logs_file.read_text(encoding="utf-8"))
            if isinstance(raw_logs, list):
                logs = [LogEntry.model_validate(item) for item in raw_logs]

        # 3. Traces (optional)
        traces: list[TraceSpan] = []
        traces_file = path / "traces.json"
        if traces_file.exists():
            raw_traces = json.loads(traces_file.read_text(encoding="utf-8"))
            if isinstance(raw_traces, list):
                traces = [TraceSpan.model_validate(item) for item in raw_traces]

        # 4. Metrics (optional)
        metrics: list[MetricPoint] = []
        metrics_file = path / "metrics.json"
        if metrics_file.exists():
            raw_metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            if isinstance(raw_metrics, list):
                metrics = [MetricPoint.model_validate(item) for item in raw_metrics]

        # 5. Configs (optional)
        configs: list[ConfigMetadata] = []
        config_file = path / "config.json"
        if not config_file.exists():
            config_file = path / "configs.json"
        if config_file.exists():
            raw_configs = json.loads(config_file.read_text(encoding="utf-8"))
            if isinstance(raw_configs, list):
                configs = [ConfigMetadata.model_validate(item) for item in raw_configs]
            elif isinstance(raw_configs, dict):
                configs = [ConfigMetadata.model_validate(raw_configs)]

        # 6. Runbooks (optional)
        runbooks: list[str] = []
        runbooks_dir = path / "runbooks"
        if runbooks_dir.exists() and runbooks_dir.is_dir():
            for rb_file in sorted(runbooks_dir.glob("*.md")):
                runbooks.append(rb_file.read_text(encoding="utf-8"))
        single_rb = path / "runbook.md"
        if single_rb.exists():
            runbooks.append(single_rb.read_text(encoding="utf-8"))

        return IncidentBundle(
            manifest=manifest,
            logs=logs,
            traces=traces,
            metrics=metrics,
            configs=configs,
            runbooks=runbooks,
        )

    @classmethod
    def save_bundle(cls, bundle: IncidentBundle, out_dir: Path | str) -> None:
        """Serialize an IncidentBundle to disk in standard directory structure.

        Args:
            bundle: In-memory IncidentBundle.
            out_dir: Target output directory.
        """
        path = Path(out_dir)
        path.mkdir(parents=True, exist_ok=True)

        # Manifest
        (path / "manifest.json").write_text(
            bundle.manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # Logs
        if bundle.logs:
            logs_json = json.dumps([e.model_dump(mode="json") for e in bundle.logs], indent=2)
            (path / "logs.json").write_text(logs_json, encoding="utf-8")

        # Traces
        if bundle.traces:
            traces_json = json.dumps([t.model_dump(mode="json") for t in bundle.traces], indent=2)
            (path / "traces.json").write_text(traces_json, encoding="utf-8")

        # Metrics
        if bundle.metrics:
            metrics_json = json.dumps([m.model_dump(mode="json") for m in bundle.metrics], indent=2)
            (path / "metrics.json").write_text(metrics_json, encoding="utf-8")

        # Configs
        if bundle.configs:
            configs_json = json.dumps([c.model_dump(mode="json") for c in bundle.configs], indent=2)
            (path / "config.json").write_text(configs_json, encoding="utf-8")

        # Runbooks
        if bundle.runbooks:
            rb_dir = path / "runbooks"
            rb_dir.mkdir(exist_ok=True)
            for idx, content in enumerate(bundle.runbooks):
                (rb_dir / f"runbook_{idx + 1}.md").write_text(content, encoding="utf-8")
