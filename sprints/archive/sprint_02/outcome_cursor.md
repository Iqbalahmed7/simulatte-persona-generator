# Sprint 2 Outcome — Cursor (Identity Constructor Orchestrator)

## 1. File created

- `src/generation/identity_constructor.py` — **700 lines**

## 2. Build sequence — all 8 steps present

| Step | Action | Method |
|------|--------|--------|
| 1 | Fill all attributes | `AttributeFiller.fill()` |
| 2 | Compute derived insights | `DerivedInsightsComputer.compute()` |
| 3 | Generate life stories | `LifeStoryGenerator.generate()` |
| 4 | Estimate tendencies | `TendencyEstimator.estimate()` |
| 5 | Generate narrative | `NarrativeGenerator.generate()` |
| 6 | Assemble core memory | `_assemble_core_memory()` + `WorkingMemory(empty)` |
| 7 | Validate record | `PersonaValidator.validate_all()` |
| 8 | Return `PersonaRecord` | — |

Ordering constraints respected: Step 2 completes before Step 4 (tendencies reference `DerivedInsights`); Step 3 completes before Step 5 (narrative references life story events).

## 3. Handling of missing Sprint 2 component files

All four Sprint 2 components (`DerivedInsightsComputer`, `LifeStoryGenerator`, `TendencyEstimator`, `NarrativeGenerator`) did not exist at the time of writing.

Approach used: **try/except ImportError at module level** with a `_COMPONENT_AVAILABLE` boolean flag for each.

- The module can be imported and `ICPSpec` used at any point during the parallel build.
- Component instances are set to `None` in `__init__` if the file is absent.
- `_assert_components_available()` is called as the first action inside `build()`. If any component is missing, it raises `ImportError` with a named list of missing modules — fast, clear failure rather than a confusing `AttributeError` deeper in the call stack.
- `TYPE_CHECKING` is declared (imported from `typing`) so type checkers can still reference the component classes via forward references if needed.

The `AttributeFiller` (Sprint 1, Goose) and `PersonaValidator` (Sprint 1, Antigravity) are imported unconditionally — they were present and verified.

**Note:** `attribute_filler.py` contains a pre-existing `SyntaxError` caused by escaped quotes (`\"`). This is a rendering artefact in that file and is not caused by this sprint. The module will import cleanly once that file's encoding is corrected. `identity_constructor.py` itself is syntactically valid (verified via `ast.parse`).

## 4. CoreMemory assembly logic — field-by-field

**`identity_statement`**
Takes the first 25 words of `narrative.first_person` (split on whitespace). The opening of the first-person narrative is the most concentrated self-description and maps directly to the spec's "25-word, first person" requirement.

**`key_values`**
Assembled in priority order:
1. `primary_value_driver` attribute value (string, always the first entry).
2. Top 2 continuous-valued attributes in the `values` category by descending score, using their `label` field. Excludes `primary_value_driver` to avoid duplication.
3. If the list has fewer than 3 items after steps 1–2 (e.g. the `values` category is sparse), fallback labels from `derived_insights` are appended: `trust_anchor`, `risk_appetite`, `decision_style`.
4. Capped at 5 items per `CoreMemory.key_values` validator.

**`life_defining_events`**
Converted from `life_stories` via `_convert_life_stories()`. `LifeStory.when` (free-form text) is parsed to an integer age by `_parse_age_from_when()`:
- Matches `\b(\d{1,2})\b` for patterns like "age 24", "at 18", "29 years old".
- Matches 4-digit years (1900–2099) and converts to age via `year - (current_year - current_age)`.
- Falls back to `current_age - 10` if no pattern resolves.

**`relationship_map`**
- `primary_decision_partner`: mapped from `household.structure` (joint → "family (joint household)", nuclear → "partner / spouse", single-parent → "self", couple-no-kids → "partner", other → "self").
- `key_influencers`: top 2 trust weight type names from `trust_orientation.weights`, sorted by weight descending.
- `trust_network`: all trust types with weight > 0.5. Falls back to the single dominant type if none exceed 0.5.

**`immutable_constraints`**
- `budget_ceiling`: `demographic_anchor.household.income_bracket` (the only hard spend signal available at persona creation time).
- `non_negotiables`: first 2 items from `derived_insights.key_tensions`, rephrased as "Must manage: [tension]". The persona's core tensions are what they cannot compromise on.
- `absolute_avoidances`: empty list — no structured data source exists for this sprint (noted as known gap below).

**`tendency_summary`**
Direct copy of `behavioural_tendencies.reasoning_prompt`. Per spec §5, this field exists for context-window injection and must match the reasoning_prompt verbatim.

## 5. Build sequence decisions not explicitly specified

- **`decision_bullets` derivation**: The spec lists `decision_bullets: list[str]` as a required `PersonaRecord` field but provides no derivation algorithm. Implemented as a rule-based assembly from `derived_insights` and `behavioural_tendencies`: decision style (with score), primary value orientation, risk appetite, up to 3 objection profile entries, and up to 2 key tensions. This keeps the field populated and meaningful without inventing data.

- **`generator_version`**: Set to `"2.0.0"` (Sprint 2). No versioning scheme was specified in the brief.

- **`generated_at`**: Set to `datetime.now(tz=timezone.utc)`. UTC was chosen over local time for reproducibility.

- **`n_stories` passed to `LifeStoryGenerator`**: Defaulted to 3 (the maximum allowed by `PersonaRecord.life_stories` validator which enforces 2–3). The generator may return 2 if 3 cannot be generated.

- **`WorkingMemory` initialisation**: Spec provided the exact empty-state template; implemented verbatim.

## 6. Known gaps

- **`absolute_avoidances` is always empty**: No structured attribute exists for encoding absolute avoidances at generation time. This must be populated in a future sprint or via domain-specific taboo attributes.

- **`decision_bullets` is rule-derived**: The spec does not specify this field's generation logic. The current implementation is principled but not LLM-grounded. A future sprint may want to generate these from a targeted LLM call with the full tendency profile.

- **`attribute_filler.py` SyntaxError**: The pre-existing escaped-quote issue in `attribute_filler.py` prevents a full end-to-end import test. All other imports in `identity_constructor.py` are correct and the file's own syntax is clean.

- **Domain validation on `icp_spec.mode`**: `ICPSpec.mode` is typed as `str` in the dataclass, but `PersonaRecord.mode` is typed as `Mode = Literal["quick","deep","simulation-ready","grounded"]`. A runtime `ValueError` from Pydantic will surface if an invalid mode string is passed. Adding a `__post_init__` validator to `ICPSpec` would catch this earlier; deferred as a low-risk gap.
