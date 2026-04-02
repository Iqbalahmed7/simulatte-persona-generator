# What Works — Proven Patterns

These are things we tested and confirmed work. Not theory — demonstrated in the LittleJoys pilot.

---

## Architecture

**Memory-backed perception produces 607% more persona differentiation than generic LLM prompting.**
Confirmed by A/B test, Sprint 29. The naive approach collapses all personas to nearly identical scores. The memory-backed approach produces genuine behavioural variance across personas.

**5-step chain-of-thought in decide() produces coherent, traceable reasoning.**
The explicit steps (gut → information → constraints → social → final) prevent the model from jumping to a conclusion without considering the persona's specific constraints. The reasoning trace is readable and auditable.

**Reflection genuinely changes downstream decisions.**
Personas who have reflected on accumulated experiences reason differently in decide() than personas who haven't. The higher-order insights get stored as high-salience memories and surface in retrieval.

**Cumulative salience threshold of 5.0 is the right trigger for reflection.**
Below 5.0, there aren't enough significant experiences to synthesise. Above 5.0, reflection is warranted. This was validated against the LittleJoys stimulus set where S2 (WOM) + S4 (pediatrician) cross the threshold.

---

## Persona Design

**Psychological anti-correlations are real and must be enforced.**
Left unconstrained, Gaussian sampling produces personas with contradictory psychologies (high risk tolerance + high loss aversion). In Sprint 28, 17.5% of personas had hard violations. In Sprint 29, post-generation enforcement reduced this to near-zero.

**The 5 most important constraint pairs for Indian consumer personas:**
1. risk_tolerance ↔ loss_aversion (cannot both exceed 0.75)
2. analysis_paralysis ↔ decision_speed (cannot both exceed 0.8)
3. supplement_necessity ↔ food_first_belief (cannot both be extreme)
4. impulse_purchase ↔ analysis_paralysis (cannot both be extreme)
5. single_parent family structure → mother_final decision rights

**Work hours must be derived from career attributes, not defaulted.**
The schema default of 0 caused 70 CAT2-R009 violations in Sprint 28. Work hours should be generated as: base(38) + career_ambition(0-12) + income_proxy(0-5), capped at 55.

**Persona IDs should be human-readable.**
Format: `{FirstName}-{City}-{Mom/Dad}-{Age}` e.g. `Priya-Delhi-Mom-32`. Makes reading batch output intuitive and allows quick mental grouping.

**Narratives and first-person summaries are load-bearing, not decorative.**
They are used as core memory in the decide() prompt. Without them, the persona has no identity anchor and the reasoning trace becomes generic.

---

## Simulation Design

**Stimulus sequence matters — order affects outcomes.**
The 5-stimulus sequence works because it mirrors a realistic consumer journey: awareness (ad) → social proof (WOM) → price signal (discount) → authority (doctor) → competitive context (school group). Running stimuli out of order changes the memory state and can change decisions.

**Pediatrician recommendation is the most powerful stimulus for child nutrition.**
In the LittleJoys pilot, 42% of personas cited pediatrician recommendation as their primary purchase driver — outweighing advertising, peer WOM, and price combined. This is a category-specific finding but the principle generalises: identify the highest-trust source in your category and make it one of your 5 stimuli.

**WTP clusters near the ask price in a well-designed population.**
Median WTP of Rs 649 exactly matched the listed price of Rs 649. This is a validation signal — if the population were miscalibrated, WTP would be systematically higher or lower.

**The "research more" segment is a retargeting signal, not a rejection.**
15.8% of personas chose "research more" — these are interested, not hostile. Their objections were specific and addressable (want to verify claims, want to see more reviews). These personas are one targeted touchpoint away from buying.

---

## Multi-Agent Orchestration

**Run Cursor + Codex + Goose in parallel; gate OpenCode and Antigravity on all three.**
This is the optimal sprint structure. The parallel wave takes 4-5 hours. The gate prevents test-writing before the implementation is stable.

**Always assign file ownership explicitly and document it.**
The Sprint 28 conflict where Codex and Goose both wrote `__init__.py` lost exports. Rule: one engineer, one file. If multiple engineers need to touch the same file, assign it to one and have the other add a coordination note.

**Antigravity should run full pytest before signalling done.**
In Sprint 29, Antigravity added a `pytest_plugins` line that broke the entire test runner due to a missing dep in an unrelated file. The fix: run `pytest --collect-only` before signalling done to catch import errors.

**Codex is the most reliable engineer for Python correctness.**
Codex runs ruff and py_compile before signalling done, produces clean output, no artefacts. Use Codex for any file that is algorithmically critical.

**Goose has a persistent HTML entity bug.**
Every sprint, Goose's output contains `&#39;` and `&lt;` inside f-strings and string literals. The bug is in the serialisation layer between the model and the file system. An `import` check passes because Python doesn't execute function bodies at import time. Always test with `python3 -c "from scripts.X import main; main.__doc__"` or actually call a function.

---

## Schema Design

**Always read the schema before writing briefs.**
Sprint 28 briefs contained 4 wrong field paths written from memory:
- `household_structure` → correct: `family_structure`
- `daily_routine.digital_payment_comfort` → correct: `media.digital_payment_comfort`
- `"single-parent"` → correct: `"single_parent"` (underscore)
- `demographics.parent_name` → correct: `persona.id`

Rule: read `schema.py` before writing any brief that references field paths.

**Test schema coherence with a dedicated test file.**
`tests/test_schema_coherence.py` formalises all known field locations as assertions. If the schema changes, this file fails fast — before any production code runs against the wrong path.
