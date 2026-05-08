"""services/benchmark/tests/registry.py — All test classes, keyed by test_id."""
from __future__ import annotations

from typing import Dict, Type

from tests.base import BaseTest
from tests.t01_identity_consistency import IdentityConsistencyTest
from tests.t02_biographical_accuracy import BiographicalAccuracyTest
from tests.t03_gap_discipline import GapDisciplineTest
from tests.t04_decision_style_fidelity import DecisionStyleFidelityTest
from tests.t05_contradiction_authenticity import ContradictionAuthenticityTest
from tests.t06_emotional_register import EmotionalRegisterTest
from tests.t07_symbolic_meaning_coherence import SymbolicMeaningCoherenceTest
from tests.t08_attachment_expression import AttachmentExpressionTest
from tests.t09_drift_resistance import DriftResistanceTest
from tests.t10_red_team_resilience import RedTeamResilienceTest

ALL_TESTS: Dict[str, Type[BaseTest]] = {
    "identity_consistency":       IdentityConsistencyTest,
    "biographical_accuracy":      BiographicalAccuracyTest,
    "gap_discipline":             GapDisciplineTest,
    "decision_style_fidelity":    DecisionStyleFidelityTest,
    "contradiction_authenticity": ContradictionAuthenticityTest,
    "emotional_register":         EmotionalRegisterTest,
    "symbolic_meaning_coherence": SymbolicMeaningCoherenceTest,
    "attachment_expression":      AttachmentExpressionTest,
    "drift_resistance":           DriftResistanceTest,
    "red_team_resilience":        RedTeamResilienceTest,
}


def get_test_instance(test_id: str) -> BaseTest:
    cls = ALL_TESTS.get(test_id)
    if cls is None:
        raise ValueError(f"Unknown test_id: {test_id!r}. Valid: {list(ALL_TESTS)}")
    return cls()
