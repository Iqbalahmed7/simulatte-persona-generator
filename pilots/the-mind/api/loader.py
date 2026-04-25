"""pilots/the-mind/api/loader.py — Load exemplar personas from frozen JSONs.

Reads exemplar_set_v1/ and deserialises each PersonaRecord.
Module-level cache: personas loaded once per process, ~22k lines total.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict

# ── repo root on sys.path ──────────────────────────────────────────────────
_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent.parent  # api/ → the-mind/ → pilots/ → repo
sys.path.insert(0, str(_REPO_ROOT))

from src.schema.persona import PersonaRecord  # noqa: E402

_EXEMPLAR_DIR = _HERE.parent / "exemplar_set_v1"

# slug → PersonaRecord, populated on first call
_CACHE: Dict[str, PersonaRecord] = {}


def load_all() -> Dict[str, PersonaRecord]:
    """Return all 5 exemplar personas. Loaded once, cached in process memory."""
    if _CACHE:
        return _CACHE

    if not _EXEMPLAR_DIR.exists():
        raise RuntimeError(
            f"Exemplar directory not found: {_EXEMPLAR_DIR}. "
            "Run pilots/the-mind/generate_exemplars.py first."
        )

    for json_path in sorted(_EXEMPLAR_DIR.glob("persona_*.json")):
        slug = json_path.stem.replace("persona_", "")
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        _CACHE[slug] = PersonaRecord.model_validate(data)

    return _CACHE


def load_one(slug: str) -> PersonaRecord:
    """Return a single persona by slug. Raises KeyError if not found."""
    personas = load_all()
    if slug not in personas:
        available = list(personas.keys())
        raise KeyError(
            f"Persona '{slug}' not found. Available slugs: {available}"
        )
    return personas[slug]
