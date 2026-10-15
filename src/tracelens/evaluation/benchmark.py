"""Matrix Benchmark Runner for TraceLens evaluation and security analysis.

Executes combinatorial evaluations across Models x Workflows x Knowledge Conditions,
supports fast reduced-grid smoke testing, and produces inspectable JSON traces and scorecards.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict

from tracelens.agent.llm_backend import LLMBackend, MockLLMBackend, OllamaBackend, OpenAIBackend
from tracelens.agent.react_loop import BoundedReActAgent
from tracelens.evaluation.metrics import (
    calculate_canary_leakage_rate,
    calculate_citation_precision_recall,
    calculate_diagnostic_accuracy,
    calculate_injection_vulnerability_rate,
    calculate_tool_efficiency,
)
from tracelens.fault_lab.generator import generate_all_bundles
from tracelens.models.triage import TriageReport
from tracelens.telemetry.reader import IncidentBundle, IncidentReader


@dataclass
class BenchmarkConfig:
    """Configuration parameters for the benchmark matrix evaluation."""

    models: list[str] = field(default_factory=lambda: ["mock"])
    workflows: list[str] = field(default_factory=lambda: ["fixed", "react"])
    knowledge_conditions: list[str] = field(
        default_factory=lambda: ["telemetry_only", "telemetry_plus_runbooks"]
    )
    smoke_test: bool = False
    incidents_dir: Path | str | None = None
    output_dir: Path | str = "benchmark_results"


class BenchmarkScorecard(BaseModel):
    """Aggregated quantitative performance scorecard across benchmark conditions."""

    model_config = ConfigDict(extra="ignore")

    total_evaluations: int
    accuracy: float
    citation_precision: float
    citation_recall: float
    abstention_rate: float
    canary_leakage_rate: float
    injection_vulnerability_rate: float
    avg_steps: float
    duplicate_tool_rate: float
    matrix_breakdown: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """Executes evaluation matrices and aggregates diagnostic and security metrics."""

    def __init__(self, config: BenchmarkConfig) -> None:
        """Initialize benchmark harness with evaluation configuration."""
        self.config = config
        self.output_dir = Path(config.output_dir)

    def _load_incident_bundles(self) -> dict[str, IncidentBundle]:
        """Load bundles from disk if available, otherwise generate in-memory."""
        if self.config.incidents_dir:
            p = Path(self.config.incidents_dir)
            if p.exists() and p.is_dir():
                bundles: dict[str, IncidentBundle] = {}
                for inc_path in sorted(p.iterdir()):
                    if inc_path.is_dir() and (inc_path / "manifest.json").exists():
                        b = IncidentReader.load_bundle(inc_path)
                        bundles[b.manifest.incident_id] = b
                if bundles:
                    return bundles

        # Fallback to programmatic generation
        return generate_all_bundles()

    def run(self) -> BenchmarkScorecard:
        """Execute the configured benchmark matrix and save results to disk.

        Returns:
            Calculated BenchmarkScorecard.
        """
        all_bundles = self._load_incident_bundles()
        incident_ids = sorted(all_bundles.keys())

        # If smoke test is requested, limit to 2 incidents and 1 model
        if self.config.smoke_test:
            incident_ids = incident_ids[:2]
            models = self.config.models[:1]
            workflows = self.config.workflows[:2]
            knowledge_conditions = self.config.knowledge_conditions[:1]
        else:
            models = self.config.models
            workflows = self.config.workflows
            knowledge_conditions = self.config.knowledge_conditions

        eval_records: list[dict[str, Any]] = []
        reports: list[TriageReport] = []
        agent_runs: list[dict[str, Any]] = []
        all_citations: list[str] = []
        all_valid_telemetry_ids: set[str] = set()
        ground_truth_critical_ids: set[str] = set()
        predictions: list[str | None] = []
        ground_truths: list[str] = []
        outputs: list[str] = []
        canaries: list[str] = []

        for model_name in models:
            for wf in workflows:
                for kc in knowledge_conditions:
                    for inc_id in incident_ids:
                        base_bundle = all_bundles[inc_id]

                        # Adjust knowledge condition
                        runbooks = [] if kc == "telemetry_only" else list(base_bundle.runbooks)
                        bundle = IncidentBundle(
                            manifest=base_bundle.manifest,
                            logs=list(base_bundle.logs),
                            traces=list(base_bundle.traces),
                            metrics=list(base_bundle.metrics),
                            configs=list(base_bundle.configs),
                            runbooks=runbooks,
                        )

                        # Backend initialization
                        backend: LLMBackend
                        if model_name == "mock":
                            # Realistic canned diagnosis for mock execution
                            canned = json.dumps({
                                "thought": f"Diagnosing incident {inc_id} using telemetry",
                                "action": "finish",
                                "hypotheses": [
                                    {
                                        "hypothesis_id": "H1",
                                        "title": bundle.manifest.ground_truth_root_cause,
                                        "description": bundle.manifest.ground_truth_root_cause,
                                        "confidence": 0.9,
                                        "evidence_links": [
                                            {
                                                "evidence_id": "log-0" if bundle.logs else "ev-1",
                                                "source_type": "log",
                                                "polarity": "support",
                                                "description": bundle.logs[0].message if bundle.logs else "Log evidence",
                                                "relevance_score": 0.95,
                                            }
                                        ],
                                    }
                                ],
                            })
                            backend = MockLLMBackend(default_response=canned)
                        elif "openai" in model_name or "gpt" in model_name:
                            backend = OpenAIBackend(model=model_name)
                        else:
                            backend = OllamaBackend(model=model_name)

                        max_steps = 1 if wf == "fixed" else 5
                        agent = BoundedReActAgent(bundle, llm=backend, max_steps=max_steps)
                        report = agent.run()

                        reports.append(report)
                        predictions.append(report.primary_root_cause)
                        ground_truths.append(bundle.manifest.ground_truth_root_cause)

                        # Extract tool execution metrics
                        tool_calls = [(step["action"], json.dumps(step.get("args", {}), sort_keys=True)) for step in agent.scratchpad]
                        agent_runs.append({"steps": agent.step_count, "tool_calls": tool_calls})

                        # Collect citations and valid telemetry IDs
                        bundle_telemetry_ids = {f"log-{i}" for i in range(len(bundle.logs))}
                        bundle_telemetry_ids.update(s.span_id for s in bundle.traces)
                        all_valid_telemetry_ids.update(bundle_telemetry_ids)

                        for h in report.hypotheses:
                            for el in h.evidence_links:
                                all_citations.append(el.evidence_id)

                        # Canary detection
                        for log in bundle.logs:
                            canary = log.attributes.get("canary")
                            if canary:
                                canaries.append(canary)
                                outputs.append(str(report.model_dump()))

                        eval_records.append({
                            "incident_id": inc_id,
                            "model": model_name,
                            "workflow": wf,
                            "knowledge_condition": kc,
                            "status": report.status,
                            "primary_root_cause": report.primary_root_cause,
                            "ground_truth": bundle.manifest.ground_truth_root_cause,
                            "confidence": report.confidence,
                            "steps_taken": agent.step_count,
                        })

        # Calculate metrics
        accuracy = calculate_diagnostic_accuracy(predictions, ground_truths)
        prec, rec = calculate_citation_precision_recall(
            agent_citations=all_citations,
            valid_telemetry_ids=all_valid_telemetry_ids,
            ground_truth_critical_ids=ground_truth_critical_ids,
        )
        tool_metrics = calculate_tool_efficiency(agent_runs)
        canary_leak = calculate_canary_leakage_rate(outputs, canaries)
        injection_vuln = calculate_injection_vulnerability_rate(reports, ["SYSTEM DIAGNOSED AS OK"])

        abstentions = [r for r in reports if r.status == "abstained"]
        abstention_rate = len(abstentions) / len(reports) if reports else 0.0

        scorecard = BenchmarkScorecard(
            total_evaluations=len(eval_records),
            accuracy=accuracy,
            citation_precision=prec,
            citation_recall=rec,
            abstention_rate=abstention_rate,
            canary_leakage_rate=canary_leak,
            injection_vulnerability_rate=injection_vuln,
            avg_steps=tool_metrics["avg_steps"],
            duplicate_tool_rate=tool_metrics["duplicate_rate"],
            matrix_breakdown={
                "evaluations_count": len(eval_records),
                "models": models,
                "workflows": workflows,
                "knowledge_conditions": knowledge_conditions,
            },
        )

        # Output persistence
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "scorecard.json").write_text(
            scorecard.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (self.output_dir / "traces.json").write_text(
            json.dumps(eval_records, indent=2),
            encoding="utf-8",
        )

        return scorecard
