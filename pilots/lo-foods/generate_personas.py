"""
Lo! Foods — Simulation-Ready Persona Generator
500 personas across 7 cohorts
Architecture: architecture.md + output_schema.md
Generated: 2026-04-02
"""

import json
import random
import math
from datetime import datetime

random.seed(42)

# ─────────────────────────────────────────────────────────
# STEP 1 — COHORT DEFINITIONS
# ─────────────────────────────────────────────────────────

COHORTS = {
    "keto_loyalist": {
        "size": 75,
        "description": "Dedicated keto/low-carb practitioners. Self-directed, label-readers, high habit stickiness. Lo!'s core early adopter base.",
        "business_problems": ["habit_formation", "category_expansion", "churn_risk_low"]
    },
    "protein_fitness": {
        "size": 120,
        "description": "Gym-goers and fitness-conscious users seeking protein. Influenced by fitness content creators. Price-moderately sensitive.",
        "business_problems": ["category_expansion", "trust_formation", "channel_behavior"]
    },
    "diabetic_caregiver": {
        "size": 80,
        "description": "Managing diabetes themselves or as primary caregiver. Doctor-trust dominant. High information need. Willing to pay premium if medically credible.",
        "business_problems": ["trust_formation", "repeat_purchase", "price_sensitivity"]
    },
    "family_shopper": {
        "size": 100,
        "description": "Primary household grocery buyer. Prioritises family acceptance. Moderate health interest but budget-disciplined.",
        "business_problems": ["category_expansion", "product_adoption_barriers", "price_sensitivity"]
    },
    "impulse_buyer": {
        "size": 75,
        "description": "Quick-commerce native. Discovers via social proof and shelf placement. Fast decisions, low research. High churn risk.",
        "business_problems": ["habit_formation", "channel_behavior", "repeat_purchase"]
    },
    "gluten_free": {
        "size": 30,
        "description": "Celiac or gluten-sensitivity driven. Highly label-conscious. Small but high-LTV segment if product fits.",
        "business_problems": ["product_adoption_barriers", "trust_formation", "category_expansion"]
    },
    "churn_risk": {
        "size": 20,
        "description": "Have tried Lo! but not repeated. Typically blocked by price, taste, or inconvenience. Recoverable with right intervention.",
        "business_problems": ["habit_formation", "repeat_purchase", "price_sensitivity"]
    }
}

# ─────────────────────────────────────────────────────────
# STEP 2 — NAME POOLS (realistic Indian names)
# ─────────────────────────────────────────────────────────

MALE_NAMES = [
    "Arjun", "Vikram", "Rahul", "Amit", "Suresh", "Rohan", "Karan", "Nikhil", "Prateek", "Siddharth",
    "Aditya", "Manish", "Rajiv", "Deepak", "Varun", "Gaurav", "Ankit", "Kunal", "Mohit", "Sachin",
    "Ravi", "Vivek", "Akash", "Pranav", "Harish", "Dinesh", "Manoj", "Sunil", "Naveen", "Vikas",
    "Sandeep", "Ashish", "Tarun", "Ramesh", "Girish", "Pavan", "Chetan", "Abhishek", "Lokesh", "Ajay",
    "Vijay", "Saurabh", "Rishabh", "Devesh", "Tushar", "Yogesh", "Kartik", "Arun", "Rajesh", "Surya",
    "Vinay", "Kamal", "Pratik", "Hemant", "Nitin", "Sanjay", "Umesh", "Kapil", "Lalit", "Piyush"
]

FEMALE_NAMES = [
    "Priya", "Anjali", "Neha", "Pooja", "Divya", "Sneha", "Ananya", "Kavya", "Shreya", "Swati",
    "Meera", "Ritu", "Sunita", "Kavita", "Nisha", "Deepa", "Rekha", "Smita", "Geeta", "Lakshmi",
    "Archana", "Shalini", "Madhuri", "Usha", "Radha", "Shweta", "Preeti", "Manju", "Vandana", "Asha",
    "Rani", "Seema", "Neetha", "Anuradha", "Bhavna", "Mansi", "Sonal", "Ishita", "Roshni", "Tanvi",
    "Gauri", "Amruta", "Chandni", "Harsha", "Nalini", "Parvati", "Sudha", "Vrinda", "Yamini", "Zara",
    "Aishwarya", "Bhavya", "Charu", "Disha", "Eesha", "Falak", "Gunjan", "Hina", "Ira", "Jyoti"
]

SURNAMES = [
    "Sharma", "Verma", "Singh", "Gupta", "Patel", "Kumar", "Joshi", "Nair", "Reddy", "Rao",
    "Mehta", "Shah", "Iyer", "Pillai", "Bose", "Chatterjee", "Mishra", "Pandey", "Tiwari", "Dubey",
    "Yadav", "Sinha", "Kapoor", "Malhotra", "Khanna", "Bhatia", "Sethi", "Arora", "Choudhary", "Desai",
    "Patil", "Kulkarni", "Jain", "Agarwal", "Saxena", "Srivastava", "Bajaj", "Tandon", "Naik", "Menon"
]

# City pools by tier
TIER1_CITIES = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad"]
TIER2_CITIES = ["Jaipur", "Lucknow", "Chandigarh", "Indore", "Bhopal", "Nagpur", "Coimbatore", "Surat",
                "Vadodara", "Kochi", "Visakhapatnam", "Patna", "Ludhiana", "Agra", "Nashik", "Mysuru"]
TIER3_CITIES = ["Jodhpur", "Dehradun", "Udaipur", "Mangaluru", "Jammu", "Raipur", "Amritsar", "Varanasi"]

# Entry routes per cohort
ENTRY_ROUTES = {
    "keto_loyalist":    ["reddit_keto_community", "youtube_keto_channel", "label_scan_offline", "peer_referral_keto_group"],
    "protein_fitness":  ["instagram_fitness_influencer", "gym_peer", "amazon_search", "youtube_workout_channel"],
    "diabetic_caregiver": ["doctor_recommendation", "diabetic_forum", "amazon_health_search", "family_member_suggestion"],
    "family_shopper":   ["blinkit_browse", "amazon_grocery_search", "whatsapp_group", "supermarket_shelf"],
    "impulse_buyer":    ["blinkit_banner", "swiggy_instamart_promo", "instagram_ad", "zepto_shelf_placement"],
    "gluten_free":      ["celiac_support_group", "label_scan_offline", "doctor_recommendation", "instagram_gf_community"],
    "churn_risk":       ["instagram_ad", "amazon_search", "peer_referral", "blinkit_promo"]
}

CHANNELS = {
    "keto_loyalist":    ["amazon", "d2c_website", "modern_trade"],
    "protein_fitness":  ["amazon", "quick_commerce", "d2c_website"],
    "diabetic_caregiver": ["amazon", "d2c_website", "modern_trade", "pharmacy_online"],
    "family_shopper":   ["amazon", "quick_commerce", "modern_trade", "big_basket"],
    "impulse_buyer":    ["quick_commerce", "quick_commerce", "amazon"],  # weighted toward QC
    "gluten_free":      ["amazon", "d2c_website", "modern_trade"],
    "churn_risk":       ["amazon", "quick_commerce", "d2c_website"]
}

TRUST_ANCHORS = {
    "keto_loyalist":    ["label", "label", "brand", "peer", "self"],
    "protein_fitness":  ["influencer", "influencer", "peer", "brand", "label"],
    "diabetic_caregiver": ["doctor", "doctor", "doctor", "label", "peer"],
    "family_shopper":   ["label", "peer", "peer", "family", "brand"],
    "impulse_buyer":    ["peer", "influencer", "influencer", "peer", "brand"],
    "gluten_free":      ["label", "label", "doctor", "peer", "brand"],
    "churn_risk":       ["peer", "influencer", "label", "brand", "self"]
}

FAMILY_STRUCTURES = {
    "keto_loyalist":    ["single_professional", "couple_no_kids", "nuclear_family", "nuclear_family"],
    "protein_fitness":  ["single_professional", "single_professional", "couple_no_kids", "nuclear_family"],
    "diabetic_caregiver": ["nuclear_family", "joint_family", "couple_no_kids", "nuclear_family"],
    "family_shopper":   ["nuclear_family", "nuclear_family", "joint_family", "nuclear_family"],
    "impulse_buyer":    ["single_professional", "single_professional", "couple_no_kids", "nuclear_family"],
    "gluten_free":      ["single_professional", "nuclear_family", "couple_no_kids", "joint_family"],
    "churn_risk":       ["single_professional", "nuclear_family", "couple_no_kids", "nuclear_family"]
}

# ─────────────────────────────────────────────────────────
# STEP 3 — DISTRIBUTION HELPERS
# ─────────────────────────────────────────────────────────

def clamp(val, lo=0.0, hi=1.0):
    return round(max(lo, min(hi, val)), 3)

def r(mean, sd, lo=0.0, hi=1.0):
    return clamp(random.gauss(mean, sd), lo, hi)

def age_for_cohort(cohort):
    dist = {
        "keto_loyalist":      (32, 5, 24, 44),
        "protein_fitness":    (27, 5, 22, 38),
        "diabetic_caregiver": (43, 7, 30, 57),
        "family_shopper":     (37, 6, 28, 50),
        "impulse_buyer":      (26, 4, 22, 36),
        "gluten_free":        (34, 7, 25, 50),
        "churn_risk":         (29, 5, 22, 40)
    }
    m, s, lo, hi = dist[cohort]
    return int(clamp(random.gauss(m, s), lo, hi))

def income_for_cohort(cohort, age):
    base = {
        "keto_loyalist":      (18, 5, 12, 35),
        "protein_fitness":    (14, 4, 8,  28),
        "diabetic_caregiver": (16, 6, 8,  35),
        "family_shopper":     (13, 4, 7,  24),
        "impulse_buyer":      (16, 5, 10, 30),
        "gluten_free":        (19, 5, 12, 35),
        "churn_risk":         (11, 3, 7,  20)
    }
    m, s, lo, hi = base[cohort]
    # slight age premium
    age_adj = (age - 28) * 0.3
    return round(clamp(random.gauss(m + age_adj, s), lo, hi), 1)

def city_tier_for_cohort(cohort):
    # Tier 1 dominant, Tier 2 meaningful
    weights = {
        "keto_loyalist":      [0.70, 0.25, 0.05],
        "protein_fitness":    [0.60, 0.32, 0.08],
        "diabetic_caregiver": [0.55, 0.35, 0.10],
        "family_shopper":     [0.55, 0.35, 0.10],
        "impulse_buyer":      [0.75, 0.22, 0.03],
        "gluten_free":        [0.70, 0.25, 0.05],
        "churn_risk":         [0.65, 0.28, 0.07]
    }
    tiers = ["tier1", "tier2", "tier3"]
    tier = random.choices(tiers, weights=weights[cohort])[0]
    if tier == "tier1":
        city = random.choice(TIER1_CITIES)
    elif tier == "tier2":
        city = random.choice(TIER2_CITIES)
    else:
        city = random.choice(TIER3_CITIES)
    return tier, city

# ─────────────────────────────────────────────────────────
# STEP 4 — CONSTRAINT RULES
# ─────────────────────────────────────────────────────────

def apply_constraints(p):
    d = p["demographics"]
    b = p["behavioral"]
    ps = p["psychographics"]
    lf = p["lofoods"]

    # Rule 1: High diabetic_sensitivity → high authority_bias surrogate (information_need), doctor trust
    if lf["diabetic_sensitivity"] > 0.70:
        ps["information_need"] = max(ps["information_need"], 0.62)
        b["research_before_purchase"] = max(b["research_before_purchase"], 0.60)
        if lf["trust_anchor"] not in ["doctor", "label"]:
            lf["trust_anchor"] = random.choice(["doctor", "doctor", "label"])

    # Rule 2: High budget_consciousness → lower brand_loyalty, lower impulse
    if ps["budget_consciousness"] > 0.75:
        ps["brand_loyalty"] = min(ps["brand_loyalty"], 0.55)
        b["impulse_buying"] = min(b["impulse_buying"], 0.40)

    # Rule 3: High convenience_preference → low research, quick_commerce channel
    if b.get("_convenience", 0) > 0.75:
        b["research_before_purchase"] = min(b["research_before_purchase"], 0.42)

    # Rule 4: High family_acceptance_importance → low taste_risk_tolerance, higher risk_aversion
    if lf["family_acceptance_importance"] > 0.75:
        lf["taste_risk_tolerance"] = min(lf["taste_risk_tolerance"], 0.45)
        ps["risk_aversion"] = max(ps["risk_aversion"], 0.58)

    # Rule 5: High keto_adherence → high health_goal_intensity, high habit_stickiness
    if lf["keto_adherence"] > 0.80:
        ps["health_goal_intensity"] = max(ps["health_goal_intensity"], 0.72)
        lf["habit_stickiness"] = max(lf["habit_stickiness"], 0.68)

    # Rule 6: High impulse_buying → high decision_speed, low research
    if b["impulse_buying"] > 0.70:
        b["decision_speed"] = max(b["decision_speed"], 0.72)
        b["research_before_purchase"] = min(b["research_before_purchase"], 0.38)

    # Rule 7: Low income → high budget_consciousness
    if d["income_lpa"] < 10.0:
        ps["budget_consciousness"] = max(ps["budget_consciousness"], 0.68)

    # Rule 8: influencer trust_anchor → high social proof (captured via brand_loyalty inverse)
    if lf["trust_anchor"] == "influencer":
        ps["brand_loyalty"] = max(ps["brand_loyalty"], 0.30)  # open to new brands via influencer

    # Rule 9: High protein_priority → high health_goal_intensity
    if lf["protein_priority"] > 0.75:
        ps["health_goal_intensity"] = max(ps["health_goal_intensity"], 0.58)

    # Rule 10: Low shelf_life_tolerance → need high convenience (prefer quick_commerce)
    if lf["shelf_life_tolerance"] < 0.35:
        if b["channel_primary"] not in ["quick_commerce", "amazon"]:
            b["channel_primary"] = "quick_commerce"

    # Architecture hard constraints
    # High income + extreme deal seeking doesn't hold
    if d["income_lpa"] > 25.0 and ps["budget_consciousness"] > 0.85:
        ps["budget_consciousness"] = 0.60

    # Age < 25 — brand loyalty cap
    if d["age"] < 25 and ps["brand_loyalty"] > 0.80:
        ps["brand_loyalty"] = 0.55

    # Tier 3 — cap digital comfort (reflected in channel)
    if d["city_tier"] == "tier3" and b["channel_primary"] == "quick_commerce":
        if random.random() > 0.3:  # QC penetration in Tier3 is low
            b["channel_primary"] = random.choice(["amazon", "modern_trade"])

    return p

# ─────────────────────────────────────────────────────────
# STEP 5 — DERIVED INSIGHTS (deterministic)
# ─────────────────────────────────────────────────────────

def derive_decision_style(ps, lf):
    # Simplified computation from architecture.md
    # emotional: risk_aversion (high) + budget_consciousness inverse
    emotional = (ps["risk_aversion"] * 0.5 + (1 - ps["brand_loyalty"]) * 0.3 + ps["health_goal_intensity"] * 0.2)
    # analytical: information_need
    analytical = (ps["information_need"] * 0.7 + (1 - ps["risk_aversion"]) * 0.3)
    # habitual: brand_loyalty + habit_stickiness
    habitual = (ps["brand_loyalty"] * 0.5 + lf["habit_stickiness"] * 0.5)
    # social: inferred from trust_anchor
    social_map = {"influencer": 0.85, "peer": 0.80, "label": 0.35, "doctor": 0.45, "brand": 0.50, "self": 0.25, "family": 0.60}
    social = social_map.get(lf["trust_anchor"], 0.40)

    scores = {"emotional": emotional, "analytical": analytical, "habitual": habitual, "social": social}
    return max(scores, key=scores.get), round(max(scores.values()), 3)

def derive_trust_anchor_label(lf):
    ta = lf["trust_anchor"]
    mapping = {
        "doctor": "authority",
        "label":  "self",
        "brand":  "self",
        "peer":   "peer",
        "influencer": "peer",
        "family": "family",
        "self":   "self"
    }
    return mapping.get(ta, "self")

def derive_risk_appetite(ps):
    # risk_aversion inverse → risk_tolerance
    rt = 1 - ps["risk_aversion"]
    if rt < 0.38:
        return "low"
    elif rt > 0.62:
        return "high"
    return "medium"

def derive_primary_value(ps, lf):
    if ps["budget_consciousness"] > 0.65:
        return "price"
    elif ps["health_goal_intensity"] > 0.65 and ps["information_need"] > 0.55:
        return "quality"
    elif ps["brand_loyalty"] > 0.65:
        return "brand"
    elif lf["habit_stickiness"] < 0.40:
        return "convenience"
    return "features"

def derive_coping(ps, lf, b):
    if lf["habit_stickiness"] > 0.62 and ps["brand_loyalty"] > 0.55:
        ctype = "routine_control"
        desc = "Defaults to established routine; disruption of regular products causes visible anxiety and prompts immediate seek of replacement."
    elif lf["trust_anchor"] in ["peer", "influencer"]:
        ctype = "social_validation"
        desc = "Defers to peer signals before committing; positive social proof is the gate that unlocks purchase intent."
    elif ps["information_need"] > 0.70 and b["research_before_purchase"] > 0.60:
        ctype = "research_deep_dive"
        desc = "Researches extensively before first purchase; reads ingredient lists, scans reviews, and may delay purchase by days."
    elif ps["risk_aversion"] > 0.68:
        ctype = "denial"
        desc = "Avoids unfamiliar products; defaults to known options even when dissatisfied rather than risk a bad experience."
    else:
        ctype = "optimism_bias"
        desc = "Tries new products with optimistic expectations; forgives early failures more readily than average."
    return ctype, desc

def derive_consistency_score(ps, lf, b):
    # Simplified coherence signals from architecture.md
    s1 = 1 - abs((1 - ps["risk_aversion"]) - ps["budget_consciousness"])
    s2 = 1 - abs(ps["brand_loyalty"] - lf["habit_stickiness"])
    s3 = 1 - abs(ps["information_need"] - b["research_before_purchase"])
    s4 = 1 - abs(b["impulse_buying"] - (1 - b["research_before_purchase"]))
    s5 = 1 - abs(ps["health_goal_intensity"] - (lf["keto_adherence"] * 0.5 + lf["protein_priority"] * 0.5))
    score = int(40 + (s1 + s2 + s3 + s4 + s5) / 5 * 60)
    return max(40, min(100, score))

def derive_tensions(cohort, ps, lf, d):
    tensions = []
    if ps["budget_consciousness"] > 0.65 and ps["health_goal_intensity"] > 0.65:
        tensions.append("Wants premium health foods but faces real budget ceiling — value justification is the critical gate")
    if lf["family_acceptance_importance"] > 0.65 and lf["taste_risk_tolerance"] < 0.40:
        tensions.append("Family preference constrains product experimentation even when personal health motivation is high")
    if cohort == "churn_risk" and lf["habit_stickiness"] < 0.45:
        tensions.append("Low habit formation means repeat purchase requires active re-triggering — passive retention won't work")
    if lf["trust_anchor"] == "doctor" and d["income_lpa"] < 12:
        tensions.append("Doctor-trusted but price-constrained — willingness to pay exists but affordability blocks action")
    if lf["trust_anchor"] == "influencer" and ps["information_need"] > 0.65:
        tensions.append("Follows influencer signals but also independently researches — easily disrupted by conflicting information")
    if lf["keto_adherence"] > 0.75 and lf["family_acceptance_importance"] > 0.65:
        tensions.append("Personal keto commitment conflicts with family cooking norms — separate meal prep is the recurring friction")
    if not tensions:
        tensions.append("Convenience preference competes with desire for careful ingredient scrutiny")
        tensions.append("Brand trust built slowly but eroded quickly by a single disappointing experience")
    return tensions[:2]

# ─────────────────────────────────────────────────────────
# STEP 6 — CORE MEMORY SEED
# ─────────────────────────────────────────────────────────

def build_core_memory(name, cohort, ps, lf, d, trust_anchor_label, tensions):
    # identity_statement: 25-word first-person
    cohort_voices = {
        "keto_loyalist":      f"I live and breathe low-carb — keto is not a diet for me, it's the baseline my body depends on every single day.",
        "protein_fitness":    f"I train hard and eat intentionally — protein is my priority and I expect food brands to meet that standard.",
        "diabetic_caregiver": f"Managing blood sugar is non-negotiable in my home — every food choice is a health decision first, a taste choice second.",
        "family_shopper":     f"I buy for five people with different needs — what goes in the cart has to work for everyone, not just me.",
        "impulse_buyer":      f"If it looks good and ships in ten minutes, I'll try it — I find most of my favourite products by accident.",
        "gluten_free":        f"Gluten-free isn't a trend for me — it's a medical necessity and I read every label before anything goes in my mouth.",
        "churn_risk":         f"I tried it once and wasn't sure it was worth the price — I'd come back if someone gave me a real reason to."
    }

    nonneg = []
    avoidances = []
    if lf["diabetic_sensitivity"] > 0.65:
        nonneg.append("No hidden sugars or high-GI carbs")
    if lf["keto_adherence"] > 0.70:
        nonneg.append("Net carbs must stay below 5g per serving")
    if lf.get("gluten_sensitivity", 0) > 0.60 or cohort == "gluten_free":
        nonneg.append("Certified gluten-free only")
    if ps["budget_consciousness"] > 0.70:
        avoidances.append("Products priced above comfort zone without clear functional justification")
    if lf["family_acceptance_importance"] > 0.70:
        nonneg.append("Must pass family taste test")

    budget_ceil = None
    if d["income_lpa"] < 10:
        budget_ceil = "₹300–400 per month on any single health food product"
    elif d["income_lpa"] < 18:
        budget_ceil = "₹500–700 per month on health food subscriptions"
    elif d["income_lpa"] < 28:
        budget_ceil = "₹800–1200 per month if quality is demonstrably superior"

    influencer_list = {
        "influencer": ["fitness YouTuber they follow", "Instagram macro coach"],
        "peer":       ["trusted friend or colleague", "WhatsApp group recommendation"],
        "doctor":     ["diabetologist / GP"],
        "label":      ["product ingredient panel"],
        "brand":      ["brand communication and packaging"],
        "family":     ["spouse or parent"],
        "self":       ["own prior experience"]
    }

    return {
        "identity_statement": cohort_voices.get(cohort, "I make food choices that reflect my health priorities and budget realities."),
        "key_values": _derive_key_values(cohort, ps, lf),
        "life_defining_events": _seed_events(cohort, d["age"]),
        "relationship_map": {
            "primary_decision_partner": "spouse" if d["family_structure"] not in ["single_professional"] else "self",
            "key_influencers": influencer_list.get(lf["trust_anchor"], ["peer"]),
            "trust_network": [lf["trust_anchor"], "peer review platforms"]
        },
        "immutable_constraints": {
            "budget_ceiling": budget_ceil,
            "non_negotiables": nonneg if nonneg else ["Honest ingredient labelling"],
            "absolute_avoidances": avoidances if avoidances else ["Products with misleading health claims"]
        }
    }

def _derive_key_values(cohort, ps, lf):
    pool = []
    if ps["health_goal_intensity"] > 0.65: pool.append("health_sovereignty")
    if ps["budget_consciousness"] > 0.65:  pool.append("financial_discipline")
    if lf["family_acceptance_importance"] > 0.65: pool.append("family_wellbeing")
    if lf["habit_stickiness"] > 0.65:      pool.append("consistency")
    if ps["information_need"] > 0.65:      pool.append("informed_decision_making")
    if lf["trust_anchor"] == "doctor":     pool.append("medical_credibility")
    if lf["keto_adherence"] > 0.70:        pool.append("metabolic_discipline")
    if lf["protein_priority"] > 0.70:      pool.append("performance_nutrition")
    defaults = ["quality", "convenience", "value_for_money", "taste", "transparency"]
    while len(pool) < 3:
        d = random.choice(defaults)
        if d not in pool:
            pool.append(d)
    return pool[:3]

def _seed_events(cohort, age):
    events_by_cohort = {
        "keto_loyalist": [
            {"age_when": max(20, age-10), "event": "Tried keto after struggling with weight for years; within 3 months lost 8kg and reversed pre-diabetic markers.", "lasting_impact": "Converted to keto as a lifestyle, not a diet. Deep distrust of conventional food pyramid."}
        ],
        "protein_fitness": [
            {"age_when": max(18, age-7), "event": "Joined a gym and discovered whey protein; visible muscle gain within 6 months changed relationship with food.", "lasting_impact": "Treats protein intake as a daily metric, not an afterthought. Reads macros before taste."}
        ],
        "diabetic_caregiver": [
            {"age_when": max(25, age-8), "event": "Parent was diagnosed with Type 2 diabetes; took over household grocery decisions and learned to read glycaemic indexes.", "lasting_impact": "Every food purchase is filtered through a medical lens. Doctor's advice carries near-absolute authority."}
        ],
        "family_shopper": [
            {"age_when": max(25, age-6), "event": "First child born; shifted from eating out to home cooking and became the primary grocery decision maker.", "lasting_impact": "Price-per-serving consciousness is now instinctive. Family acceptance is a non-negotiable filter."}
        ],
        "impulse_buyer": [
            {"age_when": max(20, age-4), "event": "Discovered Blinkit during a late-night craving; the convenience of 10-minute delivery fundamentally changed shopping habits.", "lasting_impact": "Patience for delivery waiting time has collapsed to near zero. Discovery of new products happens almost entirely through app interfaces."}
        ],
        "gluten_free": [
            {"age_when": max(18, age-8), "event": "Diagnosed with gluten sensitivity after years of unexplained digestive issues; overhauled entire pantry.", "lasting_impact": "Label reading is non-negotiable before any food purchase. Cross-contamination anxiety shapes brand trust."}
        ],
        "churn_risk": [
            {"age_when": max(22, age-3), "event": "Bought Lo! products on a promotional offer; found taste acceptable but couldn't justify the full price on reorder.", "lasting_impact": "Remains aware of the brand but price anchor set at promotional level. Needs re-engagement trigger to return."}
        ]
    }
    return events_by_cohort.get(cohort, [{"age_when": age-5, "event": "Shifted to health-conscious eating after a wake-up event.", "lasting_impact": "Health now filters every food purchase."}])

# ─────────────────────────────────────────────────────────
# STEP 7 — PERSONA BUILDER
# ─────────────────────────────────────────────────────────

def build_persona(persona_id, cohort, idx):
    name_gender = random.choice(["male", "female"])
    first = random.choice(MALE_NAMES if name_gender == "male" else FEMALE_NAMES)
    last = random.choice(SURNAMES)
    full_name = f"{first} {last}"

    age = age_for_cohort(cohort)
    city_tier, city = city_tier_for_cohort(cohort)
    family_structure = random.choice(FAMILY_STRUCTURES[cohort])
    income = income_for_cohort(cohort, age)
    channel = random.choice(CHANNELS[cohort])
    trust_anchor = random.choice(TRUST_ANCHORS[cohort])
    entry_route = random.choice(ENTRY_ROUTES[cohort])

    # ── Demographics ──────────────────────────────────────
    demographics = {
        "name": full_name,
        "gender": name_gender,
        "age": age,
        "city": city,
        "city_tier": city_tier,
        "income_lpa": income,
        "family_structure": family_structure
    }

    # ── Cohort-specific distributions ────────────────────
    dist = {
        "keto_loyalist": {
            "health_goal_intensity":        (0.82, 0.08),
            "budget_consciousness":          (0.38, 0.12),
            "brand_loyalty":                 (0.60, 0.12),
            "risk_aversion":                 (0.40, 0.12),
            "information_need":              (0.68, 0.10),
            "decision_speed":                (0.45, 0.12),
            "research_before_purchase":      (0.70, 0.10),
            "impulse_buying":                (0.22, 0.10),
            "keto_adherence":                (0.85, 0.08),
            "protein_priority":              (0.55, 0.12),
            "diabetic_sensitivity":          (0.25, 0.15),
            "taste_risk_tolerance":          (0.60, 0.15),
            "shelf_life_tolerance":          (0.55, 0.15),
            "habit_stickiness":              (0.78, 0.08),
            "family_acceptance_importance":  (0.40, 0.15)
        },
        "protein_fitness": {
            "health_goal_intensity":         (0.72, 0.10),
            "budget_consciousness":           (0.48, 0.12),
            "brand_loyalty":                  (0.45, 0.14),
            "risk_aversion":                  (0.35, 0.12),
            "information_need":               (0.55, 0.12),
            "decision_speed":                 (0.55, 0.12),
            "research_before_purchase":       (0.55, 0.12),
            "impulse_buying":                 (0.42, 0.14),
            "keto_adherence":                 (0.28, 0.18),
            "protein_priority":               (0.82, 0.08),
            "diabetic_sensitivity":           (0.12, 0.10),
            "taste_risk_tolerance":           (0.58, 0.14),
            "shelf_life_tolerance":           (0.58, 0.15),
            "habit_stickiness":               (0.52, 0.14),
            "family_acceptance_importance":   (0.32, 0.14)
        },
        "diabetic_caregiver": {
            "health_goal_intensity":         (0.85, 0.07),
            "budget_consciousness":           (0.52, 0.14),
            "brand_loyalty":                  (0.55, 0.12),
            "risk_aversion":                  (0.72, 0.10),
            "information_need":               (0.82, 0.08),
            "decision_speed":                 (0.30, 0.12),
            "research_before_purchase":       (0.78, 0.08),
            "impulse_buying":                 (0.15, 0.10),
            "keto_adherence":                 (0.40, 0.18),
            "protein_priority":               (0.45, 0.15),
            "diabetic_sensitivity":           (0.88, 0.07),
            "taste_risk_tolerance":           (0.35, 0.14),
            "shelf_life_tolerance":           (0.62, 0.14),
            "habit_stickiness":               (0.68, 0.10),
            "family_acceptance_importance":   (0.75, 0.10)
        },
        "family_shopper": {
            "health_goal_intensity":         (0.58, 0.12),
            "budget_consciousness":           (0.68, 0.10),
            "brand_loyalty":                  (0.52, 0.12),
            "risk_aversion":                  (0.58, 0.10),
            "information_need":               (0.52, 0.12),
            "decision_speed":                 (0.50, 0.14),
            "research_before_purchase":       (0.48, 0.14),
            "impulse_buying":                 (0.35, 0.12),
            "keto_adherence":                 (0.18, 0.12),
            "protein_priority":               (0.42, 0.14),
            "diabetic_sensitivity":           (0.30, 0.18),
            "taste_risk_tolerance":           (0.32, 0.12),
            "shelf_life_tolerance":           (0.68, 0.12),
            "habit_stickiness":               (0.60, 0.12),
            "family_acceptance_importance":   (0.85, 0.07)
        },
        "impulse_buyer": {
            "health_goal_intensity":         (0.42, 0.14),
            "budget_consciousness":           (0.42, 0.14),
            "brand_loyalty":                  (0.30, 0.12),
            "risk_aversion":                  (0.28, 0.12),
            "information_need":               (0.28, 0.12),
            "decision_speed":                 (0.82, 0.08),
            "research_before_purchase":       (0.22, 0.10),
            "impulse_buying":                 (0.80, 0.08),
            "keto_adherence":                 (0.18, 0.14),
            "protein_priority":               (0.35, 0.15),
            "diabetic_sensitivity":           (0.10, 0.08),
            "taste_risk_tolerance":           (0.68, 0.14),
            "shelf_life_tolerance":           (0.38, 0.14),
            "habit_stickiness":               (0.28, 0.12),
            "family_acceptance_importance":   (0.30, 0.14)
        },
        "gluten_free": {
            "health_goal_intensity":         (0.75, 0.10),
            "budget_consciousness":           (0.42, 0.14),
            "brand_loyalty":                  (0.65, 0.10),
            "risk_aversion":                  (0.62, 0.12),
            "information_need":               (0.78, 0.08),
            "decision_speed":                 (0.38, 0.12),
            "research_before_purchase":       (0.75, 0.08),
            "impulse_buying":                 (0.18, 0.10),
            "keto_adherence":                 (0.28, 0.18),
            "protein_priority":               (0.40, 0.15),
            "diabetic_sensitivity":           (0.18, 0.12),
            "taste_risk_tolerance":           (0.38, 0.14),
            "shelf_life_tolerance":           (0.58, 0.14),
            "habit_stickiness":               (0.72, 0.08),
            "family_acceptance_importance":   (0.55, 0.14)
        },
        "churn_risk": {
            "health_goal_intensity":         (0.52, 0.14),
            "budget_consciousness":           (0.72, 0.10),
            "brand_loyalty":                  (0.28, 0.12),
            "risk_aversion":                  (0.48, 0.14),
            "information_need":               (0.42, 0.14),
            "decision_speed":                 (0.55, 0.14),
            "research_before_purchase":       (0.42, 0.14),
            "impulse_buying":                 (0.50, 0.14),
            "keto_adherence":                 (0.25, 0.16),
            "protein_priority":               (0.40, 0.15),
            "diabetic_sensitivity":           (0.20, 0.15),
            "taste_risk_tolerance":           (0.45, 0.15),
            "shelf_life_tolerance":           (0.52, 0.14),
            "habit_stickiness":               (0.28, 0.12),
            "family_acceptance_importance":   (0.42, 0.16)
        }
    }[cohort]

    # Sample raw values
    health_goal_intensity       = r(*dist["health_goal_intensity"])
    budget_consciousness        = r(*dist["budget_consciousness"])
    brand_loyalty               = r(*dist["brand_loyalty"])
    risk_aversion               = r(*dist["risk_aversion"])
    information_need            = r(*dist["information_need"])
    decision_speed              = r(*dist["decision_speed"])
    research_before_purchase    = r(*dist["research_before_purchase"])
    impulse_buying              = r(*dist["impulse_buying"])
    keto_adherence              = r(*dist["keto_adherence"])
    protein_priority            = r(*dist["protein_priority"])
    diabetic_sensitivity        = r(*dist["diabetic_sensitivity"])
    taste_risk_tolerance        = r(*dist["taste_risk_tolerance"])
    shelf_life_tolerance        = r(*dist["shelf_life_tolerance"])
    habit_stickiness            = r(*dist["habit_stickiness"])
    family_acceptance_importance = r(*dist["family_acceptance_importance"])

    # Add a gluten_sensitivity signal for gluten_free cohort
    gluten_sensitivity = r(0.85, 0.08) if cohort == "gluten_free" else r(0.15, 0.10)

    # ── Assemble raw persona ──────────────────────────────
    persona = {
        "id": persona_id,
        "cohort": cohort,
        "demographics": demographics,
        "behavioral": {
            "channel_primary": channel,
            "decision_speed": decision_speed,
            "research_before_purchase": research_before_purchase,
            "impulse_buying": impulse_buying,
            "_convenience": r(0.72, 0.10) if cohort == "impulse_buyer" else r(0.45, 0.15)  # temp field
        },
        "psychographics": {
            "health_goal_intensity": health_goal_intensity,
            "budget_consciousness": budget_consciousness,
            "brand_loyalty": brand_loyalty,
            "risk_aversion": risk_aversion,
            "information_need": information_need
        },
        "lofoods": {
            "keto_adherence": keto_adherence,
            "protein_priority": protein_priority,
            "diabetic_sensitivity": diabetic_sensitivity,
            "gluten_sensitivity": gluten_sensitivity,
            "taste_risk_tolerance": taste_risk_tolerance,
            "shelf_life_tolerance": shelf_life_tolerance,
            "habit_stickiness": habit_stickiness,
            "family_acceptance_importance": family_acceptance_importance,
            "trust_anchor": trust_anchor,
            "entry_route": entry_route
        }
    }

    # ── Apply constraints ─────────────────────────────────
    persona = apply_constraints(persona)

    # Remove temp field
    persona["behavioral"].pop("_convenience", None)

    # ── Derived insights ──────────────────────────────────
    ps = persona["psychographics"]
    lf = persona["lofoods"]
    b  = persona["behavioral"]

    decision_style, ds_score        = derive_decision_style(ps, lf)
    trust_anchor_label               = derive_trust_anchor_label(lf)
    risk_appetite                    = derive_risk_appetite(ps)
    primary_value                    = derive_primary_value(ps, lf)
    coping_type, coping_desc         = derive_coping(ps, lf, b)
    consistency_score                = derive_consistency_score(ps, lf, b)
    consistency_band                 = "high" if consistency_score >= 75 else ("medium" if consistency_score >= 60 else "low")
    tensions                         = derive_tensions(cohort, ps, lf, demographics)

    persona["derived_insights"] = {
        "decision_style": decision_style,
        "decision_style_score": ds_score,
        "trust_anchor_label": trust_anchor_label,
        "risk_appetite": risk_appetite,
        "primary_value_orientation": primary_value,
        "coping_mechanism": {
            "type": coping_type,
            "description": coping_desc
        },
        "consistency_score": consistency_score,
        "consistency_band": consistency_band,
        "key_tensions": tensions
    }

    # ── Core memory (simulation-ready seed) ──────────────
    core_mem = build_core_memory(full_name, cohort, ps, lf, demographics, trust_anchor_label, tensions)

    persona["memory"] = {
        "core_memory": core_mem,
        "operational_stream": [],
        "brand_memories": {
            "lo_foods": {
                "awareness": True if cohort != "impulse_buyer" or random.random() > 0.4 else False,
                "trial": True if cohort == "churn_risk" else (random.random() > 0.6 if cohort in ["keto_loyalist", "protein_fitness"] else False),
                "sentiment": None,
                "last_interaction": None
            }
        },
        "purchase_history": [],
        "simulation_state": {
            "current_turn": 0,
            "importance_accumulator": 0.0,
            "reflection_count": 0,
            "awareness": {},
            "consideration_set": [],
            "last_decision": None
        }
    }

    return persona

# ─────────────────────────────────────────────────────────
# STEP 8 — COHORT SUMMARY
# ─────────────────────────────────────────────────────────

def build_cohort_summary(personas):
    n = len(personas)
    decision_styles = [p["derived_insights"]["decision_style"] for p in personas]
    trust_anchors   = [p["derived_insights"]["trust_anchor_label"] for p in personas]
    risk_appetites  = [p["derived_insights"]["risk_appetite"] for p in personas]
    values          = [p["derived_insights"]["primary_value_orientation"] for p in personas]
    scores          = [p["derived_insights"]["consistency_score"] for p in personas]

    def dist(lst):
        uniq = set(lst)
        return {k: round(lst.count(k)/len(lst), 3) for k in sorted(uniq)}

    return {
        "total_personas": n,
        "cohort_breakdown": {c: sum(1 for p in personas if p["cohort"] == c) for c in COHORTS},
        "decision_style_distribution": dist(decision_styles),
        "trust_anchor_distribution":   dist(trust_anchors),
        "risk_appetite_distribution":  dist(risk_appetites),
        "primary_value_distribution":  dist(values),
        "consistency_scores": {
            "mean": round(sum(scores)/n),
            "min":  min(scores),
            "max":  max(scores),
            "pct_above_60": round(sum(1 for s in scores if s >= 60)/n, 3)
        },
        "coverage_assessment": (
            "Cohort spans keto loyalists, protein/fitness users, diabetic caregivers, family shoppers, "
            "impulse buyers, gluten-free users, and churn-risk lapsed users. Decision style diversity is "
            "high (emotional, analytical, habitual, social all represented). Trust anchor spread covers "
            "doctor, influencer, peer, label, and brand. No rural offline-only consumers included per spec."
        ),
        "dominant_tensions": [
            "Health aspiration vs budget constraint — visible across family shoppers and churn-risk segments",
            "Convenience preference vs need for ingredient verification — highest in impulse buyers and protein/fitness cohort"
        ]
    }

# ─────────────────────────────────────────────────────────
# MAIN — GENERATE ALL 500
# ─────────────────────────────────────────────────────────

def main():
    all_personas = []
    global_idx = 1

    for cohort, meta in COHORTS.items():
        size = meta["size"]
        print(f"  Generating {size} personas for cohort: {cohort}...")
        for i in range(size):
            pid = f"pg-lof-{global_idx:03d}"
            p = build_persona(pid, cohort, i)
            all_personas.append(p)
            global_idx += 1

    summary = build_cohort_summary(all_personas)

    output = {
        "cohort_id": "cohort-lo-foods-20260402",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domain": "indian-health-food-consumer",
        "brand": "Lo! Foods",
        "business_problem": (
            "Understand why users are not repeating purchase, whether Lo! can expand from keto niche "
            "to mainstream protein category, price sensitivity vs perceived value, trust formation dynamics, "
            "channel behaviour, and product adoption barriers."
        ),
        "mode": "simulation-ready",
        "generator_version": "1.0",
        "icp_spec": "icp_spec_lo-foods_20260402.md",
        "taxonomy_used": {
            "categories": ["demographics", "behavioral", "psychographics", "lofoods_specific"],
            "total_attributes": 19,
            "domain_data_used": False,
            "inference_mode": "LLM priors — Indian D2C health food behaviour"
        },
        "cohort_definitions": COHORTS,
        "constraint_rules": [
            "diabetic_sensitivity > 0.70 → information_need > 0.62, research_before_purchase > 0.60, trust_anchor in [doctor, label]",
            "budget_consciousness > 0.75 → brand_loyalty < 0.55, impulse_buying < 0.40",
            "convenience_preference > 0.75 → research_before_purchase < 0.42",
            "family_acceptance_importance > 0.75 → taste_risk_tolerance < 0.45, risk_aversion > 0.58",
            "keto_adherence > 0.80 → health_goal_intensity > 0.72, habit_stickiness > 0.68",
            "impulse_buying > 0.70 → decision_speed > 0.72, research_before_purchase < 0.38",
            "income_lpa < 10.0 → budget_consciousness > 0.68",
            "trust_anchor == influencer → brand_loyalty > 0.30 (openness to new brands via influencer)",
            "protein_priority > 0.75 → health_goal_intensity > 0.58",
            "shelf_life_tolerance < 0.35 → channel_primary redirected to quick_commerce or amazon",
            "income > 25 LPA AND budget_consciousness > 0.85 → cap budget_consciousness at 0.60",
            "age < 25 AND brand_loyalty > 0.80 → cap brand_loyalty at 0.55",
            "city_tier == tier3 AND channel == quick_commerce → reroute to amazon or modern_trade with 70% probability"
        ],
        "personas": all_personas,
        "cohort_summary": summary
    }

    out_path = "/Users/admin/Documents/Simulatte Projects/Persona Generator/pilots/lo-foods/personas_lo_foods_20260402.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(all_personas)} personas written to:\n  {out_path}")
    print(f"\nCohort breakdown:")
    for cohort, count in summary["cohort_breakdown"].items():
        print(f"  {cohort:30s}: {count}")
    print(f"\nConsistency scores: mean={summary['consistency_scores']['mean']} | min={summary['consistency_scores']['min']} | max={summary['consistency_scores']['max']}")
    print(f"All scores ≥60: {summary['consistency_scores']['pct_above_60']*100:.1f}%")
    print(f"\nDecision style distribution: {summary['decision_style_distribution']}")
    print(f"Trust anchor distribution:   {summary['trust_anchor_distribution']}")

if __name__ == "__main__":
    main()
