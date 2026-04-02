# SPRINT 2 OUTCOME — CODEX
**Role:** Narrative + Life Story Engineer
**Sprint:** 2 — Identity Constructor
**Status:** Complete

---

## 1. Files Created

| File | Lines |
|------|-------|
| `src/generation/life_story_generator.py` | 293 |
| `src/generation/narrative_generator.py` | 313 |
| **Total** | **606** |

---

## 2. Attribute Selection Logic for Life Story Prompts

The `_select_top_attributes()` function in `life_story_generator.py` returns exactly 10 attributes:

**8 anchors (always included, in anchor_order)**

| # | Name | Category | Why included |
|---|------|----------|--------------|
| 1 | `personality_type` | psychology | Primary decision orientation — shapes every story |
| 2 | `risk_tolerance` | psychology | Core psychological signal; determines story stakes |
| 3 | `trust_orientation_primary` | social | Shapes whose advice or validation matters in each story |
| 4 | `economic_constraint_level` | values | Sets the financial context for every event |
| 5 | `life_stage_priority` | identity | Makes ages and events plausible and life-stage coherent |
| 6 | `primary_value_driver` | values | The lens through which lasting_impact is framed |
| 7 | `social_orientation` | social | How much social context surrounds each event |
| 8 | `tension_seed` | identity | The recurring internal contradiction — must appear in at least one story |

**2 non-anchor extremes (selected dynamically)**

Selection rule: from all non-anchor continuous attributes, pick the two with the highest `|value − 0.5|`. These represent the persona's most psychologically distinctive signals and are thus most story-generative. Examples of what tends to surface:

- A persona with `brand_loyalty = 0.92` and `analysis_paralysis = 0.87` will produce those two — both will shape vivid, specific stories.
- A persona with uniformly moderate attributes still gets the two least-moderate non-anchors, ensuring the stories have texture even for centrist profiles.

---

## 3. Word Count Enforcement

Both narrative types use `_generate_with_word_count()`:

1. **First call** — LLM generates freely against the base system prompt.
2. **Word count check** — `_count_words()` splits on whitespace (conservative; matches how humans count).
3. **If within bounds** — return immediately.
4. **If outside bounds** — construct a retry prompt that:
   - Quotes the previous word count.
   - Explicitly states the min–max range.
   - Directs the LLM to go "shorter" or "longer" as appropriate.
5. **Accept retry unconditionally** — per brief spec: do not truncate. Truncation creates incoherent mid-sentence endings. Out-of-bounds retries are rare and the deviation is typically 5–15 words, which is tolerable.

Bounds:
- First-person: 100–150 words
- Third-person: 150–200 words

---

## 4. Prompt Design Decisions Not Explicitly Specified

### 4a. Shared profile block
The brief shows the same profile block in both narrative prompts. Extracted into `_profile_block()` so the two calls are always in sync — if derived_insights change, both narratives see the same update.

### 4b. Constraint note injected into system prompt
The brief says "narrative must not contradict attributes" but does not specify where to enforce this. A `_build_constraint_note()` addendum is injected into the system prompt (not the user prompt) so it acts as a persistent instruction. Currently fires only for `brand_loyalty` and `switching_propensity` at extreme values (> 0.8 or < 0.2), as these are the two attributes explicitly cited in §14A S14. Other attribute contradictions are deterred by the detailed profile block but not mechanically enforced — see known gaps.

### 4c. Life story: single call for all stories
Kept as specified (single call for coherence). The tradeoff is that if one story is weak, a re-roll regenerates all three — but this is better than three independent calls that may produce thematically clashing stories.

### 4d. `when` field normalisation
Spec accepts `"age NN"`, `"at NN"`, `"NN years old"`, or `YYYY`. The regex validates these; if the LLM returns something non-standard (e.g. `"in her late twenties"`), the value is preserved as-is rather than discarded — the story is still usable.

### 4e. Fallback story design
Fallbacks are age-anchored to `max(18, persona_age − 10 − i*3)` — ensures the fallback is realistic and offset per story to avoid identical `when` fields when two fallbacks are needed.

### 4f. Sequential narrative generation
The brief specifies "two calls — one per narrative type" but is silent on parallel vs. sequential. Sequential chosen for consistency; an `asyncio.gather()` refactor is trivial if latency matters.

---

## 5. Known Gaps and Failure Modes

**Gap 1: Constraint enforcement is shallow.** Only `brand_loyalty` and `switching_propensity` are mechanically checked. A persona with `risk_tolerance = 0.05` could still be called "adventurous" if the LLM ignores the profile block. A full constraint layer requires post-generation attribute-to-narrative consistency checking — not implemented here.

**Gap 2: `when` field not normalised to canonical form.** The validator confirms pattern match but does not normalise (e.g. convert `"at 28"` to `"age 28"`). Downstream consumers should treat `when` as display text, not a parseable integer.

**Gap 3: LLM client interface assumed to be Anthropic SDK.** Both generators call `llm_client.messages.create(model=..., max_tokens=..., system=..., messages=[...])`. If the integration uses a different client wrapper, the call sites in `_call_llm()` and `LifeStoryGenerator._call_and_parse()` need updating.

**Gap 4: Domain attribute extremes may win over more semantically relevant non-anchors.** The extreme-value selection is purely arithmetic. A domain attribute with value 0.95 will always win over a base-taxonomy attribute with value 0.85, even if the base attribute is more story-generative for this particular persona profile.

**Gap 5: Retry does not vary sampling parameters.** Both retry attempts use the same model and default temperature. If the model consistently undershoots word count, the retry will often produce similar length. A production fix would pass a higher temperature on retry.
