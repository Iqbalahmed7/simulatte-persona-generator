# Mind Sandbox — Build Plan

**Owner:** Iqbal · **Last updated:** 2026-04-26 · **Status:** locked, executing

The "Mind Sandbox" is the free public demo at **mind.simulatte.io** — a self-serve experience where a visitor can generate a deep persona, run a structured Litmus probe on their product, chat with the persona about it, and share the verdict. The sandbox is the lead magnet that books simulation calls.

---

## 1. Mission

Convert anonymous visitors into qualified booked calls by letting them experience the Simulatte simulation engine on a single persona, then showing them what 5,000 of those would look like.

**Success metric:** booked Calendly calls / unique users.
**Secondary:** email captures, social shares of probe results.

---

## 2. User flow (the locked experience)

```
Landing (mind.simulatte.io)
   ↓ [browse 5 exemplars freely, IP-rate-limited chat with each]
   ↓
"Simulate a person of your own →"
   ↓ [Email gate — Google sign-in OR Resend magic link]
   ↓
Generate persona form (brief + domain + optional PDF)
   ↓ [persona generation, ~15s, with status events]
   ↓
Persona page
   ├─ Genuineness score chip (already built ✅)
   ├─ "Talk to {name}" button (already built ✅)
   ├─ "Test a product with {name} →" (Phase 2)
   └─ Allowance counter: 1 persona, 3 probes, 5 chats per week
   ↓
Litmus probe form
   ↓ [category memory generation + 8 parallel Sonnet probes, ~20s]
   ↓
Probe results page
   ├─ Verdict card (purchase intent, claim believability, price WTP, etc.)
   ├─ Share button → public OG-imaged URL + tweet/LinkedIn/copy-link
   ├─ Continue chat with persona about THIS product
   └─ "Test this product with another persona" / "Book a simulation call →" Calendly
   ↓
Session summary email
   └─ Sent ~5 min after last activity, contains probe results + Calendly CTA
```

---

## 3. Phases — locked

### Phase 0: Brand & landing (RUNS IN PARALLEL with Phases 2–5)

The current `mind.simulatte.io` landing page works but feels like a dev test. Before public launch we need:

#### 0.1 The Mind logo / sub-brand mark

"The Mind" is a sub-brand of Simulatte. It needs its own mark that reads as a clear child of the Simulatte system — same parchment-on-void palette, same Barlow Condensed wordmark family, but a distinct symbol that signals "individual cognition" vs the Simulatte Engine mark which signals "system / population."

**Locked spec:**
- **Symbol:** A single "synapse" mark — a centred dot with two concentric arcs around it (think eye, neuron, listening). Drawn in 1.5px stroke at 32px reference size. Same hairline weight as the Engine mark so the brand family reads consistently.
- **Wordmark:** "Mind" in Barlow Condensed 800, parchment, set to the right of the symbol. Below in 9pt Martian Mono parchment-72: "by Simulatte"
- **Sizing:** square 32×32 SVG for favicon, 120×40 for header lockup, 240×80 for hero
- **File deliverables:**
  - `pilots/the-mind/web/public/mind-mark.svg` (symbol only, 32×32)
  - `pilots/the-mind/web/public/mind-lockup.svg` (symbol + wordmark, horizontal)
  - `pilots/the-mind/web/public/favicon.svg`
  - `pilots/the-mind/web/public/apple-touch-icon.png` (180×180)
  - `pilots/the-mind/web/public/og-image.png` (1200×630, default site OG card with the lockup centred)

#### 0.2 Landing page rebuild

Current landing is functional, not persuasive. Rebuild as a single-scroll narrative that walks the visitor from "what is this" → "see it work" → "try it yourself" → "book a call."

**Sections (locked):**

1. **Hero** (single screen, parchment-on-void, signal accent on one word)
   - Lockup top-left
   - "Talk to a person who **doesn't exist.**" — Barlow Condensed 800, clamp(48px, 6.5vw, 84px)
   - 1-line subtitle: "The Mind generates a behaviourally coherent synthetic person from a brief paragraph, then lets you simulate any decision they'd make."
   - Two CTAs: primary "Try it free →" (signal), secondary "See exemplar personas" (parchment outline)
   - Animated micro-detail bottom-right: a single Mind mark with the inner arc slowly pulsing

2. **Live exemplars strip** (5 cards, horizontal scroll on mobile)
   - Existing 5 personas (Arun, David, Linnea, Madison, Priya) as clickable cards with portraits + 1-line description
   - Each opens existing PersonaDrawer
   - Header: "Five people we've already built."

3. **The Litmus probe — animated demo**
   - Split layout: left side product brief example (mock), right side animated probe results revealing one card at a time
   - Loop: brief → loading → 8 question results stream in → "purchase intent 7.4/10" lands
   - Header: "Test any product against any person, in 30 seconds."
   - CTA: "Run your own probe →" (signal)

4. **How it works** (3-step diagram)
   - Step 1: "Describe the person" → micro illustration of a textarea
   - Step 2: "We anchor them in real demographic data" → micro illustration of a Census-style chart
   - Step 3: "Then probe their decisions" → micro illustration of the Litmus cards
   - Quote/credit: "Built on the same engine that powers Simulatte's 5,000-agent population simulations."

5. **Genuineness — the trust strip**
   - Headline: "Every persona is graded."
   - Three-column explainer of the 4 genuineness components, each with a tiny example bar
   - Reassurance copy: "We tell you when our confidence is low."

6. **Social proof / shared probes** (when live, otherwise hide)
   - Wall of recent shared probe cards (auto-fed from `shares` table, public only)
   - Header: "What other people are testing."

7. **Closing CTA** (full-bleed, void background)
   - "Stop guessing what your customers think." (Barlow Condensed 800, 60pt)
   - "Simulate them." (signal green word)
   - Big primary button: "Try The Mind free →"
   - Below: "Or book a call to test against 5,000 personas." → Calendly link
   - Footer: lockup + "Simulatte / The Mind / Confidential"

**Build constraints:**
- Single Next.js page at `app/page.tsx` (rebuild current)
- All copy on-brand (no exclamation marks, no banned words from simulatte-brand skill)
- Mobile-responsive — every section must work at 375px width
- Total page weight under 200KB JS, under 500KB total
- Test on real Lighthouse: target 95+ Performance, 100 Accessibility

#### 0.3 Owner & sequencing

- The Mind logo + landing page are **a single design task** assigned to a Sonnet agent invoking the simulatte-brand skill
- Runs IN PARALLEL with Phases 2–4 (no dependency)
- Must be merged before Phase 5 launch QA

---

### Phase 1: Chat + Genuineness rating ✅ DONE
Already implemented and verified.

**Backend changes:**
- `POST /generated/{id}/chat` — Sonnet-as-persona chat endpoint
- `_compute_quality_assessment()` — 4-component score on demographic grounding, behavioural consistency, narrative depth, psychological completeness
- `quality_assessment` block injected before persist; backfilled in `GET /generated/{id}` for existing personas

**Frontend changes:**
- `chatWithGeneratedPersona()` API helper
- `GenuinenessChip.tsx` — collapsible chip with score, components, sources
- `app/persona/[id]/page.tsx` — chip + "Talk to {firstName}" CTA
- `app/persona/[id]/chat/page.tsx` — chat page

**Ships:** as a single git push → Railway + Vercel auto-deploy.

---

### Phase 2: Litmus Probe (THE killer feature)

The probe is what books calls. Without it, the sandbox is a toy.

#### 2.1 Probe questions — locked at 8, organised by intent

Four sections, two questions each:

**REACTION** — emotional, gut-level
1. **Purchase Intent** — would you buy this? (1-10 + 1-2 sentence rationale)
2. **First Impression** — what's the immediate emotion? (3-5 adjectives + a feeling sentence)

**BELIEF** — rational, claim-level
3. **Claim Believability** — for each claim (1-5, max), 1-10 + comment
4. **Differentiation** — does this feel meaningfully different from {alternatives they know}? (1-10 + comment)

**FRICTION** — what stops them
5. **Top Objection** — strongest reason NOT to buy (1-2 sentences)
6. **Trust Signals Needed** — what would make them confident? (3-5 bullets)

**COMMITMENT** — what they'd actually do
7. **Price Willingness** — WTP estimate + reaction to listed price (range + commentary)
8. **Word of Mouth** — likelihood to recommend (1-10) + what they'd actually say to a friend

#### 2.2 Backend implementation

**New endpoint:** `POST /generated/{persona_id}/probe`

**Request body:**
```json
{
  "product_name": "string",
  "category": "string",
  "description": "string",
  "claims": ["string", ...],  // up to 5
  "price": "string",  // e.g. "₹8,000" or "$49/mo"
  "image_url": "string?"  // optional hero image
}
```

**Pipeline (target ~20s end-to-end):**

1. **Category memory generation** (1 Haiku call, ~5s)
   - Cache key: `hash(persona_id + product_brief)`
   - Prompt: given persona's anchor + product brief, generate 8-12 first-person memories about the category, competitors, channels, budget, trust signals — see "Memory shape" below
   - Persist to `pilots/the-mind/probes/{persona_id}/memory_{cache_key}.json`

2. **Eight parallel Sonnet probes** (8 calls in parallel, ~10s)
   - System prompt assembled from: persona narrative + memory + product brief + structured task description
   - Each call returns JSON matching the question's response schema
   - Use prompt caching on the system prompt (huge cost savings since 8 calls share most of it)

3. **Persist probe** to `pilots/the-mind/probes/{persona_id}/{probe_id}.json`

4. **Return aggregate JSON** with all 8 question responses.

**Memory shape** (`memory_{cache_key}.json`):
```json
{
  "purchase_history": ["I bought a OnePlus 11 last year for ₹56K because..."],
  "competitor_awareness": ["My friend Aman uses Boat Airdopes and says..."],
  "channel_preferences": ["I usually buy electronics on Flipkart Big Billion Days..."],
  "budget_anchors": ["₹5K is impulse, ₹15K needs a week of thinking..."],
  "trust_signals": ["I read MKBHD reviews + 4-5 Reddit threads before buying..."],
  "category_attitudes": ["I think wearables are 70% gimmick..."]
}
```

**Endpoints:**
- `POST /generated/{id}/probe` — run probe (auth-gated, allowance-checked)
- `GET /probes/{probe_id}` — fetch probe (PUBLIC, no auth, used by share page)
- `GET /probes/{probe_id}/og` — OG image for social sharing (returns PNG)
- `GET /generated/{id}/probes` — list probes for a persona (auth-gated)

#### 2.3 Frontend implementation

**Routes:**
- `/persona/{id}/probe` — product brief form
- `/persona/{id}/probe/{probe_id}` — results page (auth-gated until shared)
- `/probe/{probe_id}` — public share page (no auth, OG-tagged for previews)

**Form page** — clean form, brand-compliant, with character limits and inline validation.

**Results page** — single scrollable card divided into 4 sections (Reaction / Belief / Friction / Commitment), each with the 2 question results. Bottom-of-page actions:
- Continue chat with persona about this product
- Test with another persona
- Share button (modal: Twitter, LinkedIn, copy link)
- Book a simulation call → Calendly

**Public share page** — same as results page but read-only, no allowance counter, soft CTA "Generate your own persona →"

#### 2.4 Cost (per probe)

| Item | Cost |
|---|---|
| Category memory (Haiku) | $0.03 |
| 8 Sonnet probes (with prompt caching) | $0.06 |
| **Total per probe** | **~$0.09** |

---

### Phase 3: Auth + Allowance + Email

#### 3.1 Auth — Google + Resend magic link

**Stack:** NextAuth.js (Auth.js v5) with two providers:
- **GoogleProvider** — re-use existing Google client ID/secret (already set up per user)
- **EmailProvider** — Resend SMTP, magic link

Why both: Google is one-tap, magic link captures the rest. Resend is already in our stack for transactional emails (so we'll use it for the auth + summary emails too).

**Session storage:** Postgres adapter on the same DB.

**Database:** add Postgres add-on to the Railway project (`$5/mo`). Use Prisma as the ORM.

**Tables:**
```
users:
  id, email, name, image, google_id, created_at, last_login_at

allowances:
  user_id (PK), week_starting,
  personas_used, personas_limit (default 1),
  probes_used, probes_limit (default 3),
  chats_used, chats_limit (default 5),
  resets_at

events:
  id, user_id, type, ref_id, created_at  -- audit log of every action

shares:
  probe_id, slug, created_at, view_count
```

#### 3.2 Allowance — locked

Per user, per ISO-week (resets Mon 00:00 UTC):
- **1 persona generation**
- **3 Litmus probes** (across all personas they've created)
- **5 chat messages** (across all personas)

After cap: hard wall, modal "you've used your weekly allowance — book a call to test against the population".

#### 3.3 Middleware

FastAPI dependency that:
1. Validates JWT from NextAuth session cookie
2. Loads user from Postgres
3. Checks allowance for the requested action
4. Increments counter on success
5. Returns 402 with allowance details if over

#### 3.4 Session summary email — locked

**Trigger:** 5 min after last activity, OR immediately on probe completion (whichever first).

**Provider:** Resend (already in stack).

**Subject:** `Your simulation with {persona_name} — purchase intent {score}/10`

**HTML body** (brand-styled, parchment-on-void):
- Hero: persona portrait + name + age + city
- Genuineness score
- Probe summary card (8 questions, condensed)
- "What this means for {product}" — auto-generated 2-3 sentence interpretation by Haiku
- Persistent permalink to the probe results page
- "Test this against 5,000 personas →" → Calendly
- Footer: how the persona was generated, sources used, unsubscribe

**Reference design:** Litmus uses a similar pattern in its existing email outputs — see `pilots/the-mind/api/main.py` and the Litmus repo's email templates if needed.

---

### Phase 4: Share & UGC card

#### 4.1 What gets shared

A `1200×630` PNG card per probe, generated on demand and cached on disk.

**Layout (locked):**
```
┌────────────────────────────────────────────────────────┐
│                                                        │
│  ┌──────────┐                                          │
│  │ portrait │   {Persona name}, {age}                  │
│  │          │   {city}, {country}                      │
│  │          │                                          │
│  └──────────┘   "tested {Product Name}"                │
│                                                        │
│  ────────────────────────────────────────              │
│                                                        │
│   PURCHASE INTENT      PRICE WILLINGNESS               │
│        7/10                  ₹6,500                    │
│                                                        │
│   "Quote pulled from Top Objection or Reaction..."     │
│                                                        │
│  ────────────────────────────────────────              │
│  Tested on Simulatte · mind.simulatte.io               │
└────────────────────────────────────────────────────────┘
```

#### 4.2 Tech

- **`@vercel/og`** for runtime image generation in the Next.js app (already a dep).
- **Cache** generated PNGs in `pilots/the-mind/og_cache/{probe_id}.png` for 7 days.
- **OG meta tags** on `/probe/{probe_id}` so LinkedIn/Twitter/iMessage previews render the card automatically.

#### 4.3 Share UI

Modal triggered by Share button on probe results page:

```
┌─ Share this verdict ────────────────┐
│                                     │
│  [og card preview]                  │
│                                     │
│  [ Tweet ]  [ LinkedIn ]  [ Copy ]  │
│                                     │
│  Public link:                       │
│  mind.simulatte.io/probe/abc123     │
│                                     │
└─────────────────────────────────────┘
```

Pre-filled tweet text:
> "I asked an AI persona of {name}, a {age}-year-old {occupation} from {city}, what they'd think of {product}. Verdict: {purchase_intent}/10. Try it on @SimulatteAI: {url}"

Pre-filled LinkedIn:
> "Just ran a Simulatte simulation: tested {product} with {name}, a synthetic {persona description}. Purchase intent: {score}/10. Top objection: {objection}. Worth thinking about. Try it: {url}"

---

### Phase 5: Polish & launch

#### 5.1 Anti-abuse
- **Cloudflare Turnstile** on `/generate-persona` and `/probe` (free, blocks 95% of bots)
- **Per-user rate limit:** 10 requests/min via Upstash Ratelimit (or Postgres-backed)
- **Brief length cap:** 5,000 chars
- **Email verification required** before any generation

#### 5.2 Observability
- Log every action to `events` table with `user_id`, `type`, timing
- Daily cron: aggregate stats (signups, generations, probes, shares, calendly clicks)
- Dashboard at `/admin` (gated by hard-coded admin email)

#### 5.3 Storage hygiene
- **Generated personas TTL:** 30 days for free-tier users (cron job)
- **Probe cache TTL:** 30 days
- **OG image cache TTL:** 7 days
- **Memory cache TTL:** 30 days

#### 5.4 Empty / error states
- "You've used your weekly allowance — book a call to scale this up" modal
- "We're at capacity, try again in a moment" graceful 503
- "Generation timed out" with retry button
- "We couldn't read your PDF" with manual entry fallback

#### 5.5 Launch checklist
- [ ] Postgres provisioned + migrations run
- [ ] Auth.js routes mounted
- [ ] Resend domain verified, magic link template tested
- [ ] Calendly link in 3 places (probe results, summary email, allowance-exceeded modal)
- [ ] OG meta on `/probe/{id}` verified via OpenGraph debugger
- [ ] Mobile-responsive (especially the probe results card and share modal)
- [ ] Privacy / terms pages
- [ ] Cookie banner (Google sign-in needs it)
- [ ] Final QA: end-to-end flow, every error state, every email
- [ ] Soft launch to 10 friendlies, watch logs, fix bugs
- [ ] Public launch: LinkedIn post + 5 invited probes pre-shared

---

## 4. Cost model

Per anonymous-then-email-converted user, full happy path:

| Step | Cost |
|---|---|
| Persona generation (Haiku ×3) | $0.07 |
| Portrait (gpt-image-1) | $0.05 |
| Quality assessment (compute, no LLM) | $0.00 |
| Litmus probe — category memory + 8 Sonnet calls | $0.09 |
| 5 chat follow-ups (Sonnet, prompt-cached) | $0.05 |
| OG card generation | $0.00 (Vercel free) |
| Summary email (Haiku for interpretation + Resend) | $0.01 |
| **Total per converted user** | **~$0.27** |

**Break-even on a $1,500 simulation call:**
At a 3% free→call conversion + 30% close rate, every $1 spent on free tier returns ~$300 in pipeline. Math works as long as we stay under ~$1/user fully loaded.

**Monthly burn projections:**
- 1,000 free users/mo: $270 Anthropic + $5 Postgres + $5 Resend + $20 Vercel + $20 Railway = **~$320/mo**
- 10,000 free users/mo: $2,700 + $25 + $20 + $50 + $50 = **~$2,850/mo**

Both manageable until product-market signal.

---

## 5. Tech stack — locked

| Layer | Tech | Notes |
|---|---|---|
| Frontend | Next.js 14 app router, TypeScript, Tailwind | Already in place |
| Backend | FastAPI on Railway | Already in place |
| Database | Postgres on Railway, Prisma ORM | NEW — provision in Phase 3 |
| Auth | NextAuth.js v5 (Auth.js), Google + Resend magic link | NEW |
| Email | Resend | NEW |
| LLM | Anthropic SDK — Haiku for memory/extraction, Sonnet for chat/probes | Already in place |
| OG images | @vercel/og | NEW |
| Captcha | Cloudflare Turnstile | NEW |
| Rate limit | Upstash Ratelimit (Redis) | NEW |
| Hosting | Vercel (frontend) + Railway (backend) | Already in place |

---

## 6. Sprint plan

| Sprint | Days | Owner | Deliverable | Status |
|---|---|---|---|---|
| 0 — Mind logo + landing rebuild | 1.5 | Sonnet (parallel) | new SVG marks + favicon + redesigned landing page with 7 sections | parallel |
| 1 — Chat + Genuineness | 0.5 | this assistant | already built | ✅ COMMITTING NOW |
| 2 — Litmus Probe (8-question) | 1.5 | Sonnet agent | working probe end-to-end with memory generation, 8 parallel Sonnet calls, results page, persistence | NEXT |
| 3a — Auth + Postgres + Allowance | 1.0 | Sonnet agent | Auth.js with Google + Resend, Postgres tables via Prisma, middleware enforcing weekly allowances | |
| 3b — Session summary email | 0.5 | Sonnet agent | Resend HTML template, trigger on probe completion, brand-styled | |
| 4 — Share card + UGC | 0.5 | Sonnet agent | OG image route, share modal, public probe page, OG meta tags | |
| 5 — Polish + launch | 1.0 | Iqbal + assistant | Turnstile, rate limit, TTLs, admin dashboard, QA, launch | |

**Total: ~5 working days** from Sprint 2 start to public launch.

---

## 7. Open decisions (none blocking — defaults locked)

- ~~Email-gated vs anonymous?~~ → Email-gated, both Google and magic link
- ~~Sonnet or Haiku for chat?~~ → Sonnet
- ~~Calendly URL?~~ → https://calendly.com/iqbal-simulatte
- ~~Probe question count?~~ → 8 (Reaction/Belief/Friction/Commitment, 2 each)
- ~~Allowance ratios?~~ → 1 persona / 3 probes / 5 chats per week
- ~~Memory generation: pre-built vs JIT?~~ → JIT at probe time, cached by `(persona, product)`
- ~~Auth provider?~~ → Auth.js with Google + Resend magic link

---

## 8. Out of scope (deliberately)

These are NOT in this plan — flag for future:
- Multi-persona probe (test one product against N personas in a single run) — wait for v2
- Population-scale simulation in the sandbox — that's the paid product, don't give it away
- Persona editing (user tweaks attributes after generation) — adds complexity, defer
- PDF export of probe results — nice-to-have, defer
- Slack / Notion integrations — defer
- Anonymous tier (no email) — chosen against
- Free portrait regeneration — pay attention to cost first

---

## 9. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Bot abuse → Anthropic bill spike | Medium | High | Turnstile + email verification + per-user rate limit + daily cost cap on Anthropic key |
| Litmus probe quality is inconsistent | Medium | High | Prompt caching on system prompt + structured output schemas + 50-sample QA before launch |
| Calendly conversion is low | High | Medium | A/B test CTA copy + measure share-rate as secondary signal |
| Email deliverability issues (magic link land in spam) | Low | High | Resend domain verification + DKIM/SPF/DMARC + manual spam-folder check during launch QA |
| User finishes flow but doesn't book → no email captured | Already mitigated | — | Email gate is at persona-generation, not at probe |
| Generated persona attributes are empty (current state) | Already known | Low | Genuineness score signals this honestly; doesn't block the experience |

---

## 10. Success criteria

**Week 1 post-launch:**
- 100+ unique signups
- 50+ probes run
- 5+ shared probes (organic)
- 5+ Calendly bookings

**Month 1 post-launch:**
- 1,000+ unique signups
- 500+ probes run
- 50+ shared probes
- 30+ Calendly bookings
- 5+ closed deals (1% close rate)

If these metrics aren't met, revisit either traffic acquisition or conversion design before scaling spend.
