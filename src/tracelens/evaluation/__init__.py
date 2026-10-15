"""Evaluation benchmark runner, metric calculators, and security scoring."""

from tracelens.evaluation.benchmark import (
    BenchmarkConfig,
    BenchmarkRunner,
    BenchmarkScorecard,
)
from tracelens.evaluation.metrics import (
    calculate_abstention_metrics,
    calculate_canary_leakage_rate,
    calculate_citation_precision_recall,
    calculate_diagnostic_accuracy,
    calculate_injection_vulnerability_rate,
    calculate_tool_efficiency,
)

__all__ = [
    "BenchmarkConfig",
    "BenchmarkRunner",
    "BenchmarkScorecard",
    "calculate_diagnostic_accuracy",
    "calculate_citation_precision_recall",
    "calculate_abstention_metrics",
    "calculate_tool_efficiency",
    "calculate_canary_leakage_rate",
    "calculate_injection_vulnerability_rate",
]
