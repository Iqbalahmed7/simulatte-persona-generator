from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schema.worldview import WorldviewAnchor  # noqa: F401 — re-exported for convenience


Gender = Literal["female", "male", "non-binary"]
UrbanTier = Literal["metro", "tier2", "tier3", "rural"]
HouseholdStructure = Literal[
    "nuclear", "joint", "single-parent", "couple-no-kids", "other"
]
Education = Literal["high-school", "undergraduate", "postgraduate", "doctoral"]
Employment = Literal[
    "full-time",
    "part-time",
    "self-employed",
    "homemaker",
    "student",
    "retired",
]

Mode = Literal["quick", "deep", "simulation-ready", "grounded"]

AttributeType = Literal["continuous", "categorical"]
AttributeSource = Literal["sampled", "inferred", "anchored", "domain_data"]

DecisionStyle = Literal["emotional", "analytical", "habitual", "social"]
TrustAnchor = Literal["self", "peer", "authority", "family"]
RiskAppetite = Literal["low", "medium", "high"]
PrimaryValueOrientation = Literal["price", "quality", "brand", "convenience", "features"]

ConsistencyBand = Literal["low", "medium", "high"]

TendencySource = Literal["grounded", "proxy", "estimated"]
TendencyBandLabel = Literal["low", "medium", "high"]
PriceSensitivityBandLabel = Literal["low", "medium", "high", "extreme"]

ObjectionType = Literal[
    "price_vs_value",
    "trust_deficit",
    "need_more_information",
    "social_proof_gap",
    "switching_cost_concern",
    "risk_aversion",
    "budget_ceiling",
    "feature_gap",
    "timing_mismatch",
]
ObjectionLikelihood = Literal["high", "medium", "low"]
ObjectionSeverity = Literal["blocking", "friction", "minor"]

CopingMechanismType = Literal[
    "routine_control",
    "social_validation",
    "research_deep_dive",
    "denial",
    "optimism_bias",
]


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str
    region: str
    city: str
    urban_tier: UrbanTier


class Household(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structure: HouseholdStructure
    size: int
    income_bracket: str
    dual_income: bool


class DemographicAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    age: int
    gender: Gender
    location: Location
    household: Household
    life_stage: str
    education: Education
    employment: Employment

    # Values & ideology anchor — optional, defaults to None.
    # Set by demographic_sampler for supported domains (currently: us_general).
    # All other domains (cpg, saas, lofoods_fmcg, etc.) leave this as None.
    # See ARCH-001 and ARCH-001-addendum-geography for architecture details.
    worldview: WorldviewAnchor | None = None


class LifeStory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    when: str
    event: str
    lasting_impact: str


class Attribute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | str
    type: AttributeType
    label: str
    source: AttributeSource

    @model_validator(mode="after")
    def _validate_value_matches_type(self) -> "Attribute":
        if self.type == "continuous":
            if not isinstance(self.value, (int, float)):
                raise ValueError("Attribute.value must be a number when type='continuous'")
            v = float(self.value)
            if not (0.0 <= v <= 1.0):
                raise ValueError("Continuous Attribute.value must be between 0.0 and 1.0")
            self.value = v
        else:
            if not isinstance(self.value, str):
                raise ValueError(
                    "Attribute.value must be a string when type='categorical'"
                )
        return self


class CopingMechanism(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: CopingMechanismType
    description: str


class DerivedInsights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_style: DecisionStyle
    decision_style_score: float
    trust_anchor: TrustAnchor
    risk_appetite: RiskAppetite
    primary_value_orientation: PrimaryValueOrientation
    coping_mechanism: CopingMechanism
    consistency_score: int
    consistency_band: ConsistencyBand
    key_tensions: list[str]

    @field_validator("decision_style_score")
    @classmethod
    def _decision_style_score_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("decision_style_score must be between 0.0 and 1.0")
        return v

    @field_validator("consistency_score")
    @classmethod
    def _consistency_score_range(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("consistency_score must be between 0 and 100")
        return v

    @field_validator("key_tensions")
    @classmethod
    def _key_tensions_min_1(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("key_tensions must have at least 1 item")
        return v


class TendencyBand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    band: TendencyBandLabel
    description: str
    source: TendencySource


class PriceSensitivityBand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    band: PriceSensitivityBandLabel
    description: str
    source: TendencySource


class TrustWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expert: float
    peer: float
    brand: float
    ad: float
    community: float
    influencer: float

    @field_validator(
        "expert", "peer", "brand", "ad", "community", "influencer", mode="after"
    )
    @classmethod
    def _weights_0_1(cls, v: float) -> float:
        if not (0.0 <= float(v) <= 1.0):
            raise ValueError("TrustWeights values must be between 0.0 and 1.0")
        return float(v)


class TrustOrientation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weights: TrustWeights
    dominant: str
    description: str
    source: TendencySource


class Objection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objection_type: ObjectionType
    likelihood: ObjectionLikelihood
    severity: ObjectionSeverity


class BehaviouralTendencies(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_sensitivity: PriceSensitivityBand
    trust_orientation: TrustOrientation
    switching_propensity: TendencyBand
    objection_profile: list[Objection]
    reasoning_prompt: str


class Narrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_person: str
    third_person: str
    display_name: str


class LifeDefiningEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_when: int
    event: str
    lasting_impact: str


class RelationshipMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_decision_partner: str
    key_influencers: list[str]
    trust_network: list[str]


class ImmutableConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    budget_ceiling: str | None = None
    non_negotiables: list[str]
    absolute_avoidances: list[str]


class CoreMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_statement: str
    key_values: list[str]
    life_defining_events: list[LifeDefiningEvent]
    relationship_map: RelationshipMap
    immutable_constraints: ImmutableConstraints
    tendency_summary: str
    # Sprint B-1 Fix 2: Dedicated field for political era / current-conditions stance.
    # Separated from key_values to prevent contamination of non-temporal survey questions.
    # Injected into the decide prompt as a distinct line, not merged into key_values.
    current_conditions_stance: str | None = None
    # Sprint B-9 Fix 1: Dedicated field for media trust stance.
    # Pulled OUT of _POLICY_STANCE_STATEMENTS where it was buried as item 5 of 7.
    # Injected into the decide prompt as a distinct labelled line so Haiku reads it
    # explicitly when answering q13-type questions (media trust / news source trust).
    media_trust_stance: str | None = None
    # Study 1B Sprint A-2 Fix 1: Dedicated field for gender norms stance (India).
    # Root cause of in12/in13 INVERSION: Haiku applies Western gender equality defaults.
    # Pew India: 87% agree wife should obey; 80% agree men should have job priority.
    # Injected as a distinct labelled line so Haiku reads it when answering
    # gender-role questions (in12 wife_obedience, in13 gender_jobs).
    gender_norms_stance: str | None = None
    # Study 1B Sprint A-2 Fix 2: Dedicated field for governance/leadership stance (India).
    # Root cause of in07 INVERSION (10.2%): Haiku defaults to Western anti-authoritarian
    # stance, choosing 'very bad' for 100% of personas.
    # Pew India: 80% think strong leader without parliament is 'very good' or 'somewhat good'.
    # Injected as a distinct labelled line so Haiku reads it for in07 strong_leader.
    governance_stance: str | None = None
    # Study 1B Sprint A-3: Cultural survey context preamble for India personas.
    # Addresses RLHF structural blocks on in07/in12/in13 where Haiku's Constitutional AI
    # training overrides explicit persona stances. Injected as a PREAMBLE to the system
    # prompt (before "You are {name}...") to establish a research simulation frame that
    # gives the model explicit permission to answer as the Indian persona without
    # defaulting to Western liberal values.
    cultural_context: str | None = None
    # Study 1B Sprint A-8 Fix 3: Dedicated field for INC (Congress party) stance (India).
    # Root cause of in04 modal-C lock: "pragmatic moderate" behavioural tendency overrides
    # policy_stance and current_conditions_stance D-anchors for bjp_supporter personas.
    # INC narrative identity (A-7) strengthened C, not D. Dedicated stance field is the
    # proven pattern (same as gender_norms_stance for in12/in13, governance_stance for in07
    # in Sprint A-2). Injected as a labelled line in the decide prompt, firing specifically
    # on INC approval questions.
    inc_stance: str | None = None

    @field_validator("key_values")
    @classmethod
    def _key_values_3_5(cls, v: list[str]) -> list[str]:
        if not (3 <= len(v) <= 5):
            raise ValueError("key_values must have 3-5 items")
        return v


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    timestamp: datetime
    type: Literal["observation"]
    content: str
    importance: int = Field(..., ge=1, le=10)
    emotional_valence: float = Field(..., ge=-1.0, le=1.0)
    source_stimulus_id: str | None = None
    last_accessed: datetime


class Reflection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    timestamp: datetime
    type: Literal["reflection"]
    content: str
    importance: int
    source_observation_ids: list[str]
    last_accessed: datetime

    @field_validator("source_observation_ids")
    @classmethod
    def _source_observation_ids_min_2(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("source_observation_ids must have at least 2 items")
        return v


class SimulationState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_turn: int
    importance_accumulator: float
    reflection_count: int
    awareness_set: dict
    consideration_set: list[str]
    last_decision: str | None = None


class WorkingMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: list[Observation]
    reflections: list[Reflection]
    plans: list[str]
    brand_memories: dict[str, Any]
    simulation_state: SimulationState


class Memory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core: CoreMemory
    working: WorkingMemory


class PersonaRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_id: str
    generated_at: datetime
    generator_version: str
    domain: str
    mode: Mode
    demographic_anchor: DemographicAnchor
    life_stories: list[LifeStory]
    attributes: dict[str, dict[str, Attribute]]
    derived_insights: DerivedInsights
    behavioural_tendencies: BehaviouralTendencies
    narrative: Narrative
    decision_bullets: list[str]
    memory: Memory

    # Seeded generation metadata — set when this persona was produced as a
    # demographic variant of an existing seed persona. None for standard
    # full-pipeline ("deep") personas. seed_persona_id links back to the
    # seed's persona_id; generation_mode distinguishes variants from seeds
    # in analytics and cost accounting.
    seed_persona_id: str | None = None
    generation_mode: Literal["full", "variant"] = "full"

    @field_validator("life_stories")
    @classmethod
    def _life_stories_2_3(cls, v: list[LifeStory]) -> list[LifeStory]:
        if not (2 <= len(v) <= 3):
            raise ValueError("life_stories must have 2-3 items")
        return v

