# The Operator — Module Implementation Spec v1.1
## Build-ready specification for Sonnet implementation

> **Status:** approved for Phase 1 build  
> **Owner:** Simulatte / iqbal.ahmed7@gmail.com  
> **Last updated:** 2026-04-30  
> **Supersedes:** v1.0 (had architectural defects — see CHANGELOG at end)

This document is the contract. If something is ambiguous when you start coding, stop and surface the question — don't infer.

---

## 0. What you are building

A dormant module inside the Persona Generator (PG) repo that, when activated by an env flag, exposes a `/operator/*` HTTP API for building "Twins" of real, named individuals from public web signals — and probing them, scoring outreach against them, and refreshing them over time.

**Phase 1 (this spec) ships:** API + DB + Claude skill. **No frontend.**

**Hard rule:** Do not modify any existing PG model, route, or business logic. The only legal modifications to existing files are:
- A single `app.include_router()` line in `main.py` (gated by env)
- A single `await _ensure_operator_tables()` line in the lifespan startup sequence

Everything else is new files.

---

## 1. Module Boundary

### Owns exclusively
- `pilots/the-mind/api/the_operator/` directory and all files within
- `/operator/*` HTTP routes
- DB tables: `twins`, `twin_probe_sessions`, `twin_probe_messages`, `twin_frame_scores`, `operator_allowances`
- Filesystem: `$MIND_DATA_DIR/twins/<twin_id>.json` (cached recon notes only — DB is source of truth)
- The Claude skill at `~/.claude/skills/the-operator/SKILL.md`

### Reuses (read-only consumer of)
- `auth.get_current_user` and `auth.get_admin_user` dependencies
- `db.get_db` session factory
- `db.User` model (foreign key target only — never modified)
- Anthropic client setup pattern from `main.py` (copy the pattern, do not import shared globals)
- `ADMIN_EMAILS` env var convention

### Never touches
- `_GENERATED` cache, `_load_all`, persona generation code paths
- `Allowance` model, `LIMITS` dict, `check_and_increment_allowance`
- Any `ChatSession`, `ChatMessage`, `Probe`, `Persona` model or endpoint
- `web/` frontend (Phase 2)

> **Rationale:** v1.0 added a column to `Allowance`. v1.1 gives Operator its own `operator_allowances` table. Costs ~30 lines of duplicated counter logic; buys total isolation. Worth it.

---

## 2. Naming Conventions

| Concept | Slug |
|---|---|
| Python package | `the_operator` (NOT `operator` — collides with stdlib) |
| Python imports | `from the_operator.router import operator_router` |
| URL prefix | `/operator` |
| DB table prefix | `twin_*` and `operator_*` |
| Env var | `OPERATOR_ENABLED` |
| Twin ID format | `tw-<name-slug>-<8hex>`, e.g. `tw-vilma-livas-3a7f2c1d` |
| Twin name slug | lowercased, alphanumeric + hyphens, max 60 chars |
| Probe session ID | `tps-<8hex>` |
| Frame score ID | `tfs-<8hex>` |

---

## 3. File Layout (additions only)

```
pilots/the-mind/api/
  the_operator/
    __init__.py                  # exposes operator_router; no logic
    config.py                    # env reads, constants, LIMITS
    models.py                    # SQLAlchemy models (Twin, TwinProbeSession, ...)
    migrations.py                # _ensure_operator_tables() — idempotent SQL
    router.py                    # FastAPI router; thin handlers, no business logic
    schemas.py                   # Pydantic request/response models
    storage.py                   # Twin JSON read/write to $MIND_DATA_DIR/twins/
    allowance.py                 # check_and_increment_operator_allowance
    recon.py                     # web research pipeline
    synthesis.py                 # Twin profile generation (LLM)
    probe.py                     # probe session loop (LLM, SSE)
    frame.py                     # frame scoring (LLM)
    prompts.py                   # all LLM prompt templates as constants
    errors.py                    # custom exceptions

  main.py                        # MODIFIED: 2 lines (router include + migration call)
```

```
~/.claude/skills/the-operator/
  SKILL.md                       # full skill instructions (separate doc — see §13)
```

---

## 4. Activation Gate (correct pattern)

`config.py`:
```python
import os
OPERATOR_ENABLED = os.environ.get("OPERATOR_ENABLED", "false").lower() in ("true", "1", "yes")
```

`main.py` lifespan additions (gated):
```python
# Inside lifespan(), after _ensure_probes_table()
if OPERATOR_ENABLED:
    from the_operator.migrations import _ensure_operator_tables
    await _ensure_operator_tables()
    logger.info("[startup] operator module enabled — tables ensured")

# After app creation, gated route registration
if OPERATOR_ENABLED:
    from the_operator.router import operator_router
    app.include_router(operator_router)
```

When `OPERATOR_ENABLED=false` (default), `/operator/*` returns 404 from FastAPI's normal not-found handler. **No catch-all, no 503.** A 404 doesn't leak that the module exists.

---

## 5. Database Schema

All migrations are idempotent raw SQL. Mirror `_ensure_probes_table` style. Run inside `_ensure_operator_tables()`.

### 5.1 `twins`

```sql
CREATE TABLE IF NOT EXISTS twins (
    id              VARCHAR PRIMARY KEY,
    user_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- subject identity
    full_name       VARCHAR NOT NULL,
    company         VARCHAR,
    title           VARCHAR,
    name_slug       VARCHAR NOT NULL,

    -- build metadata
    mode            VARCHAR NOT NULL DEFAULT 'standard',  -- 'standard' | 'enriched' | 'lite'
    confidence      VARCHAR NOT NULL DEFAULT 'medium',    -- 'high' | 'medium' | 'low'
    sources_count   INTEGER NOT NULL DEFAULT 0,
    gaps            TEXT,

    -- content (all JSON-serialised text)
    recon_notes     TEXT,                                 -- raw web research findings
    profile         TEXT NOT NULL,                        -- synthesised Twin profile (full JSON)
    enrichment      TEXT,                                 -- observed social signals (raw user paste)

    -- timestamps
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_probed_at  TIMESTAMP WITH TIME ZONE,
    last_refreshed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_twins_user_id ON twins (user_id);
CREATE INDEX IF NOT EXISTS ix_twins_name_slug ON twins (name_slug);
CREATE UNIQUE INDEX IF NOT EXISTS uq_twins_user_slug ON twins (user_id, name_slug);
```

> **Canonicalization rule:** Twins are per-user. Same `(user_id, name_slug)` pair returns the existing Twin (HTTP 409 on POST without `?force=true`). No cross-user sharing in Phase 1.

### 5.2 `twin_probe_sessions` and `twin_probe_messages`

One row per session, one row per message. Mirrors PG's `chat_sessions` / `chat_messages` exactly.

```sql
CREATE TABLE IF NOT EXISTS twin_probe_sessions (
    id              VARCHAR PRIMARY KEY,
    twin_id         VARCHAR NOT NULL REFERENCES twins(id) ON DELETE CASCADE,
    user_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_message_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    ended_at        TIMESTAMP WITH TIME ZONE,
    message_count   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_tps_twin_id ON twin_probe_sessions (twin_id);
CREATE INDEX IF NOT EXISTS ix_tps_user_id ON twin_probe_sessions (user_id);

CREATE TABLE IF NOT EXISTS twin_probe_messages (
    id              VARCHAR PRIMARY KEY,
    session_id      VARCHAR NOT NULL REFERENCES twin_probe_sessions(id) ON DELETE CASCADE,
    role            VARCHAR NOT NULL,                    -- 'user' | 'twin' | 'operator_note'
    content         TEXT NOT NULL,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    flagged         BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_tpm_session_id ON twin_probe_messages (session_id);
CREATE INDEX IF NOT EXISTS ix_tpm_created_at ON twin_probe_messages (created_at);
```

> An `operator_note` is a row appended after each `twin` reply containing the meta-commentary ("She answered that way because…").

### 5.3 `twin_frame_scores`

```sql
CREATE TABLE IF NOT EXISTS twin_frame_scores (
    id              VARCHAR PRIMARY KEY,
    twin_id         VARCHAR NOT NULL REFERENCES twins(id) ON DELETE CASCADE,
    user_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_input   TEXT NOT NULL,
    score_payload   TEXT NOT NULL,                       -- full annotated JSON
    overall_score   REAL,                                -- denormalised for sort/filter
    reply_probability VARCHAR,                           -- 'high' | 'medium' | 'low'
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_tfs_twin_id ON twin_frame_scores (twin_id);
CREATE INDEX IF NOT EXISTS ix_tfs_user_id ON twin_frame_scores (user_id);
```

### 5.4 `operator_allowances`

Per-user, per-week counter. **Independent of PG's Allowance table.**

```sql
CREATE TABLE IF NOT EXISTS operator_allowances (
    user_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_starting   DATE NOT NULL,
    twins_built     INTEGER NOT NULL DEFAULT 0,
    twin_refreshes  INTEGER NOT NULL DEFAULT 0,
    probe_messages  INTEGER NOT NULL DEFAULT 0,
    frame_scores    INTEGER NOT NULL DEFAULT 0,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, week_starting)
);
```

**Default weekly limits** (in `config.py`):
```python
OPERATOR_LIMITS = {
    "twin_build":     5,    # full builds per week
    "twin_refresh":   10,   # refresh existing twin
    "probe_message":  100,  # messages across all probe sessions
    "frame_score":    50,   # frame scores
}
```

Admin emails (`ADMIN_EMAILS`) bypass entirely, same as PG.

### 5.5 SQLAlchemy models

Defined in `the_operator/models.py`. Use the same `Base = declarative_base()` from `db.py` so they live in the same metadata. Required because Alembic isn't used; idempotent migrations need `Base.metadata` to know about these tables for any future `create_all()` fallback.

```python
# the_operator/models.py
from db import Base
# Define Twin, TwinProbeSession, TwinProbeMessage, TwinFrameScore, OperatorAllowance
# All FKs to users(id) — never to other PG tables
```

---

## 6. API Surface

All routes mounted at `/operator`. All require `Depends(get_current_user)`. Admin routes additionally require `Depends(get_admin_user)`. Streaming endpoints return `text/event-stream`. Non-streaming return `application/json`.

### 6.1 Request/Response schemas

Defined in `the_operator/schemas.py` as Pydantic v2 models. Wire format below.

### 6.2 Endpoint table

| # | Method | Path | Purpose | Streaming |
|---|---|---|---|---|
| 1 | POST | `/operator/twins` | Build a Twin | SSE |
| 2 | GET | `/operator/twins` | List user's Twins | No |
| 3 | GET | `/operator/twins/{twin_id}` | Fetch full Twin | No |
| 4 | DELETE | `/operator/twins/{twin_id}` | Delete Twin + cascades | No |
| 5 | POST | `/operator/twins/{twin_id}/refresh` | Re-run recon, re-synthesise | SSE |
| 6 | POST | `/operator/twins/{twin_id}/enrich` | Add observed signals, re-synthesise | SSE |
| 7 | POST | `/operator/twins/{twin_id}/probe` | Start probe session → returns session_id | No |
| 8 | POST | `/operator/twins/{twin_id}/probe/{session_id}/message` | Send a probe message | SSE |
| 9 | GET | `/operator/twins/{twin_id}/probe/{session_id}` | Fetch session transcript | No |
| 10 | POST | `/operator/twins/{twin_id}/probe/{session_id}/end` | Mark session ended | No |
| 11 | POST | `/operator/twins/{twin_id}/frame` | Score a message against Twin | No |
| 12 | GET | `/operator/twins/{twin_id}/frame` | List frame scores for this Twin | No |
| 13 | GET | `/operator/me` | User's Operator allowance state | No |
| 14 | GET | `/operator/admin/twins` | Admin: all Twins | No |
| 15 | DELETE | `/operator/admin/twins/{twin_id}` | Admin: force-delete | No |

### 6.3 Wire format examples

**`POST /operator/twins`** request:
```json
{
  "full_name": "Vilma Livas",
  "company": "Banza",
  "title": "CCO",
  "mode": "standard"
}
```

SSE event stream (event names match the existing PG SSE convention):
```
event: progress
data: {"stage":"recon","message":"Searching public sources..."}

event: progress
data: {"stage":"recon","message":"Found 7 sources","sources_count":7}

event: progress
data: {"stage":"synthesis","message":"Building decision architecture..."}

event: complete
data: {"twin_id":"tw-vilma-livas-3a7f2c1d","confidence":"high"}
```

On error:
```
event: error
data: {"code":"recon_failed","detail":"No public signals found","retryable":false}
```

**`GET /operator/twins/{twin_id}`** response:
```json
{
  "id": "tw-vilma-livas-3a7f2c1d",
  "full_name": "Vilma Livas",
  "company": "Banza",
  "title": "CCO",
  "mode": "standard",
  "confidence": "high",
  "sources_count": 7,
  "gaps": "No personal social signals found. Investor letters not public.",
  "profile": {
    "identity_snapshot": "...",
    "decision_architecture": {
      "first_filter": "...",
      "trust_signal": "...",
      "rejection_trigger": "...",
      "engagement_threshold": "..."
    },
    "professional_register": {
      "vocabulary_used": ["..."],
      "vocabulary_avoided": ["..."],
      "tone": "...",
      "already_knows": ["..."]
    },
    "personal_signal_layer": null,
    "trigger_map": {"leans_in": ["..."], "disengages": ["..."]},
    "objection_anticipator": {
      "first_contact": [{"objection":"...","preempt":"..."}],
      "first_call": [{"objection":"...","response":"..."}]
    },
    "message_frame_recommendations": {
      "lead_with": "...",
      "open_format": "...",
      "subject_register": "...",
      "optimal_length_words": 90,
      "withhold_for_call": "..."
    },
    "call_prep": {
      "have_ready": ["..."],
      "do_not_say": ["..."]
    }
  },
  "created_at": "2026-04-30T10:23:00Z",
  "last_refreshed_at": null,
  "last_probed_at": null
}
```

**`POST /operator/twins/{twin_id}/frame`** request:
```json
{ "message": "Subject: Banza's Costco push has a structural activation gap..." }
```

Response:
```json
{
  "id": "tfs-9b2e1a44",
  "overall_score": 8.8,
  "reply_probability": "high",
  "annotations": [
    {"segment": "Subject: ...", "score": 8.5, "reads_as": "...", "risk": null},
    {"segment": "Paragraph 1: ...", "score": 9.0, "reads_as": "...", "risk": null}
  ],
  "weakest_point": {"segment": "...", "issue": "..."},
  "strongest_point": {"segment": "...", "reason": "..."},
  "single_change_to_improve": "Reframe '$3.17/box' as 'she calculated it herself, unprompted'."
}
```

**`GET /operator/me`** response:
```json
{
  "user": {"id": "...", "email": "..."},
  "operator_allowance": {
    "twin_build":    {"used": 1, "limit": 5},
    "twin_refresh":  {"used": 0, "limit": 10},
    "probe_message": {"used": 14, "limit": 100},
    "frame_score":   {"used": 3, "limit": 50},
    "resets_at": "2026-05-04T00:00:00Z"
  }
}
```

### 6.4 Allowance enforcement

Every mutating endpoint calls `check_and_increment_operator_allowance(user, action, db)` BEFORE the LLM call. On 429-equivalent (limit hit), raise HTTP 402 with the same payload shape PG uses, but `error: "operator_allowance_exceeded"`.

```python
# Action mapping
ACTION_MAP = {
    "POST /operator/twins":                       "twin_build",
    "POST /operator/twins/{id}/refresh":          "twin_refresh",
    "POST /operator/twins/{id}/enrich":           "twin_build",   # enrich = re-synth, counts as build
    "POST /operator/twins/{id}/probe/{s}/message":"probe_message",
    "POST /operator/twins/{id}/frame":            "frame_score",
}
```

Probe `start` and `end` are free.

---

## 7. Reconnaissance Pipeline

Implemented in `the_operator/recon.py`. This is the most consequential subsystem.

### 7.1 Tooling

Use the **Anthropic Messages API `web_search_20250305` tool** (already supported by the `anthropic` SDK). Reasons:
- Already in repo dependencies — no new vendor
- Citation-attached results — no separate fetch step
- One bill, one rate limit

Model: **claude-sonnet-4-5** (codename `claude-sonnet-4-5-20250929`). Recon needs reasoning over messy public text, Haiku misses nuance.

### 7.2 Search strategy (3-pass cascade)

Run sequentially. Each pass fills a layer of the recon brief. Cap total tool turns at 12 across all passes.

**Pass 1 — Identity & role (max 4 tool turns)**
Query templates (the model will issue these as `web_search` tool calls inside one Messages turn):
- `"{full_name}" "{company}" {title}`
- `"{full_name}" linkedin {company}`
- `{full_name} {company} press release`
- `{full_name} {company} quote OR interview`

**Pass 2 — Public voice (max 5 tool turns)**
- `"{full_name}" podcast`
- `"{full_name}" keynote OR panel OR conference`
- `"{full_name}" article OR substack OR essay`
- `"{full_name}" trade press {industry vertical inferred from Pass 1}`

**Pass 3 — Career trajectory (max 3 tool turns)**
- `"{full_name}" prior role OR previous company`
- `"{full_name}" exit OR acquisition OR IPO`
- `"{full_name}" alma mater OR education`

### 7.3 Token budget

| Pass | Input cap | Output cap |
|---|---|---|
| 1 | 8K | 1.5K |
| 2 | 10K | 2K |
| 3 | 6K | 1K |
| Synthesis (§8) | 15K (recon notes in) | 4K |

Hard ceiling: `~$0.50/twin` at Sonnet 4.5 pricing. If a recon call exceeds 50K input tokens cumulatively, abort with `error: recon_budget_exceeded`.

### 7.4 Caching

Recon notes (the raw output of Passes 1–3, before synthesis) are written to `$MIND_DATA_DIR/twins/<twin_id>.recon.json` with a 14-day TTL. On `POST /refresh`, read cached recon if `now - mtime < 14d AND user did not pass ?force=true`.

### 7.5 Failure modes

| Condition | Action |
|---|---|
| Zero results across all passes | Save Twin with `confidence='low'`, `gaps='No public signals found.'`. Do not error — let user enrich manually. |
| Web search tool returns 5xx | Retry once with 30s backoff. Then fail with `error: recon_unavailable`. |
| Output exceeds token cap | Truncate, mark `confidence='medium'` with note in `gaps`. |
| LLM refuses (safety) | Surface verbatim refusal to user. Do not retry. |

### 7.6 Output shape

Recon produces a structured intermediate (NOT the final Twin profile):

```json
{
  "raw_findings": [
    {"source_url": "...", "snippet": "...", "credibility": "high|medium|low"}
  ],
  "extracted_facts": {
    "current_role_start": "2023-09",
    "prior_companies": ["..."],
    "education": ["..."],
    "public_quotes": [{"quote":"...","source":"..."}],
    "podcast_appearances": [{"show":"...","url":"...","date":"..."}],
    "industry_vertical": "...",
    "company_stage": "..."
  },
  "sources_count": 7,
  "confidence_signal": "high|medium|low"
}
```

This intermediate is passed to synthesis (§8).

---

## 8. Synthesis

In `the_operator/synthesis.py`. Takes the recon intermediate + optional enrichment text, produces the final `profile` JSON (shape per §6.3).

Model: **claude-sonnet-4-5** (same).

Prompt template lives verbatim in `prompts.py` as `TWIN_SYNTHESIS_PROMPT`. It must:
1. Demand structured JSON output matching the §6.3 `profile` schema exactly
2. Forbid hallucinated facts — every claim ties back to either `extracted_facts` or `enrichment`
3. Tag enrichment-derived claims with `[observed]`, recon-derived with `[inferred]`
4. Require the model to populate `gaps` honestly (no padding with platitudes)
5. Set `confidence` based on `sources_count` and recency: ≥5 sources → high; 2–4 → medium; <2 → low

Use Anthropic's structured output / tool-use response constraint (define a `submit_twin_profile` tool with the JSON schema, force `tool_choice: {type: "tool", name: "submit_twin_profile"}`).

---

## 9. Probe Loop

In `the_operator/probe.py`. SSE streaming, mirrors PG's chat streaming pattern.

### 9.1 Flow per message

1. Increment allowance (`probe_message`)
2. Persist user message row (`role='user'`)
3. Stream assistant response with system prompt = `TWIN_PROBE_SYSTEM_PROMPT(twin_profile)` + history
4. As tokens stream out: forward to client as `event: token` SSE events
5. After main reply complete, run a second non-streamed call to generate the `operator_note` (out-of-character meta-commentary)
6. Persist twin reply (`role='twin'`) and operator note (`role='operator_note'`)
7. Send `event: complete` with both message IDs

Two-call structure (reply + note) is intentional — keeps the in-character voice clean and lets you display them as separate UI elements.

Model for both calls: **claude-sonnet-4-5**.

### 9.2 Idle session policy

A session is considered ended after 30 min of inactivity (no new message). A new probe message after that creates a new session automatically. Same as PG chat.

### 9.3 Moderation

Run input moderation on the user message before the LLM call. Reuse PG's `moderation.py` if it exposes a callable; otherwise duplicate the check (do not import private symbols). Flagged messages: store with `flagged=true`, return `403 moderation_blocked`.

---

## 10. Frame Scoring

In `the_operator/frame.py`. Single non-streaming endpoint.

System prompt = `FRAME_SCORE_PROMPT(twin_profile)`. The user message is the input being scored.

Force structured output via `submit_frame_score` tool — schema matches §6.3 frame response shape.

The prompt instructs the model to:
- Segment the input by paragraph (or by 1–2 sentence chunks if no paragraphs)
- Score each segment 0–10 against this Twin's `decision_architecture`, `professional_register`, `trigger_map`
- Produce the `single_change_to_improve` as a concrete edit, not a vague suggestion
- Cap `reply_probability` decision: overall ≥ 8.5 → high; 6.5–8.4 → medium; < 6.5 → low

---

## 11. Skill Interface (Phase 1 deliverable)

Lives at `~/.claude/skills/the-operator/SKILL.md`. Separate document, but its API contract is fixed by §6.

**Hard rule:** The skill is API-only. No standalone fallback mode. If the API is unreachable or `OPERATOR_ENABLED=false`, the skill displays:

```
── THE OPERATOR ─────────────────────────────────────
Operator API unavailable. Confirm OPERATOR_ENABLED=true 
and OPERATOR_API_URL is reachable.
─────────────────────────────────────────────────────
```

…and exits. v1.0's local-JSON fallback was struck.

Skill commands → API mapping:

| Skill command | API call(s) |
|---|---|
| `operator run [name] at [company], [title]` | `POST /operator/twins`, then `GET /operator/twins/{id}` |
| `operator run [name] --enrich` | Above + prompts user, then `POST /operator/twins/{id}/enrich` |
| `operator refresh [name]` | Looks up twin by slug, `POST /operator/twins/{id}/refresh` |
| `operator probe [name]` | `POST /operator/twins/{id}/probe`, then loop on `/message` |
| `operator frame [name] -- [text]` | `POST /operator/twins/{id}/frame` |
| `operator status` | `GET /operator/twins` + `GET /operator/me` |
| `operator delete [name]` | `DELETE /operator/twins/{id}` (with confirmation) |

Auth: skill reads `OPERATOR_API_TOKEN` from env (a long-lived JWT issued by PG's existing token-mint endpoint — same pattern PG admin tools use).

---

## 12. Error Handling

All errors return JSON with this shape (matches PG convention):

```json
{ "error": "<machine_code>", "detail": "<human_message>", "retryable": true|false }
```

| Code | When | HTTP |
|---|---|---|
| `operator_disabled` | Module not enabled | 404 |
| `twin_not_found` | Unknown twin_id | 404 |
| `twin_already_exists` | Slug collision without `?force=true` | 409 |
| `operator_allowance_exceeded` | Limit hit | 402 |
| `recon_failed` | Web search exhausted with no useful signal | 422 |
| `recon_budget_exceeded` | Token cap hit | 422 |
| `recon_unavailable` | Web search tool 5xx after retry | 503 |
| `synthesis_failed` | LLM returned malformed JSON twice | 500 |
| `moderation_blocked` | Input moderation tripped | 403 |
| `session_ended` | Probe message to a closed session | 410 |

---

## 13. Logging & Observability

Use the existing `logger` from `main.py` pattern. Log lines must be greppable:

```
[operator] twin_built user=<email> twin_id=<id> sources=<n> confidence=<x> ms=<int>
[operator] probe_message user=<email> twin_id=<id> session=<id> tokens_in=<n> tokens_out=<n>
[operator] frame_scored user=<email> twin_id=<id> overall=<float>
[operator] recon_failed user=<email> name=<slug> reason=<code>
```

Cost-tracking: log token counts for each LLM call. Useful for the eventual cost dashboard.

---

## 14. PII / Legal

This module builds profiles of named real individuals from public web data. Required guardrails:

1. **Right to erasure**: `DELETE /operator/twins/{id}` is a hard delete (CASCADE on FKs), not soft. The Twin's recon JSON file is also unlinked. Implementation: `DELETE` endpoint must `os.unlink($MIND_DATA_DIR/twins/{id}.recon.json)` if file exists, then DB delete.
2. **Subject takedown**: Add `POST /operator/admin/twins/by-name/erase` taking `{full_name}` — admin-only, deletes ALL Twins matching that name across ALL users. For when someone writes in asking to be removed.
3. **Retention**: Twins older than 180 days with no activity (`last_probed_at` and `updated_at` both stale) are auto-deleted by the existing TTL GC loop in `main.py`. Add a single line to `_purge_old_generated`'s sibling — or extend `_ttl_gc_loop` — to call `the_operator.storage.purge_stale_twins(days=180)`.
4. **No EU subjects in Phase 1**: Document this as an explicit limitation. The skill's `operator run` MUST refuse if the user includes obvious EU markers in the input ("based in Berlin", ".de" company domain, etc.). Surface as a polite "Operator does not currently profile EU-based subjects." block.
5. **AUP check**: Before merge to main, confirm with Anthropic AUP compliance lead that this use case is covered. Cite the AUP review ticket in the merge commit.

---

## 15. Build Order (sequenced for one engineer)

Realistic estimate: **2–3 focused days**.

### Day 1 — Foundations
1. Create `the_operator/` directory structure with empty stubs
2. Write `config.py` (env reads, OPERATOR_LIMITS dict)
3. Write `models.py` (SQLAlchemy)
4. Write `migrations.py` (idempotent SQL — copy `_ensure_probes_table` style)
5. Wire `main.py` (2 lines, gated)
6. Deploy to staging with `OPERATOR_ENABLED=true`, verify tables created
7. Write `schemas.py` (all Pydantic shapes from §6)
8. Write `errors.py` (custom exceptions)
9. Write `allowance.py` (`check_and_increment_operator_allowance` — copy PG pattern)
10. Write `router.py` skeleton with all 15 endpoints returning 501

### Day 2 — Core LLM pipelines
11. Write `prompts.py` (all 3 prompt templates verbatim)
12. Implement `recon.py` end-to-end with the 3-pass cascade
13. Implement `synthesis.py` with structured tool-use output
14. Wire endpoint #1 (`POST /operator/twins`) — full SSE flow
15. Wire endpoints #2, #3, #4 (list/get/delete)
16. Manual test: build a Twin of a public exec, confirm shape

### Day 3 — Probe + frame + skill
17. Implement `probe.py` (two-call streaming pattern, moderation hook)
18. Wire endpoints #7, #8, #9, #10 (probe lifecycle)
19. Implement `frame.py` (structured output)
20. Wire endpoints #11, #12 (frame)
21. Wire endpoints #5, #6 (refresh, enrich)
22. Wire endpoint #13 (`/operator/me`)
23. Wire admin endpoints #14, #15
24. Write `~/.claude/skills/the-operator/SKILL.md` per §11
25. End-to-end test from Claude chat: build → probe → frame → refresh

### Pre-merge gates
- [ ] All 15 endpoints return real responses (no 501s)
- [ ] DB migration is idempotent (re-run on staging without error)
- [ ] `OPERATOR_ENABLED=false` returns 404 on `/operator/*` (not 503)
- [ ] PG endpoints behave identically with module enabled and disabled
- [ ] One Twin built end-to-end on staging with `confidence=high`
- [ ] AUP check ticket cited in commit message

---

## 16. Out of Scope for Phase 1

Documented now so they don't creep in:

- Web UI (`web/app/operator/`) — Phase 2
- Cohort builds (multiple Twins from a list) — Phase 3
- Cross-user Twin sharing or marketplace — Phase 3
- Twin diffing / change detection between refreshes — Phase 3
- Voice/tone generation (drafting actual outreach in the Twin's preferred register) — Phase 3
- Browser extension for one-click profiling from LinkedIn — Phase 4
- API key access for Simulatte enterprise clients — Phase 3
- EU subject support — pending DPA + AUP review

---

## 17. Out of Phase 1 Strategic Read (preserved from v1.0)

The per-person GTM use case is the proof of concept. The defensible play is **cohort building** — feed 50 target executives, get 50 Twins clustered by decision architecture, generate cohort-level outreach strategy with per-person message variants. Evidenza profiles fictional respondents from surveys. Crystal Knows tags personality types from LinkedIn. Similie does generic CX twins. None close the loop **public signal → behavioral model → message scoring → probe feedback** in one product. The Operator does. Phase 3 is where that becomes the wedge.

---

## CHANGELOG

### v1.1 (this version) — fixes from v1.0 critique
- **Renamed** package `operator` → `the_operator` (stdlib collision)
- **Activation gate corrected**: conditional registration at startup, returns 404 not 503
- **Allowance isolation**: new `operator_allowances` table; PG's `Allowance` is no longer touched
- **Probe messages normalized**: `twin_probe_messages` table replaces JSON blob in session row
- **Standalone-fallback removed**: skill is API-only; fail loudly if API unreachable
- **Allowance gating extended**: probe messages and frame scores now counted (not just builds)
- **Recon pipeline specified**: web_search_20250305 tool, 3-pass cascade, token caps, caching, failure modes
- **PII/legal section added**: erasure, subject takedown, retention TTL, EU exclusion, AUP gate
- **`refresh` command added** to skill + API
- **Twin canonicalization specified**: per-user, unique on `(user_id, name_slug)`, 409 on collision
- **Effort estimate corrected**: 2–3 days, not "one session"
- **Wire formats specified** for every endpoint (request + response JSON shapes)
- **Error codes enumerated** with HTTP status mapping

### v1.0 — initial draft
- Architectural shape; competitive positioning; phase plan
