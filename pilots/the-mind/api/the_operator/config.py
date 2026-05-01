"""the_operator/config.py — env reads, constants, model names."""
from __future__ import annotations

import os

# ── Activation ────────────────────────────────────────────────────────────
OPERATOR_ENABLED = os.environ.get("OPERATOR_ENABLED", "false").lower() in ("true", "1", "yes")

# ── Models ────────────────────────────────────────────────────────────────
RECON_MODEL    = os.environ.get("OPERATOR_RECON_MODEL",    "claude-sonnet-4-5")
SYNTHESIS_MODEL = os.environ.get("OPERATOR_SYNTHESIS_MODEL", "claude-sonnet-4-5")
PROBE_MODEL    = os.environ.get("OPERATOR_PROBE_MODEL",    "claude-sonnet-4-5")
FRAME_MODEL    = os.environ.get("OPERATOR_FRAME_MODEL",    "claude-sonnet-4-5")

# ── Weekly limits ─────────────────────────────────────────────────────────
OPERATOR_LIMITS: dict[str, int] = {
    "twin_build":     int(os.environ.get("OPERATOR_LIMIT_TWIN_BUILD",     "5")),
    "twin_refresh":   int(os.environ.get("OPERATOR_LIMIT_TWIN_REFRESH",   "10")),
    "probe_message":  int(os.environ.get("OPERATOR_LIMIT_PROBE_MESSAGE",  "100")),
    "frame_score":    int(os.environ.get("OPERATOR_LIMIT_FRAME_SCORE",    "50")),
}

# ── Token budgets (per LLM call) ──────────────────────────────────────────
RECON_MAX_TOKENS_PASS = {
    1: {"input": 8_000,  "output": 1_500},
    2: {"input": 10_000, "output": 2_000},
    3: {"input": 6_000,  "output": 1_000},
}
RECON_CUMULATIVE_INPUT_CEILING = 250_000  # abort if exceeded — ~$0.75 cost guard.
# Server-side web_search_20250305 with max_uses=5 inflates input_tokens because
# integrated search results count toward the next assistant response's input.
# Realistic per-pass usage: 20-40k tokens × 3 passes = 60-120k typical, 250k worst.
SYNTHESIS_MAX_TOKENS = 4_000
PROBE_REPLY_MAX_TOKENS = 600
PROBE_NOTE_MAX_TOKENS  = 300
FRAME_MAX_TOKENS = 2_000

# ── Recon cache TTL ───────────────────────────────────────────────────────
RECON_CACHE_TTL_DAYS = 14

# ── Twin staleness (auto-delete) ──────────────────────────────────────────
TWIN_STALE_DAYS = 180

# ── Probe session idle timeout ────────────────────────────────────────────
PROBE_IDLE_MINUTES = 30

# ── EU indicator patterns (blocked in Phase 1) ───────────────────────────
EU_COUNTRY_SIGNALS = {
    "germany", "berlin", "munich", "hamburg", "frankfurt", "stuttgart",
    "france", "paris", "lyon", "marseille",
    "spain", "madrid", "barcelona",
    "italy", "rome", "milan",
    "netherlands", "amsterdam", "rotterdam",
    "sweden", "stockholm",
    "norway", "oslo",
    "denmark", "copenhagen",
    "finland", "helsinki",
    "switzerland", "zurich", "geneva",
    "austria", "vienna",
    "belgium", "brussels",
    "poland", "warsaw",
    "portugal", "lisbon",
    "ireland", "dublin",
    ".de", ".fr", ".es", ".it", ".nl", ".se", ".no", ".dk", ".fi",
    ".ch", ".at", ".be", ".pl", ".pt", ".ie",
}
