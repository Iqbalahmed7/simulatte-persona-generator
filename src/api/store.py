"""Simple file-based cohort store for the Simulatte Persona Generator API."""
from __future__ import annotations

import os
import json
import uuid
from pathlib import Path
from typing import Optional

# Temp store for dynamically generated cohorts (ephemeral on cloud)
STORE_DIR = Path(os.environ.get("COHORT_STORE_DIR", "/tmp/simulatte_cohorts"))

# Seed cohorts committed to the repo — always available on any deployment
# store.py lives at src/api/store.py → parents[2] is the repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = _REPO_ROOT / "data" / "seed_cohorts"


def _seed_path(cohort_id: str) -> Path:
    return SEED_DIR / f"{cohort_id}.json"


def save_cohort(envelope_dict: dict) -> str:
    """Save cohort dict to temp store, return cohort_id."""
    cohort_id = str(uuid.uuid4())[:8]
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    path = STORE_DIR / f"{cohort_id}.json"
    with open(path, "w") as f:
        json.dump(envelope_dict, f, indent=2, default=str)
    return cohort_id


def load_cohort(cohort_id: str) -> Optional[dict]:
    """Load cohort dict — checks seed dir first, then temp store."""
    seed = _seed_path(cohort_id)
    if seed.exists():
        with open(seed) as f:
            return json.load(f)
    path = STORE_DIR / f"{cohort_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def cohort_path(cohort_id: str) -> str:
    """Return the full path string for a cohort_id (seed dir preferred)."""
    seed = _seed_path(cohort_id)
    if seed.exists():
        return str(seed)
    return str(STORE_DIR / f"{cohort_id}.json")


def list_cohorts() -> list[str]:
    """Return all available cohort IDs (seed + generated)."""
    ids: list[str] = []
    if SEED_DIR.exists():
        ids.extend(p.stem for p in sorted(SEED_DIR.glob("*.json")))
    if STORE_DIR.exists():
        ids.extend(p.stem for p in sorted(STORE_DIR.glob("*.json")))
    return ids
