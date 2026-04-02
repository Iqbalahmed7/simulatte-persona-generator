# SPRINT 2 BRIEF — CURSOR
**Role:** Identity Constructor Orchestrator
**Sprint:** 2 — Identity Constructor
**Spec check:** Master Spec §6 (progressive conditioning, filling order), §5 (life_stories, narrative, derived_insights schemas)
**Previous rating:** 19/20 — Excellent schema work. Two minor validators missing (patched). No spec drift.

---

## Your Job This Sprint

You own `identity_constructor.py` — the orchestration layer that runs the full identity build sequence for a single persona. Every other Sprint 2 engineer writes a component; you wire them together in the correct order and return a complete `PersonaRecord`.

One file.

---

## File: `src/generation/identity_constructor.py`

### What It Does

Takes a `DemographicAnchor` and an `ICPSpec` (defined below), calls each Sprint 2 component in the correct sequence, and returns a fully populated `PersonaRecord`. This is the single entry point for persona generation.

### Build Sequence (Strict Order)

```
Step 1:  Fill all attributes          → AttributeFiller.fill()
Step 2:  Compute derived insights     → DerivedInsightsComputer.compute()
Step 3:  Generate life stories        → LifeStoryGenerator.generate()
Step 4:  Estimate tendencies          → TendencyEstimator.estimate()
Step 5:  Generate narrative           → NarrativeGenerator.generate()
Step 6:  Assemble core memory         → assemble_core_memory()
Step 7:  Validate the record          → PersonaValidator.validate_all()
Step 8:  Return PersonaRecord
```

Steps 1–6 must run in this exact order. Step 2 (derived insights) must complete before Step 4 (tendency estimation), because tendencies reference derived insight values. Step 3 (life stories) must complete before Step 5 (narrative), because narrative references life story events.

### Interface

```python
from src.schema.persona import PersonaRecord, DemographicAnchor
from src.taxonomy.domain_templates.template_loader import load_taxonomy, get_domain_attributes
from src.generation.attribute_filler import AttributeFiller
from src.generation.derived_insights import DerivedInsightsComputer
from src.generation.life_story_generator import LifeStoryGenerator
from src.generation.tendency_estimator import TendencyEstimator
from src.generation.narrative_generator import NarrativeGenerator
from src.schema.validators import PersonaValidator
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ICPSpec:
    """User-provided specification for persona generation."""
    domain: str                              # e.g., "cpg", "saas"
    mode: str                                # "quick" | "deep" | "simulation-ready" | "grounded"
    anchor_overrides: dict[str, Any] = field(default_factory=dict)  # forced attribute values
    persona_id_prefix: str = "default"      # used in persona_id: pg-[prefix]-[NNN]
    persona_index: int = 1                   # the NNN in persona_id

class IdentityConstructor:
    def __init__(self, llm_client, model: str = "claude-sonnet-4-6"):
        self.llm = llm_client
        self.model = model
        self.filler = AttributeFiller(llm_client, model)
        self.insights_computer = DerivedInsightsComputer()
        self.story_generator = LifeStoryGenerator(llm_client, model)
        self.tendency_estimator = TendencyEstimator()
        self.narrative_generator = NarrativeGenerator(llm_client, model)
        self.validator = PersonaValidator()

    async def build(
        self,
        demographic_anchor: DemographicAnchor,
        icp_spec: ICPSpec,
    ) -> PersonaRecord:
        """
        Runs the full identity build sequence.
        Returns a validated PersonaRecord.
        Raises ValueError if validation fails (G1, G2, G3).
        """
        ...

    def _assemble_core_memory(self, partial_record: dict) -> "CoreMemory":
        """
        Assembles CoreMemory from the constructed record fields.
        - identity_statement: first 25 words of first_person narrative
        - key_values: extracted from primary_value_driver + top 2 values attributes
        - life_defining_events: from life_stories (convert to LifeDefiningEvent format)
        - relationship_map: assembled from trust_orientation + social attributes
        - immutable_constraints: budget_ceiling from income_bracket, non_negotiables from key tensions
        - tendency_summary: copy of reasoning_prompt from behavioural_tendencies
        """
        ...

    def _make_persona_id(self, icp_spec: ICPSpec) -> str:
        """Format: pg-[prefix]-[NNN] e.g. pg-cpg-001"""
        return f"pg-{icp_spec.persona_id_prefix}-{icp_spec.persona_index:03d}"
```

### Working Memory Initialisation

After the full record is assembled, initialise `WorkingMemory` with empty state:

```python
WorkingMemory(
    observations=[],
    reflections=[],
    plans=[],
    brand_memories={},
    simulation_state=SimulationState(
        current_turn=0,
        importance_accumulator=0.0,
        reflection_count=0,
        awareness_set={},
        consideration_set=[],
        last_decision=None,
    )
)
```

Working memory is empty at persona creation. It is populated during simulation and survey modalities.

### Validation Handling

After assembly, run `PersonaValidator.validate_all(persona)`. If any gate returns `passed=False`, raise `ValueError` with the gate name and failure list. Do not return invalid personas.

---

## Integration Contract

- **Imports AttributeFiller from:** `src.generation.attribute_filler`
- **Imports DerivedInsightsComputer from:** `src.generation.derived_insights` (Goose Sprint 2)
- **Imports LifeStoryGenerator from:** `src.generation.life_story_generator` (Codex Sprint 2)
- **Imports TendencyEstimator from:** `src.generation.tendency_estimator` (Goose Sprint 2)
- **Imports NarrativeGenerator from:** `src.generation.narrative_generator` (Codex Sprint 2)
- **Imports PersonaValidator from:** `src.schema.validators` (Antigravity Sprint 1 — exists)
- **Exports:** `IdentityConstructor`, `ICPSpec`

---

## Constraints

- Do NOT call any LLM directly. Delegate all LLM calls to the component classes.
- Do NOT compute derived insights, tendencies, or narrative inline — all must go through the component classes.
- The `ICPSpec` dataclass lives here. Other files may import it from `src.generation.identity_constructor`.
- If a component file doesn't exist yet (Sprint 2 parallel build), stub the import with a `TYPE_CHECKING` guard and write against the interface specified above.

---

## Outcome File

When done, write `sprints/outcome_cursor.md` (overwrite the Sprint 1 version) with:
1. File created (line count)
2. Build sequence implemented — confirm all 8 steps present
3. How you handled missing component files (stubs / TYPE_CHECKING)
4. CoreMemory assembly logic — describe how you derived each field
5. Any build sequence decisions not explicitly specified
6. Known gaps
