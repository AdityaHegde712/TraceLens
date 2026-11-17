"""Post-triage follow-up investigation chat assistance for TraceLens.

Provides structured telemetry context extraction and LLM-powered Q&A
answering questions grounded strictly in distributed traces, logs, metrics,
and runbook telemetry.
"""

from typing import Any

from tracelens.agent.llm_backend import create_backend
from tracelens.models.triage import TriageReport
from tracelens.telemetry.reader import IncidentBundle
from tracelens.telemetry.trace_dag import TraceDAG


def build_incident_chat_context(
    bundle: IncidentBundle,
    report: TriageReport | None = None,
) -> dict[str, Any]:
    """Extract a concise, grounded telemetry context for chat Q&A.

    Args:
        bundle: Telemetry incident bundle.
        report: Optional active or existing triage report.

    Returns:
        Structured dictionary containing telemetry context summaries.
    """
    manifest = bundle.manifest
    root_cause = (
        report.primary_root_cause
        if report and report.primary_root_cause
        else manifest.ground_truth_root_cause
    )

    # Trace self-times and bottlenecks
    dag_summary = "No trace data available."
    if bundle.traces:
        dag = TraceDAG.from_spans(bundle.traces)
        critical_path = dag.find_critical_path()
        bottlenecks = dag.detect_bottlenecks(threshold_pct=0.3)
        self_times = dag.calculate_self_times()
        top_self = sorted(self_times.items(), key=lambda x: x[1], reverse=True)[:3]
        dag_summary = (
            f"Critical path has {len(critical_path)} spans. "
            f"Detected bottlenecks: {[b.span.name for b in bottlenecks] or 'None'}. "
            f"Top self-time spans: {', '.join(f'{name} ({t:.1f}ms)' for name, t in top_self)}."
        )

    # Log summary
    error_logs = [
        item.message
        for item in bundle.logs
        if "error" in item.level.lower() or "warn" in item.level.lower()
    ]
    logs_summary = (
        f"{len(bundle.logs)} total logs, {len(error_logs)} error/warning logs. "
        f"Key samples: {error_logs[:3] if error_logs else 'None'}."
    )

    # Metric highlights
    metric_names = list({m.metric_name for m in bundle.metrics})
    metric_summary = (
        f"{len(bundle.metrics)} metric data points across metrics: "
        f"{', '.join(metric_names[:5]) if metric_names else 'None'}."
    )

    # Runbook titles
    runbook_titles = []
    for rb in bundle.runbooks:
        title = "Remediation Guide"
        for line in rb.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                title = stripped.lstrip("#").strip()
                break
            elif stripped and title == "Remediation Guide":
                title = stripped[:50]
        runbook_titles.append(title)

    triage_status = "diagnosed"
    if report:
        triage_status = (
            report.status.value
            if hasattr(report.status, "value")
            else str(report.status)
        )

    return {
        "incident_id": manifest.incident_id,
        "title": manifest.title,
        "symptom": manifest.symptom,
        "services_involved": manifest.services_involved,
        "root_cause": root_cause,
        "triage_status": triage_status,
        "dag_summary": dag_summary,
        "logs_summary": logs_summary,
        "metric_summary": metric_summary,
        "runbook_titles": runbook_titles,
    }


def format_context_prompt(context: dict[str, Any]) -> str:
    """Format structured context into a readable prompt block.

    Args:
        context: Context dictionary produced by build_incident_chat_context.

    Returns:
        Formatted multi-line prompt string.
    """
    runbooks_str = (
        ", ".join(context["runbook_titles"])
        if context["runbook_titles"]
        else "None"
    )
    return (
        f"Incident: {context['incident_id']} - {context['title']}\n"
        f"Reported Symptom: {context['symptom']}\n"
        f"Involved Services: {', '.join(context['services_involved'])}\n"
        f"Diagnosed Root Cause: {context['root_cause']}\n"
        f"Triage Status: {context['triage_status']}\n"
        f"Distributed Traces & Latency: {context['dag_summary']}\n"
        f"Structured Logs: {context['logs_summary']}\n"
        f"Metrics Telemetry: {context['metric_summary']}\n"
        f"Available Runbooks: {runbooks_str}"
    )


def generate_chat_answer(
    bundle: IncidentBundle,
    question: str,
    report: TriageReport | None = None,
    model: str = "mock",
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    """Generate an evidence-grounded answer to a follow-up investigation question.

    Args:
        bundle: Telemetry incident bundle.
        question: User inquiry regarding the incident.
        report: Optional active triage report.
        model: LLM model identifier.
        api_key: Optional inference API key.
        base_url: Optional inference API base URL.

    Returns:
        Direct, grounded response string.
    """
    context_dict = build_incident_chat_context(bundle, report)
    context_text = format_context_prompt(context_dict)

    if model == "mock":
        recommended_action = (
            context_dict["runbook_titles"][0]
            if context_dict["runbook_titles"]
            else "Inspect service telemetry"
        )
        return (
            f"[TraceLens Grounded Analysis for {context_dict['incident_id']}]\n"
            f"Root Cause: {context_dict['root_cause']}.\n"
            f"Latency Bottlenecks & DAG: {context_dict['dag_summary']}\n"
            f"Logs & Error Evidence: {context_dict['logs_summary']}\n"
            f"Metrics: {context_dict['metric_summary']}\n"
            f"Recommended Runbook: {recommended_action}.\n"
            f"Answer: Based on telemetry for {context_dict['title']}, the root cause is {context_dict['root_cause']} "
            f"affecting {', '.join(context_dict['services_involved'])}."
        )

    system_prompt = (
        "You are TraceLens, an evidence-grounded incident triage assistant for microservice architectures. "
        "Answer the user's follow-up questions strictly based on the provided incident telemetry context "
        "(traces, bottlenecks, logs, metrics, runbooks, and root cause). "
        "Be concise, technical, and cite specific services, metrics, or error logs. "
        "Never hallucinate telemetry not present in the context."
    )
    user_prompt = (
        f"Telemetry Context:\n{context_text}\n\n"
        f"Investigator Question: {question}\n\n"
        "Provide a grounded, direct answer:"
    )

    backend = create_backend(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    return backend.generate(prompt=user_prompt, system_prompt=system_prompt)
