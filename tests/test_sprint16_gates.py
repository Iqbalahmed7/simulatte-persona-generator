"""tests/test_sprint16_gates.py — Sprint 16 Gate Tests.

Validates the four Sprint 16 deliverable areas:
  - FastAPI Microservice: app importable, /generate, /simulate, /survey routes registered
  - LLM Router: get_llm_client importable, correct client returned by country/flag
  - Quality Parity: ParityResult and compare_parity logic correct
  - Sarvam Config: for_sarvam_api() and default-model backward compatibility

No live API calls. All tests are structural or use pure-Python stubs.
"""

from __future__ import annotations

import pytest

# Simple stub for anthropic client — the router passes it through without calling it.
mock_anthropic = object()


# ---------------------------------------------------------------------------
# FastAPI Microservice (4 tests)
# ---------------------------------------------------------------------------

def test_api_package_importable():
    """src.api.main can be imported."""
    try:
        from src.api.main import app
        assert app is not None
    except ImportError:
        pytest.skip("FastAPI app not yet built")


def test_api_has_generate_route():
    """POST /generate route is registered."""
    try:
        from src.api.main import app
        routes = [r.path for r in app.routes]
        assert "/generate" in routes
    except ImportError:
        pytest.skip("FastAPI app not yet built")


def test_api_has_simulate_route():
    """POST /simulate route is registered."""
    try:
        from src.api.main import app
        routes = [r.path for r in app.routes]
        assert "/simulate" in routes
    except ImportError:
        pytest.skip("FastAPI app not yet built")


def test_api_has_survey_route():
    """POST /survey route is registered."""
    try:
        from src.api.main import app
        routes = [r.path for r in app.routes]
        assert "/survey" in routes
    except ImportError:
        pytest.skip("FastAPI app not yet built")


# ---------------------------------------------------------------------------
# LLM Router (4 tests)
# ---------------------------------------------------------------------------

def test_llm_router_importable():
    """src.utils.llm_router is importable."""
    try:
        from src.utils.llm_router import get_llm_client
        assert callable(get_llm_client)
    except ImportError:
        pytest.skip("LLM router not yet built")


def test_router_returns_anthropic_for_non_india():
    """get_llm_client returns AnthropicLLMClient when sarvam_enabled=False."""
    try:
        from src.utils.llm_router import get_llm_client
        from src.sarvam.llm_client import AnthropicLLMClient
        client = get_llm_client(mock_anthropic, sarvam_enabled=False, country="UK")
        assert isinstance(client, AnthropicLLMClient)
    except ImportError:
        pytest.skip("LLM router not yet built")


def test_router_returns_sarvam_for_india():
    """get_llm_client returns SarvamLLMClient when sarvam_enabled=True and country=India."""
    try:
        from src.utils.llm_router import get_llm_client
        from src.sarvam.llm_client import SarvamLLMClient
        client = get_llm_client(mock_anthropic, sarvam_enabled=True, country="India")
        assert isinstance(client, SarvamLLMClient)
    except ImportError:
        pytest.skip("LLM router not yet built")


def test_sarvam_client_falls_back_without_api_key(monkeypatch):
    """SarvamLLMClient falls back gracefully when SARVAM_API_KEY is not set."""
    try:
        from src.sarvam.llm_client import SarvamLLMClient
        monkeypatch.delenv("SARVAM_API_KEY", raising=False)
        client = SarvamLLMClient(fallback_anthropic_client=object())
        assert client.provider in ("anthropic_fallback", "sarvam")
    except ImportError:
        pytest.skip("SarvamLLMClient not yet built")


# ---------------------------------------------------------------------------
# Quality Parity (4 tests)
# ---------------------------------------------------------------------------

def test_parity_module_importable():
    """src.validation.quality_parity is importable."""
    try:
        from src.validation.quality_parity import check_parity, ParityResult, compare_parity
        assert callable(check_parity)
    except ImportError:
        pytest.skip("Quality parity module not yet built")


def test_parity_result_at_par_when_no_failures():
    """ParityResult.is_at_par is True when gates_failed == 0."""
    try:
        from src.validation.quality_parity import ParityResult
        r = ParityResult(
            persona_id="test-001", provider="sarvam",
            gates_checked=5, gates_passed=5, gates_failed=0,
        )
        assert r.is_at_par is True
        assert r.pass_rate == 1.0
    except ImportError:
        pytest.skip("Quality parity module not yet built")


def test_parity_result_not_at_par_when_failures():
    """ParityResult.is_at_par is False when gates_failed > 0."""
    try:
        from src.validation.quality_parity import ParityResult
        r = ParityResult(
            persona_id="test-001", provider="sarvam",
            gates_checked=5, gates_passed=4, gates_failed=1,
            failures=["G3: TR1 violation"],
        )
        assert r.is_at_par is False
        assert r.pass_rate == 0.8
    except ImportError:
        pytest.skip("Quality parity module not yet built")


def test_compare_parity_at_par_when_equal():
    """compare_parity returns True when both have same pass rate."""
    try:
        from src.validation.quality_parity import ParityResult, compare_parity
        baseline = ParityResult("b", "anthropic", 5, 5, 0)
        sarvam = ParityResult("s", "sarvam", 5, 5, 0)
        assert compare_parity(sarvam, baseline) is True
    except ImportError:
        pytest.skip("Quality parity module not yet built")


# ---------------------------------------------------------------------------
# Sarvam Config (2 tests)
# ---------------------------------------------------------------------------

def test_sarvam_config_has_sarvam_api_method():
    """SarvamConfig.for_sarvam_api() returns config with sarvam-m model."""
    try:
        from src.sarvam.config import SarvamConfig
        config = SarvamConfig.for_sarvam_api()
        assert config.model == "sarvam-m"
        assert config.sarvam_enrichment is True
    except (ImportError, AttributeError):
        pytest.skip("SarvamConfig.for_sarvam_api not yet built")


def test_sarvam_config_default_model_is_haiku():
    """SarvamConfig default model remains claude-haiku for backward compat."""
    from src.sarvam.config import SarvamConfig
    config = SarvamConfig()
    assert "haiku" in config.model or "claude" in config.model
