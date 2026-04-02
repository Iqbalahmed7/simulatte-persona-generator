# SPRINT 1 OUTCOME — OPCODE
**Engineer:** OpenCode  
**Role:** Domain Template Architect (CPG + SaaS) + Template Loader  
**Delivered:**
- `src/taxonomy/domain_templates/cpg.py`
- `src/taxonomy/domain_templates/saas.py`
- `src/taxonomy/domain_templates/template_loader.py`
**Date:** 2026-04-02

## 1. Files Created
- `src/taxonomy/domain_templates/cpg.py` — 45 CPG domain attributes
- `src/taxonomy/domain_templates/saas.py` — 40 SaaS domain attributes
- `src/taxonomy/domain_templates/template_loader.py` — domain merge/validation utilities

## 2. CPG Attributes (name → category)
- private_label_acceptance → values
- national_brand_attachment → values
- pack_size_preference → values
- online_grocery_adoption → lifestyle
- modern_trade_preference → decision_making
- kirana_preference → social
- coupon_redemption_rate → decision_making
- bundle_offer_responsiveness → values
- cashback_sensitivity → values
- personal_care_involvement → psychology
- food_health_involvement → psychology
- household_product_involvement → psychology
- stockpiling_tendency → lifestyle
- pantry_loading_frequency → lifestyle
- subscription_box_openness → decision_making
- ingredient_scrutiny → psychology
- nutritional_label_check → decision_making
- country_of_origin_sensitivity → values
- gifting_frequency → social
- occasion_driven_purchase → lifestyle
- impulse_at_checkout → decision_making
- new_product_trial_rate → psychology
- category_exploration_width → values
- sustainability_claim_weighting → values
- ethical_certification_trust → social
- price_grade_awareness → values
- discount_cycle_planning → lifestyle
- trial_sampling_channel_preference → social
- refill_vs_replacement_preference → decision_making
- reorder_reminder_dependence → lifestyle
- out_of_stock_switching_behavior → decision_making
- brand_safety_concern → psychology
- allergy_safety_priority → values
- family_health_responsibility → values
- convenience_pack_preference → lifestyle
- free_shipping_threshold_sensitivity → decision_making
- return_refund_expectation → decision_making
- complaint_engagement_level → social
- review_writing_motivation → social
- in_app_promo_engagement → lifestyle
- loyalty_program_enrollment_drive → values
- loyalty_program_benefit_expectation → decision_making
- size_variant_openness → values
- taste_preference_adaptability → psychology
- brand_story_resonance → values

## 3. SaaS Attributes (name → category)
- free_trial_dependency → decision_making
- proof_of_concept_requirement → decision_making
- demo_request_tendency → decision_making
- solo_decision_authority → identity
- procurement_process_tolerance → decision_making
- committee_buy_in_need → social
- ux_over_features_preference → values
- onboarding_patience → lifestyle
- feature_complexity_tolerance → psychology
- integration_lock_in_sensitivity → decision_making
- data_migration_anxiety → psychology
- switching_cost_aversion → values
- per_seat_preference → values
- usage_based_comfort → values
- annual_commitment_willingness → decision_making
- scalability_concern → psychology
- enterprise_upgrade_aspiration → identity
- startup_tool_openness → values
- security_compliance_prioritisation → psychology
- data_sovereignty_concern → values
- audit_trail_need → decision_making
- vendor_trust_sensitivity → social
- sales_rep_influence → social
- csm_engagement_preference → social
- sla_requirement_tendency → decision_making
- incident_response_expectation → decision_making
- support_channel_preference → lifestyle
- documentation_sufficiency_preference → decision_making
- training_requirement_level → lifestyle
- compliance_vendor_docs_reads → psychology
- open_api_preference → decision_making
- integration_partner_preference → decision_making
- risk_management_approval_steps → decision_making
- vendor_lockin_regret → psychology
- migration_timeline_comfort → decision_making
- time_to_value_requirement → identity
- tool_sprawl_tolerance → values
- change_resistance → psychology
- internal_tooling_customization_need → identity
- dashboard_over_raw_data_preference → values

## 4. Base vs Domain Placement Uncertainty
- `return_refund_expectation` (CPG) could arguably be a more general decision trait, but it’s still grounded in CPG post-purchase norms (returns/refunds policies) and was kept domain-specific.
- `documentation_sufficiency_preference` (SaaS) sits between “general information-seeking” and “domain onboarding reality”; kept in SaaS to reflect vendor-specific evaluation behavior.

## 5. Overlap With Base Taxonomy Names
- Verified overlaps with `src.taxonomy.base_taxonomy.TAXONOMY_BY_NAME`: **0** (none of the CPG/SaaS attribute names duplicate base attribute names).

## 6. Known Gaps
### CPG
- No explicit attribute for “ethical food sourcing depth” beyond sustainability-claim weighting.
- Limited coverage of meal planning / bulk cooking behaviors (more relevant to food-specific longitudinal decisions).

### SaaS
- Missing explicit attributes for procurement budget ownership (e.g., who controls spend) beyond process tolerance and authority/committee patterns.
- Limited coverage of champion-vs-detractor dynamics beyond committee buy-in and trust sensitivity.
