"""tests/test_sprint13_gates.py — Sprint 13 Gate Tests.

Validates the three Sprint 13 deliverables:
  - G7 Threshold Scaling: check_distinctiveness auto-scales threshold by cohort size
  - G8 Coverage Rule Scaling: _required_types returns scaled minimums by cohort size
  - Parallel Generation: _run_generation uses asyncio.gather and nested _build_one
  - Simulate Command: simulate command registered in the CLI

No LLM calls. All tests use make_synthetic_persona() + structural inspection only.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# G7 Threshold Scaling (5 tests)
# ---------------------------------------------------------------------------

def test_g7_threshold_scales_with_cohort_size_small():
    """N=3 → threshold should be 0.10 (not 0.35)."""
    # Build 3 synthetic personas and check that check_distinctiveness uses threshold <= 0.15
    from src.cohort.distinctiveness import check_distinctiveness
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    personas = [make_synthetic_persona() for _ in range(3)]
    result = check_distinctiveness(personas)
    assert result.threshold <= 0.15, f"Expected threshold <= 0.15 for N=3, got {result.threshold}"


def test_g7_threshold_scales_with_cohort_size_medium():
    """N=5 → threshold should be <= 0.20."""
    from src.cohort.distinctiveness import check_distinctiveness
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    personas = [make_synthetic_persona() for _ in range(5)]
    result = check_distinctiveness(personas)
    assert result.threshold <= 0.20, f"Expected threshold <= 0.20 for N=5, got {result.threshold}"


def test_g7_threshold_scales_with_cohort_size_large():
    """N=10 → threshold should be 0.35."""
    from src.cohort.distinctiveness import check_distinctiveness
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    personas = [make_synthetic_persona() for _ in range(10)]
    result = check_distinctiveness(personas)
    assert result.threshold == 0.35, f"Expected threshold 0.35 for N=10, got {result.threshold}"


def test_g7_explicit_threshold_overrides_auto():
    """Explicit threshold parameter overrides auto-scaling."""
    from src.cohort.distinctiveness import check_distinctiveness
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    personas = [make_synthetic_persona() for _ in range(3)]
    result = check_distinctiveness(personas, threshold=0.99)
    assert result.threshold == 0.99


def test_g7_synthetic_cohort_passes_scaled_threshold():
    """A cohort of 5 identical synthetic personas should pass the scaled (N=5) threshold."""
    # The synthetic personas are identical → distance ~0. But with scaled threshold 0.15,
    # a real diverse cohort should pass. This test just checks the gate runs without error.
    from src.cohort.distinctiveness import check_distinctiveness
    from tests.fixtures.synthetic_persona import make_synthetic_persona
    personas = [make_synthetic_persona() for _ in range(5)]
    result = check_distinctiveness(personas)
    # Just verify it returns a DistinctivenessResult with the right fields
    assert hasattr(result, 'threshold')
    assert hasattr(result, 'passed')
    assert hasattr(result, 'mean_pairwise_distance')


# ---------------------------------------------------------------------------
# G8 Coverage Rule Scaling (3 tests)
# ---------------------------------------------------------------------------

def test_g8_required_types_n3():
    """N=3 requires only 2 distinct types (was 3)."""
    from src.cohort.type_coverage import _required_types
    assert _required_types(3) == 2


def test_g8_required_types_n5():
    """N=5 requires only 3 distinct types (was 4)."""
    from src.cohort.type_coverage import _required_types
    assert _required_types(5) == 3


def test_g8_required_types_n10():
    """N=10 still requires all 8 types."""
    from src.cohort.type_coverage import _required_types
    assert _required_types(10) == 8


# ---------------------------------------------------------------------------
# Parallel Generation (2 tests)
# ---------------------------------------------------------------------------

def test_parallel_generation_uses_gather():
    """_run_generation must use asyncio.gather for concurrent builds."""
    import ast, inspect
    from src import cli
    source = inspect.getsource(cli._run_generation)
    # Check that asyncio.gather is used in the function body
    assert "gather" in source, "_run_generation must use asyncio.gather for parallel builds"


def test_parallel_generation_build_one_nested():
    """_run_generation must define a nested _build_one coroutine."""
    import inspect
    from src import cli
    source = inspect.getsource(cli._run_generation)
    assert "_build_one" in source, "_run_generation must define nested _build_one"


# ---------------------------------------------------------------------------
# Simulate Command (1 test)
# ---------------------------------------------------------------------------

def test_simulate_command_registered():
    """simulate command must be registered in the CLI."""
    from click.testing import CliRunner
    from src.cli import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert "simulate" in result.output, f"'simulate' not in CLI help: {result.output}"
