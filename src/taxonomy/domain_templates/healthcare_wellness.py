from __future__ import annotations

from src.taxonomy.base_taxonomy import AttributeDefinition


def _domain_attr_definitions(
    attrs: list[AttributeDefinition],
) -> list[AttributeDefinition]:
    # Mark all attributes as domain-specific so the filler knows to treat
    # them as supplemental, and normalise population_prior floats to the
    # dict contract used by AttributeFiller.
    for a in attrs:
        setattr(a, "is_domain_specific", True)

        pp = getattr(a, "population_prior", None)
        if isinstance(pp, (int, float)):
            v = float(pp)
            if v > 0.66:
                label = "high"
            elif v > 0.33:
                label = "medium"
            else:
                label = "low"
            setattr(a, "population_prior", {"value": v, "label": label})
    return attrs


HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES: list[AttributeDefinition] = _domain_attr_definitions(
    [
        # ── preventive care orientation ───────────────────────────────────
        AttributeDefinition(
            name="preventive_care_orientation",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.52,
            description="Proactive tendency to seek routine medical check-ups and screenings before symptoms arise.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="doctor_trust",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.64,
            description="Degree of trust placed in GP or specialist recommendations when making clinical decisions.",
            is_anchor=False,
        ),
        # NOTE: health_wellness.py defines `alternative_medicine_openness` covering
        # consumer wellness contexts (Ayurveda, homeopathy, fitness supplements).
        # This attribute covers the clinical equivalent — patient willingness to
        # integrate complementary medicine alongside conventional treatment.
        AttributeDefinition(
            name="complementary_medicine_openness",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.38,
            description="Willingness to use non-Western or complementary therapies alongside conventional medical treatment.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="medical_consultation_anxiety",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.43,
            description="Degree of health-related worry that influences frequency and urgency of medical consultations.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="treatment_adherence_propensity",
            category="lifestyle",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.57,
            description="Likelihood of completing prescribed treatment plans, medication courses, and follow-up schedules.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="second_opinion_seeking",
            category="decision_making",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.37,
            description="Tendency to consult multiple clinicians before committing to a significant diagnosis or treatment.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="telehealth_comfort",
            category="lifestyle",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.48,
            description="Comfort with remote or video-based healthcare consultations as an alternative to in-person visits.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="pharmaceutical_brand_trust",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.44,
            description="Preference for branded medications over generic equivalents, based on perceived quality or safety.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="family_health_influence",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.55,
            description="Degree to which known family medical history and hereditary conditions drive personal health decisions.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="self_diagnosis_tendency",
            category="decision_making",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.46,
            description="Reliance on internet searches or AI tools to self-diagnose symptoms before or instead of consulting a clinician.",
            is_anchor=False,
        ),
        # ── healthcare system engagement ──────────────────────────────────
        AttributeDefinition(
            name="nhs_vs_private_preference",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.35,
            description="Preference for private healthcare provision (1.0) versus reliance on public health systems (0.0).",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="specialist_referral_willingness",
            category="decision_making",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.52,
            description="Willingness to pursue specialist referrals rather than managing conditions through a GP alone.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="elective_procedure_openness",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.32,
            description="Openness to elective procedures (cosmetic, corrective, or non-urgent surgical) when medically advised.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="healthcare_wait_time_tolerance",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.46,
            description="Patience for healthcare waiting lists or appointment delays before seeking faster private alternatives.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="emergency_service_utilisation_threshold",
            category="decision_making",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.38,
            description="Threshold of symptom severity at which the persona decides to use emergency services vs waiting.",
            is_anchor=False,
        ),
        # ── doctor-patient relationship ───────────────────────────────────
        AttributeDefinition(
            name="shared_decision_making_preference",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.58,
            description="Preference for collaborative treatment planning with clinicians rather than deferring entirely to medical authority.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="medical_paternalism_acceptance",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.42,
            description="Acceptance of physician-directed decisions without demanding detailed rationale or alternatives.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="continuity_of_care_priority",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.60,
            description="Priority placed on seeing the same GP or specialist consistently over accessing whoever is available.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="consultation_duration_expectation",
            category="lifestyle",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.47,
            description="Expectation of longer, thorough appointments over quick transactional consultations.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="medical_record_access_motivation",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.41,
            description="Motivation to access and review personal medical records and test results directly.",
            is_anchor=False,
        ),
        # ── clinical information seeking ──────────────────────────────────
        AttributeDefinition(
            name="clinical_trial_awareness",
            category="identity",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.24,
            description="Awareness of and openness to participating in clinical trials as a treatment pathway.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="medical_journal_consumption",
            category="lifestyle",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.18,
            description="Frequency of reading peer-reviewed medical literature or evidence summaries to inform health decisions.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="symptom_tracker_usage",
            category="lifestyle",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.33,
            description="Active use of digital symptom-tracking apps or health diaries to monitor ongoing conditions.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="online_patient_community_engagement",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.28,
            description="Participation in online patient forums or communities to share experiences and gather medical insight.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="healthcare_chatbot_comfort",
            category="lifestyle",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.35,
            description="Comfort using AI-powered chatbots or triage tools for initial symptom assessment.",
            is_anchor=False,
        ),
        # ── medication attitudes ──────────────────────────────────────────
        AttributeDefinition(
            name="medication_side_effect_concern",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.54,
            description="Level of concern about medication side effects that influences willingness to start or continue treatment.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="polypharmacy_resistance",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.45,
            description="Resistance to taking multiple concurrent medications and desire to reduce overall pharmaceutical load.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="vaccination_acceptance",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.68,
            description="Acceptance of recommended vaccinations and immunisation programmes for self and family.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="generic_substitution_acceptance",
            category="decision_making",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.56,
            description="Acceptance of pharmacist-substituted generic medications when prescribed branded equivalents.",
            is_anchor=False,
        ),
        # ── chronic condition management ──────────────────────────────────
        AttributeDefinition(
            name="chronic_condition_self_management",
            category="lifestyle",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.44,
            description="Proactive self-management of chronic conditions through lifestyle, monitoring, and independent knowledge.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="comorbidity_management_complexity_tolerance",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.40,
            description="Tolerance for managing multiple simultaneous health conditions without becoming overwhelmed.",
            is_anchor=False,
        ),
        # ── mental health engagement ──────────────────────────────────────
        AttributeDefinition(
            name="mental_health_help_seeking",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.40,
            description="Willingness to seek professional psychological support when experiencing mental health difficulties.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="mental_health_stigma_sensitivity",
            category="psychology",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.43,
            description="Sensitivity to perceived social stigma that inhibits disclosure or treatment-seeking for mental health.",
            is_anchor=False,
        ),
        # ── reproductive and family health ────────────────────────────────
        AttributeDefinition(
            name="paediatric_health_vigilance",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.58,
            description="Vigilance in monitoring children's health milestones and seeking timely paediatric care.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="caregiver_health_proxy_tendency",
            category="social",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.47,
            description="Tendency to actively manage healthcare decisions on behalf of elderly or dependent family members.",
            is_anchor=False,
        ),
        # ── health information channel ────────────────────────────────────
        AttributeDefinition(
            name="primary_health_information_source",
            category="decision_making",
            attr_type="categorical",
            options=["gp_or_specialist", "nhs_or_gov_sites", "medical_apps", "social_media", "peer_network"],
            population_prior=0.0,
            description="Preferred primary source for health information when assessing symptoms or treatment options.",
            is_anchor=False,
        ),
        AttributeDefinition(
            name="health_data_sharing_consent",
            category="values",
            attr_type="continuous",
            range_min=0.0,
            range_max=1.0,
            population_prior=0.39,
            description="Willingness to share anonymised personal health data for research or public health benefit.",
            is_anchor=False,
        ),
    ]
)


__all__ = ["HEALTHCARE_WELLNESS_DOMAIN_ATTRIBUTES"]
