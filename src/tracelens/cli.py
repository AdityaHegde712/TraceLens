"""Command-line interface for TraceLens incident triage and inspection."""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from tracelens.agent.chat import generate_chat_answer
from tracelens.agent.llm_backend import create_backend
from tracelens.agent.react_loop import BoundedReActAgent
from tracelens.telemetry.reader import IncidentBundle, IncidentReader
from tracelens.telemetry.trace_dag import TraceDAG


def build_parser() -> argparse.ArgumentParser:
    """Build the TraceLens argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="tracelens",
        description="TraceLens: Evidence-Grounded Incident Triage Assistant for RAG APIs",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Triage command
    triage_parser = subparsers.add_parser("triage", help="Triage an incident bundle")
    triage_parser.add_argument("incident_dir", help="Path to incident dataset directory")
    triage_parser.add_argument("--model", default="llama3:8b", help="LLM model identifier")
    triage_parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM backend")
    triage_parser.add_argument("--base-url", default=None, help="Inference API base URL")
    triage_parser.add_argument("--api-key", default=None, help="Inference API key for OpenAI-compatible providers")
    triage_parser.add_argument("--max-steps", type=int, default=5, help="Maximum diagnostic step budget")

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect telemetry data without LLM")
    inspect_parser.add_argument("incident_dir", help="Path to incident dataset directory")

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run matrix benchmark evaluation")
    bench_parser.add_argument("--incidents-dir", default=None, help="Directory containing incident bundles")
    bench_parser.add_argument("--output-dir", default="benchmark_results", help="Directory for scorecard and traces")
    bench_parser.add_argument("--smoke", action="store_true", help="Run fast 2x2 smoke test")
    bench_parser.add_argument("--mock", action="store_true", help="Force mock LLM backend")
    bench_parser.add_argument("--model", default="mock", help="Model identifier")

    # UI command
    ui_parser = subparsers.add_parser("ui", help="Launch interactive browser dashboard")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Server bind host")
    ui_parser.add_argument("--port", type=int, default=8000, help="Server bind port")
    ui_parser.add_argument("--reload", action="store_true", help="Enable live code reloading")

    # Models command
    models_parser = subparsers.add_parser("models", help="Discover and list free models")
    models_parser.add_argument("--api-key", default=None, help="Optional OpenRouter API key")

    # Chat command
    chat_parser = subparsers.add_parser("chat", help="Post-triage follow-up investigation chat")
    chat_parser.add_argument("incident_dir_or_id", help="Path to incident dataset directory or archetype ID")
    chat_parser.add_argument("question", help="Question about incident telemetry or remediation")
    chat_parser.add_argument("--model", default="mock", help="LLM model identifier")
    chat_parser.add_argument("--mock", action="store_true", help="Use deterministic mock LLM backend")
    chat_parser.add_argument("--api-key", default=None, help="Inference API key for OpenAI-compatible providers")
    chat_parser.add_argument("--base-url", default=None, help="Inference API base URL")

    return parser


def handle_inspect(incident_dir: str, console: Console) -> int:
    """Print structured telemetry overview of an incident bundle."""
    bundle = IncidentReader.load_bundle(incident_dir)
    console.print(f"[bold cyan]Incident:[/bold cyan] {bundle.manifest.incident_id} - {bundle.manifest.title}")
    console.print(f"[bold yellow]Reported Symptom:[/bold yellow] {bundle.manifest.symptom}")
    console.print(f"[bold green]Services:[/bold green] {', '.join(bundle.manifest.services_involved)}")

    table = Table(title="Telemetry Summary")
    table.add_column("Telemetry Type", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_row("Structured Logs", str(len(bundle.logs)))
    table.add_row("Distributed Traces", str(len(bundle.traces)))
    table.add_row("Metric Points", str(len(bundle.metrics)))
    table.add_row("Config Snapshots", str(len(bundle.configs)))
    table.add_row("Runbooks", str(len(bundle.runbooks)))
    console.print(table)

    if bundle.traces:
        dag = TraceDAG.from_spans(bundle.traces)
        critical_path = dag.find_critical_path()
        bottlenecks = dag.detect_bottlenecks(threshold_pct=0.3)

        console.print("\n[bold]Critical Path Analysis:[/bold]")
        for node in critical_path:
            console.print(f"  |-- {node.span.name} ({node.duration_ms:.1f}ms) [status={node.span.status}]")

        if bottlenecks:
            console.print("\n[bold red]Detected Bottlenecks:[/bold red]")
            for b in bottlenecks:
                console.print(f"  [!] Span {b.span.span_id} ({b.span.name}): self-time {b.self_time_ms:.1f}ms")

    return 0


def handle_triage(args: argparse.Namespace, console: Console) -> int:
    """Execute bounded ReAct triage agent over an incident bundle."""
    bundle = IncidentReader.load_bundle(args.incident_dir)

    # Configure backend
    model_name = "mock" if args.mock else args.model
    backend = create_backend(
        model=model_name,
        api_key=args.api_key,
        base_url=args.base_url,
    )

    agent = BoundedReActAgent(bundle, llm=backend, max_steps=args.max_steps)
    console.print(f"[bold]Starting TraceLens triage on incident {bundle.manifest.incident_id}...[/bold]")

    report = agent.run()

    console.print("\n[bold green]================ TRIAGE REPORT ================[/bold green]")
    console.print(f"[bold]Incident ID:[/bold] {report.incident_id}")
    console.print(f"[bold]Status:[/bold] {report.status.upper()}")
    console.print(f"[bold]Primary Root Cause:[/bold] {report.primary_root_cause or 'N/A'}")
    console.print(f"[bold]Confidence:[/bold] {report.confidence:.2f}")

    if report.abstention_reason:
        console.print(f"[bold yellow]Abstention Reason:[/bold yellow] {report.abstention_reason}")

    if report.hypotheses:
        console.print("\n[bold]Evaluated Hypotheses:[/bold]")
        for h in report.hypotheses:
            console.print(f"  * [bold]{h.title}[/bold] (Confidence: {h.confidence:.2f}, Support: {h.support_count}, Refute: {h.refutation_count})")
            for e in h.evidence_links:
                console.print(f"    - [{e.polarity.value.upper()}] ({e.source_type}): {e.description} (score: {e.relevance_score})")

    return 0


def handle_benchmark(args: argparse.Namespace, console: Console) -> int:
    """Execute matrix benchmark evaluation harness."""
    from tracelens.evaluation.benchmark import BenchmarkConfig, BenchmarkRunner

    models = ["mock"] if args.mock else [args.model]
    config = BenchmarkConfig(
        models=models,
        smoke_test=args.smoke,
        incidents_dir=args.incidents_dir,
        output_dir=args.output_dir,
    )
    console.print(f"[bold]Running TraceLens Benchmark (smoke={args.smoke})...[/bold]")
    runner = BenchmarkRunner(config)
    scorecard = runner.run()

    table = Table(title="Benchmark Evaluation Scorecard")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Evaluations", str(scorecard.total_evaluations))
    table.add_row("Diagnostic Accuracy", f"{scorecard.accuracy * 100:.1f}%")
    table.add_row("Citation Precision", f"{scorecard.citation_precision * 100:.1f}%")
    table.add_row("Abstention Rate", f"{scorecard.abstention_rate * 100:.1f}%")
    table.add_row("Canary Leakage Rate", f"{scorecard.canary_leakage_rate * 100:.1f}%")
    table.add_row("Injection Vulnerability", f"{scorecard.injection_vulnerability_rate * 100:.1f}%")
    table.add_row("Average Tool Steps", f"{scorecard.avg_steps:.2f}")
    table.add_row("Duplicate Tool Rate", f"{scorecard.duplicate_tool_rate * 100:.1f}%")
    console.print(table)
    console.print(f"[bold green]Artifacts saved to {args.output_dir}[/bold green]")
    return 0


def handle_ui(args: argparse.Namespace, console: Console) -> int:
    """Launch the interactive browser dashboard server."""
    import uvicorn

    console.print(f"[bold cyan]Launching TraceLens UI on http://{args.host}:{args.port}...[/bold cyan]")
    uvicorn.run("tracelens.web.server:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def handle_models(args: argparse.Namespace, console: Console) -> int:
    """Discover and display available free LLM models."""
    from tracelens.discovery import discover_free_models

    console.print("[bold cyan]Querying active free models...[/bold cyan]")
    models = discover_free_models(api_key=args.api_key)

    table = Table(title="Available Free Tier & Local Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Context", style="magenta")
    table.add_column("Params", style="yellow")

    for m in models:
        table.add_row(
            m["id"],
            m.get("name", m["id"]),
            f"{m.get('context_length', 0):,}" if m.get("context_length") else "N/A",
            m.get("params") or "N/A",
        )
    console.print(table)
    return 0


def _resolve_bundle(target: str) -> IncidentBundle:
    """Resolve an incident bundle from either a filesystem directory path or archetype ID."""
    from tracelens.fault_lab.generator import generate_all_bundles

    path = Path(target)
    if path.exists() and (path / "manifest.json").exists():
        return IncidentReader.load_bundle(path)

    fixtures_path = Path("data/fixtures/incidents") / target
    if fixtures_path.exists() and (fixtures_path / "manifest.json").exists():
        return IncidentReader.load_bundle(fixtures_path)

    all_bundles = generate_all_bundles()
    if target in all_bundles:
        return all_bundles[target]

    return IncidentReader.load_bundle(path)


def handle_chat(args: argparse.Namespace, console: Console) -> int:
    """Execute post-triage follow-up investigation chat and print grounded answer."""
    bundle = _resolve_bundle(args.incident_dir_or_id)
    model_name = "mock" if args.mock else args.model

    console.print(
        f"[bold cyan]TraceLens Post-Triage Chat[/bold cyan] - "
        f"[bold]{bundle.manifest.incident_id}[/bold]: {bundle.manifest.title}"
    )
    console.print(f"[bold yellow]Question:[/bold yellow] {args.question}")

    answer = generate_chat_answer(
        bundle=bundle,
        question=args.question,
        model=model_name,
        api_key=args.api_key,
        base_url=args.base_url,
    )

    console.print("\n[bold green]Answer:[/bold green]")
    console.print(answer)
    return 0


def main(args: list[str] | None = None) -> int:
    """Entry point for the tracelens command-line tool."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)
    console = Console()

    if parsed_args.command == "inspect":
        return handle_inspect(parsed_args.incident_dir, console)
    elif parsed_args.command == "triage":
        return handle_triage(parsed_args, console)
    elif parsed_args.command == "benchmark":
        return handle_benchmark(parsed_args, console)
    elif parsed_args.command == "ui":
        return handle_ui(parsed_args, console)
    elif parsed_args.command == "models":
        return handle_models(parsed_args, console)
    elif parsed_args.command == "chat":
        return handle_chat(parsed_args, console)

    return 1


if __name__ == "__main__":
    sys.exit(main())
