"""tests/test_cognitive_loop_routing.py — Signature tests for cognitive loop LLM routing.

Verifies that perceive, reflect, and decide accept an optional llm_client parameter,
enabling the LLM router to inject Sarvam or Anthropic clients at simulation time.
"""
import inspect
import pytest


def test_perceive_accepts_llm_client_param():
    """perceive() must have an optional llm_client parameter."""
    from src.cognition.perceive import perceive
    sig = inspect.signature(perceive)
    assert 'llm_client' in sig.parameters, (
        "perceive() is missing the llm_client parameter"
    )
    param = sig.parameters['llm_client']
    assert param.default is None, (
        "perceive() llm_client parameter should default to None"
    )


def test_decide_accepts_llm_client_param():
    """decide() must have an optional llm_client parameter."""
    from src.cognition.decide import decide
    sig = inspect.signature(decide)
    assert 'llm_client' in sig.parameters, (
        "decide() is missing the llm_client parameter"
    )
    param = sig.parameters['llm_client']
    assert param.default is None, (
        "decide() llm_client parameter should default to None"
    )


def test_reflect_accepts_llm_client_param():
    """reflect() must have an optional llm_client parameter."""
    from src.cognition.reflect import reflect
    sig = inspect.signature(reflect)
    assert 'llm_client' in sig.parameters, (
        "reflect() is missing the llm_client parameter"
    )
    param = sig.parameters['llm_client']
    assert param.default is None, (
        "reflect() llm_client parameter should default to None"
    )
