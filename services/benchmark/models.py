"""services/benchmark/models.py — Pydantic + dataclass models for the benchmark service."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Tiers ─────────────────────────────────────────────────────────────────────

class BenchmarkTier(str, Enum):
    QUICK = "quick"           # ~$0.05 · 3 tests · ~90s
    STANDARD = "standard"     # ~$0.18 · 6 tests · ~3min
    RESEARCH = "research"     # ~$0.40 · 10 tests · ~7min
    CUSTOM = "custom"         # caller-specified test subset


TIER_TESTS: Dict[BenchmarkTier, List[str]] = {
    BenchmarkTier.QUICK: [
        "identity_consistency",
        "biographical_accuracy",
        "gap_discipline",
    ],
    BenchmarkTier.STANDARD: [
        "identity_consistency",
        "biographical_accuracy",
        "gap_discipline",
        "decision_style_fidelity",
        "contradiction_authenticity",
        "emotional_register",
    ],
    BenchmarkTier.RESEARCH: [
        "identity_consistency",
        "biographical_accuracy",
        "gap_discipline",
        "decision_style_fidelity",
        "contradiction_authenticity",
        "emotional_register",
        "symbolic_meaning_coherence",
        "attachment_expression",
        "drift_resistance",
        "red_team_resilience",
    ],
    BenchmarkTier.CUSTOM: [],  # populated by caller
}

# Weight of each test in the composite credibility score (must sum to 1.0)
TEST_WEIGHTS: Dict[str, float] = {
    "identity_consistency":       0.15,
    "biographical_accuracy":      0.15,
    "gap_discipline":             0.12,
    "decision_style_fidelity":    0.12,
    "contradiction_authenticity": 0.10,
    "emotional_register":         0.10,
    "symbolic_meaning_coherence": 0.08,
    "attachment_expression":      0.08,
    "drift_resistance":           0.05,
    "red_team_resilience":        0.05,
}


# ── Status ─────────────────────────────────────────────────────────────────────

class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


# ── Individual test result ────────────────────────────────────────────────────

class TestResult(BaseModel):
    test_id: str
    label: str
    status: TestStatus
    score: float = Field(ge=0.0, le=10.0)          # raw score 0-10
    weight: float = Field(ge=0.0, le=1.0)
    weighted_contribution: float = Field(ge=0.0)    # score/10 * weight * 100
    rationale: str = ""
    evidence: List[str] = Field(default_factory=list)  # quoted excerpts
    flags: List[str] = Field(default_factory=list)     # named issues found
    duration_s: float = 0.0
    cost_usd: float = 0.0


# ── Run-level report ──────────────────────────────────────────────────────────

class BenchmarkReport(BaseModel):
    run_id: str
    persona_id: str
    persona_name: str
    tier: BenchmarkTier
    status: RunStatus
    credibility_score: float = Field(ge=0.0, le=100.0)
    grade: str = ""                              # A / B / C / D / F
    grade_label: str = ""                        # "Research Grade — A"
    tests: List[TestResult] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    total_duration_s: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # ── Derived helpers ────────────────────────────────────────────────────────

    @staticmethod
    def grade_from_score(score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 45:
            return "D"
        return "F"

    @staticmethod
    def grade_label_from(tier: BenchmarkTier, grade: str) -> str:
        tier_names = {
            BenchmarkTier.QUICK: "Quick Scan",
            BenchmarkTier.STANDARD: "Standard",
            BenchmarkTier.RESEARCH: "Research Grade",
            BenchmarkTier.CUSTOM: "Custom",
        }
        return f"{tier_names[tier]} — {grade}"


# ── API request / response ────────────────────────────────────────────────────

class RunRequest(BaseModel):
    persona_id: str
    tier: BenchmarkTier = BenchmarkTier.STANDARD
    custom_tests: List[str] = Field(default_factory=list)
    # The persona JSON is fetched from The Mind API by the benchmark service.
    # Optionally callers can embed it directly (e.g. for testing).
    persona_payload: Optional[Dict[str, Any]] = None


class RunResponse(BaseModel):
    run_id: str
    status: RunStatus
    stream_url: str       # GET /runs/{run_id}/stream
    poll_url: str         # GET /runs/{run_id}


# ── SSE event ────────────────────────────────────────────────────────────────

class BenchmarkEvent(BaseModel):
    type: str             # "started" | "test_complete" | "complete" | "error"
    run_id: str
    test_id: Optional[str] = None
    test_label: Optional[str] = None
    score: Optional[float] = None
    credibility_score: Optional[float] = None
    grade: Optional[str] = None
    message: Optional[str] = None
    report: Optional[BenchmarkReport] = None
