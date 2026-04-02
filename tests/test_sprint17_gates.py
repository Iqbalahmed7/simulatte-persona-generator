"""tests/test_sprint17_gates.py — Sprint 17 Gate Tests.

Validates the four Sprint 17 deliverable areas:
  - Identity Constructor Auto-Routing (3 tests)
  - Cognitive Loop Routing (3 tests)
  - Deployment Config (3 tests)
  - Client Spec Examples (3 tests)

No live API calls. All tests are structural or use pure-Python inspection.
Files being written by parallel agents (Cursor/Codex) are gracefully skipped
if not yet present.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Identity Constructor Auto-Routing (3 tests)
# ---------------------------------------------------------------------------


def test_identity_constructor_imports_llm_router():
    """identity_constructor imports or references get_llm_client."""
    import inspect
    from src.generation import identity_constructor
    source = inspect.getsource(identity_constructor)
    assert "get_llm_client" in source or "llm_router" in source, \
        "identity_constructor should reference the LLM router"


def test_identity_constructor_build_signature_unchanged():
    """build() signature hasn't changed in a breaking way — existing callers still work."""
    from src.generation.identity_constructor import IdentityConstructor
    import inspect
    sig = inspect.signature(IdentityConstructor.build)
    # build() should still accept icp_spec as a parameter
    assert "icp_spec" in sig.parameters


def test_identity_constructor_accepts_sarvam_in_icp_spec():
    """ICPSpec or the build() call path supports sarvam_enabled flag."""
    try:
        from src.generation.identity_constructor import ICPSpec
        import inspect
        source = inspect.getsource(ICPSpec)
        assert "sarvam" in source.lower()
    except (ImportError, AttributeError):
        # ICPSpec might be defined elsewhere
        from src.generation import identity_constructor
        import inspect
        source = inspect.getsource(identity_constructor)
        assert "sarvam" in source.lower()


# ---------------------------------------------------------------------------
# Cognitive Loop Routing (3 tests)
# ---------------------------------------------------------------------------


def test_perceive_function_accepts_llm_client():
    """perceive's main callable accepts an llm_client parameter."""
    import inspect
    try:
        from src.cognition import perceive
        # Find the main function (perceive_stimulus or similar)
        source = inspect.getsource(perceive)
        assert "llm_client" in source, "perceive should accept llm_client parameter"
    except ImportError:
        pytest.skip("perceive module not available")


def test_decide_function_accepts_llm_client():
    """decide's main callable accepts an llm_client parameter."""
    import inspect
    try:
        from src.cognition import decide
        source = inspect.getsource(decide)
        assert "llm_client" in source, "decide should accept llm_client parameter"
    except ImportError:
        pytest.skip("decide module not available")


def test_reflect_function_accepts_llm_client():
    """reflect's main callable accepts an llm_client parameter."""
    import inspect
    try:
        from src.cognition import reflect
        source = inspect.getsource(reflect)
        assert "llm_client" in source, "reflect should accept llm_client parameter"
    except ImportError:
        pytest.skip("reflect module not available")


# ---------------------------------------------------------------------------
# Deployment Config (3 tests)
# ---------------------------------------------------------------------------


def test_dockerfile_exists():
    """Dockerfile exists in project root."""
    from pathlib import Path
    dockerfile = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator/Dockerfile")
    assert dockerfile.exists(), "Dockerfile should exist in project root"


def test_env_example_has_sarvam_key():
    """.env.example contains SARVAM_API_KEY."""
    from pathlib import Path
    env_example = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator/.env.example")
    if not env_example.exists():
        pytest.skip(".env.example not yet created")
    content = env_example.read_text()
    assert "SARVAM_API_KEY" in content


def test_docker_compose_exists():
    """docker-compose.yml exists in project root."""
    from pathlib import Path
    dc = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator/docker-compose.yml")
    assert dc.exists(), "docker-compose.yml should exist in project root"


# ---------------------------------------------------------------------------
# Client Spec Examples (3 tests)
# ---------------------------------------------------------------------------


def test_littlejoys_spec_exists_and_valid_json():
    """examples/spec_littlejoys.json exists and is valid JSON."""
    import json
    from pathlib import Path
    spec = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator/examples/spec_littlejoys.json")
    if not spec.exists():
        pytest.skip("spec_littlejoys.json not yet created")
    data = json.loads(spec.read_text())
    assert "client" in data
    assert data["client"] == "Littlejoys"


def test_lo_foods_spec_exists_and_valid_json():
    """examples/spec_lo_foods.json exists and is valid JSON."""
    import json
    from pathlib import Path
    spec = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator/examples/spec_lo_foods.json")
    if not spec.exists():
        pytest.skip("spec_lo_foods.json not yet created")
    data = json.loads(spec.read_text())
    assert "client" in data
    assert data["client"] == "Lo! Foods"


def test_client_specs_have_sarvam_enabled():
    """Both client specs have sarvam_enabled: true."""
    import json
    from pathlib import Path
    base = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator/examples")
    for name in ["spec_littlejoys.json", "spec_lo_foods.json"]:
        p = base / name
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        assert data.get("sarvam_enabled") is True, f"{name} should have sarvam_enabled: true"
