"""Synthetic Fault Lab, canonical incident generators, and golden datasets."""

from tracelens.fault_lab.generator import (
    ARCHETYPE_IDS,
    generate_all_bundles,
    generate_incident_bundle,
    materialize_fixtures,
)

__all__ = [
    "ARCHETYPE_IDS",
    "generate_all_bundles",
    "generate_incident_bundle",
    "materialize_fixtures",
]
