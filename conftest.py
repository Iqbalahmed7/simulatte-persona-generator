"""conftest.py — Root pytest configuration for the Simulatte Persona Generator.

Defines the 'integration' marker. Integration tests make real LLM calls
and require a valid ANTHROPIC_API_KEY in the environment.

Usage:
  # Run only unit tests (skip integration):
  python -m pytest

  # Run all tests including integration:
  python -m pytest --integration

  # Run only BV integration tests:
  python -m pytest tests/test_bv1_stability.py tests/test_bv2_memory_fidelity.py --integration
"""

import os
import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --integration flag to pytest CLI."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that make live LLM calls (requires ANTHROPIC_API_KEY).",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the integration marker so pytest does not warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test requiring a live Anthropic API key.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip integration tests unless --integration flag is passed.

    Also skips integration tests if ANTHROPIC_API_KEY is not set in the environment,
    even when --integration is passed — avoids confusing AuthenticationError failures.
    """
    run_integration = config.getoption("--integration")
    api_key_present = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

    skip_no_flag = pytest.mark.skip(reason="Integration test: pass --integration to run.")
    skip_no_key = pytest.mark.skip(
        reason="Integration test skipped: ANTHROPIC_API_KEY not set in environment."
    )

    for item in items:
        if item.get_closest_marker("integration"):
            if not run_integration:
                item.add_marker(skip_no_flag)
            elif not api_key_present:
                item.add_marker(skip_no_key)
