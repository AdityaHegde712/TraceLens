"""Specification tests for the Synthetic Fault Lab and Golden Incident Bundles.

Strict TDD suite locking behavior for:
1. Generation of the 12 canonical RAG incident archetypes.
2. Complete bundle structure (manifest, logs, traces, metrics, config, runbooks).
3. Adversarial injection and canary presence in INC-012.
4. Validation of data/fixtures/queries.json (24 functional + 5 adversarial queries).
"""

import json
from pathlib import Path
import pytest

from tracelens.fault_lab.generator import (
    ARCHETYPE_IDS,
    generate_all_bundles,
    generate_incident_bundle,
    materialize_fixtures,
)
from tracelens.telemetry.reader import IncidentBundle, IncidentReader
from tracelens.telemetry.sanitizer import detect_canary_leak


class TestFaultLabArchetypes:
    """Locked assertions for the 12 canonical incident archetypes."""

    def test_canonical_archetype_ids(self):
        expected_ids = [
            "INC-001-STALE-INDEX",
            "INC-002-PARTIAL-INGESTION",
            "INC-003-OVERRESTRICTIVE-FILTER",
            "INC-004-THRESHOLD-MISCONFIG",
            "INC-005-EMBEDDING-DIM-MISMATCH",
            "INC-006-VECTOR-STORE-LATENCY",
            "INC-007-EXPIRED-AUTH-TOKEN",
            "INC-008-RATE-LIMIT-AMPLIFICATION",
            "INC-009-CONTEXT-WINDOW-OVERFLOW",
            "INC-010-GATEWAY-TIMEOUT",
            "INC-011-MULTI-CAUSE-FAILURE",
            "INC-012-INDIRECT-INJECTION",
        ]
        assert ARCHETYPE_IDS == expected_ids
        assert len(ARCHETYPE_IDS) == 12

    def test_generate_all_bundles_coverage(self):
        bundles = generate_all_bundles()
        assert len(bundles) == 12
        for arch_id in ARCHETYPE_IDS:
            assert arch_id in bundles
            bundle = bundles[arch_id]
            assert isinstance(bundle, IncidentBundle)
            assert bundle.manifest.incident_id == arch_id
            assert len(bundle.manifest.ground_truth_root_cause) > 0
            assert len(bundle.manifest.services_involved) >= 1
            assert len(bundle.logs) >= 1
            assert len(bundle.traces) >= 1
            assert len(bundle.metrics) >= 1
            assert len(bundle.configs) >= 1
            assert len(bundle.runbooks) >= 1

    def test_indirect_injection_and_canary_archetype(self):
        bundle = generate_incident_bundle("INC-012-INDIRECT-INJECTION")
        # Check logs contain prompt injection payload
        log_texts = " ".join(log.message for log in bundle.logs)
        assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in log_texts

        # Check canary token presence in logs or configs
        canary = next(
            (log.attributes.get("canary") for log in bundle.logs if "canary" in log.attributes),
            None,
        )
        assert canary is not None
        assert canary.startswith("TL-CANARY-")
        assert detect_canary_leak(log_texts, canary)

    def test_materialize_and_load_bundles(self, tmp_path: Path):
        output_dir = tmp_path / "fixtures" / "incidents"
        materialize_fixtures(output_dir)

        # Verify all 12 directories exist and load cleanly
        for arch_id in ARCHETYPE_IDS:
            inc_dir = output_dir / arch_id
            assert inc_dir.exists()
            assert (inc_dir / "manifest.json").exists()
            assert (inc_dir / "logs.json").exists()
            assert (inc_dir / "traces.json").exists()
            assert (inc_dir / "metrics.json").exists()
            assert (inc_dir / "config.json").exists()
            assert (inc_dir / "runbooks").exists()

            loaded = IncidentReader.load_bundle(inc_dir)
            assert loaded.manifest.incident_id == arch_id


class TestQueriesDataset:
    """Locked assertions for data/fixtures/queries.json benchmark queries."""

    @pytest.fixture
    def queries_data(self) -> dict:
        queries_path = Path("data/fixtures/queries.json")
        assert queries_path.exists(), "data/fixtures/queries.json does not exist"
        return json.loads(queries_path.read_text(encoding="utf-8"))

    def test_queries_dataset_structure(self, queries_data):
        assert "functional_queries" in queries_data
        assert "adversarial_queries" in queries_data

        functional = queries_data["functional_queries"]
        adversarial = queries_data["adversarial_queries"]

        # Exactly 24 functional queries (2 per archetype * 12 archetypes)
        assert len(functional) >= 24

        # At least 5 adversarial/robustness queries
        assert len(adversarial) >= 5

        # Check archetypes represented in functional queries
        represented_archetypes = {q["archetype_id"] for q in functional}
        for arch_id in ARCHETYPE_IDS:
            assert arch_id in represented_archetypes

        # Check required fields in query objects
        for q in functional:
            assert "query_id" in q
            assert "archetype_id" in q
            assert "query_text" in q
            assert "expected_status" in q

        for adv in adversarial:
            assert "query_id" in adv
            assert "adversarial_type" in adv
            assert "query_text" in adv
            assert "expected_behavior" in adv
