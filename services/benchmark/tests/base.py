"""services/benchmark/tests/base.py — Abstract base class for all benchmark tests."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from chat import haiku_cost, run_conversation
from judge import judge
from models import TestResult, TestStatus
from system_prompt import build_system_prompt


class BaseTest(ABC):
    """
    Subclass this for each benchmark test.

    Subclasses must define:
        test_id   : str — machine key matching TEST_WEIGHTS
        label     : str — human-readable name shown in reports
        weight    : float — from TEST_WEIGHTS (for reference)

    And implement:
        conversation_turns(persona) -> List[str]
        evaluation_criteria(persona) -> str
    """

    test_id: str
    label: str
    weight: float

    @abstractmethod
    def conversation_turns(self, persona: Dict[str, Any]) -> List[str]:
        """Return the list of user messages to send to the persona."""
        ...

    @abstractmethod
    def evaluation_criteria(self, persona: Dict[str, Any]) -> str:
        """Return the evaluation criteria string for the LLM judge."""
        ...

    # ── max tokens per conversation reply ────────────────────────────────────
    max_tokens_per_turn: int = 400

    async def run(self, persona: Dict[str, Any]) -> TestResult:
        """Execute the test and return a TestResult."""
        t0 = time.monotonic()
        total_cost = 0.0
        status = TestStatus.RUNNING

        try:
            # 1. Build system prompt
            sys_prompt = build_system_prompt(persona)

            # 2. Run conversation with Haiku
            turns = self.conversation_turns(persona)
            history, tok_in, tok_out = await run_conversation(
                sys_prompt, turns, self.max_tokens_per_turn
            )
            chat_cost = haiku_cost(tok_in, tok_out)
            total_cost += chat_cost

            # 3. Judge with Sonnet
            criteria = self.evaluation_criteria(persona)
            verdict, judge_cost = await judge(
                test_label=self.label,
                persona_spec=persona,
                conversation_history=history,
                evaluation_criteria=criteria,
            )
            total_cost += judge_cost

            # 4. Determine pass/fail (threshold: score >= 5.0)
            status = TestStatus.PASSED if verdict.score >= 5.0 else TestStatus.FAILED

            return TestResult(
                test_id=self.test_id,
                label=self.label,
                status=status,
                score=verdict.score,
                weight=self.weight,
                weighted_contribution=0.0,  # filled by scoring.py
                rationale=verdict.rationale,
                evidence=verdict.evidence,
                flags=verdict.flags,
                duration_s=round(time.monotonic() - t0, 2),
                cost_usd=round(total_cost, 6),
            )

        except Exception as exc:
            return TestResult(
                test_id=self.test_id,
                label=self.label,
                status=TestStatus.ERROR,
                score=0.0,
                weight=self.weight,
                weighted_contribution=0.0,
                rationale=f"Test error: {exc}",
                flags=["test_exception"],
                duration_s=round(time.monotonic() - t0, 2),
                cost_usd=round(total_cost, 6),
            )
