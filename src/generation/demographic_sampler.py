"""Demographic anchor sampler for CLI persona generation.

Sprint 12. Generates diverse, realistic DemographicAnchor instances for
cohort generation when no explicit anchor is provided by the caller.

Diversity rules (G6):
- No single city > 20% of cohort
- No single age bracket > 40% of cohort
- ≥ 3 income brackets represented for cohorts ≥ 6

The sampler uses a round-robin pool strategy: cycle through a pool of
diverse demographic profiles so that any cohort of N ≤ pool_size is
automatically diverse across city, age, and income.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Demographic pools — all values use valid schema Literal values
# ---------------------------------------------------------------------------

_CPG_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment)
    ("Priya Mehta",     36, "female",     "India", "Maharashtra",    "Mumbai",    "metro",  "nuclear",         4, "middle",       True,  "mid-career",     "undergraduate", "full-time"),
    ("Rahul Verma",     28, "male",       "India", "Karnataka",      "Bengaluru", "metro",  "other",           1, "upper-middle", False, "early-career",   "postgraduate",  "full-time"),
    ("Sunita Devi",     45, "female",     "India", "Uttar Pradesh",  "Lucknow",   "tier2",  "joint",           6, "lower-middle", False, "mid-career",     "high-school",   "part-time"),
    ("Amit Sharma",     38, "male",       "India", "Delhi",          "Delhi",     "metro",  "nuclear",         3, "upper-middle", True,  "mid-career",     "postgraduate",  "full-time"),
    ("Deepa Nair",      31, "female",     "India", "Kerala",         "Kochi",     "tier2",  "nuclear",         3, "middle",       True,  "early-family",   "undergraduate", "full-time"),
    ("Vikram Singh",    52, "male",       "India", "Rajasthan",      "Jaipur",    "tier2",  "joint",           7, "middle",       False, "late-career",    "undergraduate", "self-employed"),
    ("Ananya Roy",      25, "female",     "India", "West Bengal",    "Kolkata",   "metro",  "other",           1, "lower-middle", False, "early-career",   "postgraduate",  "full-time"),
    ("Suresh Patel",    41, "male",       "India", "Gujarat",        "Ahmedabad", "metro",  "nuclear",         4, "upper-middle", True,  "mid-career",     "undergraduate", "full-time"),
    ("Meena Krishnan",  36, "female",     "India", "Tamil Nadu",     "Chennai",   "metro",  "nuclear",         3, "middle",       True,  "mid-career",     "postgraduate",  "full-time"),
    ("Rohit Gupta",     29, "male",       "India", "Madhya Pradesh", "Bhopal",    "tier2",  "nuclear",         2, "lower-middle", False, "early-career",   "undergraduate", "full-time"),
    ("Kavita Joshi",    48, "female",     "India", "Maharashtra",    "Pune",      "metro",  "nuclear",         4, "upper-middle", True,  "late-career",    "postgraduate",  "full-time"),
    ("Arun Nambiar",    33, "male",       "India", "Kerala",         "Thiruvananthapuram", "tier2", "nuclear", 3, "middle",       True,  "early-family",   "postgraduate",  "full-time"),
]

_SAAS_POOL = [
    ("Alex Chen",       32, "male",       "USA",  "California",     "San Francisco", "metro", "other",        1, "upper-middle", False, "early-career",  "postgraduate",  "full-time"),
    ("Sarah Johnson",   38, "female",     "USA",  "New York",       "New York",      "metro", "nuclear",      3, "upper-middle", True,  "mid-career",    "undergraduate", "full-time"),
    ("Marcus Williams", 45, "male",       "USA",  "Texas",          "Austin",        "metro", "nuclear",      4, "upper-middle", True,  "mid-career",    "undergraduate", "full-time"),
    ("Priya Patel",     29, "female",     "USA",  "Washington",     "Seattle",       "metro", "other",        1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
    ("Tom Baker",       52, "male",       "UK",   "England",        "London",        "metro", "nuclear",      4, "upper-middle", True,  "late-career",   "undergraduate", "full-time"),
    ("Emma Schmidt",    35, "female",     "Germany", "Bavaria",     "Munich",        "metro", "couple-no-kids", 2, "upper-middle", True, "mid-career",   "postgraduate",  "full-time"),
    ("Carlos Mendez",   41, "male",       "USA",  "Illinois",       "Chicago",       "metro", "nuclear",      3, "middle",       True,  "mid-career",    "undergraduate", "full-time"),
    ("Yuki Tanaka",     27, "non-binary", "USA",  "Massachusetts",  "Boston",        "metro", "other",        1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
]

_GENERAL_POOL = _CPG_POOL  # Default to CPG pool

# ---------------------------------------------------------------------------
# Lo! Foods FMCG pool — metro-first, spans all 19 archetypes (C1–C15, P1–P4)
# Ages 25–60, income middle/upper-middle, metro + select tier2 for C9/P4
# ---------------------------------------------------------------------------
_LOFOODS_FMCG_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment)
    ("Arjun Menon",       29, "male",   "India", "Karnataka",      "Bengaluru", "metro",  "other",   1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
    ("Priya Sharma",      34, "female", "India", "Maharashtra",    "Mumbai",    "metro",  "nuclear", 3, "upper-middle", True,  "early-family",  "postgraduate",  "full-time"),
    ("Karthik Rajan",     27, "male",   "India", "Tamil Nadu",     "Chennai",   "metro",  "other",   1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
    ("Nisha Agarwal",     38, "female", "India", "Delhi",          "Delhi",     "metro",  "nuclear", 4, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time"),
    ("Siddharth Iyer",    32, "male",   "India", "Telangana",      "Hyderabad", "metro",  "nuclear", 3, "middle",       True,  "early-family",  "postgraduate",  "full-time"),
    ("Riya Kapoor",       26, "female", "India", "Maharashtra",    "Pune",      "metro",  "other",   1, "upper-middle", False, "early-career",  "postgraduate",  "full-time"),
    ("Venkat Subramaniam",44, "male",   "India", "Karnataka",      "Bengaluru", "metro",  "nuclear", 4, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time"),
    ("Anita Desai",       31, "female", "India", "Delhi",          "Delhi",     "metro",  "nuclear", 3, "middle",       True,  "early-family",  "undergraduate", "full-time"),
    ("Rohan Mehta",       36, "male",   "India", "Maharashtra",    "Mumbai",    "metro",  "nuclear", 4, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time"),
    ("Divya Krishnaswamy",28, "female", "India", "Tamil Nadu",     "Chennai",   "metro",  "other",   1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
    ("Aakash Gupta",      42, "male",   "India", "Telangana",      "Hyderabad", "metro",  "nuclear", 4, "upper-middle", True,  "mid-career",    "undergraduate", "full-time"),
    ("Sheetal Joshi",     33, "female", "India", "Maharashtra",    "Pune",      "metro",  "nuclear", 3, "middle",       True,  "early-family",  "postgraduate",  "full-time"),
    ("Nikhil Bhat",       25, "male",   "India", "Karnataka",      "Bengaluru", "metro",  "other",   1, "middle",       False, "early-career",  "postgraduate",  "full-time"),
    ("Pooja Raghavan",    39, "female", "India", "Tamil Nadu",     "Chennai",   "metro",  "nuclear", 4, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time"),
    ("Sameer Khan",       30, "male",   "India", "Delhi",          "Delhi",     "metro",  "nuclear", 3, "middle",       True,  "early-family",  "undergraduate", "full-time"),
    ("Meghna Pillai",     45, "female", "India", "Kerala",         "Kochi",     "tier2",  "nuclear", 4, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time"),
    ("Raghav Pandey",     55, "male",   "India", "Delhi",          "Delhi",     "metro",  "joint",   5, "middle",       False, "late-career",   "undergraduate", "full-time"),
    ("Usha Srinivasan",   52, "female", "India", "Tamil Nadu",     "Chennai",   "metro",  "nuclear", 3, "upper-middle", True,  "late-career",   "postgraduate",  "full-time"),
    ("Deepak Jain",       47, "male",   "India", "Rajasthan",      "Jaipur",    "tier2",  "nuclear", 4, "middle",       True,  "mid-career",    "undergraduate", "self-employed"),
    ("Kavitha Nair",      35, "female", "India", "Kerala",         "Thiruvananthapuram", "tier2", "nuclear", 3, "middle", True, "early-family", "postgraduate",  "full-time"),
]

# ---------------------------------------------------------------------------
# US General Population pool — for research/credibility studies
# Designed to approximate Pew Research Center American Trends Panel (ATP)
# composition: probability-based, nationally representative US adult sample.
#
# Distribution targets (US Census 2020 + Pew ATP):
#   Gender:    52% female, 48% male
#   Age:       18-29 (16%), 30-49 (34%), 50-64 (27%), 65+ (23%)
#   Race:      63% White non-Hispanic, 12% Black, 13% Hispanic, 5% Asian, 7% other
#   Education: 30% college grad+, 28% some college, 27% HS grad, 15% <HS
#   Region:    South (38%), Midwest (21%), West (24%), Northeast (18%)
# ---------------------------------------------------------------------------
_US_GENERAL_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment, political_lean)
    #
    # Political lean distribution (n=34) calibrated against Pew 2023 party ID:
    #   conservative:       5 (15%)  target 15%
    #   lean_conservative:  7 (21%)  target 20%
    #   moderate:           9 (26%)  target 25%
    #   lean_progressive:   8 (24%)  target 22%
    #   progressive:        5 (15%)  target 18%
    # Assignments based on region, education, age, and racial identity patterns
    # from Pew Research Center 2023 Political Typology data.

    # South — female, varied age + income
    ("Patricia Williams",  43, "female", "USA", "Georgia",        "Atlanta",       "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "full-time",  "lean_conservative"),
    ("Sandra Johnson",     58, "female", "USA", "Texas",          "Houston",       "metro",    "nuclear",        3, "middle",        False, "late-career",   "high-school",   "part-time",  "conservative"),
    ("Maria Garcia",       35, "female", "USA", "Florida",        "Miami",         "metro",    "nuclear",        4, "lower-middle",  True,  "early-family",  "high-school",   "full-time",  "lean_progressive"),
    ("Linda Brown",        67, "female", "USA", "North Carolina", "Charlotte",     "metro",    "couple-no-kids", 2, "middle",        False, "retired",       "undergraduate", "retired",    "moderate"),
    ("Betty Jackson",      63, "female", "USA", "Alabama",        "Birmingham",    "tier2",    "nuclear",        3, "lower-middle",  False, "late-career",   "high-school",   "part-time",  "conservative"),
    ("Nancy Moore",        54, "female", "USA", "Iowa",           "Des Moines",    "tier2",    "nuclear",        4, "middle",        True,  "late-career",   "high-school",   "full-time",  "conservative"),

    # Midwest — male, varied age + income
    ("James Miller",       48, "male",   "USA", "Ohio",           "Columbus",      "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "undergraduate", "full-time",  "moderate"),
    ("Robert Davis",       61, "male",   "USA", "Michigan",       "Detroit",       "metro",    "nuclear",        3, "lower-middle",  False, "late-career",   "high-school",   "full-time",  "lean_conservative"),
    ("William Wilson",     38, "male",   "USA", "Illinois",       "Chicago",       "metro",    "nuclear",        4, "upper-middle",  True,  "mid-career",    "undergraduate", "full-time",  "moderate"),
    ("Thomas Anderson",    55, "male",   "USA", "Minnesota",      "Minneapolis",   "metro",    "nuclear",        3, "upper-middle",  True,  "late-career",   "postgraduate",  "full-time",  "moderate"),

    # Northeast — female, higher education
    ("Jennifer Taylor",    32, "female", "USA", "New York",       "New York",      "metro",    "other",          1, "upper-middle",  False, "early-career",  "postgraduate",  "full-time",  "progressive"),
    ("Barbara Martinez",   44, "female", "USA", "Pennsylvania",   "Philadelphia",  "metro",    "nuclear",        3, "middle",        True,  "mid-career",    "undergraduate", "full-time",  "lean_progressive"),
    ("Susan Thompson",     29, "female", "USA", "Massachusetts",  "Boston",        "metro",    "other",          2, "middle",        False, "early-career",  "postgraduate",  "full-time",  "progressive"),
    ("Dorothy White",      71, "female", "USA", "Connecticut",    "Hartford",      "metro",    "couple-no-kids", 2, "middle",        False, "retired",       "undergraduate", "retired",    "moderate"),

    # West — male, varied income
    ("Charles Harris",     36, "male",   "USA", "California",     "Los Angeles",   "metro",    "nuclear",        4, "middle",        True,  "early-family",  "high-school",   "full-time",  "lean_conservative"),
    ("Joseph Jackson",     52, "male",   "USA", "Washington",     "Seattle",       "metro",    "nuclear",        3, "upper-middle",  True,  "late-career",   "undergraduate", "full-time",  "lean_progressive"),
    ("Christopher Martin", 28, "male",   "USA", "Arizona",        "Phoenix",       "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",   "full-time",  "lean_conservative"),
    ("Daniel Thompson",    45, "male",   "USA", "Colorado",       "Denver",        "metro",    "nuclear",        4, "upper-middle",  True,  "mid-career",    "postgraduate",  "full-time",  "lean_progressive"),

    # South — male, varied
    ("Mark Taylor",        42, "male",   "USA", "Tennessee",      "Nashville",     "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "full-time",  "conservative"),
    ("Paul Rodriguez",     31, "male",   "USA", "Nevada",         "Las Vegas",     "metro",    "other",          2, "lower-middle",  False, "early-career",  "high-school",   "full-time",  "lean_conservative"),

    # Older adults — retired
    ("Helen Lewis",        74, "female", "USA", "Florida",        "Orlando",       "metro",    "couple-no-kids", 2, "middle",        False, "retired",       "high-school",   "retired",    "lean_conservative"),
    ("Frank Lee",          69, "male",   "USA", "Arizona",        "Phoenix",       "metro",    "couple-no-kids", 2, "upper-middle",  False, "retired",       "undergraduate", "retired",    "conservative"),

    # Young adults
    ("Michelle Walker",    24, "female", "USA", "Texas",          "Austin",        "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",   "full-time",  "moderate"),
    ("Kevin Hall",         22, "male",   "USA", "California",     "San Diego",     "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",   "part-time",  "lean_progressive"),
    ("Amanda Allen",       27, "female", "USA", "New York",       "Brooklyn",      "metro",    "other",          2, "middle",        False, "early-career",  "undergraduate", "full-time",  "progressive"),
    ("Ryan Young",         26, "male",   "USA", "Washington",     "Seattle",       "metro",    "other",          1, "middle",        False, "early-career",  "postgraduate",  "full-time",  "progressive"),

    # Black Americans (~12% of pool) — Pew: ~80% Dem-leaning
    ("Denise Robinson",    40, "female", "USA", "Georgia",        "Atlanta",       "metro",    "nuclear",        3, "middle",        True,  "mid-career",    "undergraduate", "full-time",  "lean_progressive"),
    ("Marcus Johnson",     33, "male",   "USA", "Illinois",       "Chicago",       "metro",    "other",          1, "middle",        False, "early-career",  "undergraduate", "full-time",  "lean_progressive"),
    ("Keisha Brown",       28, "female", "USA", "Texas",          "Dallas",        "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",   "full-time",  "lean_progressive"),
    ("Darnell Williams",   55, "male",   "USA", "Maryland",       "Baltimore",     "metro",    "nuclear",        4, "upper-middle",  True,  "late-career",   "undergraduate", "full-time",  "progressive"),

    # Hispanic Americans (~13% of pool) — Pew: majority Dem-leaning, significant moderate
    ("Carmen Lopez",       38, "female", "USA", "California",     "Los Angeles",   "metro",    "nuclear",        5, "lower-middle",  True,  "early-family",  "high-school",   "full-time",  "lean_progressive"),
    ("Miguel Hernandez",   29, "male",   "USA", "Texas",          "San Antonio",   "metro",    "nuclear",        4, "lower-middle",  True,  "early-career",  "high-school",   "full-time",  "moderate"),
    ("Rosa Gonzalez",      52, "female", "USA", "Florida",        "Miami",         "metro",    "nuclear",        4, "middle",        False, "late-career",   "high-school",   "full-time",  "lean_conservative"),
    ("Carlos Reyes",       44, "male",   "USA", "Arizona",        "Tucson",        "tier2",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "self-employed", "moderate"),

    # Sprint B-1 Fix 3: Upper-income additions (~6 personas).
    # Pew shows 34% of US adults "living comfortably" financially.
    # Prior pool had only ~21% upper-middle income → q15 financial_security collapsed.
    # These profiles raise upper-income share to ~28% of 40-persona pool.
    # Political lean kept proportional to maintain existing distribution calibration.
    ("Andrew Mitchell",    49, "male",   "USA", "Virginia",       "McLean",        "metro",    "nuclear",        4, "upper",         True,  "mid-career",    "postgraduate",  "full-time",  "lean_conservative"),
    ("Katherine Spencer",  41, "female", "USA", "Connecticut",    "Greenwich",     "metro",    "couple-no-kids", 2, "upper",         True,  "mid-career",    "postgraduate",  "full-time",  "moderate"),
    ("David Nakamura",     38, "male",   "USA", "California",     "San Francisco", "metro",    "other",          1, "upper",         False, "early-career",  "postgraduate",  "full-time",  "lean_progressive"),
    ("Elizabeth Warren",   55, "female", "USA", "Illinois",       "Chicago",       "metro",    "nuclear",        3, "upper",         True,  "late-career",   "postgraduate",  "full-time",  "lean_progressive"),
    ("Richard Coleman",    62, "male",   "USA", "Texas",          "Dallas",        "metro",    "couple-no-kids", 2, "upper",         False, "retired",       "undergraduate", "retired",    "conservative"),
    ("Laura Fitzgerald",   46, "female", "USA", "Massachusetts",  "Cambridge",     "metro",    "nuclear",        3, "upper",         True,  "mid-career",    "postgraduate",  "full-time",  "progressive"),
]

# WorldviewAnchor base dimensions per political lean.
# (institutional_trust, social_change_pace, collectivism_score, economic_security_priority)
# Derived from Pew Research "Political Typology" 2023 attitudinal data.
# institutional_trust here represents a general composite (govt + media + science),
# which the AttributeFiller then splits into three distinct taxonomy attrs with offsets.
_WORLDVIEW_BASE_DIMS: dict[str, tuple[float, float, float, float]] = {
    "conservative":      (0.35, 0.18, 0.30, 0.28),
    "lean_conservative": (0.44, 0.33, 0.40, 0.38),
    "moderate":          (0.50, 0.50, 0.50, 0.50),
    "lean_progressive":  (0.58, 0.65, 0.60, 0.62),
    "progressive":       (0.65, 0.80, 0.68, 0.72),
}

# Religious salience per persona — personal faith/devotion dimension.
# Deliberately INDEPENDENT of institutional_trust or political lean.
# Sources: Pew Religious Landscape Survey 2023.
# Patterns: South > Midwest > West/Northeast; Black Americans high;
# Hispanic Americans moderate-high; older > younger; rural > urban.
_US_GENERAL_RELIGIOUS_SALIENCE: dict[str, float] = {
    # South — female
    "Patricia Williams":   0.70,
    "Sandra Johnson":      0.75,
    "Maria Garcia":        0.60,   # Hispanic Catholic, FL
    "Linda Brown":         0.55,
    "Betty Jackson":       0.80,   # Alabama, conservative
    "Nancy Moore":         0.65,   # Iowa
    # Midwest — male
    "James Miller":        0.50,
    "Robert Davis":        0.55,
    "William Wilson":      0.35,   # urban Chicago
    "Thomas Anderson":     0.40,
    # Northeast — female
    "Jennifer Taylor":     0.20,   # NYC, progressive
    "Barbara Martinez":    0.45,
    "Susan Thompson":      0.15,   # Boston, progressive
    "Dorothy White":       0.50,   # older, CT
    # West — male
    "Charles Harris":      0.45,
    "Joseph Jackson":      0.30,   # Seattle, lean_progressive
    "Christopher Martin":  0.40,
    "Daniel Thompson":     0.30,   # Denver, lean_progressive
    # South — male
    "Mark Taylor":         0.75,   # Tennessee, conservative
    "Paul Rodriguez":      0.45,
    # Older adults
    "Helen Lewis":         0.60,
    "Frank Lee":           0.55,
    # Young adults — lower overall
    "Michelle Walker":     0.45,
    "Kevin Hall":          0.20,
    "Amanda Allen":        0.18,
    "Ryan Young":          0.15,
    # Black Americans — high per Pew (78% say religion very/somewhat important)
    "Denise Robinson":     0.75,
    "Marcus Johnson":      0.65,
    "Keisha Brown":        0.70,
    "Darnell Williams":    0.65,
    # Hispanic Americans — moderate-high (Catholic majority)
    "Carmen Lopez":        0.65,
    "Miguel Hernandez":    0.60,
    "Rosa Gonzalez":       0.70,
    "Carlos Reyes":        0.55,
    # Sprint B-1 Fix 3: Upper-income additions
    "Andrew Mitchell":     0.45,   # Virginia suburban, moderate church attendance
    "Katherine Spencer":   0.30,   # Greenwich CT, secular professional
    "David Nakamura":      0.15,   # SF tech, progressive, secular
    "Elizabeth Warren":    0.25,   # Chicago professional, progressive
    "Richard Coleman":     0.55,   # Dallas retiree, conservative Protestant
    "Laura Fitzgerald":    0.20,   # Cambridge academic, progressive, secular
}

# Temporal political era for us_general studies.
# Reflects the governing party at the time of study generation.
# April 2026 → Trump second term (Republican, Jan 2025–).
# Update this string if running studies under a different administration.
_US_POLITICAL_ERA = "Republican administration in power (Trump, Jan 2025–)"

# ---------------------------------------------------------------------------
# India General Population pool — for Study 1B Pew India replication.
# Approximates nationally representative Indian adults across religion,
# region, caste, urban tier, income, and BJP/opposition political lean.
#
# Political lean distribution (n=40, BJP-era calibrated):
#   bjp_supporter:   7 (18%)  → BJP very favorable 42%
#   bjp_lean:        8 (20%)  → BJP somewhat favorable 31%
#   neutral:        10 (25%)  → pragmatic / issue-based
#   opposition_lean: 8 (20%)  → INC somewhat favorable 37%
#   opposition:      7 (18%)  → BJP very unfavorable + strong INC
#
# Religion:  Hindu 80%, Muslim 13%, Sikh 5%, Christian 5% (slightly oversampled)
# Caste:     General 37%, OBC 41%, SC 13%, ST 6%  (Hindu only)
# Region:    North 33%, South 23%, West 20%, East/NE 20%, Mixed 5%
# ---------------------------------------------------------------------------
_INDIA_GENERAL_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment, political_lean, religion, caste)
    #
    # NORTH — Hindi belt
    ("Rajesh Sharma",        42, "male",   "India", "Uttar Pradesh", "Lucknow",           "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "bjp_supporter",  "hindu",    "general"),
    ("Sunita Gupta",         35, "female", "India", "Delhi",         "New Delhi",         "metro",  "nuclear",        4, "middle",  False, "early-family",  "undergraduate", "full-time",     "bjp_lean",       "hindu",    "general"),
    ("Vikram Singh",         50, "male",   "India", "Haryana",       "Gurgaon",           "metro",  "nuclear",        5, "upper",   True,  "late-career",   "postgraduate",  "full-time",     "bjp_lean",       "hindu",    "general"),
    ("Meera Agarwal",        28, "female", "India", "Rajasthan",     "Jaipur",            "metro",  "other",          2, "middle",  False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",    "general"),
    ("Ram Prasad Yadav",     55, "male",   "India", "Uttar Pradesh", "Gorakhpur",         "tier2",  "nuclear",        6, "lower",   False, "late-career",   "high-school",     "full-time",     "bjp_supporter",  "hindu",    "obc"),
    ("Savitri Devi",         48, "female", "India", "Bihar",         "Patna",             "tier2",  "nuclear",        5, "lower",   False, "mid-career",    "high-school",       "part-time",     "bjp_lean",       "hindu",    "obc"),
    ("Suresh Kumar",         32, "male",   "India", "Madhya Pradesh","Bhopal",            "metro",  "other",          3, "lower",   False, "early-career",  "high-school",     "full-time",     "neutral",        "hindu",    "obc"),
    ("Poonam Verma",         40, "female", "India", "Uttar Pradesh", "Varanasi",          "tier2",  "nuclear",        4, "lower",   True,  "mid-career",    "high-school",     "part-time",     "bjp_supporter",  "hindu",    "general"),
    ("Ramesh Chamar",        38, "male",   "India", "Punjab",        "Ludhiana",          "metro",  "nuclear",        4, "lower",   False, "mid-career",    "high-school",     "full-time",     "opposition_lean","hindu",    "sc"),
    ("Kamla Devi",           52, "female", "India", "Uttar Pradesh", "Agra",              "tier2",  "nuclear",        5, "lower",   False, "late-career",   "high-school",       "part-time",     "opposition",     "hindu",    "sc"),
    ("Mohammad Iqbal",       44, "male",   "India", "Uttar Pradesh", "Lucknow",           "metro",  "nuclear",        5, "lower",   True,  "mid-career",    "high-school",     "full-time",     "opposition",     "muslim",   "obc"),
    ("Fatima Begum",         33, "female", "India", "West Bengal",   "Kolkata",           "metro",  "nuclear",        4, "lower",   False, "early-family",  "high-school",     "homemaker",     "opposition",     "muslim",   "general"),
    # SOUTH — Dravidian / regional
    ("Venkatesh Iyer",       45, "male",   "India", "Tamil Nadu",    "Chennai",           "metro",  "nuclear",        3, "upper",   True,  "mid-career",    "postgraduate",  "full-time",     "neutral",        "hindu",    "general"),
    ("Lakshmi Nair",         38, "female", "India", "Kerala",        "Kochi",             "metro",  "nuclear",        3, "middle",  True,  "mid-career",    "postgraduate",  "full-time",     "opposition_lean","hindu",    "general"),
    ("Suresh Reddy",         52, "male",   "India", "Telangana",     "Hyderabad",         "metro",  "nuclear",        4, "upper",   True,  "late-career",   "postgraduate",  "full-time",     "bjp_lean",       "hindu",    "general"),
    ("Priya Krishnamurthy",  29, "female", "India", "Karnataka",     "Bengaluru",         "metro",  "other",          2, "middle",  False, "early-career",  "postgraduate",  "full-time",     "neutral",        "hindu",    "general"),
    ("Murugan Pillai",       60, "male",   "India", "Tamil Nadu",    "Madurai",           "tier2",  "couple-no-kids", 2, "lower",   False, "retired",       "high-school",     "retired",       "opposition",     "hindu",    "obc"),
    ("Geetha Rani",          42, "female", "India", "Andhra Pradesh","Vijayawada",        "tier2",  "nuclear",        4, "lower",   False, "mid-career",    "high-school",     "part-time",     "neutral",        "hindu",    "obc"),
    ("Thomas Mathew",        48, "male",   "India", "Kerala",        "Thiruvananthapuram","metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "opposition_lean","christian","general"),
    ("Mary George",          35, "female", "India", "Goa",           "Panaji",            "metro",  "nuclear",        3, "middle",  True,  "early-family",  "undergraduate", "full-time",     "neutral",        "christian","general"),
    # WEST — Maharashtra / Gujarat
    ("Amit Patel",           40, "male",   "India", "Gujarat",       "Ahmedabad",         "metro",  "nuclear",        4, "upper",   True,  "mid-career",    "undergraduate", "self-employed", "bjp_supporter",  "hindu",    "general"),
    ("Nisha Shah",           33, "female", "India", "Maharashtra",   "Mumbai",            "metro",  "other",          2, "upper",   False, "early-career",  "postgraduate",  "full-time",     "neutral",        "hindu",    "general"),
    ("Deepak Joshi",         55, "male",   "India", "Rajasthan",     "Udaipur",           "metro",  "nuclear",        5, "middle",  False, "late-career",   "undergraduate", "self-employed", "bjp_lean",       "hindu",    "general"),
    ("Bhavna Desai",         46, "female", "India", "Gujarat",       "Surat",             "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "high-school",     "part-time",     "bjp_supporter",  "hindu",    "obc"),
    ("Ganesh Patil",         38, "male",   "India", "Maharashtra",   "Pune",              "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "neutral",        "hindu",    "obc"),
    ("Salim Khan",           40, "male",   "India", "Maharashtra",   "Mumbai",            "metro",  "nuclear",        5, "lower",   False, "mid-career",    "high-school",     "self-employed", "opposition",     "muslim",   "obc"),
    # EAST / NORTHEAST
    ("Subhash Ghosh",        50, "male",   "India", "West Bengal",   "Kolkata",           "metro",  "nuclear",        3, "middle",  True,  "late-career",   "postgraduate",  "full-time",     "opposition",     "hindu",    "general"),
    ("Anjali Bose",          31, "female", "India", "West Bengal",   "Kolkata",           "metro",  "other",          2, "middle",  False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","hindu",    "general"),
    ("Prasad Mishra",        44, "male",   "India", "Odisha",        "Bhubaneswar",       "metro",  "nuclear",        4, "lower",   True,  "mid-career",    "undergraduate", "full-time",     "neutral",        "hindu",    "obc"),
    ("Birsa Munda",          36, "male",   "India", "Jharkhand",     "Ranchi",            "tier2",  "nuclear",        5, "lower",   False, "mid-career",    "high-school",       "full-time",     "opposition_lean","hindu",    "st"),
    ("Meena Oram",           48, "female", "India", "Chhattisgarh",  "Raipur",            "tier2",  "nuclear",        5, "lower",   False, "mid-career",    "high-school",       "part-time",     "neutral",        "hindu",    "st"),
    ("Raju Bora",            34, "male",   "India", "Assam",         "Guwahati",          "metro",  "nuclear",        4, "lower",   True,  "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",    "obc"),
    # SIKH — Punjab
    ("Gurpreet Singh",       45, "male",   "India", "Punjab",        "Amritsar",          "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "opposition_lean","sikh",     "general"),
    ("Harjinder Kaur",       38, "female", "India", "Punjab",        "Chandigarh",        "metro",  "nuclear",        3, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "neutral",        "sikh",     "general"),
    # YOUNG URBAN
    ("Arjun Mehta",          24, "male",   "India", "Delhi",         "New Delhi",         "metro",  "other",          1, "lower",   False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",    "general"),
    ("Neha Tiwari",          22, "female", "India", "Maharashtra",   "Mumbai",            "metro",  "other",          2, "lower",   False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",    "obc"),
    ("Kabir Hussain",        26, "male",   "India", "Karnataka",     "Bengaluru",         "metro",  "other",          1, "middle",  False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","muslim",   "general"),
    ("Priya Sharma",         23, "female", "India", "Uttar Pradesh", "Kanpur",            "metro",  "other",          2, "lower",   False, "early-career",  "undergraduate", "part-time",     "bjp_supporter",  "hindu",    "general"),
    # RETIRED / ELDERLY
    ("Ramnarayan Tripathi",  68, "male",   "India", "Uttar Pradesh", "Allahabad",         "tier2",  "couple-no-kids", 2, "lower",   False, "retired",       "high-school",     "retired",       "bjp_supporter",  "hindu",    "general"),
    ("Kamakshi Iyer",        65, "female", "India", "Tamil Nadu",    "Chennai",           "metro",  "couple-no-kids", 2, "middle",  False, "retired",       "undergraduate", "retired",       "neutral",        "hindu",    "general"),
]

# WorldviewAnchor base dimensions per India political lean.
# (institutional_trust, social_change_pace, collectivism_score, economic_security_priority)
# Calibrated against Spring 2023 Pew India: BJP very fav 42%, Modi fav 79%,
# democracy satisfied 72%, economy positive majority.
_INDIA_WORLDVIEW_BASE_DIMS: dict[str, tuple[float, float, float, float]] = {
    "bjp_supporter":  (0.78, 0.28, 0.72, 0.42),  # high trust, low change pace, high collectivism
    "bjp_lean":       (0.65, 0.38, 0.65, 0.48),
    "neutral":        (0.55, 0.50, 0.60, 0.52),
    "opposition_lean":(0.42, 0.62, 0.55, 0.58),
    "opposition":     (0.32, 0.72, 0.50, 0.62),
}

# Religious salience for India general pool.
# India is among the world's most religious countries (Pew 2021: 84% very important).
# Variation by region (South more secular), education (postgrad slightly lower),
# religion (Muslim highest devoutness per Pew data).
_INDIA_GENERAL_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Rajesh Sharma": 0.82,
    "Sunita Gupta": 0.78,
    "Vikram Singh": 0.75,
    "Meera Agarwal": 0.72,
    "Ram Prasad Yadav": 0.92,   # rural UP, very devout
    "Savitri Devi": 0.95,       # rural Bihar, highly devout
    "Suresh Kumar": 0.80,
    "Poonam Verma": 0.88,       # Varanasi, high religiosity
    "Ramesh Chamar": 0.75,
    "Kamla Devi": 0.90,
    "Mohammad Iqbal": 0.92,     # Muslim, high devoutness
    "Fatima Begum": 0.94,
    "Venkatesh Iyer": 0.72,     # South, slightly lower
    "Lakshmi Nair": 0.68,       # Kerala, secular educated
    "Suresh Reddy": 0.78,
    "Priya Krishnamurthy": 0.62, # Bengaluru tech, lower
    "Murugan Pillai": 0.82,
    "Geetha Rani": 0.85,
    "Thomas Mathew": 0.88,      # Christian, devout
    "Mary George": 0.86,
    "Amit Patel": 0.80,
    "Nisha Shah": 0.65,         # Mumbai urban, lower
    "Deepak Joshi": 0.83,
    "Bhavna Desai": 0.88,
    "Ganesh Patil": 0.78,
    "Salim Khan": 0.90,         # Muslim, high devoutness
    "Subhash Ghosh": 0.70,      # Kolkata, more secular
    "Anjali Bose": 0.62,        # educated Kolkata, secular
    "Prasad Mishra": 0.82,
    "Birsa Munda": 0.88,        # tribal, animist/Hindu mix
    "Meena Oram": 0.90,
    "Raju Bora": 0.80,
    "Gurpreet Singh": 0.88,     # Sikh, devout
    "Harjinder Kaur": 0.85,
    "Arjun Mehta": 0.70,        # young Delhi, lower
    "Neha Tiwari": 0.72,
    "Kabir Hussain": 0.88,      # Muslim, devout
    "Priya Sharma": 0.82,
    "Ramnarayan Tripathi": 0.92, # elderly UP, very devout
    "Kamakshi Iyer": 0.80,
}

_INDIA_POLITICAL_ERA = "BJP government in power (Modi, 2014– second term from 2024)"

_DOMAIN_POOLS = {
    "cpg": _CPG_POOL,
    "saas": _SAAS_POOL,
    "general": _CPG_POOL,
    "health_wellness": _CPG_POOL,
    "lofoods_fmcg": _LOFOODS_FMCG_POOL,
    "us_general": _US_GENERAL_POOL,
    "india_general": _INDIA_GENERAL_POOL,
}


def sample_demographic_anchor(
    domain: str,
    index: int,
    seed: int | None = None,
) -> Any:
    """Sample a DemographicAnchor for persona generation.

    Uses round-robin from a domain-specific pool to maximise diversity.
    The index parameter ensures different personas in the same cohort get
    different demographics.

    Args:
        domain: Domain key (cpg, saas, general, health_wellness).
        index: Persona index within the cohort (0-based). Used for pool cycling.
        seed: Optional random seed for reproducibility.

    Returns:
        A DemographicAnchor instance.
    """
    from src.schema.persona import DemographicAnchor, Location, Household
    from src.schema.worldview import WorldviewAnchor, PoliticalProfile

    pool = _DOMAIN_POOLS.get(domain.lower(), _GENERAL_POOL)

    # Round-robin through pool — ensures diversity within a cohort
    entry = pool[index % len(pool)]

    is_us_general = domain.lower() == "us_general"
    is_india_general = domain.lower() == "india_general"

    if is_us_general:
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean) = entry
    elif is_india_general:
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean,
         _religion, _caste) = entry
    else:
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment) = entry
        political_lean = None

    # Optional: add small age variation (+/-3 years) for diversity when wrapping
    if seed is not None and index >= len(pool):
        rng = random.Random(seed + index)
        age = max(18, min(65, age + rng.randint(-3, 3)))

    # Build WorldviewAnchor for us_general domain.
    # Other domains leave worldview as None — zero impact on existing behaviour.
    worldview = None
    if is_us_general and political_lean is not None:
        base = _WORLDVIEW_BASE_DIMS[political_lean]
        inst_trust, change_pace, collectivism, econ_security = base

        # Add small persona-level variation (±0.04) for realism.
        # Seeded by persona name for reproducibility.
        persona_seed = abs(hash(name)) % 10000
        rng = random.Random(persona_seed)
        jitter = lambda v: round(max(0.0, min(1.0, v + rng.uniform(-0.04, 0.04))), 2)  # noqa: E731

        religious_salience = _US_GENERAL_RELIGIOUS_SALIENCE.get(name)
        if religious_salience is not None:
            # Add small persona-level jitter for realism (±0.03)
            religious_salience = round(
                max(0.0, min(1.0, religious_salience + rng.uniform(-0.03, 0.03))), 2
            )

        worldview = WorldviewAnchor(
            institutional_trust=jitter(inst_trust),
            social_change_pace=jitter(change_pace),
            collectivism_score=jitter(collectivism),
            economic_security_priority=jitter(econ_security),
            political_profile=PoliticalProfile(
                country="USA",
                archetype=political_lean,
            ),
            political_era=_US_POLITICAL_ERA,
            religious_salience=religious_salience,
        )

    elif is_india_general and political_lean is not None:
        # Study 1B: India general population WorldviewAnchor.
        # Uses India-calibrated base dimensions and BJP/opposition political leans.
        base = _INDIA_WORLDVIEW_BASE_DIMS.get(political_lean, (0.55, 0.50, 0.60, 0.52))
        inst_trust, change_pace, collectivism, econ_security = base

        persona_seed = abs(hash(name)) % 10000
        rng = random.Random(persona_seed)
        jitter = lambda v: round(max(0.0, min(1.0, v + rng.uniform(-0.04, 0.04))), 2)  # noqa: E731

        religious_salience = _INDIA_GENERAL_RELIGIOUS_SALIENCE.get(name, 0.82)
        religious_salience = round(
            max(0.0, min(1.0, religious_salience + rng.uniform(-0.03, 0.03))), 2
        )

        worldview = WorldviewAnchor(
            institutional_trust=jitter(inst_trust),
            social_change_pace=jitter(change_pace),
            collectivism_score=jitter(collectivism),
            economic_security_priority=jitter(econ_security),
            political_profile=PoliticalProfile(
                country="India",
                archetype=political_lean,
            ),
            political_era=_INDIA_POLITICAL_ERA,
            religious_salience=religious_salience,
        )

    return DemographicAnchor(
        name=name,
        age=age,
        gender=gender,
        location=Location(
            country=country,
            region=region,
            city=city,
            urban_tier=urban_tier,
        ),
        household=Household(
            structure=structure,
            size=size,
            income_bracket=income_bracket,
            dual_income=dual_income,
        ),
        life_stage=life_stage,
        education=education,
        employment=employment,
        worldview=worldview,
    )
