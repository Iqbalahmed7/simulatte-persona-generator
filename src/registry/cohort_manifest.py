"""src/registry/cohort_manifest.py — Cohort manifest format.

A cohort manifest is a lightweight JSON file stored in a client project.
It contains only persona_id references (not full PersonaRecord data).

No LLM calls.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class CohortManifest:
    cohort_id: str              # e.g. "lj-cohort-v3"
    domain: str                 # e.g. "child-nutrition"
    icp_spec_hash: str          # hash of the ICP spec used to generate this cohort
    persona_ids: list[str]      # e.g. ["pg-lj-001", "pg-lj-002", ...]
    snapshot_date: str          # ISO date string, e.g. "2026-04-03"
    registry_version: str       # e.g. "simulatte-v1.2"
    notes: str = ""


def save_manifest(manifest: CohortManifest, path: str | Path) -> None:
    """Write the manifest as JSON to the given path. Creates parent dirs if needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(asdict(manifest), indent=2))


def load_manifest(path: str | Path) -> CohortManifest:
    """Load a CohortManifest from a JSON file at the given path."""
    data = json.loads(Path(path).read_text())
    return CohortManifest(**data)


def make_manifest(
    cohort_id: str,
    domain: str,
    persona_ids: list[str],
    icp_spec_hash: str = "",
    registry_version: str = "simulatte-v1.0",
    notes: str = "",
) -> CohortManifest:
    """Convenience constructor. Sets snapshot_date to today (UTC)."""
    snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return CohortManifest(
        cohort_id=cohort_id,
        domain=domain,
        icp_spec_hash=icp_spec_hash,
        persona_ids=persona_ids,
        snapshot_date=snapshot_date,
        registry_version=registry_version,
        notes=notes,
    )
