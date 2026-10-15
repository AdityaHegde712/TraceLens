"""Specification tests for the TraceLens Web Server and REST/SSE API.

Strict TDD suite locking behavior for:
1. Incident listing endpoint (/api/incidents).
2. Incident detail with DAG critical-path analysis (/api/incidents/{incident_id}).
3. Triage invocation endpoint (/api/triage).
4. SSE live stream endpoint (/api/triage/stream/{session_id}).
5. Frontend static file delivery (/).
"""

import pytest
from fastapi.testclient import TestClient

from tracelens.web.server import app


@pytest.fixture
def client():
    return TestClient(app)


class TestWebServerAPI:
    """Locked assertions for FastAPI backend endpoints."""

    def test_list_incidents(self, client):
        response = client.get("/api/incidents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 12
        first = data[0]
        assert "incident_id" in first
        assert "title" in first
        assert "symptom" in first
        assert "services_involved" in first

    def test_get_incident_detail(self, client):
        response = client.get("/api/incidents/INC-001-STALE-INDEX")
        assert response.status_code == 200
        detail = response.json()
        assert detail["manifest"]["incident_id"] == "INC-001-STALE-INDEX"
        assert "logs" in detail
        assert "traces" in detail
        assert "metrics" in detail
        assert "configs" in detail
        assert "runbooks" in detail
        assert "dag_analysis" in detail
        assert "critical_path" in detail["dag_analysis"]
        assert "bottlenecks" in detail["dag_analysis"]

    def test_get_incident_not_found(self, client):
        response = client.get("/api/incidents/INC-DOES-NOT-EXIST")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_post_triage_execution(self, client):
        payload = {
            "incident_id": "INC-001-STALE-INDEX",
            "model": "mock",
            "workflow": "react",
        }
        response = client.post("/api/triage", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "report" in data
        assert data["report"]["incident_id"] == "INC-001-STALE-INDEX"

    def test_stream_triage_sse(self, client):
        # 1. Start a triage session
        triage_resp = client.post(
            "/api/triage",
            json={"incident_id": "INC-001-STALE-INDEX", "model": "mock"},
        )
        session_id = triage_resp.json()["session_id"]

        # 2. Consume SSE stream
        with client.stream("GET", f"/api/triage/stream/{session_id}") as stream:
            assert stream.status_code == 200
            content_type = stream.headers.get("content-type", "")
            assert "text/event-stream" in content_type

            events = []
            for line in stream.iter_lines():
                if line.startswith("data:"):
                    events.append(line)
            assert len(events) >= 1

    def test_static_index_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "TraceLens" in response.text
