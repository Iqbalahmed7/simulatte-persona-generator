"""pilots/the_mind_api.py — Railway entry point for The Mind API.

Bridges the hyphen-in-directory naming issue: `the-mind` is not a valid
Python package name, so this module lives at pilots/the_mind_api.py (no hyphen)
and dynamically loads pilots/the-mind/api/main.py.

Railway start command:
    uvicorn pilots.the_mind_api:app --host 0.0.0.0 --port $PORT

Version: exemplar_set_v1_2026_04
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# Load pilots/the-mind/api/main.py via importlib (bypasses hyphen)
_main_path = Path(__file__).parent / "the-mind" / "api" / "main.py"
_spec = importlib.util.spec_from_file_location("the_mind_main", _main_path)
_mod = importlib.util.module_from_spec(_spec)          # type: ignore[arg-type]
_spec.loader.exec_module(_mod)                          # type: ignore[union-attr]

# Re-export the FastAPI app — this is what uvicorn imports
app = _mod.app
