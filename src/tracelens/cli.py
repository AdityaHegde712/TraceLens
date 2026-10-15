"""Command-line interface for TraceLens incident triage and inspection."""

import argparse
import sys
from rich.console import Console
from rich.table import Table

from tracelens.agent.llm_backend import MockLLMBackend, OllamaBackend, OpenAIBackend
from tracelens.agent.react_loop import BoundedReActAgent
from tracelens.telemetry.reader import IncidentReader
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
    if args.mock:
        backend = MockLLMBackend()
    elif args.api_key:
        backend = OpenAIBackend(
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url or "https://api.openai.com/v1",
        )
    else:
        backend = OllamaBackend(
            model=args.model,
            base_url=args.base_url or "http://localhost:11434",
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


def main(args: list[str] | None = None) -> int:
    """Entry point for the tracelens command-line tool."""
    parser = build_parser()
    parsed_args = parser.parse_args(args)
    console = Console()

    if parsed_args.command == "inspect":
        return handle_inspect(parsed_args.incident_dir, console)
    elif parsed_args.command == "triage":
        return handle_triage(parsed_args, console)

    return 1


if __name__ == "__main__":
    sys.exit(main())
