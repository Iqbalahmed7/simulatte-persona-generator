"""Tests for prompt cache discipline (BRIEF-012).

Verifies that new optional parameters exist on cache-aware functions:
1. decide() accepts manifesto_context and domain_framing parameters
2. run_loop() accepts manifesto_context and domain_framing parameters

Cache_control: ephemeral is applied directly in _build_decide_messages,
_build_perceive_messages, and _build_reflect_messages via the existing pattern.
"""

import inspect
import pytest


class TestCacheControlParametersExist:
    """Verify new parameters exist on cache-aware functions."""

    def test_decide_accepts_manifesto_context(self):
        """decide() must accept optional manifesto_context parameter."""
        from src.cognition.decide import decide
        sig = inspect.signature(decide)
        assert 'manifesto_context' in sig.parameters, (
            "decide() is missing the manifesto_context parameter"
        )
        param = sig.parameters['manifesto_context']
        assert param.default is None, (
            "decide() manifesto_context parameter should default to None"
        )

    def test_decide_accepts_domain_framing(self):
        """decide() must accept optional domain_framing parameter."""
        from src.cognition.decide import decide
        sig = inspect.signature(decide)
        assert 'domain_framing' in sig.parameters, (
            "decide() is missing the domain_framing parameter"
        )
        param = sig.parameters['domain_framing']
        assert param.default is None, (
            "decide() domain_framing parameter should default to None"
        )

    def test_run_loop_accepts_manifesto_context(self):
        """run_loop() must accept optional manifesto_context parameter."""
        from src.cognition.loop import run_loop
        sig = inspect.signature(run_loop)
        assert 'manifesto_context' in sig.parameters, (
            "run_loop() is missing the manifesto_context parameter"
        )
        param = sig.parameters['manifesto_context']
        assert param.default is None, (
            "run_loop() manifesto_context parameter should default to None"
        )

    def test_run_loop_accepts_domain_framing(self):
        """run_loop() must accept optional domain_framing parameter."""
        from src.cognition.loop import run_loop
        sig = inspect.signature(run_loop)
        assert 'domain_framing' in sig.parameters, (
            "run_loop() is missing the domain_framing parameter"
        )
        param = sig.parameters['domain_framing']
        assert param.default is None, (
            "run_loop() domain_framing parameter should default to None"
        )


class TestBuildDecideMessagesFunctionSignature:
    """Verify _build_decide_messages has the new parameters."""

    def test_build_decide_messages_has_manifesto_context_param(self):
        """_build_decide_messages must have manifesto_context parameter."""
        from src.cognition.decide import _build_decide_messages
        sig = inspect.signature(_build_decide_messages)
        assert 'manifesto_context' in sig.parameters

    def test_build_decide_messages_has_domain_framing_param(self):
        """_build_decide_messages must have domain_framing parameter."""
        from src.cognition.decide import _build_decide_messages
        sig = inspect.signature(_build_decide_messages)
        assert 'domain_framing' in sig.parameters
