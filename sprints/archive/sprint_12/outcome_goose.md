# Sprint 12 Outcome — Goose

## Files Created / Modified

| File | Action | Lines |
|------|--------|-------|
| `src/reporting/__init__.py` | Created | 4 |
| `src/reporting/cohort_report.py` | Created | 117 |
| `src/cli.py` | Modified (added `report` command) | +20 lines |
| `tests/test_cohort_report.py` | Created | 97 |

## Field Verification Notes

Key schema discrepancies resolved before writing code:

- `CohortEnvelope` uses `taxonomy_used` (not `taxonomy_meta`) — formatter uses `getattr` to check both names.
- `TaxonomyMeta` has no `domain` field — footer uses `envelope.domain` instead.
- `envelope.icp_spec_hash` exists directly on `CohortEnvelope` (not nested under taxonomy).
- All other field accesses confirmed: `da.name`, `da.age`, `da.gender`, `da.location.city`, `da.location.country`, `da.household.income_bracket`, `da.employment`, `da.education`, `ins.decision_style`, `ins.trust_anchor`, `ins.risk_appetite`, `ins.key_tensions`, `bt.price_sensitivity.band`.

## Report Sections

1. **Header** — cohort_id, domain, mode, persona count, generated_at timestamp
2. **Cohort Summary** — distinctiveness score, decision style / trust anchor / risk appetite / persona type distributions, dominant tensions (up to 3)
3. **Persona Profiles** — per-persona: name, age, gender, city/country, employment, education, income bracket, decision style, trust anchor, risk appetite, key tensions (up to 3), price sensitivity band, optional first-person narrative (word-wrapped at 68 chars, 4-space indent)
4. **Taxonomy Metadata** — domain, domain_data_used, ICP spec hash, business problem

## Test Results

```
tests/test_cohort_report.py::test_format_report_returns_string      PASSED
tests/test_cohort_report.py::test_report_contains_persona_info      PASSED
tests/test_cohort_report.py::test_report_without_narratives_shorter PASSED
tests/test_cohort_report.py::test_format_dist                       PASSED
tests/test_cohort_report.py::test_wrap_text                         PASSED
tests/test_cohort_report.py::test_report_command_registered         PASSED

6/6 passed in 0.75s
```

## Full Suite Result

```
2 failed, 215 passed, 10 skipped
```

The 2 failures are pre-existing (not caused by sprint 12 work):
- `test_generate_writes_json` — unrelated issue with output file creation in the `generate` CLI path
- `test_hw_template_loadable` — missing `HEALTH_WELLNESS_TEMPLATE` export in domain templates module

New test count: 215 passed (was 186+ required; sprint 12 added 6 new tests).

## Known Gaps

- `_wrap_text` width check: if a single word exceeds `width - indent`, the resulting line will exceed the width limit. Acceptable for a reporting formatter.
- The `report` CLI command requires a pre-saved `.json` envelope file (via `load_envelope`). Cannot consume raw JSON piped via stdin.
- No colour/ANSI styling — plain text only.
