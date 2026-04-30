# The Operator — Frontend Spec v1.0

Author: 2026-04-30
Status: ready to build (backend live, awaiting `OPERATOR_ENABLED=true`)
Backend: 16 endpoints under `/operator/*` — see `docs/THE_OPERATOR_SPEC.md` §6

---

## 0. Conventions confirmed from the existing PG frontend

The Operator UI lives inside `pilots/the-mind/web` and reuses every primitive
already in place:

- **Framework:** Next.js 14 App Router, TypeScript, Tailwind. Pages are
  `app/<route>/page.tsx`. Client-only routes use `"use client"`.
- **Brand palette:** `bg-void` (#050505), `text-parchment` (#E9E6DF), accents
  in Signal green `#A8FF3E`, secondary text `#9A9997`. Border radius 0.
  See Simulatte brand skill — same tokens as PG dashboard.
- **Auth:** every backend call goes through `_authHeaders()` in `lib/api.ts`
  (HS256 JWT minted by `/api/token`). New Operator helpers reuse the same
  pattern. No new auth surface.
- **Allowance:** `AllowanceProvider` already wraps the app. Operator gets a
  parallel context — `OperatorAllowanceProvider` — so persona/probe/chat
  counters and twin/probe-message counters don't collide.
- **Access guard:** `AccessGate` already enforces signed-in + active. Reuse it.
  Add a server-side feature flag check on top: hide Operator nav when
  `NEXT_PUBLIC_OPERATOR_ENABLED !== "true"`.
- **Layout:** `AppShell` + `NavRail` (md+) and `MobileBottomNav` (below md).
  Operator adds 1 nav entry — "Twins" — and a mobile bottom-nav slot.
- **SSE:** the existing probe page (`app/probe/[probeId]/PublicProbeClient.tsx`)
  already demonstrates `fetch` + `ReadableStream` reading of `data: {...}\n\n`
  events. Copy that pattern verbatim for build/refresh/probe streams.

If a convention here clashes with current PG code, current code wins.

---

## 1. Information architecture

```
/operator                       List view — all Twins (cards) + "Build new" CTA
/operator/build                 Build form (name, company, title) → SSE stream
/operator/[twin_id]             Twin detail view (profile, gaps, last refreshed)
/operator/[twin_id]/probe       Live probe session (Twin reply + Operator note)
/operator/[twin_id]/frame       Frame-score draft outreach against Twin
/operator/[twin_id]/enrich      Paste enrichment text → re-synthesise

/admin/twins                    (admin only) all Twins across users
/admin/users/[user_id]/limits   (admin only) per-user allowance overrides
```

The base `/operator` route 404s if `NEXT_PUBLIC_OPERATOR_ENABLED !== "true"`.

---

## 2. Navigation entry

**Desktop (NavRail):** add a new entry between "Probes" and the divider:

```
icon:    crosshair / target  (lucide: Target)
label:   "Twins"
href:    /operator
badge:   builds remaining (X/5) — pulled from /operator/me
```

Hidden when feature flag off.

**Mobile (MobileBottomNav):** if there's room, add Twins as a 5th slot.
Otherwise tuck under a "More" overflow.

**Allowance counter:** the existing `AllowanceCounter` shows persona/probe/chat
weekly remaining. Add a 4th line for "Twins" linked to `/operator`. Visually
identical pill — same styling.

---

## 3. Pages

### 3.1 `/operator` — Twin grid

**Purpose:** see all your twins at a glance, decide what to build / probe / refresh.

**Data:** `GET /operator/twins` → `TwinCard[]`
```
{ twin_id, full_name, title, company, confidence, last_refreshed_at,
  is_stale, probe_count, last_frame_score }
```

**Layout:**
- Header: "Twins" h1 + "Build a Twin" primary button (links to `/operator/build`)
- Subhead pill: `12 of 5 weekly builds used · resets Mon 00:00 UTC`
- Grid (3 columns md, 1 column sm) of `TwinCard`s
- Empty state: centred copy "No Twins yet. Build your first prospect Twin."
  + same CTA

**`TwinCard` (new component, mirrors `PersonaGrid`):**
- Top row: full name (parchment, 18px) + role/company (static grey, 13px)
- Confidence chip: `high` (signal-green text), `medium` (parchment),
  `low` (static grey + warning icon)
- Footer row: `12 probes · last frame 8.7 · refreshed 14d ago` (mono 11px)
- Stale (>180d) shows a subtle red dot + tooltip "Refresh recommended"
- Click → `/operator/[twin_id]`
- Right-click / `…` menu: Probe / Frame / Refresh / Enrich / Delete

### 3.2 `/operator/build` — Build flow

**Purpose:** create a new Twin from name + company + title, watch SSE progress.

**Layout:**
- Form (centred, 480px max width):
  - Full name (required, text)
  - Company (optional, text) — note: "improves recon precision"
  - Title (optional, text)
  - "Build Twin" button → `POST /operator/twins` with `Accept: text/event-stream`
- Progress strip below form once submitted:
  - Stages: `recon` (3 sub-stages) → `synthesis` → `ready`
  - Each stage shows a status line (the `message` field from each SSE frame)
  - Live token-cost meter (cumulative input + output) — pulled from frames if
    backend exposes it; otherwise omit.
- On `ready` event: redirect to `/operator/[twin_id]`
- On error event: show the error code + suggested action from the spec error
  table (e.g. `eu_subject_blocked` → "EU subjects unavailable in Phase 1")

**SSE wire format (matches backend):**
```
data: {"stage":"recon","message":"Searching public sources (pass 1/3)…"}
data: {"stage":"synthesis","message":"Building decision filter…"}
data: {"stage":"ready","twin_id":"tw-priya-sharma-c32e"}
```

### 3.3 `/operator/[twin_id]` — Twin detail

**Purpose:** read the full synthesised profile, decide next action.

**Data:** `GET /operator/twins/{twin_id}` → `TwinDetail`

**Layout (2-column md, stacked sm):**

LEFT COLUMN (60%) — profile sections, in order:
1. Header: name, title, company, confidence chip, "Refresh" + "Enrich" buttons
2. Identity snapshot — single paragraph
3. Decision architecture — 4 labelled rows (first_filter, trust_signal,
   rejection_trigger, engagement_threshold)
4. Trigger map — two columns: "Leans in" (signal-green dots) /
   "Disengages" (static grey dots)
5. Objection anticipator — two collapsibles: First contact / First call,
   each a list of `objection → preempt | response` pairs
6. Message frame recommendations — 5 labelled rows
7. Call prep — two columns: "Have ready" / "Do not say"
8. Gaps — small static-grey block at bottom: "What we couldn't find"

RIGHT COLUMN (40%, sticky on md+):
- Action card with 4 buttons stacked: "Open probe", "Frame a draft",
  "Enrich with new signal", "Delete twin"
- Stats card: probes count, last frame score, last refresh date,
  recon source count
- Hard rules reminder (small, static grey): "This is a probabilistic
  decision-filter model. Not the person."

### 3.4 `/operator/[twin_id]/probe` — Probe session

**Purpose:** chat with the Twin, see the Operator analyst note after each turn.

**Layout (2-column 60/40 md, stacked sm):**

LEFT (60%) — Twin chat:
- ChatGPT-style scrolling transcript
- Twin messages: parchment text on void, no avatar (keep it sparse)
- User messages: signal-green text on a 1px border-parchment/10 box, right-aligned
- Composer at bottom: textarea (autoresize) + Send button + cmd/ctrl+enter
- Live SSE token streaming — copy from `PublicProbeClient.tsx`

RIGHT (40%) — Operator notes pane:
- Sticky, scrollable
- One card per turn, in reverse order (newest top)
- Each card: turn timestamp + 2-4 sentence analyst note in mono-ish styling
  (Barlow 14px, static grey, leading 1.6)
- Empty state: "Operator notes appear here after each Twin reply."

**Session model:**
- On page load: `POST /operator/twins/{id}/probe` → session_id (or reuse last
  open session if <30 min idle)
- On send: `POST /operator/twins/{id}/probe/{session_id}/message` returns SSE
  with two events: Twin reply tokens, then a single "operator_note" event
- "End session" button in header → `POST .../end`. Modal confirm.

**Idle handling:** if the page stays open >30 min, the next send returns
`session_ended`. Show banner: "Session ended (idle 30 min). Start new session."
Button → reload with new session.

### 3.5 `/operator/[twin_id]/frame` — Frame score

**Purpose:** paste a draft, score against the Twin, iterate.

**Layout (2-column md, stacked sm):**

LEFT (50%) — Draft input:
- Large textarea, 12-line minimum, Barlow 15px
- Char/word counter below
- "Score this draft" button (only enabled when ≥ 20 words)

RIGHT (50%) — Last result panel (shown after first score):
- Top: overall score (large, signal-green if ≥8.5, parchment if 6.5–8.4,
  static grey if <6.5) + reply probability chip
- Annotations — render the input textarea on the left as inline-highlighted
  segments. Hovering a segment reveals `reads_as` + optional `risk` in a
  small popover. Use background colour, not text colour, for highlights:
  - score ≥8: subtle signal-green/10 background
  - score 5–7: no highlight
  - score <5 OR risk present: static-grey/15 background
- Strongest point — green block, the segment + `reason`
- Weakest point — grey block, the segment + `issue`
- Single change to improve — bordered card, full-width, with a "Copy"
  affordance

**Iteration loop:** the user edits the draft and re-scores. Each score is
appended to a "History" collapsible at the bottom of the right column
showing score-over-time as a sparkline.

**Persistence:** every score is server-side via `POST .../frame`. The
"history" is `GET .../frame_scores` (last 10).

### 3.6 `/operator/[twin_id]/enrich` — Enrichment

**Purpose:** add new signal (talk transcript, podcast, article excerpt) and
re-synthesise.

**Layout:** same form pattern as build, but:
- One large textarea ("Enrichment text"), 6000 char max with counter
- Note above: "Paste a recent talk transcript, podcast excerpt, or article.
  This re-runs synthesis with the new signal added."
- "Re-synthesise" button → SSE stream → on `ready`, redirect back to detail

### 3.7 `/admin/twins` — Admin Twin browser

**Purpose:** ops view for support / abuse handling.

**Layout:** table view (mirrors `/admin/personas`):
- Columns: full_name, owner_email, company, confidence, created_at,
  last_refreshed, probe_count, status
- Row actions: View / Delete / Erase by name (subject request)
- Search: name OR owner_email
- "Erase by name" opens a confirm modal explaining hard-delete + cache wipe

### 3.8 `/admin/users/[user_id]/limits` — Per-user allowance overrides

**Purpose:** admin can grant a user more weekly persona/probe/chat capacity.

**Layout:**
- Header: user name + email
- Form with 3 number inputs:
  - "Personas / week (default 5)" → `persona_limit`
  - "Probes / week (default 50)" → `probe_limit`
  - "Chats / week (default 100)" → `chat_limit`
- Each shows current effective value (override OR global default)
- "Reset" button next to each = sends `null` for that field
- "Save" → `POST /admin/users/{user_id}/set-limits` with non-null fields only
- Toast on success: "Limits updated for X"

This page is reachable from the existing `/admin/users/[user_id]` detail page
via a new "Edit limits" button.

---

## 4. New TypeScript types (`lib/operator-api.ts`)

A new module to keep Operator types separate from PG types.

```ts
export interface TwinCard {
  twin_id: string;
  full_name: string;
  title: string | null;
  company: string | null;
  confidence: "high" | "medium" | "low";
  last_refreshed_at: string;
  is_stale: boolean;
  probe_count: number;
  last_frame_score: number | null;
}

export interface TwinProfile {
  identity_snapshot: string;
  decision_architecture: { first_filter: string; trust_signal: string;
    rejection_trigger: string; engagement_threshold: string };
  professional_register: { vocabulary_used: string[]; vocabulary_avoided: string[];
    tone: string; already_knows: string[] };
  personal_signal_layer: string | null;
  trigger_map: { leans_in: string[]; disengages: string[] };
  objection_anticipator: {
    first_contact: { objection: string; preempt: string }[];
    first_call: { objection: string; response: string }[];
  };
  message_frame_recommendations: { lead_with: string; open_format: string;
    subject_register: string; optimal_length_words: number;
    withhold_for_call: string };
  call_prep: { have_ready: string[]; do_not_say: string[] };
  confidence: "high" | "medium" | "low";
  gaps: string;
}

export interface TwinDetail extends TwinCard { profile: TwinProfile; }

export interface FrameAnnotation {
  segment: string; score: number; reads_as: string; risk: string | null;
}
export interface FrameScoreResponse {
  annotations: FrameAnnotation[];
  overall_score: number;
  reply_probability: "high" | "medium" | "low";
  weakest_point: { segment: string; issue: string };
  strongest_point: { segment: string; reason: string };
  single_change_to_improve: string;
}

export interface OperatorAllowanceState {
  twin_build: { used: number; limit: number };
  twin_refresh: { used: number; limit: number };
  probe_message: { used: number; limit: number };
  frame_score: { used: number; limit: number };
  resets_at: string;
}

// CRUD helpers — all reuse _authHeaders + API base from lib/api.ts
export async function listTwins(): Promise<TwinCard[]> { … }
export async function getTwin(id: string): Promise<TwinDetail> { … }
export async function deleteTwin(id: string): Promise<void> { … }
export async function streamBuild(...): AsyncIterable<BuildEvent> { … }
export async function streamProbeMessage(...): AsyncIterable<ProbeEvent> { … }
export async function frameScore(id, message): Promise<FrameScoreResponse> { … }
export async function getOperatorAllowance(): Promise<OperatorAllowanceState> { … }
```

---

## 5. New components

| Component | Purpose | Mirrors |
|-----------|---------|---------|
| `TwinCard` | Grid card on `/operator` | `PersonaGrid` row |
| `TwinDetail` | Profile sections renderer | n/a |
| `TwinBuildStream` | SSE progress strip | bits of `PersonaWizard` |
| `OperatorProbe` | Two-pane chat + notes | `PublicProbeClient` |
| `FrameScorePanel` | Annotated draft + score readout | new |
| `FrameAnnotatedText` | Inline highlight + popover | new |
| `OperatorAllowanceProvider` | Context + counter | `AllowanceProvider` |
| `OperatorAllowanceCounter` | Pill in nav | `AllowanceCounter` |
| `EnrichForm` | Textarea + submit | bits of `PersonaWizard` |
| `AdminTwinsTable` | Admin browser | `/admin/personas` table |
| `UserLimitsForm` | Per-user override editor | new |

---

## 6. Feature flag

`NEXT_PUBLIC_OPERATOR_ENABLED` set on Vercel → `mind.simulatte.io`.

When `false`:
- NavRail entry hidden
- All `/operator/*` routes 404 server-side (in `layout.tsx`)
- Allowance counter doesn't show twin row

When `true` but backend returns 404 on `/operator/me`: show a "Module
deploying" placeholder. This decouples frontend deploys from backend ones.

---

## 7. Build order (8–10 day estimate)

| Day | Slice |
|-----|-------|
| 1 | `lib/operator-api.ts` types + helpers, `OperatorAllowanceProvider`, NavRail entry, feature flag plumbing |
| 2 | `/operator` grid + `TwinCard` |
| 3 | `/operator/build` form + SSE stream wiring |
| 4 | `/operator/[twin_id]` detail page (read-only render of all profile sections) |
| 5 | `/operator/[twin_id]/probe` — two-pane SSE chat + operator notes |
| 6 | `/operator/[twin_id]/frame` — score panel + annotations + history |
| 7 | `/operator/[twin_id]/enrich` + delete + refresh actions |
| 8 | `/admin/twins` browser + erase-by-name modal |
| 9 | `/admin/users/[user_id]/limits` form + wire to backend |
| 10 | Polish — empty states, mobile layouts, error toasts, copy review |

Each slice is independently deployable behind the feature flag.

---

## 8. Acceptance — what "done" looks like

- [ ] All 8 user-facing routes ship behind `NEXT_PUBLIC_OPERATOR_ENABLED`
- [ ] Build → detail → probe → frame full loop works end-to-end on prod
- [ ] All 16 backend endpoints have a frontend caller
- [ ] All 10 error codes from the spec render with helpful copy + next action
- [ ] Mobile layouts checked on iPhone 13 viewport
- [ ] Brand audit pass (parchment/void/signal palette only, no third colour)
- [ ] Admin can edit per-user limits and the change reflects in `/me`
- [ ] Admin can hard-erase a Twin by name
- [ ] Stale Twin (>180d) shows refresh nudge

---

## 9. Out of scope (Phase 2)

- EU subject support (DPIA dependency)
- Bulk twin import (CSV)
- Twin-to-twin comparison view
- Email integration for sending the framed draft
- Slack notifications on probe replies
- Per-twin sharing / multi-user collaboration
