"""Simple file-based cohort store for the Simulatte Persona Generator API."""
from __future__ import annotations

import os
import json
import uuid
from pathlib import Path
from typing import Optional

STORE_DIR = Path(os.environ.get("COHORT_STORE_DIR", "/tmp/simulatte_cohorts"))


def save_cohort(envelope_dict: dict) -> str:
    """Save cohort dict to disk, return cohort_id."""
    cohort_id = str(uuid.uuid4())[:8]
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    path = STORE_DIR / f"{cohort_id}.json"
    with open(path, "w") as f:
        json.dump(envelope_dict, f, indent=2, default=str)
    return cohort_id


def load_cohort(cohort_id: str) -> Optional[dict]:
    """Load cohort dict from disk. Returns None if not found."""
    path = STORE_DIR / f"{cohort_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def cohort_path(cohort_id: str) -> str:
    """Return the full path string for a cohort_id."""
    return str(STORE_DIR / f"{cohort_id}.json")
