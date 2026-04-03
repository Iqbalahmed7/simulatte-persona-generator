# SPRINT 20 BRIEF — CURSOR
**Role:** Domain Extractor
**Sprint:** 20 — MiroFish Domain Taxonomy Extraction
**Spec ref:** Master Spec §6 (Layer 2 domain extension, MiroFish adoption), §4 (Grounded Mode pipeline)
**Previous rating:** 20/20

---

## Context

The master spec adopts the MiroFish principle for domain taxonomy extension: when domain data is provided, the system should automatically extract a domain-specific attribute set from that data — not rely on hand-authored templates. This is the last in-scope v1 gap.

Your job is the extractor: the LLM call that reads the domain data corpus and produces a list of `DomainAttribute` objects.

**Dependency note:** OpenCode writes `ICPSpec` and `icp_spec_parser.py` in parallel. Write against the interface spec below — import it with `from src.schema.icp_spec import ICPSpec` once it exists.

---

## File: `src/taxonomy/domain_extractor.py`

```python
"""src/taxonomy/domain_extractor.py

MiroFish-style domain attribute extraction.

Takes a raw signal corpus (reviews, forum posts, transcripts, ICP spec)
and uses an LLM to extract the domain-specific attribute set (Layer 2).

Spec ref: Master Spec §6 — "Seed-document-to-ontology via LLM: Adopt the principle,
modify the scope. Used for domain taxonomy extension (Layer 2) only."
"""
```

### `DomainAttribute` dataclass

```python
@dataclass
class DomainAttribute:
    name: str              # snake_case — e.g. "pediatrician_trust"
    description: str       # 1-2 sentences defining what this attribute captures
    valid_range: str       # "0.0-1.0" | "low|medium|high" | "categorical: [a, b, c]"
    example_values: list[str]  # 3 concrete examples from the corpus
    signal_count: int      # how many signals from the corpus mention this attribute
    extraction_source: str # "corpus" | "icp_anchor" | "template_fallback"
```

### `extract_domain_attributes()` function

**Signature:**
```python
async def extract_domain_attributes(
    corpus: list[str],
    icp_spec: "ICPSpec | None" = None,
    llm_client=None,
    max_attributes: int = 80,
) -> list[DomainAttribute]:
```

**Logic:**
1. If `len(corpus) < 200` — log a warning, set `extraction_source = "template_fallback"` for all results, return an empty list (caller handles template fallback). Do NOT crash.
2. Build a prompt that:
   - Provides the first 100 signals (or all if < 100) as context
   - If `icp_spec` is provided, includes `icp_spec.anchor_traits` as "must-include" attributes
   - Asks the LLM to identify up to `max_attributes` distinct attributes that differentiate how people in this domain make decisions
   - Instructs the LLM to respond in JSON: `[{"name": ..., "description": ..., "valid_range": ..., "example_values": [...], "signal_count": ...}]`
3. Call Sonnet (`claude-sonnet-4-6`), parse the JSON response
4. For each parsed attribute: set `extraction_source = "icp_anchor"` if the attribute name matches an `icp_spec.anchor_traits` entry, else `"corpus"`
5. Return the list of `DomainAttribute` objects

**Fallback:** If the LLM response is malformed JSON, retry once. If still malformed, log the error and return whatever was successfully parsed.

**Sync wrapper** (for non-async callers):
```python
def extract_domain_attributes_sync(
    corpus: list[str],
    icp_spec=None,
    llm_client=None,
    max_attributes: int = 80,
) -> list[DomainAttribute]:
    return asyncio.run(extract_domain_attributes(corpus, icp_spec, llm_client, max_attributes))
```

### LLM prompt template

```python
_EXTRACTION_PROMPT = """
You are analyzing consumer research data for a domain taxonomy extraction task.

Domain: {domain}
Business problem: {business_problem}

Here is a sample of {signal_count} consumer signals from this domain:
{signals_block}

{anchor_block}

Your task: Identify up to {max_attributes} distinct PSYCHOLOGICAL and BEHAVIOURAL attributes
that differentiate how people in this domain make decisions. Focus on attributes that:
- Directly affect purchase, usage, or loyalty decisions
- Vary meaningfully across consumers (not universal)
- Can be scored on a 0.0-1.0 scale or as a categorical value

DO NOT include demographic attributes (age, income, location) — those are handled separately.
DO NOT include product features — these are consumer psychology attributes.

Return a JSON array only (no other text):
[
  {{
    "name": "snake_case_attribute_name",
    "description": "1-2 sentences defining what this attribute captures in this domain",
    "valid_range": "0.0-1.0 OR low|medium|high OR categorical: [option1, option2, ...]",
    "example_values": ["example showing low value", "example showing mid value", "example showing high value"],
    "signal_count": <integer: how many of the provided signals mention or imply this attribute>
  }},
  ...
]
"""
```

---

## Constraints

- Use `claude-sonnet-4-6` for extraction (spec §4: "Taxonomy Engine — Sonnet, one-time per domain")
- Never call the LLM in `attribute_ranker.py`, `domain_merger.py`, or `icp_spec_parser.py` — those are deterministic
- The `extraction_source` field is mandatory on every attribute (constitution P10 — traceability)
- Attributes must not include demographics — enforce by adding explicit exclusion to the prompt

---

## Outcome file

When your code is done, write `sprints/outcome_cursor.md`:
- What you built and any deviations from the spec
- Edge cases you found
- Any interface assumptions you made about ICPSpec
- Confirmation that you ran the unit tests and they pass
