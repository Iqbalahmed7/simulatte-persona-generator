# Domain Guide — Taxonomy Patterns by Business Domain

Use this as a starting point for taxonomy construction in Step 2.
Adapt, remove, or extend based on the actual business problem.
These are illustrative patterns, not fixed schemas.

---

## How to Read This Guide

Each domain shows:
- **Key questions** the taxonomy must answer
- **Root categories** (6-8)
- **Sample leaf attributes** per category
- **Domain-specific tensions** that will drive persona differentiation
- **Environment spaces** (for simulation-ready mode)

---

## Domain 1: Consumer Product — FMCG / Nutrition / Health

**Key questions:** Who buys, who decides, what triggers trial, what drives repeat?

**Root categories:**
```
PSYCHOLOGY
  - risk_tolerance: how willing to try unfamiliar products (0-1)
  - information_need: research depth before purchase (0-1)
  - guilt_sensitivity: susceptibility to guilt-based messaging (0-1)
  - status_quo_bias: resistance to switching from current product (0-1)

HEALTH & DOMAIN BELIEFS
  - health_anxiety: how worried about child/own health (0-1)
  - supplement_necessity_belief: believes products in this category are needed (0-1)
  - natural_vs_synthetic_preference: prefers natural ingredients (0-1)
  - preventive_vs_reactive_orientation: prevents vs treats problems (0-1)

SOCIAL INFLUENCE
  - peer_influence_strength: how much friends/community shapes decisions (0-1)
  - authority_bias: how much expert recommendations override own view (0-1)
  - wom_transmitter_tendency: actively shares recommendations (0-1)
  - mommy_group_activity: engaged in parenting communities (0-1)

ECONOMICS
  - budget_consciousness: price sensitivity (0-1)
  - deal_seeking_intensity: actively seeks offers/discounts (0-1)
  - brand_loyalty_tendency: sticks with known brands (0-1)
  - best_for_my_child_intensity: willing to stretch budget for quality (0-1)

LIFESTYLE
  - perceived_time_scarcity: feels time-poor (0-1)
  - convenience_food_acceptance: ok with shortcuts (0-1)
  - meal_planning_habit: structured vs. spontaneous approach (0-1)
  - wellness_trend_follower: adopts new health trends (0-1)

MEDIA & DISCOVERY
  - primary_discovery_channel: categorical — instagram/youtube/doctor/word-of-mouth/search
  - ad_receptivity: responds positively to advertising (0-1)
  - review_platform_trust: trusts online reviews (0-1)
```

**Key tensions:**
- Budget ceiling vs. "best for my child" aspiration
- Traditional/natural preference vs. scientific/clinical claims
- Self-research tendency vs. authority deference

**Environment spaces (simulation):**
- Online grocery app (Blinkit, BigBasket)
- WhatsApp parenting group
- Paediatrician consultation room
- School gate / playground
- Pharmacy aisle

---

## Domain 2: B2B SaaS — Mid-Market Buyer

**Key questions:** Who champions, who blocks, what triggers evaluation, what kills deals?

**Root categories:**
```
PROFESSIONAL IDENTITY
  - role_type: categorical — champion/economic-buyer/blocker/end-user
  - years_in_role: 1-20 (normalise to 0-1)
  - career_risk_sensitivity: how much a bad decision affects their career (0-1)
  - technical_depth: can evaluate product technically (0-1)

DECISION PROCESS
  - committee_buying_tendency: needs group consensus (0-1)
  - vendor_due_diligence_depth: reference checks, trials, deep evaluation (0-1)
  - status_quo_inertia: how hard to displace incumbent vendor (0-1)
  - urgency_driven: needs a burning platform to act (0-1)

ORGANISATIONAL CONTEXT
  - budget_autonomy: controls own budget (0-1)
  - it_dependency: needs IT sign-off (0-1)
  - compliance_sensitivity: regulated industry (0-1)
  - change_management_burden: how hard to get team to adopt (0-1)

VENDOR EVALUATION
  - price_sensitivity: (0-1)
  - roi_focus: needs to prove financial return (0-1)
  - brand_trust_bias: prefers large established vendors (0-1)
  - integration_complexity_tolerance: ok with complex implementations (0-1)

INFLUENCE & SOCIAL PROOF
  - peer_reference_dependence: needs to hear from similar companies (0-1)
  - analyst_influence: Gartner/Forrester shapes their view (0-1)
  - community_presence: active in professional communities (0-1)
```

**Key tensions:**
- Champion enthusiasm vs. organisational inertia
- Feature richness vs. implementation risk
- Price sensitivity vs. career safety (cheap = risky)

**Environment spaces (simulation):**
- Discovery: G2/Capterra, LinkedIn, peer conversation
- Evaluation: product demo, reference call, security review
- Purchase: procurement/legal, IT review, executive approval
- Post-purchase: onboarding, expansion conversation

---

## Domain 3: Real Estate — First-Time Home Buyer

**Key questions:** What triggers search, what builds conviction, what causes drop-off?

**Root categories:**
```
FINANCIAL READINESS
  - down_payment_readiness: (0-1)
  - emi_stress_tolerance: comfort with long-term debt (0-1)
  - financial_literacy: understands home loan products (0-1)
  - opportunity_cost_awareness: aware of renting vs. buying trade-offs (0-1)

LIFE TRIGGER
  - marriage_proximity: recently married or planning to (categorical: yes/no)
  - child_planning: expecting or planning children (categorical)
  - parental_pressure: family pushing toward ownership (0-1)
  - job_stability_confidence: feels secure in current employment (0-1)

PROPERTY BELIEFS
  - property_as_investment_belief: views home as financial asset (0-1)
  - location_status_sensitivity: neighbourhood as social signal (0-1)
  - vastu_compliance_importance: cultural/religious property criteria (0-1)
  - new_vs_resale_preference: categorical

SEARCH BEHAVIOUR
  - online_research_intensity: spends hours on portals (0-1)
  - broker_dependence: relies on agents vs. self-researches (0-1)
  - peer_consultation_tendency: talks to friends who bought (0-1)
  - decision_speed: quick vs. deliberate (0-1)

EMOTIONAL DIMENSION
  - aspiration_gap: current life vs. dream home gap (0-1)
  - fear_of_missing_out: anxious about rising prices (0-1)
  - regret_sensitivity: worried about making wrong choice (0-1)
```

**Key tensions:**
- Aspiration vs. affordability
- FOMO (buy now) vs. fear (what if prices drop / job insecurity)
- Parental/social pressure vs. personal readiness

---

## Domain 4: Healthcare — Patient / Caregiver Decision

**Key questions:** What drives care-seeking, adherence, channel choice, product adoption?

**Root categories:**
```
HEALTH LITERACY
  - medical_knowledge: understands conditions/treatments (0-1)
  - internet_health_research: Dr. Google tendency (0-1)
  - clinical_trial_awareness: aware of research/evidence (0-1)

DOCTOR RELATIONSHIP
  - physician_trust: how much they defer to doctor (0-1)
  - second_opinion_tendency: seeks multiple views (0-1)
  - self_advocacy_strength: pushes back on recommendations (0-1)

TREATMENT ATTITUDES
  - alternative_medicine_openness: considers non-conventional treatments (0-1)
  - medication_adherence_tendency: follows through on prescriptions (0-1)
  - side_effect_anxiety: overly worried about adverse effects (0-1)
  - cost_vs_efficacy_trade_off: price sensitivity on treatments (0-1)

CAREGIVER DYNAMICS (if patient is a child/elderly relative)
  - caregiver_burden: how overwhelmed they feel (0-1)
  - guilt_driven_care: over-compensates due to guilt (0-1)
  - family_consensus_need: multiple family members in decision (0-1)

SYSTEM TRUST
  - healthcare_system_trust: trusts the system to help (0-1)
  - insurance_navigation_comfort: handles insurance well (0-1)
  - out_of_pocket_willingness: pays beyond insurance limits (0-1)
```

**Key tensions:**
- Doctor's recommendation vs. personal research/beliefs
- Affordability vs. quality of care
- Immediate symptom relief vs. long-term health investment

---

## Domain 5: EdTech — Parent Choosing Supplementary Education

**Key questions:** What triggers enrolment, what drives retention, what causes churn?

**Root categories:**
```
EDUCATION BELIEFS
  - academic_pressure_intensity: how much they push academic achievement (0-1)
  - holistic_vs_grades_orientation: all-round development vs. marks (0-1)
  - school_trust: relies on school vs. supplements it (0-1)
  - growth_mindset_belief: believes effort changes outcomes (0-1)

CHILD CONTEXT
  - child_learning_style: categorical — visual/auditory/kinesthetic/reading
  - current_academic_gap: perceives child is behind (0-1)
  - child_motivation: child is self-driven vs. needs pushing (0-1)
  - peer_comparison_anxiety: compares child to others (0-1)

TECHNOLOGY COMFORT
  - screen_time_guilt: worried about too much device use (0-1)
  - edtech_scepticism: doubts technology can replace human teaching (0-1)
  - app_adoption_ease: picks up new apps quickly (0-1)

ECONOMICS
  - education_spend_priority: education as % of discretionary budget (0-1)
  - multiple_class_juggling: already enrolled in many activities (0-1)
  - roi_measurement: tracks whether child is improving (0-1)
```

**Key tensions:**
- Screen time guilt vs. convenience of digital learning
- Fear of child falling behind vs. not wanting to over-pressure
- Premium product aspiration vs. price sensitivity

---

## Domain 6: Financial Services — Retail Investor / Insurance Buyer

**Key questions:** What builds trust, what triggers action, what creates inertia?

**Root categories:**
```
FINANCIAL PSYCHOLOGY
  - loss_aversion: fear of losing money more than gaining (0-1)
  - present_bias: discounts future benefits heavily (0-1)
  - financial_anxiety: general money worry (0-1)
  - complexity_avoidance: avoids products they don't understand (0-1)

TRUST & RELATIONSHIP
  - advisor_dependence: needs human advisor (0-1)
  - digital_channel_comfort: ok with app-only products (0-1)
  - brand_reputation_weight: big brand = safe (0-1)
  - peer_investment_influence: invests because friends did (0-1)

GOAL ORIENTATION
  - retirement_planning_horizon: thinks long-term (0-1)
  - goal_specificity: has named financial goals (0-1)
  - insurance_necessity_belief: sees insurance as protection not waste (0-1)

BEHAVIOUR
  - diy_investing_tendency: researches and acts independently (0-1)
  - procrastination_tendency: delays decisions indefinitely (0-1)
  - portfolio_review_frequency: categorical — monthly/quarterly/annually/never
```

**Key tensions:**
- Fear of loss vs. fear of missing market returns
- Complexity aversion vs. desire for control
- Advisor trust vs. distrust of commission-driven advice

---

## Domain 7: D2C / E-commerce — Repeat Purchase and Loyalty

**Key questions:** What drives first purchase, trial-to-repeat conversion, and LTV?

**Root categories:**
```
SHOPPING BEHAVIOUR
  - impulse_purchase_tendency: (0-1)
  - comparison_shopping_depth: how much they compare before buying (0-1)
  - review_dependence: reads reviews before every purchase (0-1)
  - subscription_comfort: ok with auto-renewal (0-1)

BRAND RELATIONSHIP
  - brand_narrative_resonance: connects with brand story/mission (0-1)
  - packaging_aesthetics_weight: packaging matters to purchase (0-1)
  - sustainability_premium_willingness: pays more for eco-friendly (0-1)
  - customer_service_sensitivity: bad support = instant churn (0-1)

DIGITAL BEHAVIOUR
  - social_commerce_activity: buys via Instagram/WhatsApp (0-1)
  - influencer_purchase_attribution: buys because influencer said so (0-1)
  - cashback_redemption_behaviour: actively uses loyalty/points (0-1)
  - app_vs_web_preference: categorical

ECONOMICS
  - average_order_value_comfort: categorical — <500/500-2000/>2000
  - free_shipping_threshold_sensitivity: behaviour changes at free shipping (0-1)
  - return_policy_importance: return ease as pre-purchase criterion (0-1)
```

---

## Domain 8: HR / Talent — Candidate / Employee Experience

**Key questions:** What motivates application, acceptance, engagement, retention?

**Root categories:**
```
CAREER MOTIVATION
  - financial_primary_driver: money above all (0-1)
  - growth_orientation: wants to learn and advance (0-1)
  - stability_preference: values security over upside (0-1)
  - purpose_alignment_need: needs to believe in company mission (0-1)

WORK STYLE
  - autonomy_need: needs independence to perform (0-1)
  - collaboration_preference: energy from team vs. solo work (0-1)
  - remote_work_preference: (0-1)
  - structure_vs_ambiguity_comfort: needs clear process (0-1)

EMPLOYER EVALUATION
  - glassdoor_research_depth: researches employer online (0-1)
  - peer_network_influence: listens to friends at company (0-1)
  - brand_prestige_weight: company name matters (0-1)
  - manager_relationship_importance: quality of direct manager (0-1)

DECISION DYNAMICS
  - competing_offer_tendency: uses other offers as leverage (0-1)
  - negotiation_comfort: asks for more (0-1)
  - time_to_decision: days from offer to accept (normalised)
```

---

## Building a Custom Taxonomy (for domains not listed above)

When the business domain doesn't match any of the above, follow this process:

**1. Start with the decision to be made**
Write the decision in one sentence: "A [person] deciding whether to [action] given [context]."

**2. Identify the three critical differentiators**
What are the top 3 things that would make two people in this population respond differently?
These become the first three leaf attributes.

**3. Build outward from the decision**
For each differentiator, ask:
- What psychological trait drives this?
- What economic constraint amplifies or limits it?
- What social factor modifies it?
- What past experience shaped it?

**4. Check for coverage across these five dimensions:**
- [ ] A financial/economic axis (budget, price sensitivity, ROI)
- [ ] A social/influence axis (peer, authority, family)
- [ ] A psychological axis (risk, information need, anxiety)
- [ ] A behavioural/habit axis (routine, convenience, inertia)
- [ ] A values/belief axis (what they prioritise and why)

If any dimension is missing, add 2-3 attributes to cover it.

**5. Aim for 30-50 total attributes** in Deep Mode, 15-25 in Quick Mode.
More than 60 attributes rarely adds value and increases incoherence risk.
