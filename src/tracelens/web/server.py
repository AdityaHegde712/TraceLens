"""FastAPI backend server for the TraceLens interactive browser UI.

Provides REST endpoints for incident exploration, telemetry inspection,
bounded ReAct triage execution, and Server-Sent Events (SSE) live streaming.
"""

import json
from pathlib import Path
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tracelens.agent.llm_backend import MockLLMBackend, OllamaBackend, OpenAIBackend
from tracelens.agent.react_loop import BoundedReActAgent
from tracelens.fault_lab.generator import generate_all_bundles
from tracelens.models.triage import TriageReport
from tracelens.telemetry.reader import IncidentBundle, IncidentReader
from tracelens.telemetry.trace_dag import TraceDAG

app = FastAPI(title="TraceLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active triage sessions
SESSIONS: dict[str, dict[str, Any]] = {}

STATIC_DIR = Path(__file__).parent / "static"


class TriageRequest(BaseModel):
    """Payload to launch an incident triage execution."""

    incident_id: str = Field(..., description="Target incident archetype ID")
    symptom: str | None = Field(default=None, description="Optional custom symptom alert")
    model: str = Field(default="mock", description="Model backend (mock, ollama, openai)")
    workflow: str = Field(default="react", description="Workflow type (react or fixed)")
    api_key: str | None = Field(default=None, description="OpenAI API key")
    base_url: str | None = Field(default=None, description="Inference endpoint base URL")


def _get_bundle(incident_id: str) -> IncidentBundle:
    """Retrieve an incident bundle from disk fixtures or generator."""
    fixtures_dir = Path("data/fixtures/incidents") / incident_id
    if fixtures_dir.exists() and (fixtures_dir / "manifest.json").exists():
        return IncidentReader.load_bundle(fixtures_dir)

    all_bundles = generate_all_bundles()
    if incident_id in all_bundles:
        return all_bundles[incident_id]

    raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")


@app.get("/api/incidents")
def list_incidents() -> list[dict[str, Any]]:
    """List all available benchmark incident archetypes."""
    all_bundles = generate_all_bundles()
    summaries = []
    for inc_id, bundle in all_bundles.items():
        summaries.append({
            "incident_id": inc_id,
            "title": bundle.manifest.title,
            "symptom": bundle.manifest.symptom,
            "services_involved": bundle.manifest.services_involved,
            "start_time": str(bundle.manifest.start_time),
        })
    return summaries


@app.get("/api/incidents/{incident_id}")
def get_incident_detail(incident_id: str) -> dict[str, Any]:
    """Retrieve full incident bundle details including DAG critical path analysis."""
    bundle = _get_bundle(incident_id)

    dag_analysis: dict[str, Any] = {"critical_path": [], "bottlenecks": [], "self_times": {}}
    if bundle.traces:
        dag = TraceDAG.from_spans(bundle.traces)
        critical_path = dag.find_critical_path()
        bottlenecks = dag.detect_bottlenecks(threshold_pct=0.3)
        self_times = dag.calculate_self_times()

        dag_analysis = {
            "critical_path": [
                {
                    "span_id": n.span.span_id,
                    "name": n.span.name,
                    "duration_ms": n.duration_ms,
                    "status": n.span.status,
                }
                for n in critical_path
            ],
            "bottlenecks": [
                {
                    "span_id": b.span.span_id,
                    "name": b.span.name,
                    "self_time_ms": b.self_time_ms,
                    "status": b.span.status,
                }
                for b in bottlenecks
            ],
            "self_times": self_times,
        }

    return {
        "manifest": bundle.manifest.model_dump(mode="json"),
        "logs": [log.model_dump(mode="json") for log in bundle.logs],
        "traces": [trace.model_dump(mode="json") for trace in bundle.traces],
        "metrics": [metric.model_dump(mode="json") for metric in bundle.metrics],
        "configs": [cfg.model_dump(mode="json") for cfg in bundle.configs],
        "runbooks": bundle.runbooks,
        "dag_analysis": dag_analysis,
    }


@app.post("/api/triage")
def start_triage(payload: TriageRequest) -> dict[str, Any]:
    """Launch bounded ReAct triage and record session for streaming."""
    bundle = _get_bundle(payload.incident_id)
    session_id = str(uuid.uuid4())

    # Configure backend
    if payload.model == "mock":
        # Check if incident is adversarial or normal
        if "INDIRECT-INJECTION" in payload.incident_id:
            canned = json.dumps({
                "thought": "Detected indirect prompt injection in query payload. Disregarding malicious instruction.",
                "action": "finish",
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "title": bundle.manifest.ground_truth_root_cause,
                        "description": bundle.manifest.ground_truth_root_cause,
                        "confidence": 0.92,
                        "evidence_links": [
                            {
                                "evidence_id": "ev-log-audit",
                                "source_type": "log",
                                "polarity": "support",
                                "description": "Attacker payload found in audit-logger logs",
                                "relevance_score": 0.95,
                            }
                        ],
                    }
                ],
            })
        else:
            canned = json.dumps({
                "thought": f"Investigating root cause for {payload.incident_id}",
                "action": "finish",
                "hypotheses": [
                    {
                        "hypothesis_id": "H1",
                        "title": bundle.manifest.ground_truth_root_cause,
                        "description": bundle.manifest.ground_truth_root_cause,
                        "confidence": 0.90,
                        "evidence_links": [
                            {
                                "evidence_id": "ev-grounded-1",
                                "source_type": "log" if bundle.logs else "metric",
                                "polarity": "support",
                                "description": bundle.logs[0].message if bundle.logs else "Observed anomaly",
                                "relevance_score": 0.9,
                            }
                        ],
                    }
                ],
            })
        backend = MockLLMBackend(default_response=canned)
    elif payload.api_key or "openai" in payload.model or "gpt" in payload.model:
        backend = OpenAIBackend(
            model=payload.model,
            api_key=payload.api_key or "",
            base_url=payload.base_url or "https://api.openai.com/v1",
        )
    else:
        backend = OllamaBackend(
            model=payload.model,
            base_url=payload.base_url or "http://localhost:11434",
        )

    max_steps = 1 if payload.workflow == "fixed" else 5
    agent = BoundedReActAgent(bundle, llm=backend, max_steps=max_steps)
    report: TriageReport = agent.run(symptom=payload.symptom)

    SESSIONS[session_id] = {
        "incident_id": payload.incident_id,
        "report": report,
        "scratchpad": agent.scratchpad,
        "state": agent.state.value,
    }

    return {
        "session_id": session_id,
        "report": report.model_dump(mode="json"),
    }


@app.get("/api/triage/stream/{session_id}")
def stream_triage(session_id: str) -> StreamingResponse:
    """Stream live ReAct state transitions and final triage report via SSE."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    def event_generator():
        # 1. State event: INIT -> THINKING
        yield f"data: {json.dumps({'type': 'state', 'state': 'THINKING'})}\n\n"

        # 2. ReAct steps
        for step in session.get("scratchpad", []):
            yield f"data: {json.dumps({'type': 'step', 'data': step})}\n\n"

        # 3. Grounding evaluation
        yield f"data: {json.dumps({'type': 'state', 'state': 'EVALUATING_GROUNDING'})}\n\n"

        # 4. Final state and report
        final_state = session.get("state", "TERMINATED")
        yield f"data: {json.dumps({'type': 'state', 'state': final_state})}\n\n"
        report_data = session["report"].model_dump(mode="json")
        yield f"data: {json.dumps({'type': 'report', 'data': report_data})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Serve static web frontend
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index() -> FileResponse:
    """Serve the single-page application dashboard."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend assets not found.")
    return FileResponse(index_file, media_type="text/html")
