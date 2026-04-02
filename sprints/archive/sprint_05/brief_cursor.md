# SPRINT 5 BRIEF — CURSOR
**Role:** Cohort Assembler + Experiment Session
**Sprint:** 5 — Cohort Assembly + Experiment Modularity
**Spec check:** Master Spec §11 (Distinctiveness Enforcement), §14A S18 (experiment isolation settled)
**Previous rating:** 19/20

---

## Your Job This Sprint

Three files. You own the cohort assembly orchestrator and the experiment layer.

---

## File 1: `src/cohort/assembler.py`

### What It Does

Takes a list of `PersonaRecord` objects and assembles them into a validated `CohortEnvelope`. Runs G6, G7, G8, G9, G11 gates (delegating to Antigravity's gate runner). Returns the envelope or raises with the failed gates.

### Interface

```python
from src.schema.cohort import CohortEnvelope, CohortSummary
from src.schema.persona import PersonaRecord

def assemble_cohort(
    personas: list[PersonaRecord],
    domain: str,
    cohort_id: str | None = None,
) -> CohortEnvelope:
    """
    Assemble N personas into a validated CohortEnvelope.

    Steps:
    1. Validate each persona passes G1 (schema valid — they should already be valid PersonaRecords)
    2. Run cohort-level gates: G6, G7, G8, G9, G11 via CohortGateRunner
    3. Compute CohortSummary (demographic breakdown, type distribution)
    4. Build and return CohortEnvelope

    Raises ValueError listing failed gates if any gate fails.
    cohort_id defaults to f"cohort-{uuid4().hex[:8]}"
    """
    ...
```

### CohortSummary computation

```python
def _compute_summary(personas: list[PersonaRecord]) -> CohortSummary:
    """
    Compute:
    - size: len(personas)
    - domain: passed in
    - persona_types: list of detected PersonaType labels (use type_coverage.classify_persona_type)
    - age_distribution: dict[str, int] — bracket → count
    - city_distribution: dict[str, int] — city → count
    - income_distribution: dict[str, int] — income_bracket → count
    """
```

### Create `src/cohort/__init__.py`

Empty package init. Required for imports.

---

## File 2: `src/experiment/modality.py`

### What It Does

Defines the experiment modality enum and the working memory reset operation.

```python
from enum import Enum
from src.schema.persona import PersonaRecord, Memory, WorkingMemory, SimulationState

class ExperimentModality(Enum):
    ONE_TIME_SURVEY = "one_time_survey"
    TEMPORAL_SIMULATION = "temporal_simulation"
    POST_EVENT_SURVEY = "post_event_survey"
    DEEP_INTERVIEW = "deep_interview"

def reset_working_memory(persona: PersonaRecord) -> PersonaRecord:
    """
    Reset a persona's working memory for a new experiment.

    Clears: observations, reflections, plans, brand_memories.
    Resets SimulationState: current_turn=0, importance_accumulator=0.0,
      reflection_count=0, awareness_set={}, consideration_set=[], last_decision=None.

    Core memory is NEVER touched — immutable by design (§14A S18).
    Returns a new PersonaRecord via model_copy. Never mutates the input.

    Idempotent: calling reset on an already-empty working memory produces
    the same result as the first reset.
    """
    empty_state = SimulationState(
        current_turn=0,
        importance_accumulator=0.0,
        reflection_count=0,
        awareness_set={},
        consideration_set=[],
        last_decision=None,
    )
    empty_working = WorkingMemory(
        observations=[],
        reflections=[],
        plans=[],
        brand_memories={},
        simulation_state=empty_state,
    )
    new_memory = persona.memory.model_copy(update={"working": empty_working})
    return persona.model_copy(update={"memory": new_memory})
```

### Create `src/experiment/__init__.py`

Empty package init.

---

## File 3: `src/experiment/session.py`

### What It Does

Ties a persona (or cohort), a modality, and a stimulus sequence into an experiment session.

```python
from dataclasses import dataclass, field
from src.schema.persona import PersonaRecord
from src.schema.cohort import CohortEnvelope
from src.experiment.modality import ExperimentModality

@dataclass
class ExperimentSession:
    session_id: str
    modality: ExperimentModality
    persona: PersonaRecord | None = None           # single-persona mode
    cohort: CohortEnvelope | None = None           # cohort mode
    stimuli: list[str] = field(default_factory=list)
    decision_scenarios: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.persona is None and self.cohort is None:
            raise ValueError("ExperimentSession requires either persona or cohort")
        if self.persona is not None and self.cohort is not None:
            raise ValueError("ExperimentSession takes persona OR cohort, not both")

def create_session(
    modality: ExperimentModality,
    stimuli: list[str],
    persona: PersonaRecord | None = None,
    cohort: CohortEnvelope | None = None,
    decision_scenarios: list[str] | None = None,
    session_id: str | None = None,
) -> ExperimentSession:
    """
    Factory function. Resets working memory before returning the session.
    session_id defaults to f"session-{uuid4().hex[:8]}"
    """
    ...
```

---

## Integration Contract

- **Imports Antigravity's gate runner:** `from src.schema.validators import CohortGateRunner`
- **Imports Codex's type coverage:** `from src.cohort.type_coverage import classify_persona_type`
- **Imports from schema:** `from src.schema.cohort import CohortEnvelope, CohortSummary`

---

## Outcome File

When done, write `sprints/outcome_cursor.md` with:
1. Files created (line counts)
2. `assemble_cohort` — describe gate delegation and summary computation
3. `reset_working_memory` — confirm core memory is untouched + idempotency
4. Known gaps
