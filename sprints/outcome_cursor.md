# Sprint 20 — Domain Attribute Extractor: Outcome

## What was built

**File:** `src/taxonomy/domain_extractor.py`

Implements the MiroFish-style domain taxonomy extractor as specified in the Sprint 20 brief.

### Components

**`DomainAttribute` dataclass** — six fields as specified:
- `name`, `description`, `valid_range`, `example_values: list[str]`, `signal_count: int`, `extraction_source: str`
- Defaults: `example_values=[]`, `signal_count=0`, `extraction_source="corpus"`

**`extract_domain_attributes()` async function** — full logic:
1. Guards on `len(corpus) < 200`: logs a warning at WARNING level, returns `[]` without an LLM call.
2. Builds prompt using `_EXTRACTION_PROMPT` template (embedded verbatim from brief).
3. Signals block uses the first 100 corpus entries (or all if fewer than 100).
4. Anchor block: if `icp_spec` is provided and has `anchor_traits`, inserts a MUST-INCLUDE instruction line listing the trait names.
5. Calls `claude-sonnet-4-6` via `anthropic.AsyncAnthropic().messages.create()` using `api_call_with_retry` (same pattern as `decide.py`). Falls back to `llm_client.complete()` if a test double is provided.
6. JSON parse via `_parse_json_array()` — strips markdown fences, falls back to bracket-boundary extraction.
7. On parse failure: logs a warning and retries once. On second failure: logs an error and returns `[]`.
8. `extraction_source` set to `"icp_anchor"` if attribute name (lowercased) matches an anchor trait name (lowercased), else `"corpus"`.

**`extract_domain_attributes_sync()` wrapper** — uses `asyncio.run()` exactly as specified.

**Model constant:** `_SONNET_MODEL = "claude-sonnet-4-6"` (hardcoded).

## Deviations from brief

None. All requirements implemented as specified.

## Edge cases handled

- **Empty corpus / undersized corpus:** Returns `[]` with a warning — no LLM call made.
- **Malformed LLM JSON:** Retry once. If still malformed, returns `[]`.
- **Partial parse:** `_parse_json_array()` attempts bracket-boundary extraction before giving up, so partially-wrapped responses (e.g., prose before/after the array) are recovered.
- **Non-dict items in parsed array:** Skipped silently in `_assemble_attributes()`.
- **Missing or non-integer `signal_count` in LLM response:** Defaults to 0.
- **Missing `example_values` or non-list value:** Defaults to `[]`.
- **Case mismatch on anchor trait matching:** Both sides lowercased before comparison.
- **`icp_spec` without `anchor_traits`:** Handled — `anchor_block` becomes `""`.

## Interface assumptions about ICPSpec

- `icp_spec.domain: str` — used as the `{domain}` field in the prompt.
- `icp_spec.business_problem: str` — used as the `{business_problem}` field.
- `icp_spec.anchor_traits: list[str]` — used for MUST-INCLUDE block and `extraction_source` tagging. Defaults to `[]` if absent (matches the Pydantic model's `default_factory=list`).

No other ICPSpec fields are accessed.

## Verification

**Import check:**
```
python3 -c "from src.taxonomy.domain_extractor import DomainAttribute, extract_domain_attributes_sync; print('Import OK')"
Import OK
```

**Test suite:**
```
400 passed, 15 skipped in 2.16s
```

No regressions. All 400 tests pass.
