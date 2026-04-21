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
    # Political lean distribution (n=40, A-US-1 rebalance for 2024 election accuracy):
    #   conservative:       6 (15%)
    #   lean_conservative: 11 (27.5%)  A-US-2: +2 (Miller OH white male, Reyes AZ Hispanic self-employed)
    #   moderate:           9 (22.5%)  A-US-2: -2 (Miller, Reyes)
    #   lean_progressive:   9 (22.5%)  A-US-1: -1 (Garcia), -1 (Hall)
    #   progressive:        6 (15%)
    # A-US-1 rationale: Pew 2024 shows Hispanic men +15pp toward Trump, young non-college
    # men +11pp toward R, FL Hispanic women +8pp right vs 2020. Prior pool overrepresented
    # progressive Hispanic/young entries relative to 2024 electorate.
    # A-US-2 expected 2-party: 17 Trump-lean + ~50% of 9 moderates ≈ 21.5/41 = ~52.5% Trump → matches swing avg.
    # Assignments based on region, education, age, and racial identity patterns
    # from Pew Research Center 2023/2024 Political Typology data.

    # South — female, varied age + income
    ("Patricia Williams",  43, "female", "USA", "Georgia",        "Atlanta",       "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "full-time",  "lean_conservative"),
    ("Sandra Johnson",     58, "female", "USA", "Texas",          "Houston",       "metro",    "nuclear",        3, "middle",        False, "late-career",   "high-school",   "part-time",  "conservative"),
    ("Maria Garcia",       35, "female", "USA", "Florida",        "Miami",         "metro",    "nuclear",        4, "lower-middle",  True,  "early-family",  "high-school",   "full-time",  "moderate"),  # A-US-1: lean_progressive→moderate (FL Hispanic women +8pp right, Pew 2024)
    ("Linda Brown",        67, "female", "USA", "North Carolina", "Charlotte",     "metro",    "couple-no-kids", 2, "middle",        False, "retired",       "undergraduate", "retired",    "moderate"),
    ("Betty Jackson",      63, "female", "USA", "Alabama",        "Birmingham",    "tier2",    "nuclear",        3, "lower-middle",  False, "late-career",   "high-school",   "part-time",  "conservative"),
    ("Nancy Moore",        54, "female", "USA", "Iowa",           "Des Moines",    "tier2",    "nuclear",        4, "middle",        True,  "late-career",   "high-school",   "full-time",  "conservative"),

    # Midwest — male, varied age + income
    ("James Miller",       48, "male",   "USA", "Ohio",           "Columbus",      "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "undergraduate", "full-time",  "lean_conservative"),  # A-US-2: moderate→lean_conservative (white Midwest non-postgrad males 45-64 voted Trump 65-32, exit polls 2024)
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
    ("Kevin Hall",         22, "male",   "USA", "California",     "San Diego",     "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",   "part-time",  "moderate"),  # A-US-1: lean_progressive→moderate (young non-college men shifted right 2024; Pew: 18-29 men +11pp R)
    ("Amanda Allen",       27, "female", "USA", "New York",       "Brooklyn",      "metro",    "other",          2, "middle",        False, "early-career",  "undergraduate", "full-time",  "progressive"),
    ("Ryan Young",         26, "male",   "USA", "Washington",     "Seattle",       "metro",    "other",          1, "middle",        False, "early-career",  "postgraduate",  "full-time",  "progressive"),

    # Black Americans (~12% of pool) — Pew: ~80% Dem-leaning
    ("Denise Robinson",    40, "female", "USA", "Georgia",        "Atlanta",       "metro",    "nuclear",        3, "middle",        True,  "mid-career",    "undergraduate", "full-time",  "lean_progressive"),
    ("Marcus Johnson",     33, "male",   "USA", "Illinois",       "Chicago",       "metro",    "other",          1, "middle",        False, "early-career",  "undergraduate", "full-time",  "lean_progressive"),
    ("Keisha Brown",       28, "female", "USA", "Texas",          "Dallas",        "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",   "full-time",  "lean_progressive"),
    ("Darnell Williams",   55, "male",   "USA", "Maryland",       "Baltimore",     "metro",    "nuclear",        4, "upper-middle",  True,  "late-career",   "undergraduate", "full-time",  "progressive"),

    # Hispanic Americans (~13% of pool) — Pew 2024: Hispanic men shifted sharply right
    # (+15pp toward Trump vs 2020); Hispanic women also moved but less dramatically.
    # A-US-1: Garcia lean_progressive→moderate (FL Hispanic women shifted ~8pp right, 2024)
    # A-US-1: Hernandez moderate→lean_conservative (TX Hispanic men, 2024 shift documented)
    ("Carmen Lopez",       38, "female", "USA", "California",     "Los Angeles",   "metro",    "nuclear",        5, "lower-middle",  True,  "early-family",  "high-school",   "full-time",  "lean_progressive"),
    ("Miguel Hernandez",   29, "male",   "USA", "Texas",          "San Antonio",   "metro",    "nuclear",        4, "lower-middle",  True,  "early-career",  "high-school",   "full-time",  "lean_conservative"),
    ("Rosa Gonzalez",      52, "female", "USA", "Florida",        "Miami",         "metro",    "nuclear",        4, "middle",        False, "late-career",   "high-school",   "full-time",  "lean_conservative"),
    ("Carlos Reyes",       44, "male",   "USA", "Arizona",        "Tucson",        "tier2",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "self-employed", "lean_conservative"),  # A-US-2: moderate→lean_conservative (self-employed Hispanic males SW, Pew 2024: Hispanic men +15pp toward Trump)

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
    # South Asian Muslim diaspora — analytical/less-practicing segment
    # Pew 2017: US Muslims report high importance of religion (~65%) but diaspora
    # professionals skew lower. Values here represent the less-to-moderately practicing end.
    "Zara Ahmed":          0.35,
    "Imran Sheikh":        0.38,
    "Fatima Siddiqui":     0.38,
    "Sana Mirza":          0.35,
    "Nadia Rahman":        0.28,
    "Tariq Hussain":       0.40,
    "Ayesha Malik":        0.35,
    "Ruqayyah Patel":      0.42,
    "Hamza Qureshi":       0.38,
    "Maryam Chaudhry":     0.35,
    "Safia Begum":         0.32,
    "Yusuf Iqbal":         0.38,
    "Hana Syed":           0.30,
    "Omar Shaikh":         0.35,
    # South Asian Muslim diaspora — devout segment (waswasa / authority-trust ICP)
    # Pew 2017: 65% of US Muslims say religion is very important. Devout segment
    # skews toward high salience (0.80+). Names selected to reflect observant practice.
    "Amina Hassan":        0.84,
    "Khadija Rahman":      0.85,
    "Safiya Abdullah":     0.82,
    "Ibrahim Al-Rashid":   0.83,
    "Sumayyah Okafor":     0.82,
    "Bilal Mahmood":       0.83,
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
# Political lean distribution (n=40, Sprint A-22 rebalance):
#   bjp_supporter:  14 (35%)  → Pew BJP very favorable ~42%
#   bjp_lean:        8 (20%)  → Pew BJP somewhat favorable ~31%
#   neutral:         8 (20%)  → pragmatic / issue-based (A-22: +3 from opposition_lean)
#   opposition_lean: 3 (7.5%) → INC/opposition lean (A-22: 6→3)
#   opposition:      7 (17.5%)→ BJP very unfavorable + strong INC
#
# A-22 change: Birsa Munda, Ramesh Chamar, Thomas Mathew: opposition_lean → neutral
# Rationale: ST/SC communities and Kerala Christians are demographically mixed-affiliation.
# Jharkhand ST votes on local/tribal issues (JMM, not firmly anti-BJP); Punjab SC votes
# AAP/INC/BSP depending on local dynamics; Kerala Syrian Christians shifted BJP-ward.
# Target: reduce in09 structural C-pool from 13 to 10 personas (32.5%→25% maximum C).
#
# A-12 root cause fix: original 7 bjp_supporter (18%) created structural ceiling —
# impossible to reach Pew's ~42% A-option for in02/in03/in12 with only 7/40 very-BJP personas.
# Rebalanced by converting 7 neutral/opposition personas to bjp_supporter/bjp_lean.
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
    ("Meera Agarwal",        28, "female", "India", "Rajasthan",     "Jaipur",            "metro",  "other",          2, "middle",  False, "early-career",  "undergraduate", "full-time",     "bjp_supporter",  "hindu",    "general"),  # A-12: neutral→bjp_supporter (Rajasthan BJP stronghold)
    ("Ram Prasad Yadav",     55, "male",   "India", "Uttar Pradesh", "Gorakhpur",         "tier2",  "nuclear",        6, "lower",   False, "late-career",   "high-school",     "full-time",     "bjp_supporter",  "hindu",    "obc"),
    ("Savitri Devi",         48, "female", "India", "Bihar",         "Patna",             "tier2",  "nuclear",        5, "lower",   False, "mid-career",    "high-school",       "part-time",     "bjp_lean",       "hindu",    "obc"),
    ("Suresh Kumar",         32, "male",   "India", "Madhya Pradesh","Bhopal",            "metro",  "other",          3, "lower",   False, "early-career",  "high-school",     "full-time",     "bjp_supporter",  "hindu",    "obc"),   # A-12: neutral→bjp_supporter (MP is BJP stronghold, OBC BJP base)
    ("Poonam Verma",         40, "female", "India", "Uttar Pradesh", "Varanasi",          "tier2",  "nuclear",        4, "lower",   True,  "mid-career",    "high-school",     "part-time",     "bjp_supporter",  "hindu",    "general"),
    ("Ramesh Chamar",        38, "male",   "India", "Punjab",        "Ludhiana",          "metro",  "nuclear",        4, "lower",   False, "mid-career",    "high-school",     "full-time",     "neutral",        "hindu",    "sc"),   # A-22: opposition_lean→neutral (SC/Punjab politics mixed: AAP/INC/BSP, not firmly anti-BJP)
    ("Kamla Devi",           52, "female", "India", "Uttar Pradesh", "Agra",              "tier2",  "nuclear",        5, "lower",   False, "late-career",   "high-school",       "part-time",     "opposition",     "hindu",    "sc"),
    ("Mohammad Iqbal",       44, "male",   "India", "Uttar Pradesh", "Lucknow",           "metro",  "nuclear",        5, "lower",   True,  "mid-career",    "high-school",     "full-time",     "opposition",     "muslim",   "obc"),
    ("Fatima Begum",         33, "female", "India", "West Bengal",   "Kolkata",           "metro",  "nuclear",        4, "lower",   False, "early-family",  "high-school",     "homemaker",     "opposition",     "muslim",   "general"),
    # SOUTH — Dravidian / regional
    ("Venkatesh Iyer",       45, "male",   "India", "Tamil Nadu",    "Chennai",           "metro",  "nuclear",        3, "upper",   True,  "mid-career",    "postgraduate",  "full-time",     "neutral",        "hindu",    "general"),
    ("Lakshmi Nair",         38, "female", "India", "Kerala",        "Kochi",             "metro",  "nuclear",        3, "middle",  True,  "mid-career",    "postgraduate",  "full-time",     "opposition_lean","hindu",    "general"),
    ("Suresh Reddy",         52, "male",   "India", "Telangana",     "Hyderabad",         "metro",  "nuclear",        4, "upper",   True,  "late-career",   "postgraduate",  "full-time",     "bjp_lean",       "hindu",    "general"),
    ("Priya Krishnamurthy",  29, "female", "India", "Karnataka",     "Bengaluru",         "metro",  "other",          2, "middle",  False, "early-career",  "postgraduate",  "full-time",     "bjp_lean",       "hindu",    "general"),  # A-12: neutral→bjp_lean (BJP won Karnataka 2023; urban Hindu vote)
    ("Murugan Pillai",       60, "male",   "India", "Tamil Nadu",    "Madurai",           "tier2",  "couple-no-kids", 2, "lower",   False, "retired",       "high-school",     "retired",       "opposition",     "hindu",    "obc"),
    ("Geetha Rani",          42, "female", "India", "Andhra Pradesh","Vijayawada",        "tier2",  "nuclear",        4, "lower",   False, "mid-career",    "high-school",     "part-time",     "bjp_supporter",  "hindu",    "obc"),   # A-12: neutral→bjp_supporter (AP/TG has BJP Hindu base)
    ("Thomas Mathew",        48, "male",   "India", "Kerala",        "Thiruvananthapuram","metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "neutral",        "christian","general"),  # A-22: opposition_lean→neutral (Kerala Syrian Christians shifting BJP-ward; anti-Left, economically conservative)
    ("Mary George",          35, "female", "India", "Goa",           "Panaji",            "metro",  "nuclear",        3, "middle",  True,  "early-family",  "undergraduate", "full-time",     "neutral",        "christian","general"),
    # WEST — Maharashtra / Gujarat
    ("Amit Patel",           40, "male",   "India", "Gujarat",       "Ahmedabad",         "metro",  "nuclear",        4, "upper",   True,  "mid-career",    "undergraduate", "self-employed", "bjp_supporter",  "hindu",    "general"),
    ("Nisha Shah",           33, "female", "India", "Maharashtra",   "Mumbai",            "metro",  "other",          2, "upper",   False, "early-career",  "postgraduate",  "full-time",     "bjp_supporter",  "hindu",    "general"),  # A-12: neutral→bjp_supporter (upper-caste Mumbai business class is BJP base)
    ("Deepak Joshi",         55, "male",   "India", "Rajasthan",     "Udaipur",           "metro",  "nuclear",        5, "middle",  False, "late-career",   "undergraduate", "self-employed", "bjp_lean",       "hindu",    "general"),
    ("Bhavna Desai",         46, "female", "India", "Gujarat",       "Surat",             "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "high-school",     "part-time",     "bjp_supporter",  "hindu",    "obc"),
    ("Ganesh Patil",         38, "male",   "India", "Maharashtra",   "Pune",              "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "bjp_supporter",  "hindu",    "obc"),   # A-12: neutral→bjp_supporter (BJP won Maharashtra 2024; OBC urban base)
    ("Salim Khan",           40, "male",   "India", "Maharashtra",   "Mumbai",            "metro",  "nuclear",        5, "lower",   False, "mid-career",    "high-school",     "self-employed", "opposition",     "muslim",   "obc"),
    # EAST / NORTHEAST
    ("Subhash Ghosh",        50, "male",   "India", "West Bengal",   "Kolkata",           "metro",  "nuclear",        3, "middle",  True,  "late-career",   "postgraduate",  "full-time",     "opposition",     "hindu",    "general"),
    ("Anjali Bose",          31, "female", "India", "West Bengal",   "Kolkata",           "metro",  "other",          2, "middle",  False, "early-career",  "postgraduate",  "full-time",     "neutral",        "hindu",    "general"),  # A-12: opposition_lean→neutral (WB complex; BJP growing but not dominant)
    ("Prasad Mishra",        44, "male",   "India", "Odisha",        "Bhubaneswar",       "metro",  "nuclear",        4, "lower",   True,  "mid-career",    "undergraduate", "full-time",     "bjp_supporter",  "hindu",    "obc"),   # A-12: neutral→bjp_supporter (BJP won Odisha 2024 for first time)
    ("Birsa Munda",          36, "male",   "India", "Jharkhand",     "Ranchi",            "tier2",  "nuclear",        5, "lower",   False, "mid-career",    "high-school",       "full-time",     "neutral",        "hindu",    "st"),   # A-22: opposition_lean→neutral (Jharkhand ST votes on local/tribal issues; JMM/BJP both compete, not firmly anti-BJP)
    # A-12: Meena Oram removed (duplicate ST tribal — Birsa Munda covers ST adequately)
    # A-12: Abdul Karim added — elderly Muslim Kerala, retired opposition (Muslim minority signal)
    ("Abdul Karim",          70, "male",   "India", "Kerala",        "Kozhikode",         "tier2",  "nuclear",        5, "lower",   False, "retired",       "high-school",       "retired",       "opposition",     "muslim",   "obc"),
    ("Raju Bora",            34, "male",   "India", "Assam",         "Guwahati",          "metro",  "nuclear",        4, "lower",   True,  "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",    "obc"),
    # SIKH — Punjab
    ("Gurpreet Singh",       45, "male",   "India", "Punjab",        "Amritsar",          "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "opposition_lean","sikh",     "general"),
    ("Harjinder Kaur",       38, "female", "India", "Punjab",        "Chandigarh",        "metro",  "nuclear",        3, "middle",  True,  "mid-career",    "undergraduate", "full-time",     "neutral",        "sikh",     "general"),
    # YOUNG URBAN
    ("Arjun Mehta",          24, "male",   "India", "Delhi",         "New Delhi",         "metro",  "other",          1, "lower",   False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",    "general"),
    ("Neha Tiwari",          22, "female", "India", "Maharashtra",   "Mumbai",            "metro",  "other",          2, "lower",   False, "early-career",  "undergraduate", "full-time",     "bjp_supporter",  "hindu",    "obc"),   # A-12: neutral→bjp_supporter (young urban Hindu OBC — BJP youth base)
    ("Kabir Hussain",        26, "male",   "India", "Karnataka",     "Bengaluru",         "metro",  "other",          1, "middle",  False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","muslim",   "general"),
    ("Priya Sharma",         23, "female", "India", "Uttar Pradesh", "Kanpur",            "metro",  "other",          2, "lower",   False, "early-career",  "undergraduate", "part-time",     "bjp_supporter",  "hindu",    "general"),
    # RETIRED / ELDERLY
    ("Ramnarayan Tripathi",  68, "male",   "India", "Uttar Pradesh", "Allahabad",         "tier2",  "couple-no-kids", 2, "lower",   False, "retired",       "high-school",     "retired",       "bjp_supporter",  "hindu",    "general"),
    ("Kamakshi Iyer",        65, "female", "India", "Tamil Nadu",    "Chennai",           "metro",  "couple-no-kids", 2, "middle",  False, "retired",       "undergraduate", "retired",       "neutral",        "hindu",    "general"),
]

# ── Delhi-specific pool ───────────────────────────────────────────────────────
# 24 personas calibrated to Delhi (NCT) 2025 demographic and political profile.
# Political lean distribution: bjp_supporter=4 (17%), bjp_lean=4 (17%),
# neutral=5 (21%), opposition_lean=5 (21%), opposition=6 (25%).
# This reflects Delhi's actual 2025 electorate: BJP 47.5%, AAP 29%, Others 23%.
# Religion: Hindu=20 (83%), Muslim=3 (13%), Sikh=1 (4%).
# Routed when anchor_overrides location contains "delhi".
_DELHI_GENERAL_POOL = [
    # BJP supporters (4) — strong Modi/BJP voters
    ("Dinesh Kumar",    45, "male",   "India", "Delhi", "Old Delhi",   "metro", "joint",   5, "lower",  False, "mid-career",   "high-school",  "self-employed",   "bjp_supporter", "hindu",  "general"),
    ("Anuj Sharma",     38, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "middle", True,  "mid-career",   "postgraduate", "full-time",       "bjp_supporter", "hindu",  "general"),
    ("Rahul Malhotra",  43, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "upper",  True,  "mid-career",   "postgraduate", "self-employed",   "bjp_supporter", "hindu",  "general"),
    ("Vinod Kapoor",    55, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "upper",  False, "late-career",  "postgraduate", "self-employed",   "neutral",       "hindu",  "general"),
    # BJP leaners (4) — soft BJP, Modi economy / cultural identity
    ("Ravi Kumar",      35, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "lower",  False, "mid-career",   "high-school",  "full-time",       "bjp_lean",      "hindu",  "obc"),
    ("Manoj Gupta",     48, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "middle", False, "mid-career",   "undergraduate","self-employed",   "bjp_lean",      "hindu",  "general"),
    ("Sanjay Khanna",   52, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "middle", False, "late-career",  "undergraduate","retired",         "bjp_lean",      "hindu",  "general"),
    ("Deepika Arora",   38, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "upper",  True,  "mid-career",   "postgraduate", "full-time",       "opposition_lean","hindu",  "general"),
    # Neutral (5) — pragmatic, infrastructure-focused, swing voters
    ("Sunil Prasad",    28, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "lower",  False, "early-career", "undergraduate","full-time",       "neutral",       "hindu",  "general"),
    ("Rekha Singh",     40, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "middle", False, "mid-career",   "undergraduate","full-time",       "neutral",       "hindu",  "general"),
    ("Neha Verma",      33, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "middle", True,  "early-family", "undergraduate","full-time",       "neutral",       "hindu",  "general"),
    ("Vikas Pandey",    31, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "middle", True,  "early-career", "postgraduate", "full-time",       "neutral",       "hindu",  "general"),
    ("Sonia Mehta",     35, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "upper",  True,  "mid-career",   "postgraduate", "self-employed",   "neutral",       "hindu",  "general"),
    # AAP-leaning opposition (5) — welfare beneficiaries, anti-BJP
    ("Pushpa Rani",     38, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "lower",  False, "mid-career",   "high-school",  "part-time",       "opposition_lean","hindu", "dalit"),
    ("Anita Chauhan",   32, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "lower",  False, "early-family", "high-school",  "homemaker",       "opposition_lean","hindu", "obc"),
    ("Priya Rawat",     29, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 2, "middle", True,  "early-career", "undergraduate","full-time",       "opposition_lean","hindu", "general"),
    ("Kavita Joshi",    44, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "middle", False, "mid-career",   "undergraduate","full-time",       "opposition_lean","hindu", "general"),
    ("Gurpreet Kaur",   44, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "middle", False, "mid-career",   "undergraduate","full-time",       "opposition_lean","sikh",  "general"),
    # Strong opposition (6) — Muslim voters + AAP loyalists disillusioned but still opposed to BJP
    ("Geeta Devi",      42, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "lower",  False, "mid-career",   "high-school",  "homemaker",       "opposition",    "hindu",  "dalit"),
    ("Rohit Yadav",     36, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "middle", True,  "mid-career",   "undergraduate","full-time",       "opposition",    "hindu",  "obc"),
    ("Sunita Devi",     45, "female", "India", "Delhi", "Old Delhi",   "metro", "joint",   5, "lower",  False, "mid-career",   "high-school",  "homemaker",       "opposition",    "hindu",  "obc"),
    ("Shaheen Akhtar",  34, "female", "India", "Delhi", "Old Delhi",   "metro", "joint",   5, "lower",  False, "mid-career",   "high-school",  "homemaker",       "opposition",    "muslim", "general"),
    ("Imran Siddiqui",  40, "male",   "India", "Delhi", "Old Delhi",   "metro", "nuclear", 4, "middle", True,  "mid-career",   "undergraduate","self-employed",   "opposition",    "muslim", "general"),
    ("Nasreen Bano",    48, "female", "India", "Delhi", "Old Delhi",   "metro", "joint",   6, "lower",  False, "mid-career",   "high-school",  "homemaker",       "opposition",    "muslim", "general"),
]


# WorldviewAnchor base dimensions per India political lean.
# (institutional_trust, social_change_pace, collectivism_score, economic_security_priority)
# Calibrated against Spring 2023 Pew India: BJP very fav 42%, Modi fav 79%,
# democracy satisfied 72%, economy positive majority.
_INDIA_WORLDVIEW_BASE_DIMS: dict[str, tuple[float, float, float, float]] = {
    # Sprint A-9: raised bjp_supporter inst_trust 0.78 → 0.83 (fixed in09 A=0%).
    # Sprint A-16: lowered bjp_supporter inst_trust 0.83 → 0.76.
    # Sprint A-17: lowered bjp_supporter inst_trust 0.76 → 0.68.
    # Sprint A-18: RAISED bjp_supporter 0.68 → 0.74; RAISED bjp_lean 0.65 → 0.72.
    # Sprint A-21: LOWER bjp_supporter 0.74 → 0.72 (small reduction to reduce in09/in07 A-overshoot).
    # A-18/A-20: in09 A=62% vs Pew 42% — bjp_supporters still too often saying "a lot" trust.
    # Lowering 0.74→0.72 keeps range 0.68–0.76 (same upper bound as bjp_lean) but shifts
    # the center of mass toward B ("somewhat a lot") for more bjp_supporter personas.
    # Safe: bjp_lean at 0.72 didn't cause bimodal collapse in A-18, so 0.72 is a stable value.
    "bjp_supporter":  (0.72, 0.28, 0.72, 0.42),  # trust A-21 (0.74→0.72), low change pace, high collectivism
    "bjp_lean":       (0.72, 0.38, 0.65, 0.48),  # trust unchanged A-18
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
    "Abdul Karim": 0.94,        # A-12: elderly Muslim Kerala, very devout
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

# ---------------------------------------------------------------------------
# West Bengal General Population pool — for Bengal 2026 state assembly election.
# Approximates Bengal electorate across religion, region, community, caste,
# urban/rural tier, and TMC/BJP/Left-Congress political lean.
#
# Political lean mapping for Bengal context:
#   opposition/opposition_lean = TMC (Trinamool Congress, Mamata Banerjee)
#   bjp_supporter/bjp_lean     = BJP (Narendra Modi / state BJP leadership)
#   neutral                    = swing voters (includes Left/Congress residual)
#
# 2021 Assembly ground truth: TMC 47.9% (215/294 seats), BJP 38.1% (77/294),
#   Left+Congress ~9.7% (2 seats).
#
# Political lean distribution (n=40, B-WB-1 initial calibration):
#   opposition:      10 (25.0%) — strong TMC (Muslim vote bank, South Bengal heartland)
#   opposition_lean:  8 (20.0%) — soft TMC (educated Bengali Hindu, swing TMC)
#   neutral:          8 (20.0%) — swing + residual Left/Congress
#   bjp_lean:         8 (20.0%) — soft BJP (Matua belt, North Bengal OBC)
#   bjp_supporter:    6 (15.0%) — strong BJP (Cooch Behar, Jungle Mahal OBC/ST)
# Expected BJP vote share proxy: 35% (2021 actual: 38.1%); TMC: 45% (2021: 47.9%)
#
# Religion: Hindu 80% (32), Muslim 20% (8); actual Bengal ~70/27 — minor under-sample
#   of Muslim adjusted upward from India general pool's typical 13%.
# Caste: general ~28%, obc ~35%, sc ~22%, st ~15%
# Geography: Kolkata metro (8), North Bengal (7), Murshidabad/Malda (5),
#   Nadia/N24Pgs Matua belt (6), South Bengal/Howrah (6), Jungle Mahal (4),
#   Birbhum/Burdwan/Hooghly (4)
# ---------------------------------------------------------------------------
_BENGAL_GENERAL_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment, political_lean, religion, caste)

    # ── KOLKATA METRO (8) ──────────────────────────────────────────────────
    # Urban educated Bengali — more secular, mixed TMC/BJP
    ("Dipankar Chatterjee", 52, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "middle",       True,  "late-career",   "postgraduate",  "full-time",     "opposition",     "hindu",  "general"),   # College lecturer, South Kolkata, TMC intellectual
    ("Supriya Roy",         38, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition_lean","hindu",  "general"),   # Schoolteacher, New Alipore, soft TMC
    ("Abhijit Sen",         44, "male",   "India", "West Bengal", "Kolkata",         "metro",  "other",          2, "upper-middle", False, "mid-career",    "postgraduate",  "full-time",     "neutral",        "hindu",  "general"),   # IT professional, New Town, fence-sitter
    ("Malati Ghosh",        60, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "lower",        False, "late-career",   "high-school",   "part-time",     "opposition",     "hindu",  "sc"),        # Domestic worker, North Kolkata, strong TMC
    ("Rina Das",            29, "female", "India", "West Bengal", "Kolkata",         "metro",  "other",          1, "middle",       False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Private-sector, BJP-sympathetic young Hindu
    ("Sabir Ahmed",         35, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "self-employed", "opposition",     "muslim", "general"),   # Small shopkeeper, Park Circus, strong TMC
    ("Priyanka Bose",       26, "female", "India", "West Bengal", "Kolkata",         "metro",  "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","hindu",  "general"),   # Graduate, Salt Lake, lean TMC
    ("Sanjay Poddar",       48, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "self-employed", "neutral",        "hindu",  "obc"),       # Trader, Behala, pragmatic swing

    # ── NORTH BENGAL — Cooch Behar / Jalpaiguri / Darjeeling (7) ──────────
    # BJP stronghold since 2019; Rajbanshi (OBC) + tea garden (ST) communities
    ("Biswajit Barman",     42, "male",   "India", "West Bengal", "Cooch Behar",     "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_supporter",  "hindu",  "obc"),       # Rajbanshi community, BJP stronghold
    ("Purnima Adhikari",    38, "female", "India", "West Bengal", "Cooch Behar",     "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_lean",       "hindu",  "obc"),       # North Bengal housewife, BJP lean
    ("Ranjit Barua",        55, "male",   "India", "West Bengal", "Darjeeling",      "tier2",  "nuclear",        3, "middle",       False, "late-career",   "undergraduate", "self-employed", "bjp_supporter",  "hindu",  "general"),   # Tea-estate adjacent trader, BJP
    ("Kamala Oraon",        45, "female", "India", "West Bengal", "Jalpaiguri",      "rural",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "part-time",     "bjp_lean",       "hindu",  "st"),        # Tea garden worker (Oraon tribal), BJP lean
    ("Dilip Saha",          33, "male",   "India", "West Bengal", "Siliguri",        "tier2",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",  "general"),   # Small trader, Siliguri, swing
    ("Mahadev Ray",         62, "male",   "India", "West Bengal", "Cooch Behar",     "tier2",  "couple-no-kids", 2, "lower",        False, "retired",       "high-school",   "retired",       "bjp_supporter",  "hindu",  "obc"),       # Retired, Cooch Behar town, strong BJP
    ("Renuka Barman",       28, "female", "India", "West Bengal", "Jalpaiguri",      "tier3",  "nuclear",        3, "lower",        False, "early-career",  "high-school",   "full-time",     "neutral",        "hindu",  "obc"),       # Young North Bengal woman, uncertain

    # ── MURSHIDABAD / MALDA (5) ────────────────────────────────────────────
    # Muslim-majority districts, TMC stronghold; moderate Left legacy
    ("Rahim Sheikh",        50, "male",   "India", "West Bengal", "Berhampore",      "tier2",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Farmer, Murshidabad, strong TMC
    ("Hasina Bibi",         40, "female", "India", "West Bengal", "Malda",           "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Homemaker, Malda, strong TMC
    ("Nazrul Islam",        32, "male",   "India", "West Bengal", "Berhampore",      "tier2",  "nuclear",        4, "lower",        False, "early-career",  "high-school",   "full-time",     "opposition",     "muslim", "obc"),       # Factory worker, Murshidabad, TMC
    ("Sabina Begum",        47, "female", "India", "West Bengal", "Jangipur",        "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "opposition_lean","muslim", "general"),   # Schoolteacher, Jangipur, soft TMC
    ("Abdul Mannan",        58, "male",   "India", "West Bengal", "Malda",           "rural",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "neutral",        "muslim", "obc"),       # Farmer, border area, pragmatic swing

    # ── NADIA / NORTH 24 PARGANAS — Matua Belt (6) ─────────────────────────
    # Matua community (SC Hindu, Bangladesh-origin refugees) — BJP's CAA voter base
    ("Haripada Biswas",     55, "male",   "India", "West Bengal", "Ranaghat",        "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "sc"),        # Matua community, Ranaghat, strong BJP
    ("Gour Mandal",         48, "male",   "India", "West Bengal", "Bangaon",         "tier3",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "sc"),        # Matua, Bangaon (BJP seat 2021), BJP lean
    ("Saraswati Mondal",    42, "female", "India", "West Bengal", "Basirhat",        "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_lean",       "hindu",  "sc"),        # SC woman, Basirhat, BJP lean
    ("Nikhil Gain",         36, "male",   "India", "West Bengal", "Ranaghat",        "tier3",  "nuclear",        3, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "neutral",        "hindu",  "sc"),        # SC, Nadia, neutral — CAA issue cuts both ways
    ("Lakshmi Sarkar",      50, "female", "India", "West Bengal", "Barasat",         "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "part-time",     "opposition_lean","hindu",  "obc"),       # N24 Pgs OBC woman, soft TMC
    ("Pratap Roy",          62, "male",   "India", "West Bengal", "Barasat",         "tier2",  "couple-no-kids", 2, "middle",       False, "retired",       "undergraduate", "retired",       "bjp_lean",       "hindu",  "general"),   # Retired, suburban Kolkata orbit, BJP lean

    # ── SOUTH 24 PARGANAS / HOWRAH (6) ─────────────────────────────────────
    # TMC heartland; industrial Howrah; Sundarbans fisher communities
    ("Tapas Haldar",        44, "male",   "India", "West Bengal", "Howrah",          "metro",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "hindu",  "sc"),        # Industrial worker, Howrah, strong TMC
    ("Rekha Das",           38, "female", "India", "West Bengal", "Diamond Harbour", "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "hindu",  "sc"),        # S24 Pgs, TMC stronghold
    ("Subrata Pal",         52, "male",   "India", "West Bengal", "Howrah",          "metro",  "nuclear",        4, "lower-middle", True,  "late-career",   "undergraduate", "full-time",     "opposition_lean","hindu",  "obc"),       # Howrah suburb, soft TMC
    ("Mina Khatun",         33, "female", "India", "West Bengal", "Canning",         "tier3",  "nuclear",        5, "lower",        False, "early-family",  "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim, Canning, strong TMC
    ("Bablu Roy",           28, "male",   "India", "West Bengal", "Howrah",          "metro",  "other",          2, "lower",        False, "early-career",  "high-school",   "full-time",     "neutral",        "hindu",  "obc"),       # Young jobseeker, Howrah, swing
    ("Champa Bhunia",       55, "female", "India", "West Bengal", "Kakdwip",         "rural",  "joint",          6, "lower",        False, "late-career",   "high-school",   "part-time",     "opposition",     "hindu",  "obc"),       # Fisherwoman, Sundarbans, strong TMC

    # ── JUNGLE MAHAL — West Midnapore / Bankura / Purulia (4) ─────────────
    # Tribal (ST) belt; BJP made inroads post-2019 in former Left stronghold
    ("Mangal Soren",        40, "male",   "India", "West Bengal", "Bankura",         "tier3",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "st"),        # Santali farmer, Bankura, BJP lean
    ("Sukru Munda",         35, "male",   "India", "West Bengal", "Purulia",         "tier3",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "st"),        # Tribal, Purulia, TMC/BJP swing
    ("Basanti Kisku",       30, "female", "India", "West Bengal", "Bankura",         "rural",  "joint",          5, "lower",        False, "early-family",  "high-school",   "part-time",     "opposition_lean","hindu",  "st"),        # Tribal woman, MGNREGA beneficiary, lean TMC
    ("Anil Mahato",         50, "male",   "India", "West Bengal", "Midnapore",       "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "self-employed", "bjp_supporter",  "hindu",  "obc"),       # OBC trader, Jungle Mahal, BJP since 2019

    # ── BIRBHUM / BURDWAN / HOOGHLY (4) ────────────────────────────────────
    # Mixed: CPM history → TMC; BJP urban gains; Muslim pocket in Birbhum
    ("Mosaraf Hossain",     45, "male",   "India", "West Bengal", "Suri",            "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition_lean","muslim", "obc"),       # Birbhum Muslim, aware of TMC flaws, lean TMC
    ("Pratima Ghosh",       42, "female", "India", "West Bengal", "Durgapur",        "tier2",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition_lean","hindu",  "general"),   # Durgapur educated woman, soft TMC
    ("Kartik Pal",          57, "male",   "India", "West Bengal", "Hooghly",         "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "obc"),       # Ex-CPM voter shifted BJP, frustrated with TMC
    ("Ratna Mukherjee",     35, "female", "India", "West Bengal", "Durgapur",        "tier2",  "other",          2, "middle",       False, "mid-career",    "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Urban educated, BJP sympathiser

    # ── B-WB-2 EXPANSION (+40): Rural Bengal, Women, Matua depth, Youth, ─────
    # Gorkha hills, Ex-CPM→BJP switchers, Sandeshkhali women.
    # Brings pool to 80 personas. Political lean (new 40):
    #   opposition×12 / opposition_lean×4 / neutral×10 / bjp_lean×11 / bjp_supporter×3
    # Full 80-pool: TMC-lean 42.5% (34/80) / BJP-lean 35% (28/80) / neutral 22.5% (18/80)
    # Rural share raised from ~30% → ~50% (Bengal is 72% rural per 2021 census).
    # Women raised from 30% → 43% (women are Mamata's primary constituency).

    # ── RURAL BENGAL (15) ────────────────────────────────────────────────────
    # Rural Muslim Murshidabad/Malda
    ("Akbar Ali",           48, "male",   "India", "West Bengal", "Murshidabad",     "rural",  "joint",          7, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Paddy farmer, strong TMC
    ("Rani Begum",          35, "female", "India", "West Bengal", "Malda",           "rural",  "joint",          6, "lower",        False, "early-family",  "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Lakshmir Bhandar recipient, loyal TMC
    ("Jabbar Sheikh",       62, "male",   "India", "West Bengal", "Berhampore",      "rural",  "joint",          8, "lower",        False, "retired",       "high-school",   "retired",       "opposition",     "muslim", "general"),   # Elderly farmer, opposition bloc
    # Rural South Bengal — TMC heartland
    ("Kamala Baidya",       45, "female", "India", "West Bengal", "Basirhat",        "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "part-time",     "opposition",     "hindu",  "obc"),       # Agricultural worker, Lakshmir Bhandar
    ("Sukumar Mondal",      55, "male",   "India", "West Bengal", "Kakdwip",         "rural",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "sc"),        # Sundarbans fisherman community, S24Pgs
    ("Shefali Roy",         40, "female", "India", "West Bengal", "Canning",         "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition_lean","hindu",  "sc"),        # S24Pgs rural, soft TMC
    # Rural North Bengal BJP belt
    ("Dinesh Barman",       50, "male",   "India", "West Bengal", "Cooch Behar",     "rural",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "obc"),       # Rajbanshi, rural Cooch Behar, strong BJP
    ("Phul Maya Rai",       38, "female", "India", "West Bengal", "Jalpaiguri",      "rural",  "joint",          7, "lower",        False, "mid-career",    "high-school",   "part-time",     "bjp_lean",       "hindu",  "obc"),       # Tea garden worker community, BJP lean
    # Rural Jungle Mahal — tribal
    ("Budhna Hansda",       45, "male",   "India", "West Bengal", "Jhargram",        "rural",  "joint",          7, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "st"),        # Santali, Jhargram, BJP inroads
    ("Somri Murmu",         35, "female", "India", "West Bengal", "Bankura",         "rural",  "joint",          5, "lower",        False, "early-family",  "high-school",   "part-time",     "opposition_lean","hindu",  "st"),        # Tribal woman, MGNREGA dependent, lean TMC
    # Rural Birbhum/Burdwan
    ("Gopal Mondal",        52, "male",   "India", "West Bengal", "Bolpur",          "rural",  "joint",          5, "lower",        False, "late-career",   "high-school",   "full-time",     "neutral",        "hindu",  "obc"),       # Birbhum, ex-CPM area, undecided swing
    ("Sufia Khatun",        38, "female", "India", "West Bengal", "Birbhum",         "rural",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim rural Birbhum, TMC
    ("Bhola Bauri",         48, "male",   "India", "West Bengal", "Burdwan",         "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # SC, Burdwan rural, pragmatic
    # Rural Nadia/N24Pgs
    ("Laltu Biswas",        44, "male",   "India", "West Bengal", "Krishnagar",      "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "sc"),        # Matua-adjacent, Nadia, BJP lean
    ("Mamata Sarkar",       36, "female", "India", "West Bengal", "Barasat",         "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "part-time",     "opposition",     "hindu",  "obc"),       # Welfare recipient, N24Pgs, TMC

    # ── WOMEN VOTERS (8) ─────────────────────────────────────────────────────
    ("Gita Mondal",         42, "female", "India", "West Bengal", "Howrah",          "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "hindu",  "obc"),       # Howrah rural, Lakshmir Bhandar loyal
    ("Parveen Bibi",        38, "female", "India", "West Bengal", "Murshidabad",     "rural",  "joint",          7, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Rural Muslim woman, TMC
    ("Laxmi Bai Roy",       50, "female", "India", "West Bengal", "Midnapore",       "rural",  "joint",          6, "lower",        False, "late-career",   "high-school",   "part-time",     "opposition_lean","hindu",  "sc"),        # SC woman, Lakshmir Bhandar, soft TMC
    ("Sunita Ghosh",        32, "female", "India", "West Bengal", "Kolkata",         "metro",  "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","hindu",  "general"),   # Educated Kolkata woman, soft TMC
    ("Rupa Mandal",         28, "female", "India", "West Bengal", "Siliguri",        "tier2",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",  "obc"),       # Young North Bengal woman, BJP lean
    ("Nasrin Ahmed",        34, "female", "India", "West Bengal", "Berhampore",      "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "undergraduate", "full-time",     "opposition",     "muslim", "general"),   # Muslim educated woman, TMC
    ("Mridula Chatterjee",  55, "female", "India", "West Bengal", "Durgapur",        "tier2",  "nuclear",        3, "middle",       True,  "late-career",   "undergraduate", "full-time",     "neutral",        "hindu",  "general"),   # Educated Durgapur woman, uncommitted
    ("Anwara Begum",        46, "female", "India", "West Bengal", "Canning",         "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "obc"),       # Muslim woman S24Pgs, strong TMC

    # ── MATUA COMMUNITY DEPTH (4) ────────────────────────────────────────────
    # Matua = SC Hindu (Bangladesh-origin), ~17 lakh voters, Nadia/N24Pgs belt.
    # Most pivotal 2026 swing community: CAA promise from BJP vs welfare from TMC.
    ("Tarun Biswas",        38, "male",   "India", "West Bengal", "Bangaon",         "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "neutral",        "hindu",  "sc"),        # Young Matua activist — CAA promise proven hollow, SIR deleted family members from rolls; genuine swing
    ("Bimala Mondal",       52, "female", "India", "West Bengal", "Ranaghat",        "tier3",  "nuclear",        4, "lower",        False, "late-career",   "high-school",   "homemaker",     "neutral",        "hindu",  "sc"),        # Matua woman — CAA disillusionment + SIR anxiety, torn between BJP identity and TMC welfare
    ("Nirmal Sarkar",       60, "male",   "India", "West Bengal", "Basirhat",        "tier3",  "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "neutral",        "hindu",  "sc"),        # Elderly Matua, pragmatic, genuinely undecided
    ("Kalyani Das",         35, "female", "India", "West Bengal", "Bangaon",         "tier3",  "nuclear",        3, "lower",        False, "mid-career",    "high-school",   "part-time",     "bjp_lean",       "hindu",  "sc"),        # Matua woman, BJP lean on identity grounds

    # ── YOUNG FIRST-TIME VOTERS 18-25 (5) ────────────────────────────────────
    # Unemployment is #1 issue for this cohort — volatile, no strong party loyalty.
    ("Arpita Roy",          21, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "middle",       False, "early-career",  "undergraduate", "student",       "neutral",        "hindu",  "general"),   # Kolkata student, first vote, undecided
    ("Rahul Barman",        22, "male",   "India", "West Bengal", "Siliguri",        "tier2",  "nuclear",        4, "lower-middle", False, "early-career",  "undergraduate", "part-time",     "bjp_lean",       "hindu",  "obc"),       # Unemployed graduate, North Bengal, BJP lean
    ("Sabana Khatun",       20, "female", "India", "West Bengal", "Berhampore",      "tier2",  "nuclear",        5, "lower",        False, "early-career",  "high-school",   "part-time",     "opposition",     "muslim", "general"),   # Young Muslim woman, first vote, TMC
    ("Sourav Das",          23, "male",   "India", "West Bengal", "Howrah",          "metro",  "other",          3, "lower",        False, "early-career",  "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # Young SC jobseeker, Howrah, disillusioned
    ("Priya Barua",         24, "female", "India", "West Bengal", "Darjeeling",      "tier2",  "nuclear",        3, "middle",       False, "early-career",  "undergraduate", "part-time",     "neutral",        "hindu",  "general"),   # Young Gorkha-adjacent, complex identity

    # ── GORKHA / DARJEELING HILL SEATS (3) ───────────────────────────────────
    # 3 hill seats with distinct GJM/GNLF vs BJP dynamics. Separate statehood demand.
    ("Pemba Tamang",        45, "male",   "India", "West Bengal", "Darjeeling",      "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "neutral",        "hindu",  "obc"),       # GJM voter, Gorkhaland demand overrides party
    ("Sunita Rai",          38, "female", "India", "West Bengal", "Kurseong",        "tier2",  "nuclear",        3, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Gorkha woman, BJP/GJM alignment
    ("Bishal Gurung",       52, "male",   "India", "West Bengal", "Kalimpong",       "tier2",  "nuclear",        4, "middle",       False, "late-career",   "undergraduate", "self-employed", "neutral",        "hindu",  "obc"),       # Gorkha identity politics, pragmatic swing

    # ── EX-CPM → BJP SWITCHERS (3) ───────────────────────────────────────────
    # Documented demographic: voted CPM 1977-2011, refused TMC, flipped BJP 2019.
    # Concentrated in Hooghly/Burdwan industrial belt and Jungle Mahal.
    ("Debabrata Mondal",    58, "male",   "India", "West Bengal", "Chinsurah",       "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "undergraduate", "full-time",     "bjp_lean",       "hindu",  "obc"),       # Ex-CPM union man, Hooghly, BJP since 2019
    ("Sudha Pal",           54, "female", "India", "West Bengal", "Burdwan",         "tier2",  "nuclear",        3, "middle",       True,  "late-career",   "undergraduate", "full-time",     "bjp_lean",       "hindu",  "sc"),        # Ex-CPM schoolteacher, shifted BJP on corruption
    ("Haran Mahato",        55, "male",   "India", "West Bengal", "Midnapore",       "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "self-employed", "bjp_supporter",  "hindu",  "obc"),       # Ex-CPM Jungle Mahal, firm BJP since 2019

    # ── SANDESHKHALI-PROXIMATE WOMEN (2) ─────────────────────────────────────
    # North 24 Pgs coastal belt. 2024 sexual violence/land-grab case (TMC leaders)
    # created a specific anti-TMC sentiment among local women.
    ("Rekha Halder",        40, "female", "India", "West Bengal", "Sandeshkhali",    "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "neutral",        "hindu",  "sc"),        # Angry at TMC but fearful of BJP too — genuine swing
    ("Bina Naskar",         45, "female", "India", "West Bengal", "Sandeshkhali",    "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_lean",       "hindu",  "obc"),       # Sandeshkhali, anti-TMC post-incident, BJP lean

    # ── B-WB-3 CALIBRATION FIXES (+9): CPM holdouts, AIMIM Muslims, ────────
    # Matua lean corrections. Grounded in real poll data (Matrize/VoteVibe/
    # Matrix-IANS, April 2026): consensus TMC ~43%, BJP ~40%, Others ~12-16%.
    # Key new signals: SIR voter-roll deletions hitting TMC strongholds;
    # Matua CAA disillusionment (BJP promise hollow); AIMIM fragmenting
    # Muslim vote in Murshidabad/Malda. Pool now 89 personas.

    # ── CPM / LEFT-CONGRESS HOLDOUTS (6) ─────────────────────────────────────
    # Committed Left-Congress voters — refuse to vote TMC or BJP.
    # Concentrated in Birbhum/Burdwan/Hooghly industrial belt and Jadavpur.
    # Political lean = neutral; Left identity encoded in geography + background.
    ("Arun Bhattacharya",   67, "male",   "India", "West Bengal", "Jadavpur",        "metro",  "couple-no-kids", 2, "middle",       True,  "retired",       "postgraduate",  "retired",       "left_lean",      "hindu",  "general"),   # Retired professor, Jadavpur, lifelong CPM voter, deeply secular
    ("Subhas Chattopadhyay",58, "male",   "India", "West Bengal", "Bolpur",          "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "left_lean",      "hindu",  "obc"),       # CPM booth worker, Birbhum, never left the party
    ("Meenakshi Roy",       52, "female", "India", "West Bengal", "Burdwan",         "tier2",  "nuclear",        3, "lower-middle", True,  "late-career",   "undergraduate", "full-time",     "left_lean",      "hindu",  "general"),   # Ex-CITU union member, Burdwan, Congress-Left voter
    ("Pradip Ghosh",        62, "male",   "India", "West Bengal", "Berhampore",      "tier2",  "couple-no-kids", 3, "middle",       False, "retired",       "undergraduate", "retired",       "left_lean",      "hindu",  "general"),   # Congress loyalist, Berhampore (Adhir Ranjan's base), Murshidabad
    ("Tapan Mondal",        56, "male",   "India", "West Bengal", "Durgapur",        "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "left_lean",      "hindu",  "obc"),       # Ex-CPM steel worker, Durgapur, will not vote TMC or BJP
    ("Sabitri Das",         49, "female", "India", "West Bengal", "Chinsurah",       "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "left_lean",      "hindu",  "sc"),        # SC woman, Hooghly, Left-Congress alliance loyalty

    # ── AIMIM / OTHERS — DISILLUSIONED MUSLIMS (3) ───────────────────────────
    # AIMIM-AJUP alliance contesting Muslim-majority seats in Murshidabad/Malda.
    # Fragments TMC's Muslim vote bank. ~5-8% peel in dense Muslim constituencies.
    ("Abdul Karim",         55, "male",   "India", "West Bengal", "Murshidabad",     "tier2",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "self-employed", "left_lean",      "muslim", "general"),   # Madrasa-educated, Murshidabad, AIMIM sympathiser, anti-TMC tokenism
    ("Ruksana Parvin",      36, "female", "India", "West Bengal", "Malda",           "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "left_lean",      "muslim", "general"),   # Educated Muslim woman, Malda, sceptical of TMC, open to AIMIM
    ("Nurul Haque",         46, "male",   "India", "West Bengal", "Berhampore",      "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "self-employed", "left_lean",      "muslim", "obc"),       # Muslim trader, Berhampore, angry at TMC corruption, considering AIMIM

    # ── B-WB-4 CALIBRATION (+9): BJP pool expansion ──────────────────────────
    # BJP is under-represented vs real polls (~39%). Adding personas from three
    # documented BJP-strong geographies: Koch-Rajbongshi (North Bengal), Jungle
    # Mahal tribals (Jhargram/Purulia), Hindu consolidation belt (Bankura/Burdwan).
    # Pool now 98 personas. BJP-lean: 31/98=32%, TMC-lean: 38/98=39%, left_lean: 9/98=9%, neutral: 20/98=20%.

    # ── KOCH-RAJBONGSHI / NORTH BENGAL BJP (3) ────────────────────────────────
    ("Uttam Barman",        48, "male",   "India", "West Bengal", "Cooch Behar",     "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "bjp_supporter",  "hindu",  "obc"),       # Koch-Rajbongshi, BJP-GJM base, Cooch Behar
    ("Shefali Barman",      42, "female", "India", "West Bengal", "Cooch Behar",     "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_lean",       "hindu",  "obc"),       # Koch-Rajbongshi woman, Hindu nationalist, BJP
    ("Gobinda Roy",         55, "male",   "India", "West Bengal", "Alipurduar",      "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "self-employed", "bjp_lean",       "hindu",  "obc"),       # Tea garden community, Alipurduar, BJP lean

    # ── JUNGLE MAHAL TRIBALS / JHARGRAM-PURULIA BJP (3) ──────────────────────
    ("Mangal Murmu",        44, "male",   "India", "West Bengal", "Jhargram",        "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "self-employed", "bjp_lean",       "hindu",  "st"),        # Santali tribal, Jhargram, BJP on tribal identity
    ("Sushila Hansda",      38, "female", "India", "West Bengal", "Purulia",         "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "part-time",     "bjp_lean",       "hindu",  "st"),        # Tribal woman, Purulia, BJP-NDA alignment
    ("Ratan Tudu",          50, "male",   "India", "West Bengal", "Bankura",         "tier3",  "nuclear",        4, "lower",        False, "late-career",   "high-school",   "self-employed", "bjp_supporter",  "hindu",  "st"),        # Tribal farmer, Bankura, firm BJP voter since 2019

    # ── HINDU CONSOLIDATION BELT / BURDWAN-BANKURA (3) ───────────────────────
    ("Nikhil Ghosh",        52, "male",   "India", "West Bengal", "Asansol",         "tier2",  "nuclear",        3, "middle",       False, "late-career",   "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Hindu middle-class, Asansol, anti-TMC governance failure
    ("Rekha Singh",         45, "female", "India", "West Bengal", "Bankura",         "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "bjp_lean",       "hindu",  "obc"),       # Hindu OBC woman, Bankura, BJP on identity + welfare
    ("Subal Pal",           58, "male",   "India", "West Bengal", "Burdwan",         "tier2",  "nuclear",        3, "lower-middle", False, "late-career",   "high-school",   "self-employed", "bjp_supporter",  "hindu",  "general"),   # Hindu trader, Burdwan, BJP consolidation voter
]

# Religious salience for Bengal general pool.
# Bengal Hindu is significantly more secular than pan-India average (Kolkata
# intellectual tradition; Rabindranath legacy; Left 34-year rule).
# Muslim voters in Murshidabad/Malda rank among India's more devout rural Muslims.
_BENGAL_GENERAL_RELIGIOUS_SALIENCE: dict[str, float] = {
    # Kolkata metro — lower salience, urban secular Bengali
    "Dipankar Chatterjee": 0.55,   # college lecturer, secular intellectual
    "Supriya Roy":         0.62,
    "Abhijit Sen":         0.45,   # IT professional, secular
    "Malati Ghosh":        0.72,   # working-class woman, moderate Hindu
    "Rina Das":            0.65,
    "Sabir Ahmed":         0.85,   # Muslim, devout
    "Priyanka Bose":       0.55,
    "Sanjay Poddar":       0.68,
    # North Bengal
    "Biswajit Barman":     0.78,   # Rajbanshi community, Hindu devout
    "Purnima Adhikari":    0.80,
    "Ranjit Barua":        0.72,
    "Kamala Oraon":        0.82,   # tribal, syncretist Hindu + folk religion
    "Dilip Saha":          0.65,
    "Mahadev Ray":         0.75,
    "Renuka Barman":       0.72,
    # Murshidabad/Malda — high Muslim devoutness (rural)
    "Rahim Sheikh":        0.90,
    "Hasina Bibi":         0.92,
    "Nazrul Islam":        0.88,
    "Sabina Begum":        0.82,   # teacher, somewhat lower
    "Abdul Mannan":        0.88,
    # Nadia/N24Pgs — Matua community (lower-caste Hindu, moderate salience)
    "Haripada Biswas":     0.78,
    "Gour Mandal":         0.80,
    "Saraswati Mondal":    0.82,
    "Nikhil Gain":         0.70,
    "Lakshmi Sarkar":      0.75,
    "Pratap Roy":          0.65,
    # South Bengal/Howrah
    "Tapas Haldar":        0.75,
    "Rekha Das":           0.78,
    "Subrata Pal":         0.65,
    "Mina Khatun":         0.88,   # Muslim woman
    "Bablu Roy":           0.60,   # young urban, lower
    "Champa Bhunia":       0.80,   # rural fisherwoman, folk Hindu
    # Jungle Mahal — tribal, syncretist religion
    "Mangal Soren":        0.82,
    "Sukru Munda":         0.80,
    "Basanti Kisku":       0.78,
    "Anil Mahato":         0.72,
    # Birbhum/Burdwan/Hooghly
    "Mosaraf Hossain":     0.86,   # Muslim
    "Pratima Ghosh":       0.58,   # urban educated, secular Bengali
    "Kartik Pal":          0.72,
    "Ratna Mukherjee":     0.60,   # urban educated

    # ── B-WB-2 expansion (+40 personas) ─────────────────────────────────────
    # Rural Bengal (15)
    "Akbar Ali":           0.90,   # rural Muslim Murshidabad, devout
    "Rani Begum":          0.88,   # rural Muslim Malda, devout
    "Jabbar Sheikh":       0.90,   # elderly Muslim farmer, devout
    "Kamala Baidya":       0.78,   # Hindu OBC agricultural worker
    "Sukumar Mondal":      0.80,   # Hindu SC fisherman, Sundarbans
    "Shefali Roy":         0.75,   # Hindu SC rural woman
    "Dinesh Barman":       0.82,   # Rajbanshi Hindu, BJP-leaning communal identity
    "Phul Maya Rai":       0.78,   # tea garden woman, Hindu OBC
    "Budhna Hansda":       0.82,   # Santali Hindu, Jhargram tribal belt
    "Somri Murmu":         0.80,   # tribal woman, syncretist Hindu
    "Gopal Mondal":        0.72,   # Hindu OBC, Birbhum ex-CPM secular legacy
    "Sufia Khatun":        0.88,   # Muslim rural Birbhum, devout
    "Bhola Bauri":         0.76,   # SC Hindu, Burdwan rural
    "Laltu Biswas":        0.78,   # Matua-adjacent SC, Nadia
    "Mamata Sarkar":       0.72,   # Hindu OBC, N24Pgs welfare recipient
    # Women voters (8)
    "Gita Mondal":         0.78,   # Hindu OBC homemaker, Howrah rural
    "Parveen Bibi":        0.90,   # Muslim woman, rural Murshidabad, devout
    "Laxmi Bai Roy":       0.76,   # SC woman, rural Midnapore
    "Sunita Ghosh":        0.52,   # educated Kolkata woman, secular
    "Rupa Mandal":         0.72,   # young North Bengal OBC woman
    "Nasrin Ahmed":        0.85,   # Muslim educated woman, moderate devout
    "Mridula Chatterjee":  0.50,   # educated Durgapur, secular
    "Anwara Begum":        0.88,   # Muslim woman S24Pgs, devout
    # Matua community depth (4)
    "Tarun Biswas":        0.82,   # young Matua activist, identity-religious salience (CAA)
    "Bimala Mondal":       0.80,   # Matua woman homemaker
    "Nirmal Sarkar":       0.72,   # elderly Matua, pragmatic moderate
    "Kalyani Das":         0.80,   # Matua woman, identity-driven
    # Young first-time voters (5)
    "Arpita Roy":          0.50,   # Kolkata student, secular urban milieu
    "Rahul Barman":        0.68,   # unemployed graduate, North Bengal
    "Sabana Khatun":       0.88,   # young Muslim woman, first vote
    "Sourav Das":          0.65,   # SC jobseeker, Howrah, disillusioned
    "Priya Barua":         0.62,   # young Gorkha-adjacent, mixed identity
    # Gorkha / Darjeeling hills (3)
    "Pemba Tamang":        0.72,   # GJM voter, Hindu OBC, Gorkha identity primary
    "Sunita Rai":          0.68,   # Gorkha woman, moderate Hindu
    "Bishal Gurung":       0.65,   # Gorkha pragmatic, secular-ish business
    # Ex-CPM → BJP switchers (3)
    "Debabrata Mondal":    0.58,   # ex-CPM union man, secular Left legacy
    "Sudha Pal":           0.55,   # ex-CPM schoolteacher, secular
    "Haran Mahato":        0.68,   # ex-CPM OBC, Jungle Mahal, modest salience
    # Sandeshkhali women (2)
    "Rekha Halder":        0.78,   # SC woman, folk Hindu, rural
    "Bina Naskar":         0.76,   # OBC woman, anti-TMC post-incident

    # ── B-WB-3 calibration additions (9) ─────────────────────────────────────
    # CPM / Left-Congress holdouts (6) — secular Left tradition, low salience
    "Arun Bhattacharya":   0.38,   # Jadavpur retired professor, deeply secular
    "Subhas Chattopadhyay":0.62,   # CPM booth worker, moderate Hindu
    "Meenakshi Roy":       0.55,   # Ex-CITU union, urban educated, secular
    "Pradip Ghosh":        0.52,   # Congress loyalist, Berhampore, secular
    "Tapan Mondal":        0.60,   # Ex-CPM steel worker, working-class moderate
    "Sabitri Das":         0.68,   # SC woman, Hooghly, folk Hindu
    # AIMIM / disillusioned Muslim voters (3) — high devoutness
    "Abdul Karim":         0.92,   # Madrasa-educated, Murshidabad, very devout
    "Ruksana Parvin":      0.82,   # Educated Muslim woman, Malda, moderate devout
    "Nurul Haque":         0.86,   # Muslim trader, Berhampore, devout

    # ── B-WB-4 calibration additions (9) ─────────────────────────────────────
    # Koch-Rajbongshi / North Bengal BJP (3)
    "Uttam Barman":        0.82,   # Koch-Rajbongshi, Hindu OBC, BJP communal identity
    "Shefali Barman":      0.80,   # Koch-Rajbongshi woman, Hindu nationalist
    "Gobinda Roy":         0.78,   # tea garden community, Alipurduar, Hindu OBC
    # Jungle Mahal tribals (3) — syncretist Hindu + folk religion
    "Mangal Murmu":        0.80,   # Santali tribal, Jhargram, syncretist
    "Sushila Hansda":      0.78,   # tribal woman, Purulia, folk Hindu
    "Ratan Tudu":          0.76,   # tribal farmer, Bankura, BJP voter
    # Hindu consolidation belt (3)
    "Nikhil Ghosh":        0.62,   # middle-class Asansol, moderate Hindu
    "Rekha Singh":         0.72,   # Hindu OBC woman, Bankura, BJP identity
    "Subal Pal":           0.75,   # Hindu trader, Burdwan, BJP consolidation
}

# ---------------------------------------------------------------------------
# Bengal Constituency Cluster Pools — B-WB-6
# Each pool covers one demographic archetype cluster for constituency-level
# simulation. 10 clusters × 20 personas = 200 simulation units covering all
# 294 West Bengal assembly seats.
#
# Format (same as _BENGAL_GENERAL_POOL):
# (name, age, gender, country, region, city, urban_tier,
#  structure, size, income_bracket, dual_income,
#  life_stage, education, employment, political_lean, religion, caste)
# ---------------------------------------------------------------------------

# ── CLUSTER 1: Murshidabad Muslim Heartland (22 seats) ─────────────────────
# 2021 baseline: TMC 90%, BJP 10%
# 2026 risk: SIR 460k deletions, AIMIM-AJUP alliance fragmentation
# Pool: 16 Muslim (9 opposition, 4 opposition_lean, 3 neutral/AIMIM-curious)
#        4 Hindu (2 bjp_lean, 1 bjp_supporter, 1 neutral)
_BENGAL_MURSHIDABAD_POOL = [
    ("Abul Kasem",      54, "male",   "India", "West Bengal", "Murshidabad",  "rural",  "joint",          7, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Paddy farmer, Bhagabangola area, TMC loyalist
    ("Farida Begum",    38, "female", "India", "West Bengal", "Murshidabad",  "rural",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Lakshmir Bhandar recipient, Domkal
    ("Harunur Rashid",  45, "male",   "India", "West Bengal", "Jangipur",     "tier3",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "obc"),       # Small farmer, Jangipur block, anti-BJP
    ("Joynal Abedin",   60, "male",   "India", "West Bengal", "Berhampore",   "tier2",  "joint",          8, "lower",        False, "retired",       "high-school",   "retired",       "opposition",     "muslim", "general"),   # Retired, Berhampore, strong TMC elderly
    ("Khaleda Khatun",  33, "female", "India", "West Bengal", "Domkal",       "tier3",  "nuclear",        4, "lower",        False, "early-family",  "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Rural woman, Domkal, TMC welfare beneficiary
    ("Lutfur Rahman",   42, "male",   "India", "West Bengal", "Farakka",      "tier3",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "obc"),       # Fisherman, Farakka area, TMC
    ("Mafizul Islam",   29, "male",   "India", "West Bengal", "Murshidabad",  "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "opposition",     "muslim", "general"),   # Young educated Muslim, aware of AIMIM but TMC
    ("Nasima Khatun",   47, "female", "India", "West Bengal", "Kandi",        "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "part-time",     "opposition",     "muslim", "general"),   # Schoolworker, Kandi, opposition
    ("Obaidur Rahman",  36, "male",   "India", "West Bengal", "Jalangi",      "rural",  "joint",          7, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "obc"),       # Boatman, Jalangi, river community, TMC
    ("Parvez Alam",     26, "male",   "India", "West Bengal", "Berhampore",   "tier2",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "opposition_lean","muslim", "general"),   # College grad, Berhampore, TMC but frustrated
    ("Rokeya Bibi",     50, "female", "India", "West Bengal", "Raghunathganj","tier3",  "joint",          6, "lower",        False, "late-career",   "high-school",   "part-time",     "opposition_lean","muslim", "general"),   # Rural woman, Raghunathganj, soft TMC
    ("Saminur Rahman",  40, "male",   "India", "West Bengal", "Lalgola",      "rural",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition_lean","muslim", "general"),   # Farmer, Lalgola, reliable TMC voter
    ("Tahera Khatun",   35, "female", "India", "West Bengal", "Murshidabad",  "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition_lean","muslim", "obc"),       # Muslim OBC woman, soft TMC, frustrated
    ("Umar Faruk",      31, "male",   "India", "West Bengal", "Suti",         "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "neutral",        "muslim", "general"),   # Educated, SIR voter deletion affected, open to AIMIM
    ("Wahida Begum",    44, "female", "India", "West Bengal", "Domkal",       "rural",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "neutral",        "muslim", "general"),   # SIR-affected, husband's name deleted, wavering
    ("Ziaur Rehman",    38, "male",   "India", "West Bengal", "Berhampore",   "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "neutral",        "muslim", "general"),   # Small trader, considers AIMIM as protest vote
    ("Bhaskar Ghosh",   52, "male",   "India", "West Bengal", "Berhampore",   "tier2",  "nuclear",        3, "middle",       True,  "late-career",   "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Hindu professional, BJP-leaning in Muslim-maj district
    ("Chaitali Mondal", 39, "female", "India", "West Bengal", "Kandi",        "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "general"),   # Hindu woman, BJP minority consciousness
    ("Debasish Pal",    48, "male",   "India", "West Bengal", "Murshidabad",  "tier2",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "self-employed", "bjp_supporter",  "hindu",  "obc"),       # Hindu trader, Hindu consolidation zone
    ("Esha Sarkar",     27, "female", "India", "West Bengal", "Lalgola",      "tier3",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",  "sc"),        # Young Hindu SC woman, pragmatic
]

_BENGAL_MURSHIDABAD_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Abul Kasem": 0.90, "Farida Begum": 0.92, "Harunur Rashid": 0.88,
    "Joynal Abedin": 0.90, "Khaleda Khatun": 0.90, "Lutfur Rahman": 0.88,
    "Mafizul Islam": 0.78, "Nasima Khatun": 0.86, "Obaidur Rahman": 0.88,
    "Parvez Alam": 0.72, "Rokeya Bibi": 0.88, "Saminur Rahman": 0.86,
    "Tahera Khatun": 0.86, "Umar Faruk": 0.75, "Wahida Begum": 0.86,
    "Ziaur Rehman": 0.80, "Bhaskar Ghosh": 0.65, "Chaitali Mondal": 0.72,
    "Debasish Pal": 0.70, "Esha Sarkar": 0.60,
}

# ── CLUSTER 2: Malda Muslim Plurality Belt (12 seats) ──────────────────────
# 2021 baseline: TMC 67%, BJP 33%
# 2026 risk: SIR 240k deletions, AIMIM-ISF-AJUP three-way split
# Pool: 11 Muslim (5 opp, 2 opp_lean, 4 neutral/AIMIM-open), 9 Hindu (5 bjp_lean, 3 bjp_supp, 1 neutral)
_BENGAL_MALDA_POOL = [
    ("Amirul Islam",    46, "male",   "India", "West Bengal", "Malda",        "tier2",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Mango farmer, English Bazar, TMC
    ("Badrunnessa",     40, "female", "India", "West Bengal", "Malda",        "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Welfare scheme recipient, TMC
    ("Feroz Khan",      34, "male",   "India", "West Bengal", "Harishchandrapur","tier3","joint",          5, "lower",        False, "early-career",  "high-school",   "full-time",     "opposition",     "muslim", "obc"),       # Rural Muslim, Harishchandrapur, TMC
    ("Golam Rasul",     55, "male",   "India", "West Bengal", "Ratua",        "rural",  "joint",          7, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Farmer, Ratua, TMC loyalist
    ("Hasibur Rahman",  30, "male",   "India", "West Bengal", "Mothabari",    "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "opposition",     "muslim", "general"),   # Young educated, Mothabari
    ("Ismail Hossain",  43, "male",   "India", "West Bengal", "Malda",        "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "opposition_lean","muslim", "general"),   # Small trader, Malda town, soft TMC
    ("Jahanara Bibi",   37, "female", "India", "West Bengal", "Kaliachak",    "rural",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition_lean","muslim", "obc"),       # Rural woman, Kaliachak, uncertain loyalty
    ("Kader Ali",       28, "male",   "India", "West Bengal", "Malda",        "tier2",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "neutral",        "muslim", "general"),   # Educated youth, considers ISF/AIMIM option
    ("Liaquat Ali",     50, "male",   "India", "West Bengal", "Gazole",       "tier3",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "neutral",        "muslim", "general"),   # Farmer, SIR voter deletion affected
    ("Masum Ali",       35, "male",   "India", "West Bengal", "Old Malda",    "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "muslim", "obc"),       # Disenchanted with TMC corruption, swing voter
    ("Naima Khatun",    42, "female", "India", "West Bengal", "Malda",        "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "undergraduate", "part-time",     "neutral",        "muslim", "general"),   # Educated woman, open to AIMIM women's platform
    ("Ajit Kumar Das",  49, "male",   "India", "West Bengal", "Malda",        "tier2",  "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Hindu professional, Malda town
    ("Benu Barman",     58, "male",   "India", "West Bengal", "Gajol",        "tier3",  "joint",          5, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # Rajbanshi community, Gajol, BJP Hindu
    ("Chandan Roy",     32, "male",   "India", "West Bengal", "Malda",        "tier2",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Young Hindu trader, BJP lean
    ("Dilip Kumar Ghosh",55,"male",   "India", "West Bengal", "Ingrej Bazar", "tier2",  "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "self-employed", "bjp_supporter",  "hindu",  "general"),   # Senior Hindu trader, BJP supporter
    ("Evelina Mandal",  44, "female", "India", "West Bengal", "Bamongola",    "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "sc"),        # SC Hindu woman, BJP lean
    ("Falguni Sen",     36, "female", "India", "West Bengal", "Malda",        "tier2",  "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "bjp_lean",       "hindu",  "general"),   # Educated Hindu woman, BJP-sympathetic
    ("Gouri Devi",      60, "female", "India", "West Bengal", "Ratua",        "rural",  "joint",          6, "lower",        False, "retired",       "high-school",   "homemaker",     "bjp_supporter",  "hindu",  "obc"),       # Elderly Hindu OBC, BJP community anchor
    ("Hrishikesh Biswas",40,"male",   "India", "West Bengal", "Malda",        "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_supporter",  "hindu",  "sc"),        # SC Hindu, BJP since 2019
    ("Indira Pal",      29, "female", "India", "West Bengal", "Kaliachak",    "tier3",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",  "general"),   # Young Hindu woman, pragmatic
]

_BENGAL_MALDA_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Amirul Islam": 0.88, "Badrunnessa": 0.90, "Feroz Khan": 0.86,
    "Golam Rasul": 0.90, "Hasibur Rahman": 0.78, "Ismail Hossain": 0.82,
    "Jahanara Bibi": 0.88, "Kader Ali": 0.70, "Liaquat Ali": 0.86,
    "Masum Ali": 0.82, "Naima Khatun": 0.75,
    "Ajit Kumar Das": 0.62, "Benu Barman": 0.78, "Chandan Roy": 0.65,
    "Dilip Kumar Ghosh": 0.70, "Evelina Mandal": 0.75, "Falguni Sen": 0.58,
    "Gouri Devi": 0.78, "Hrishikesh Biswas": 0.72, "Indira Pal": 0.60,
}

# ── CLUSTER 3: Matua Belt — Nadia + North 24 Parganas (40 seats) ───────────
# 2021 baseline: TMC 65%, BJP 30%, Left 5%
# 2026 shift: CAA promise vs SIR mass deletions (Nadia 77.86% deletion rate!)
#             BJP risks losing Matua base; TMC could recover 8-12 seats
# Pool: 17 Hindu SC (Matua/Namasudra), 3 Muslim (N24Pgs minorities)
#        BJP-heavy but with neutral/angry SIR bloc
_BENGAL_MATUA_BELT_POOL = [
    ("Ashok Biswas",        52, "male",   "India", "West Bengal", "Ranaghat",     "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "sc"),        # Matua activist, CAA loyalist, BJP strongman
    ("Binodini Haldar",     46, "female", "India", "West Bengal", "Bangaon",      "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_supporter",  "hindu",  "sc"),        # Matua woman, BJP since CAA promise
    ("Chittaranjan Das",    58, "male",   "India", "West Bengal", "Krishnaganj",  "tier3",  "joint",          5, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "sc"),        # Matua community elder, BJP community leader
    ("Dulal Mondal",        44, "male",   "India", "West Bengal", "Gaighata",     "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "sc"),        # Gaighata Matua — 26k SIR deletions; shaken BJP voter
    ("Ekadashi Sarkar",     39, "female", "India", "West Bengal", "Gaighata",     "rural",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_lean",       "hindu",  "sc"),        # SIR deleted from roll, CAA fury turned BJP anger
    ("Fakirchand Biswas",   63, "male",   "India", "West Bengal", "Ranaghat",     "tier3",  "couple-no-kids", 2, "lower",        False, "retired",       "high-school",   "retired",       "bjp_supporter",  "hindu",  "sc"),        # Elderly Matua, BJP loyalist, though worried
    ("Gopal Biswas",        34, "male",   "India", "West Bengal", "Nakashipara",  "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",  "sc"),        # Young Matua, Nakashipara, BJP lean but restless
    ("Hrishikesh Haldar",   48, "male",   "India", "West Bengal", "Karimpur",     "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "neutral",        "hindu",  "sc"),        # Karimpur small trader, Matua, CAA-SIR paradox breaks BJP loyalty
    ("Indubhushan Mondal",  42, "male",   "India", "West Bengal", "Chapra",       "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # Matua, SIR deleted neighbor, considering TMC again
    ("Jayanti Das",         36, "female", "India", "West Bengal", "Bangaon",      "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "neutral",        "hindu",  "sc"),        # Matua woman, Lakshmir Bhandar recipient, wavering
    ("Kanta Biswas",        27, "female", "India", "West Bengal", "Ranaghat",     "tier3",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",  "sc"),        # Young Matua woman, first major election
    ("Latika Sarkar",       54, "female", "India", "West Bengal", "Haringhata",   "rural",  "nuclear",        5, "lower",        False, "late-career",   "high-school",   "homemaker",     "bjp_lean",       "hindu",  "sc"),        # Rural Matua woman, BJP lean, Swasthya Sathi beneficiary too
    ("Madhab Biswas",       31, "male",   "India", "West Bengal", "Gaighata",     "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # Gaighata youth, SIR deleted from roll, angry
    ("Nabin Mondal",        45, "male",   "India", "West Bengal", "Hanskhali",    "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # Matua, Hanskhali, considers TMC Lakshmir Bhandar
    ("Prabha Biswas",       60, "female", "India", "West Bengal", "Ranaghat",     "tier3",  "joint",          6, "lower",        False, "retired",       "high-school",   "homemaker",     "opposition_lean","hindu",  "sc"),        # Elderly Matua woman, returning to TMC over SIR
    ("Ratan Biswas",        38, "male",   "India", "West Bengal", "Bangaon",      "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "opposition_lean","hindu",  "sc"),        # Matua, returning to TMC after BJP anger
    ("Sarat Haldar",        50, "male",   "India", "West Bengal", "Santipur",     "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "self-employed", "opposition_lean","hindu",  "sc"),        # Santipur weaver, Matua community, drift back to TMC
    ("Ahamad Ali",          40, "male",   "India", "West Bengal", "Barasat",      "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "general"),   # N24Pgs Muslim, TMC stronghold Barasat
    ("Bachchu Sk",          35, "male",   "India", "West Bengal", "Habra",        "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "obc"),       # Muslim, N24Pgs suburban, TMC
    ("Chand Bibi",          44, "female", "India", "West Bengal", "Barasat",      "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim woman, N24Pgs, welfare recipient
]

_BENGAL_MATUA_BELT_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Ashok Biswas": 0.82, "Binodini Haldar": 0.84, "Chittaranjan Das": 0.80,
    "Dulal Mondal": 0.78, "Ekadashi Sarkar": 0.80, "Fakirchand Biswas": 0.82,
    "Gopal Biswas": 0.76, "Hrishikesh Haldar": 0.72, "Indubhushan Mondal": 0.74,
    "Jayanti Das": 0.78, "Kanta Biswas": 0.68, "Latika Sarkar": 0.80,
    "Madhab Biswas": 0.72, "Nabin Mondal": 0.74, "Prabha Biswas": 0.80,
    "Ratan Biswas": 0.76, "Sarat Haldar": 0.72,
    "Ahamad Ali": 0.88, "Bachchu Sk": 0.86, "Chand Bibi": 0.88,
}

# ── CLUSTER 4: Jungle Mahal Tribal Belt (50 seats) ─────────────────────────
# Districts: Jhargram, Bankura, Purulia, West Midnapore
# 2021 baseline: TMC 78%, BJP 18%, Left 4%
# Key seats: Ghatal (966 margin), Bankura (1,468 margin)
# Pool: 13 ST tribal, 7 Hindu OBC (Mahato communities)
_BENGAL_JUNGLE_MAHAL_POOL = [
    ("Amol Soren",      44, "male",   "India", "West Bengal", "Jhargram",     "tier3",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "hindu",  "st"),        # Santali farmer, MGNREGA beneficiary, TMC
    ("Bhulo Murmu",     38, "male",   "India", "West Bengal", "Bankura",      "tier3",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "hindu",  "st"),        # Santali, Bankura, welfare TMC voter
    ("Champa Hansda",   34, "female", "India", "West Bengal", "Jhargram",     "rural",  "joint",          5, "lower",        False, "early-family",  "high-school",   "part-time",     "opposition",     "hindu",  "st"),        # Tribal woman, Jhargram, TMC MGNREGA
    ("Dhanu Kisku",     50, "male",   "India", "West Bengal", "Purulia",      "tier3",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "st"),        # Tribal farmer, Purulia, opposition
    ("Eknath Munda",    42, "male",   "India", "West Bengal", "Midnapore",    "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "hindu",  "st"),        # Munda tribal, Midnapore, TMC
    ("Fulchand Besra",  36, "male",   "India", "West Bengal", "Bankura",      "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition_lean","hindu",  "st"),        # Young Santali, Bankura, lean TMC but BJP wave 2019 affected
    ("Ganga Hembram",   48, "female", "India", "West Bengal", "Jhargram",     "rural",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition_lean","hindu",  "st"),        # Tribal woman, moderate TMC
    ("Habu Tudu",       32, "male",   "India", "West Bengal", "Bankura",      "rural",  "joint",          5, "lower",        False, "early-career",  "high-school",   "full-time",     "opposition_lean","hindu",  "st"),        # Young tribal, Bankura — BJP gained here 2019-2021
    ("Ila Soren",       29, "female", "India", "West Bengal", "Purulia",      "tier3",  "other",          2, "lower",        False, "early-career",  "high-school",   "full-time",     "opposition_lean","hindu",  "st"),        # Young tribal woman, first few votes, TMC-leaning
    ("Jairam Mahali",   55, "male",   "India", "West Bengal", "Jhargram",     "tier3",  "joint",          7, "lower",        False, "late-career",   "high-school",   "full-time",     "neutral",        "hindu",  "st"),        # Tribal elder, Jhargram, pragmatic swing
    ("Kali Murmu",      40, "female", "India", "West Bengal", "Bankura",      "rural",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "part-time",     "neutral",        "hindu",  "st"),        # Tribal woman, considering BJP for BJP tribal programs
    ("Lakhan Soren",    46, "male",   "India", "West Bengal", "Midnapore",    "tier3",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "st"),        # Ex-BJP voter 2019, Midnapore tribal, BJP lean
    ("Mani Munda",      35, "male",   "India", "West Bengal", "Purulia",      "tier3",  "nuclear",        3, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "st"),        # Tribal, Purulia, uncertain — BJP made inroads
    ("Arjun Mahato",    48, "male",   "India", "West Bengal", "Midnapore",    "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "bjp_supporter",  "hindu",  "obc"),       # Kurmi Mahato, Midnapore, BJP since 2019
    ("Biren Mahato",    42, "male",   "India", "West Bengal", "Bankura",      "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # OBC, Bankura, BJP voter
    ("Charan Mahato",   37, "male",   "India", "West Bengal", "Purulia",      "tier3",  "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # Mahato OBC, BJP lean
    ("Devaki Mahato",   50, "female", "India", "West Bengal", "Midnapore",    "tier3",  "nuclear",        4, "lower",        False, "late-career",   "high-school",   "homemaker",     "opposition",     "hindu",  "obc"),       # Rural OBC woman, MGNREGA beneficiary, TMC
    ("Ekadashi Pal",    58, "male",   "India", "West Bengal", "Ghatal",       "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "self-employed", "opposition",     "hindu",  "obc"),       # Ghatal small trader (966-vote margin seat), TMC
    ("Fatik Das",       33, "male",   "India", "West Bengal", "Bankura",      "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "opposition",     "hindu",  "sc"),        # Young SC, Bankura, TMC welfare
    ("Gopal Mahato",    62, "male",   "India", "West Bengal", "Jhargram",     "tier3",  "couple-no-kids", 2, "lower",        False, "retired",       "high-school",   "retired",       "bjp_lean",       "hindu",  "obc"),       # Elderly OBC, Jhargram, BJP consolidation vote
]

_BENGAL_JUNGLE_MAHAL_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Amol Soren": 0.82, "Bhulo Murmu": 0.80, "Champa Hansda": 0.78,
    "Dhanu Kisku": 0.82, "Eknath Munda": 0.80, "Fulchand Besra": 0.76,
    "Ganga Hembram": 0.78, "Habu Tudu": 0.76, "Ila Soren": 0.72,
    "Jairam Mahali": 0.80, "Kali Murmu": 0.78, "Lakhan Soren": 0.76,
    "Mani Munda": 0.78,
    "Arjun Mahato": 0.72, "Biren Mahato": 0.74, "Charan Mahato": 0.72,
    "Devaki Mahato": 0.76, "Ekadashi Pal": 0.68, "Fatik Das": 0.74, "Gopal Mahato": 0.72,
}

# ── CLUSTER 5: North Bengal Koch-Rajbongshi (30 seats) ─────────────────────
# Districts: Cooch Behar, Alipurduar, Jalpaiguri
# 2021 baseline: BJP 60%, TMC 32%, Left 8%
# BJP stronghold. Rajbanshi OBC + tea garden ST community.
# Pool: 14 Hindu OBC (Rajbanshi/Koch), 4 ST (tea garden), 2 general
_BENGAL_NORTH_BENGAL_POOL = [
    ("Ananda Barman",   44, "male",   "India", "West Bengal", "Cooch Behar",  "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_supporter",  "hindu",  "obc"),       # Rajbanshi, Cooch Behar, BJP heartland
    ("Birendra Barman", 52, "male",   "India", "West Bengal", "Cooch Behar",  "tier2",  "joint",          5, "lower-middle", False, "late-career",   "high-school",   "self-employed", "bjp_supporter",  "hindu",  "obc"),       # Koch-Rajbongshi trader, BJP strong
    ("Chandra Barman",  38, "female", "India", "West Bengal", "Cooch Behar",  "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_supporter",  "hindu",  "obc"),       # Rajbanshi woman, BJP identity voter
    ("Dhiren Barman",   60, "male",   "India", "West Bengal", "Dinhata",      "tier3",  "nuclear",        3, "lower",        False, "retired",       "high-school",   "retired",       "bjp_supporter",  "hindu",  "obc"),       # Dinhata (57-vote margin!), BJP stronghold
    ("Ekramul Barman",  35, "male",   "India", "West Bengal", "Tufanganj",    "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "bjp_supporter",  "hindu",  "obc"),       # Young Rajbanshi, BJP educated voter
    ("Falguni Barman",  29, "female", "India", "West Bengal", "Cooch Behar",  "tier3",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",  "obc"),       # Young Rajbanshi woman, BJP lean
    ("Ganesh Barman",   46, "male",   "India", "West Bengal", "Mathabhanga",  "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # Mathabhanga (BJP but contested), BJP lean
    ("Hemanta Roy",     40, "male",   "India", "West Bengal", "Jalpaiguri",   "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "bjp_lean",       "hindu",  "obc"),       # Jalpaiguri (941-vote margin), close contest
    ("Indra Barman",    56, "male",   "India", "West Bengal", "Alipurduar",   "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # Alipurduar BJP voter, Koch community
    ("Jamini Barman",   48, "female", "India", "West Bengal", "Cooch Behar",  "tier3",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_lean",       "hindu",  "obc"),       # Rajbanshi woman, BJP lean
    ("Kanu Barman",     33, "male",   "India", "West Bengal", "Sitai",        "rural",  "nuclear",        3, "lower",        False, "early-career",  "high-school",   "full-time",     "neutral",        "hindu",  "obc"),       # Young Rajbanshi, Sitai, less politicised
    ("Lalita Barman",   41, "female", "India", "West Bengal", "Dinhata",      "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_supporter",  "hindu",  "obc"),       # Dinhata woman, BJP stronghold
    ("Makhanlal Roy",   58, "male",   "India", "West Bengal", "Cooch Behar",  "tier2",  "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "bjp_supporter",  "hindu",  "obc"),       # Elderly Koch-Rajbongshi, BJP loyalist
    ("Narayan Barman",  45, "male",   "India", "West Bengal", "Tufanganj",    "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "obc"),       # Rajbanshi, pragmatic vote based on development
    ("Asha Oraon",      36, "female", "India", "West Bengal", "Alipurduar",   "rural",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "part-time",     "bjp_lean",       "hindu",  "st"),        # Tea garden tribal woman, BJP
    ("Bahadur Oraon",   44, "male",   "India", "West Bengal", "Jalpaiguri",   "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "st"),        # Tea garden tribal, BJP
    ("Champa Tirkey",   38, "female", "India", "West Bengal", "Alipurduar",   "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "neutral",        "hindu",  "st"),        # Tea garden woman, swing voter
    ("Dhansing Lakra",  50, "male",   "India", "West Bengal", "Jalpaiguri",   "rural",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "st"),        # Tea garden tribal, TMC MGNREGA loyalty
    ("Aakash Dey",      30, "male",   "India", "West Bengal", "Siliguri",     "tier2",  "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "neutral",        "hindu",  "general"),   # Young professional Siliguri, swing
    ("Bulbul Sharma",   42, "female", "India", "West Bengal", "Jalpaiguri",   "tier2",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition",     "hindu",  "general"),   # Educated woman, Jalpaiguri town, anti-BJP
]

_BENGAL_NORTH_BENGAL_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Ananda Barman": 0.82, "Birendra Barman": 0.80, "Chandra Barman": 0.80,
    "Dhiren Barman": 0.78, "Ekramul Barman": 0.75, "Falguni Barman": 0.72,
    "Ganesh Barman": 0.78, "Hemanta Roy": 0.74, "Indra Barman": 0.76,
    "Jamini Barman": 0.80, "Kanu Barman": 0.68, "Lalita Barman": 0.78,
    "Makhanlal Roy": 0.78, "Narayan Barman": 0.70,
    "Asha Oraon": 0.80, "Bahadur Oraon": 0.80, "Champa Tirkey": 0.78,
    "Dhansing Lakra": 0.80,
    "Aakash Dey": 0.52, "Bulbul Sharma": 0.55,
}

# ── CLUSTER 6: Urban Kolkata (11 seats) ────────────────────────────────────
# TMC fortress; educated Bengali middle/upper-middle class; Left intellectual legacy
# 2021 baseline: TMC 90%, BJP 8%, Left 2%
# Pool: 15 Hindu general (bhadralok + educated), 3 OBC, 2 Muslim
_BENGAL_KOLKATA_URBAN_POOL = [
    ("Amitabh Basu",        55, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "upper-middle", True,  "late-career",   "postgraduate",  "full-time",     "opposition",     "hindu",  "general"),   # Academic, South Kolkata, TMC intellectual
    ("Barnali Banerjee",    42, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "opposition",     "hindu",  "general"),   # Professional, Balygunge, strong TMC
    ("Chandan Mukherjee",   36, "male",   "India", "West Bengal", "Kolkata",         "metro",  "other",          1, "upper-middle", False, "mid-career",    "postgraduate",  "full-time",     "opposition",     "hindu",  "general"),   # Media professional, South Kolkata, TMC
    ("Dipti Roy",           48, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition",     "hindu",  "general"),   # Schoolteacher, North Kolkata, TMC
    ("Eesha Chatterjee",    29, "female", "India", "West Bengal", "Kolkata",         "metro",  "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "opposition",     "hindu",  "general"),   # Young professional, new voter, TMC
    ("Gourab Sen",          62, "male",   "India", "West Bengal", "Kolkata",         "metro",  "couple-no-kids", 2, "upper-middle", True,  "late-career",   "postgraduate",  "retired",       "opposition",     "hindu",  "general"),   # Retired academic, Jadavpur area, TMC
    ("Himadri Bose",        44, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "opposition_lean","hindu",  "general"),   # IT professional, Salt Lake, soft TMC
    ("Ipsita Datta",        38, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition",     "hindu",  "general"),   # Working woman, Tollygunge, TMC
    ("Jaydeep Roy",         52, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "self-employed", "opposition_lean","hindu",  "general"),   # Trader, Hatibagan, soft TMC
    ("Kasturi Ghosh",       33, "female", "India", "West Bengal", "Kolkata",         "metro",  "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","hindu",  "general"),   # Young professional, Shyambazar area, TMC
    ("Leena Sarkar",        57, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "lower-middle", False, "late-career",   "undergraduate", "full-time",     "opposition",     "hindu",  "general"),   # Teacher, Beliaghata, strong TMC
    ("Moumita Chakraborty", 27, "female", "India", "West Bengal", "Kolkata",         "metro",  "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","hindu",  "general"),   # Young grad, Gariahaat, TMC-leaning
    ("Nirupa Roy",          46, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "self-employed", "neutral",        "hindu",  "general"),   # Small business, Burrabazar, more practical
    ("Oindri Majumdar",     35, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "opposition",     "hindu",  "general"),   # Educator, Bhowanipore, strong TMC
    ("Partha Roy",          41, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Businessman, Shyampukur, BJP sympathiser
    ("Sajida Begum",        39, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim woman, Metiabruz, strong TMC
    ("Imtiaz Ahmed",        44, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "opposition",     "muslim", "general"),   # Muslim trader, Park Circus, TMC
    ("Tapan Dutta",         49, "male",   "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "neutral",        "hindu",  "obc"),       # OBC professional, Kolkata, pragmatic
    ("Usha Ghosh",          37, "female", "India", "West Bengal", "Kolkata",         "metro",  "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "opposition_lean","hindu",  "obc"),       # OBC working woman, North Kolkata
    ("Vikrant Saha",        32, "male",   "India", "West Bengal", "Kolkata",         "metro",  "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "bjp_lean",       "hindu",  "general"),   # Young professional, BJP-sympathetic urban Hindu
]

_BENGAL_KOLKATA_URBAN_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Amitabh Basu": 0.42, "Barnali Banerjee": 0.48, "Chandan Mukherjee": 0.40,
    "Dipti Roy": 0.58, "Eesha Chatterjee": 0.45, "Gourab Sen": 0.42,
    "Himadri Bose": 0.48, "Ipsita Datta": 0.55, "Jaydeep Roy": 0.62,
    "Kasturi Ghosh": 0.48, "Leena Sarkar": 0.60, "Moumita Chakraborty": 0.45,
    "Nirupa Roy": 0.65, "Oindri Majumdar": 0.50, "Partha Roy": 0.68,
    "Sajida Begum": 0.86, "Imtiaz Ahmed": 0.80,
    "Tapan Dutta": 0.62, "Usha Ghosh": 0.65, "Vikrant Saha": 0.60,
}

# ── CLUSTER 7: South Bengal Rural TMC Stronghold (55 seats) ────────────────
# Districts: South 24-Parganas, Hooghly, parts of West Midnapore
# 2021 baseline: TMC 77%, BJP 20%, Left 3%
# Mamata's original powerbase: welfare, fishermen, Sundarbans
# Pool: 12 Hindu SC/OBC rural, 5 Muslim, 3 Hindu general
_BENGAL_SOUTH_RURAL_POOL = [
    ("Arati Mondal",    48, "female", "India", "West Bengal", "Kakdwip",         "rural",  "joint",          6, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "hindu",  "obc"),       # Fisherwoman, Kakdwip, TMC
    ("Biren Das",       52, "male",   "India", "West Bengal", "Basirhat",        "tier3",  "nuclear",        4, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "sc"),        # SC farmer, Basirhat, TMC welfare
    ("Chhanda Roy",     36, "female", "India", "West Bengal", "Baruipur",        "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "hindu",  "sc"),        # Baruipur SC woman, Lakshmir Bhandar
    ("Debdas Mondal",   45, "male",   "India", "West Bengal", "Canning",         "tier3",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "hindu",  "sc"),        # Canning farmer, Sundarbans-adjacent, TMC
    ("Ela Bhowmik",     40, "female", "India", "West Bengal", "Hooghly",         "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "opposition",     "hindu",  "obc"),       # Hooghly OBC woman, TMC loyalty
    ("Felu Mondal",     58, "male",   "India", "West Bengal", "Diamond Harbour", "tier3",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "sc"),        # Fisher, Diamond Harbour, old-guard TMC
    ("Geeta Sasmal",    43, "female", "India", "West Bengal", "Contai",          "tier3",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "hindu",  "obc"),       # East Midnapore woman, TMC
    ("Harekrishna Patra",50,"male",   "India", "West Bengal", "Contai",          "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "self-employed", "opposition_lean","hindu",  "obc"),       # Small trader, Contai, soft TMC
    ("Itu Pradhan",     34, "female", "India", "West Bengal", "Kakdwip",         "rural",  "nuclear",        4, "lower",        False, "early-family",  "high-school",   "part-time",     "opposition",     "hindu",  "sc"),        # SC fisherwoman, TMC welfare dependent
    ("Jiten Bhunia",    46, "male",   "India", "West Bengal", "Joynagar",        "tier3",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition_lean","hindu",  "sc"),        # Joynagar SC, soft TMC
    ("Kamala Maity",    60, "female", "India", "West Bengal", "Tamluk",          "tier3",  "joint",          6, "lower",        False, "retired",       "high-school",   "homemaker",     "opposition_lean","hindu",  "obc"),       # Tamluk (793-vote margin), OBC woman
    ("Latika Giri",     38, "female", "India", "West Bengal", "Hooghly",         "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # SC woman, Hooghly, welfare seeker but uncertain
    ("Mintu Haldar",    42, "male",   "India", "West Bengal", "Baruipur",        "tier3",  "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "bjp_lean",       "hindu",  "obc"),       # OBC trader, BJP-leaning
    ("Nilu Naskar",     29, "male",   "India", "West Bengal", "Canning",         "tier3",  "other",          2, "lower",        False, "early-career",  "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # Young SC, Sundarbans zone, uncertain
    ("Parimal Pal",     55, "male",   "India", "West Bengal", "Uluberia",        "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "obc"),       # Howrah rural BJP, OBC consolidation
    ("Rabia Khatun",    37, "female", "India", "West Bengal", "Canning",         "rural",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim woman, Canning, TMC
    ("Salim Khan",      44, "male",   "India", "West Bengal", "Basirhat",        "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "obc"),       # Muslim OBC, Basirhat, TMC
    ("Taslima Bibi",    39, "female", "India", "West Bengal", "Joynagar",        "rural",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim woman, rural S24Pgs, TMC
    ("Wazed Ali",       50, "male",   "India", "West Bengal", "Diamond Harbour", "tier3",  "joint",          6, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Muslim farmer, TMC loyal
    ("Yunus Molla",     33, "male",   "India", "West Bengal", "Basirhat",        "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "opposition_lean","muslim", "general"),   # Educated Muslim, S24Pgs, soft TMC
]

_BENGAL_SOUTH_RURAL_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Arati Mondal": 0.78, "Biren Das": 0.76, "Chhanda Roy": 0.78,
    "Debdas Mondal": 0.75, "Ela Bhowmik": 0.74, "Felu Mondal": 0.78,
    "Geeta Sasmal": 0.76, "Harekrishna Patra": 0.70, "Itu Pradhan": 0.76,
    "Jiten Bhunia": 0.74, "Kamala Maity": 0.78, "Latika Giri": 0.74,
    "Mintu Haldar": 0.70, "Nilu Naskar": 0.62, "Parimal Pal": 0.74,
    "Rabia Khatun": 0.88, "Salim Khan": 0.86, "Taslima Bibi": 0.88,
    "Wazed Ali": 0.88, "Yunus Molla": 0.78,
}

# ── CLUSTER 8: Burdwan Industrial Zone (25 seats) ──────────────────────────
# Districts: West Burdwan (Asansol-Durgapur), East Burdwan (Bardhaman)
# 2021 baseline: TMC 72%, BJP 25%, Left 3%
# Left legacy in coal-belt; industrial workers; CPM residual
# Pool: 12 Hindu OBC (workers), 4 Muslim, 4 general/SC — Left represented
_BENGAL_BURDWAN_INDUSTRIAL_POOL = [
    ("Alok Pal",        50, "male",   "India", "West Bengal", "Asansol",         "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "obc"),       # Coal-belt worker, TMC since Left decline
    ("Bulbul Mondal",   44, "female", "India", "West Bengal", "Durgapur",        "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "opposition",     "hindu",  "obc"),       # Factory worker woman, Durgapur, TMC
    ("Chitta Pal",      56, "male",   "India", "West Bengal", "Kulti",           "tier2",  "nuclear",        4, "lower",        False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "sc"),        # Kulti (679-vote margin), SC worker, TMC
    ("Durga Mallick",   38, "female", "India", "West Bengal", "Bardhaman",       "tier2",  "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "opposition",     "hindu",  "obc"),       # Worker woman, Bardhaman, TMC welfare
    ("Ekram Mondal",    42, "male",   "India", "West Bengal", "Asansol",         "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "opposition_lean","hindu",  "obc"),       # Trade-adjacent, soft TMC
    ("Fatema Khatun",   36, "female", "India", "West Bengal", "Asansol",         "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim woman, Asansol, TMC
    ("Gobinda Pal",     48, "male",   "India", "West Bengal", "Burdwan",         "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "opposition_lean","hindu",  "obc"),       # Burdwan worker, soft TMC
    ("Haider Ali",      45, "male",   "India", "West Bengal", "Durgapur",        "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Muslim worker, Durgapur, TMC
    ("Ikram Sheikh",    31, "male",   "India", "West Bengal", "Asansol",         "tier2",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "opposition_lean","muslim", "obc"),       # Young Muslim, Asansol, soft TMC
    ("Joydev Das",      53, "male",   "India", "West Bengal", "Kulti",           "tier2",  "nuclear",        4, "lower",        False, "late-career",   "high-school",   "full-time",     "left_lean",      "hindu",  "sc"),        # Ex-CITU Kulti worker, CPM residual vote
    ("Kartika Sarkar",  39, "female", "India", "West Bengal", "Bardhaman",       "tier2",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition_lean","hindu",  "general"),   # Educated woman, Bardhaman, soft TMC
    ("Laxman Pal",      46, "male",   "India", "West Bengal", "Durgapur",        "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # OBC worker, Durgapur, BJP lean
    ("Mina Sahani",     35, "female", "India", "West Bengal", "Asansol",         "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # OBC woman, BJP lean
    ("Nirmal Roy",      60, "male",   "India", "West Bengal", "Asansol",         "tier2",  "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "bjp_lean",       "hindu",  "general"),   # Retired, Asansol, BJP lean
    ("Om Pal",          28, "male",   "India", "West Bengal", "Durgapur",        "tier2",  "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",  "obc"),       # Young worker, Durgapur, uncertain
    ("Pranab Das",      54, "male",   "India", "West Bengal", "Burdwan",         "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "sc"),        # SC worker, Burdwan, TMC loyal
    ("Quasar Hossain",  40, "male",   "India", "West Bengal", "Asansol",         "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition_lean","muslim", "general"),   # Muslim, Asansol, soft TMC
    ("Rekha Kundu",     44, "female", "India", "West Bengal", "Bardhaman",       "tier2",  "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "obc"),       # OBC woman, Bardhaman, pragmatic
    ("Sukdeb Pal",      47, "male",   "India", "West Bengal", "Kulti",           "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_supporter",  "hindu",  "obc"),       # BJP OBC, Kulti industrial
    ("Tapasi Roy",      33, "female", "India", "West Bengal", "Durgapur",        "tier2",  "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "left_lean",      "hindu",  "general"),   # Educated Durgapur woman, CPM tradition, Left-Congress
]

_BENGAL_BURDWAN_INDUSTRIAL_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Alok Pal": 0.68, "Bulbul Mondal": 0.70, "Chitta Pal": 0.74,
    "Durga Mallick": 0.72, "Ekram Mondal": 0.65, "Fatema Khatun": 0.86,
    "Gobinda Pal": 0.66, "Haider Ali": 0.85, "Ikram Sheikh": 0.78,
    "Joydev Das": 0.52, "Kartika Sarkar": 0.55, "Laxman Pal": 0.72,
    "Mina Sahani": 0.72, "Nirmal Roy": 0.68, "Om Pal": 0.60,
    "Pranab Das": 0.70, "Quasar Hossain": 0.82, "Rekha Kundu": 0.65,
    "Sukdeb Pal": 0.72, "Tapasi Roy": 0.48,
}

# ── CLUSTER 9: Presidency Division Suburbs (40 seats) ──────────────────────
# North 24-Parganas suburban + remaining Presidency seats
# 2021 baseline: TMC 70%, BJP 12%, Left 18%
# KINGMAKER zone — highest Left legacy outside urban Kolkata
# SIR: 330k deletions in N24Pgs
# Pool: 11 Hindu general (educated urban/suburban), 6 Muslim, 3 OBC — Left represented
_BENGAL_PRESIDENCY_SUBURBS_POOL = [
    ("Abhijit Mukherjee", 52, "male",  "India", "West Bengal", "Barasat",         "tier2",  "nuclear",        3, "middle",       True,  "late-career",   "postgraduate",  "full-time",     "opposition",     "hindu",  "general"),   # Educated professional, Barasat, TMC
    ("Bina Dey",          44, "female","India", "West Bengal", "Baranagar",       "tier2",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition",     "hindu",  "general"),   # Teacher, Baranagar, TMC
    ("Chinmoy Roy",       38, "male",  "India", "West Bengal", "Dum Dum",         "tier2",  "nuclear",        3, "middle",       False, "mid-career",    "undergraduate", "full-time",     "opposition_lean","hindu",  "general"),   # Dum Dum suburban, TMC-lean
    ("Debarati Ghosh",    31, "female","India", "West Bengal", "Saltlake",        "metro",  "other",          1, "upper-middle", False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","hindu",  "general"),   # Young IT professional, Salt Lake, TMC
    ("Elias Ahmed",       46, "male",  "India", "West Bengal", "Barasat",         "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Muslim, Barasat, TMC loyal
    ("Firoza Khatun",     38, "female","India", "West Bengal", "Habra",           "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "opposition",     "muslim", "general"),   # Muslim woman, Habra, welfare TMC
    ("Goutam Biswas",     48, "male",  "India", "West Bengal", "Bongaon",         "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # SC, Bongaon (BJP 2021), swing SIR-affected
    ("Hemlata Pal",       56, "female","India", "West Bengal", "Krishnanagar",    "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "general"),   # Krishnanagar suburb, TMC
    ("Indraneel Bose",    35, "male",  "India", "West Bengal", "Kalyani",         "tier2",  "other",          2, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "left_lean",      "hindu",  "general"),   # Kalyani academic, Left-Congress tradition
    ("Jayshree Sen",      42, "female","India", "West Bengal", "Dum Dum",         "tier2",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "left_lean",      "hindu",  "general"),   # Educated suburban woman, Left-Congress voter
    ("Karim Sk",          33, "male",  "India", "West Bengal", "Basirhat",        "tier2",  "nuclear",        4, "lower",        False, "early-career",  "high-school",   "full-time",     "neutral",        "muslim", "obc"),       # Muslim OBC, Basirhat, SIR-deleted, open to alternatives
    ("Lakhan Das",        50, "male",  "India", "West Bengal", "Ashokenagar",     "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "neutral",        "hindu",  "sc"),        # Ashokenagar SC, swing seat, SIR-affected
    ("Mita Roy",          27, "female","India", "West Bengal", "Baranagar",       "tier2",  "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "opposition_lean","hindu",  "general"),   # Young suburban woman, TMC
    ("Nandu Mondal",      60, "male",  "India", "West Bengal", "Dum Dum",         "tier2",  "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "left_lean",      "hindu",  "general"),   # Retired CPM voter, North Kolkata suburb
    ("Osman Hossain",     44, "male",  "India", "West Bengal", "Barasat",         "tier2",  "nuclear",        5, "lower",        False, "mid-career",    "high-school",   "self-employed", "opposition",     "muslim", "general"),   # Muslim trader, Barasat, TMC
    ("Pallab Mukherjee",  47, "male",  "India", "West Bengal", "Barrackpore",     "tier2",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "opposition_lean","hindu",  "general"),   # Barrackpore professional, soft TMC
    ("Qaiyum Khan",       36, "male",  "India", "West Bengal", "Habra",           "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition_lean","muslim", "obc"),       # Muslim OBC, N24Pgs, TMC-lean
    ("Rina Bose",         39, "female","India", "West Bengal", "Barasat",         "tier2",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "neutral",        "hindu",  "general"),   # Suburban professional woman, uncertain
    ("Suman Das",         44, "male",  "India", "West Bengal", "Kalyani",         "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "obc"),       # Kalyani OBC, BJP lean
    ("Tultul Ghosh",      51, "female","India", "West Bengal", "Dum Dum",         "tier2",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "general"),   # BJP supporter, North Kolkata suburb
]

_BENGAL_PRESIDENCY_SUBURBS_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Abhijit Mukherjee": 0.48, "Bina Dey": 0.55, "Chinmoy Roy": 0.58,
    "Debarati Ghosh": 0.42, "Elias Ahmed": 0.86, "Firoza Khatun": 0.88,
    "Goutam Biswas": 0.70, "Hemlata Pal": 0.62, "Indraneel Bose": 0.40,
    "Jayshree Sen": 0.50, "Karim Sk": 0.84, "Lakhan Das": 0.68,
    "Mita Roy": 0.48, "Nandu Mondal": 0.48, "Osman Hossain": 0.84,
    "Pallab Mukherjee": 0.58, "Qaiyum Khan": 0.82, "Rina Bose": 0.55,
    "Suman Das": 0.68, "Tultul Ghosh": 0.65,
}

# ── CLUSTER 10: Darjeeling Hills + Adjacent Plains (9 seats) ───────────────
# 3 hill seats + 6 adjacent plains (Siliguri, Phansidewa, Matigara-Naxalbari etc.)
# 2021 baseline: BJP ~65-70%, TMC ~20%, Left ~10%
# 5-cornered ethnic race in hills; plains slightly more TMC-open
# Pool: 13 Hindu Gorkha/general, 4 ST (tea garden), 2 Muslim (plains), 1 OBC
_BENGAL_DARJEELING_HILLS_POOL = [
    ("Amit Rai",         40, "male",   "India", "West Bengal", "Darjeeling",      "tier2",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "bjp_supporter",  "hindu",  "general"),   # Gorkha, Darjeeling town, BJP-BGPM
    ("Binita Gurung",    36, "female", "India", "West Bengal", "Darjeeling",      "tier2",  "nuclear",        3, "middle",       False, "mid-career",    "undergraduate", "full-time",     "bjp_supporter",  "hindu",  "general"),   # Gorkha woman, BJP identity voter
    ("Chetan Rai",       52, "male",   "India", "West Bengal", "Kurseong",        "tier2",  "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "self-employed", "bjp_supporter",  "hindu",  "general"),   # Gorkha trader, Kurseong, BJP
    ("Dawa Tamang",      45, "male",   "India", "West Bengal", "Kalimpong",       "tier2",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "self-employed", "bjp_lean",       "hindu",  "general"),   # Gorkha, Kalimpong, BJP-leaning GJM voter
    ("Elisha Rai",       29, "female", "India", "West Bengal", "Darjeeling",      "tier2",  "other",          2, "middle",       False, "early-career",  "undergraduate", "full-time",     "bjp_lean",       "hindu",  "general"),   # Young Gorkha woman, BJP lean
    ("Fikra Tamang",     48, "male",   "India", "West Bengal", "Kurseong",        "tier2",  "nuclear",        5, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "hindu",  "obc"),       # Gorkha OBC, BJP supporter
    ("Gyan Rai",         58, "male",   "India", "West Bengal", "Darjeeling",      "tier2",  "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "bjp_supporter",  "hindu",  "general"),   # Retired Gorkha, BJP loyalist, GTA politics
    ("Hira Sherpa",      34, "female", "India", "West Bengal", "Kalimpong",       "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "homemaker",     "bjp_lean",       "hindu",  "general"),   # Gorkha woman, BJP community voter
    ("Ipsita Roy",       42, "female", "India", "West Bengal", "Siliguri",        "tier2",  "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "neutral",        "hindu",  "general"),   # Siliguri plains woman, mixed vote, pragmatic
    ("Jagadish Ray",     46, "male",   "India", "West Bengal", "Siliguri",        "tier2",  "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "self-employed", "bjp_lean",       "hindu",  "general"),   # Siliguri businessman, BJP lean
    ("Kumkum Sharma",    39, "female", "India", "West Bengal", "Matigara",        "tier3",  "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "neutral",        "hindu",  "general"),   # Matigara-Naxalbari plains, swing constituency
    ("Lakhpa Tamang",    44, "male",   "India", "West Bengal", "Darjeeling",      "tier2",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_supporter",  "hindu",  "general"),   # Gorkha community man, BJP loyalist
    ("Manisha Rai",      31, "female", "India", "West Bengal", "Kurseong",        "tier3",  "nuclear",        3, "lower-middle", False, "early-career",  "high-school",   "full-time",     "bjp_lean",       "hindu",  "general"),   # Young Gorkha woman, BJP
    ("Nina Oraon",       40, "female", "India", "West Bengal", "Darjeeling",      "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "part-time",     "bjp_lean",       "hindu",  "st"),        # Tea garden tribal woman, BJP
    ("Pawan Tirkey",     48, "male",   "India", "West Bengal", "Jalpaiguri",      "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "full-time",     "bjp_lean",       "hindu",  "st"),        # Tea garden tribal, BJP
    ("Qasim Ali",        35, "male",   "India", "West Bengal", "Phansidewa",      "tier3",  "nuclear",        4, "lower",        False, "mid-career",    "high-school",   "full-time",     "opposition",     "muslim", "general"),   # Muslim, plains Phansidewa, TMC
    ("Rajib Barman",     50, "male",   "India", "West Bengal", "Phansidewa",      "tier3",  "joint",          5, "lower-middle", False, "late-career",   "high-school",   "full-time",     "opposition",     "hindu",  "obc"),       # Plains Rajbanshi OBC, some TMC loyalty
    ("Sunanda Oraon",    36, "female", "India", "West Bengal", "Darjeeling",      "rural",  "joint",          5, "lower",        False, "mid-career",    "high-school",   "homemaker",     "neutral",        "hindu",  "st"),        # Tea garden woman, uncertain vote
    ("Tapsi Rai",        27, "female", "India", "West Bengal", "Siliguri",        "tier2",  "other",          2, "middle",       False, "early-career",  "undergraduate", "full-time",     "neutral",        "hindu",  "general"),   # Young Siliguri woman, pragmatic swing
    ("Upen Barman",      53, "male",   "India", "West Bengal", "Matigara",        "tier3",  "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "bjp_supporter",  "muslim", "general"),   # Muslim (unusual BJP Muslim), Matigara plains BJP
]

_BENGAL_DARJEELING_HILLS_RELIGIOUS_SALIENCE: dict[str, float] = {
    "Amit Rai": 0.72, "Binita Gurung": 0.70, "Chetan Rai": 0.68,
    "Dawa Tamang": 0.72, "Elisha Rai": 0.65, "Fikra Tamang": 0.74,
    "Gyan Rai": 0.72, "Hira Sherpa": 0.70,
    "Ipsita Roy": 0.58, "Jagadish Ray": 0.65, "Kumkum Sharma": 0.60,
    "Lakhpa Tamang": 0.72, "Manisha Rai": 0.68,
    "Nina Oraon": 0.80, "Pawan Tirkey": 0.80, "Sunanda Oraon": 0.78,
    "Qasim Ali": 0.86, "Rajib Barman": 0.72,
    "Tapsi Rai": 0.52, "Upen Barman": 0.80,
}

# ---------------------------------------------------------------------------
# Europe Benchmark v2 — demographic pools (9 countries)
# Each entry: (name, age, gender, country, region, city, urban_tier,
#              structure, size, income_bracket, dual_income,
#              life_stage, education, employment, political_lean, religious_salience_base)
# political_lean must match archetype keys in the country's PoliticalRegistry.
# religious_salience_base: per-persona anchor (pre-jitter), calibrated to national surveys.
# ---------------------------------------------------------------------------

_UK_GENERAL_POOL = [
    # reform ~10% (2/20) — anti-establishment, Brexit-aligned, working-class England
    ("Nigel Whitmore",    52, "male",   "United Kingdom", "England",  "Doncaster",  "tier2",    "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "reform",          0.32),
    ("Sandra Briggs",     44, "female", "United Kingdom", "England",  "Grimsby",    "tier2",    "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "reform",          0.30),
    # conservative ~25% (5/20) — suburban England, older, pro-market
    ("Edward Hartley",    58, "male",   "United Kingdom", "England",  "Guildford",  "tier2", "nuclear",        4, "upper-middle", True,  "late-career",   "undergraduate", "full-time",     "conservative",    0.45),
    ("Caroline Fletcher", 48, "female", "United Kingdom", "England",  "Chester",    "tier2", "nuclear",        4, "upper-middle", True,  "mid-career",    "undergraduate", "part-time",     "conservative",    0.50),
    ("Robert Simmons",    55, "male",   "United Kingdom", "England",  "Maidstone",  "tier2", "nuclear",        3, "upper-middle", False, "late-career",   "undergraduate", "self-employed", "conservative",    0.42),
    ("Patricia Dawson",   63, "female", "United Kingdom", "England",  "York",       "tier2",    "couple-no-kids", 2, "middle",       False, "retired",       "undergraduate", "retired",       "conservative",    0.55),
    ("Andrew Morrison",   44, "male",   "United Kingdom", "Scotland", "Edinburgh",  "metro",    "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "conservative",    0.38),
    # labour ~35% (7/20) — urban England, Wales, diverse coalition
    ("Sarah Mitchell",    34, "female", "United Kingdom", "England",  "Manchester", "metro",    "other",          1, "lower-middle", False, "early-career",  "postgraduate",  "full-time",     "labour",          0.22),
    ("Daniel Okafor",     29, "male",   "United Kingdom", "England",  "London",     "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "labour",          0.35),
    ("Rebecca Hughes",    41, "female", "United Kingdom", "Wales",    "Cardiff",    "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "undergraduate", "full-time",     "labour",          0.28),
    ("James Patel",       38, "male",   "United Kingdom", "England",  "Birmingham", "metro",    "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "labour",          0.50),
    ("Aisha Rahman",      26, "female", "United Kingdom", "England",  "Bradford",   "metro",    "nuclear",        5, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "labour",          0.68),
    ("Marcus Thompson",   46, "male",   "United Kingdom", "England",  "Leeds",      "metro",    "nuclear",        5, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "labour",          0.30),
    ("Fiona Murray",      32, "female", "United Kingdom", "Scotland", "Glasgow",    "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "labour",          0.20),
    # lib_dem ~10% (2/20) — urban professional, pro-EU, highly educated
    ("Charlotte Webb",    33, "female", "United Kingdom", "England",  "Bristol",    "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "lib_dem",         0.18),
    ("Thomas Ashford",    40, "male",   "United Kingdom", "England",  "Oxford",     "metro",    "couple-no-kids", 2, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "lib_dem",         0.20),
    # snp_plaid_green ~10% (2/20) — Scotland/Wales nationalist-left
    ("Callum MacLeod",    36, "male",   "United Kingdom", "Scotland", "Glasgow",    "metro",    "other",          2, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "snp_plaid_green", 0.15),
    ("Sioned Williams",   28, "female", "United Kingdom", "Wales",    "Swansea",    "tier2",    "other",          1, "lower-middle", False, "early-career",  "undergraduate", "part-time",     "snp_plaid_green", 0.22),
    # non_partisan ~10% (2/20)
    ("Peter Grant",       50, "male",   "United Kingdom", "England",  "Norwich",    "tier2",    "nuclear",        3, "middle",       False, "mid-career",    "undergraduate", "full-time",     "non_partisan",    0.38),
    ("Helen Foster",      59, "female", "United Kingdom", "England",  "Liverpool",  "metro",    "couple-no-kids", 2, "lower-middle", False, "late-career",   "high-school",   "full-time",     "non_partisan",    0.40),
]

_FRANCE_GENERAL_POOL = [
    # rn ~30% (6/20) — peripheral France, lower-education, economic anxiety
    ("Jean-Pierre Durand", 54, "male",   "France", "Provence-Alpes-Côte d'Azur", "Toulon",       "metro",    "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "rn",          0.48),
    ("Martine Lebrun",     47, "female", "France", "Hauts-de-France",             "Calais",       "tier2",    "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "rn",          0.52),
    ("Gérard Fontaine",    60, "male",   "France", "Auvergne-Rhône-Alpes",        "Saint-Étienne","tier2",    "couple-no-kids", 2, "lower-middle", False, "late-career",   "high-school",   "full-time",     "rn",          0.58),
    ("Brigitte Moreau",    51, "female", "France", "Normandie",                   "Rouen",        "metro",    "nuclear",        4, "lower-middle", True,  "late-career",   "high-school",   "full-time",     "rn",          0.55),
    ("Pascal Renard",      43, "male",   "France", "Grand Est",                   "Metz",         "tier2",    "nuclear",        3, "lower-middle", True,  "mid-career",    "high-school",   "self-employed", "rn",          0.44),
    ("Dominique Picard",   56, "male",   "France", "Pays de la Loire",            "Le Mans",      "tier2",    "couple-no-kids", 2, "lower-middle", False, "late-career",   "undergraduate", "full-time",     "rn",          0.42),
    # renaissance ~15% (3/20) — urban professional, pro-EU centrist
    ("Émilie Dubois",      35, "female", "France", "Île-de-France",               "Paris",        "metro",    "other",          1, "upper-middle", False, "early-career",  "postgraduate",  "full-time",     "renaissance", 0.18),
    ("Stéphane Blanchard", 45, "male",   "France", "Auvergne-Rhône-Alpes",        "Lyon",         "metro",    "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "renaissance", 0.22),
    ("Nathalie Girard",    40, "female", "France", "Nouvelle-Aquitaine",          "Bordeaux",     "metro",    "couple-no-kids", 2, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "renaissance", 0.20),
    # lfi ~10% (2/20) — urban young, radical left
    ("Kevin Benali",       27, "male",   "France", "Île-de-France",               "Paris",        "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "lfi",         0.15),
    ("Amina Bouzid",       24, "female", "France", "Île-de-France",               "Saint-Denis",  "metro",    "other",          2, "lower-middle", False, "early-career",  "undergraduate", "part-time",     "lfi",         0.60),
    # lr ~5% (1/20) — traditional right, shrinking
    ("Xavier Bertrand",    58, "male",   "France", "Île-de-France",               "Versailles",   "tier2", "nuclear",        4, "upper-middle", True,  "late-career",   "postgraduate",  "self-employed", "lr",          0.55),
    # ps ~15% (3/20) — centre-left, urban public sector
    ("Claire Lefebvre",    42, "female", "France", "Île-de-France",               "Paris",        "metro",    "other",          2, "upper-middle", False, "mid-career",    "postgraduate",  "full-time",     "ps",          0.20),
    ("Luc Mercier",        50, "male",   "France", "Bretagne",                    "Rennes",       "metro",    "nuclear",        4, "middle",       True,  "late-career",   "postgraduate",  "full-time",     "ps",          0.22),
    ("Isabelle Perrin",    38, "female", "France", "Occitanie",                   "Toulouse",     "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "ps",          0.18),
    # non_partisan ~25% (5/20) — abstainers, fragmented
    ("Henri Lapointe",     62, "male",   "France", "Bretagne",                    "Brest",        "metro",    "couple-no-kids", 2, "middle",       False, "retired",       "undergraduate", "retired",       "non_partisan",0.38),
    ("Valérie Morin",      55, "female", "France", "Centre-Val de Loire",         "Tours",        "tier2",    "nuclear",        3, "lower-middle", False, "late-career",   "high-school",   "part-time",     "non_partisan",0.45),
    ("Rachid Boudiaf",     39, "male",   "France", "Provence-Alpes-Côte d'Azur", "Marseille",    "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "non_partisan",0.65),
    ("Sophie Lacroix",     31, "female", "France", "Auvergne-Rhône-Alpes",        "Grenoble",     "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "non_partisan",0.15),
    ("Michel Gautier",     68, "male",   "France", "Occitanie",                   "Montpellier",  "metro",    "couple-no-kids", 2, "middle",       False, "retired",       "undergraduate", "retired",       "non_partisan",0.50),
]

_GREECE_GENERAL_POOL = [
    # nd ~37% (6/16) — centre-right, pro-EU, moderate-devout Orthodox
    ("Nikos Papadopoulos",  50, "male",   "Greece", "Attiki",            "Athens",       "metro",    "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "nd",          0.68),
    ("Maria Georgiou",      44, "female", "Greece", "Attiki",            "Athens",       "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "nd",          0.62),
    ("Kostas Alexiou",      58, "male",   "Greece", "Central Macedonia", "Thessaloniki", "metro",    "nuclear",        4, "middle",       False, "late-career",   "undergraduate", "full-time",     "nd",          0.72),
    ("Eleni Nikolaou",      35, "female", "Greece", "Peloponnese",       "Kalamata",     "tier2",    "nuclear",        3, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "nd",          0.78),
    ("Giorgos Stavros",     62, "male",   "Greece", "Crete",             "Heraklion",    "metro",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "nd",          0.80),
    ("Stavroula Papas",     47, "female", "Greece", "Western Greece",    "Patras",       "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "part-time",     "nd",          0.75),
    # syriza ~12% (2/16) — urban educated, secular left
    ("Alexandros Katsaros", 38, "male",   "Greece", "Attiki",            "Athens",       "metro",    "other",          1, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "syriza",      0.35),
    ("Dimitra Vassilakis",  32, "female", "Greece", "Attiki",            "Athens",       "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "syriza",      0.28),
    # pasok ~12% (2/16) — centrist social democratic
    ("Yannis Konstantinos", 55, "male",   "Greece", "Central Macedonia", "Thessaloniki", "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "pasok",       0.58),
    ("Anna Tsakali",        40, "female", "Greece", "Attiki",            "Athens",       "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "pasok",       0.55),
    # kkm_other ~12% (2/16) — KKE communist / hard nationalist
    ("Spyros Michalopoulos",42, "male",   "Greece", "Attiki",            "Piraeus",      "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "undergraduate", "full-time",     "kkm_other",   0.50),
    ("Katerina Papagiannis",30, "female", "Greece", "Attiki",            "Athens",       "metro",    "other",          1, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "kkm_other",   0.40),
    # non_partisan ~25% (4/16)
    ("Takis Anastasiou",    65, "male",   "Greece", "Crete",             "Chania",       "tier2",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "non_partisan",0.82),
    ("Sofia Theodorakis",   28, "female", "Greece", "Attiki",            "Athens",       "metro",    "other",          2, "lower-middle", False, "early-career",  "undergraduate", "part-time",     "non_partisan",0.48),
    ("Manolis Papakonstantinou", 52, "male", "Greece", "Epirus",         "Ioannina",     "tier2",    "nuclear",        4, "lower-middle", True,  "late-career",   "high-school",   "full-time",     "non_partisan",0.76),
    ("Ioanna Karamanlis",   45, "female", "Greece", "Attiki",            "Athens",       "tier2", "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "non_partisan",0.60),
]

_HUNGARY_GENERAL_POOL = [
    # fidesz ~42% (5/12) — rural/small city, older, national conservative
    ("István Kovács",      55, "male",   "Hungary", "Borsod-Abaúj-Zemplén", "Miskolc",     "metro",    "nuclear",        4, "lower-middle", True,  "late-career",   "high-school",   "full-time",     "fidesz",      0.62),
    ("Erzsébet Szabó",     48, "female", "Hungary", "Hajdú-Bihar",          "Debrecen",    "metro",    "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "fidesz",      0.68),
    ("László Tóth",        62, "male",   "Hungary", "Baranya",              "Pécs",        "metro",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "fidesz",      0.72),
    ("Katalin Horváth",    44, "female", "Hungary", "Győr-Moson-Sopron",    "Győr",        "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "fidesz",      0.58),
    ("Ferenc Nagy",        50, "male",   "Hungary", "Pest",                 "Érd",         "tier2", "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "fidesz",      0.55),
    # opposition ~33% (4/12) — Budapest urban, educated, liberal
    ("Gábor Vass",         39, "male",   "Hungary", "Budapest",             "Budapest",    "metro",    "other",          1, "upper-middle", False, "mid-career",    "postgraduate",  "full-time",     "opposition",  0.22),
    ("Ágnes Papp",         34, "female", "Hungary", "Budapest",             "Budapest",    "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "opposition",  0.18),
    ("Attila Fekete",      45, "male",   "Hungary", "Budapest",             "Budapest",    "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "opposition",  0.25),
    ("Erika Molnár",       31, "female", "Hungary", "Budapest",             "Budapest",    "metro",    "other",          2, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "opposition",  0.20),
    # non_partisan ~25% (3/12)
    ("Zoltán Balogh",      57, "male",   "Hungary", "Szabolcs-Szatmár-Bereg","Nyíregyháza","metro",    "nuclear",        5, "lower",        False, "late-career",   "high-school",   "full-time",     "non_partisan",0.55),
    ("Ildikó Simon",       43, "female", "Hungary", "Bács-Kiskun",          "Kecskemét",   "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "non_partisan",0.48),
    ("Tibor Kiss",         52, "male",   "Hungary", "Pest",                 "Budapest",    "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "non_partisan",0.38),
]

_ITALY_GENERAL_POOL = [
    # fdi ~25% (5/20) — South/Rome, national conservative, culturally Catholic
    ("Marco Ferraro",      50, "male",   "Italy", "Lazio",          "Rome",              "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "fdi",         0.55),
    ("Laura Conti",        44, "female", "Italy", "Campania",       "Naples",            "metro",    "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "fdi",         0.62),
    ("Giovanni Russo",     58, "male",   "Italy", "Sicilia",        "Palermo",           "metro",    "nuclear",        5, "lower-middle", False, "late-career",   "high-school",   "full-time",     "fdi",         0.68),
    ("Francesca Gallo",    38, "female", "Italy", "Lazio",          "Rome",              "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "fdi",         0.52),
    ("Roberto Mancini",    55, "male",   "Italy", "Calabria",       "Reggio Calabria",   "metro",    "nuclear",        4, "lower-middle", True,  "late-career",   "high-school",   "full-time",     "fdi",         0.65),
    # pd ~20% (4/20) — urban North/Centre, educated progressive
    ("Giulia Ricci",       33, "female", "Italy", "Toscana",        "Florence",          "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "pd",          0.30),
    ("Luca Bianchi",       46, "male",   "Italy", "Lombardia",      "Milan",             "metro",    "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "pd",          0.28),
    ("Elena Marino",       39, "female", "Italy", "Emilia-Romagna", "Bologna",           "metro",    "other",          2, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "pd",          0.25),
    ("Stefano Romano",     52, "male",   "Italy", "Piemonte",       "Turin",             "metro",    "nuclear",        3, "middle",       True,  "late-career",   "postgraduate",  "full-time",     "pd",          0.30),
    # m5s ~15% (3/20) — Southern Italy, populist, anti-establishment
    ("Maria Esposito",     36, "female", "Italy", "Campania",       "Naples",            "metro",    "nuclear",        4, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "m5s",         0.52),
    ("Antonio Greco",      30, "male",   "Italy", "Sicilia",        "Catania",           "metro",    "other",          1, "lower-middle", False, "early-career",  "undergraduate", "part-time",    "m5s",         0.48),
    ("Valentina Bruno",    29, "female", "Italy", "Puglia",         "Bari",              "metro",    "nuclear",        3, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "m5s",         0.44),
    # lega_fi ~20% (4/20) — Northern Italy, right nationalist/liberal conservative
    ("Paolo Ferrari",      54, "male",   "Italy", "Lombardia",      "Bergamo",           "metro",    "nuclear",        4, "upper-middle", True,  "late-career",   "undergraduate", "self-employed", "lega_fi",     0.48),
    ("Chiara Lombardi",    42, "female", "Italy", "Veneto",         "Verona",            "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "lega_fi",     0.55),
    ("Giuseppe Fontana",   60, "male",   "Italy", "Lombardia",      "Milan",             "metro",    "couple-no-kids", 2, "upper-middle", False, "retired",       "undergraduate", "retired",       "lega_fi",     0.52),
    ("Martina Pellegrino", 35, "female", "Italy", "Piemonte",       "Turin",             "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "high-school",   "full-time",     "lega_fi",     0.45),
    # non_partisan ~20% (4/20) — disengaged, Southern or lower-income
    ("Andrea Costa",       27, "male",   "Italy", "Lazio",          "Rome",              "metro",    "other",          1, "lower-middle", False, "early-career",  "postgraduate",  "part-time",     "non_partisan",0.35),
    ("Sofia Riva",         48, "female", "Italy", "Lombardia",      "Milan",             "metro",    "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "non_partisan",0.32),
    ("Matteo Caruso",      65, "male",   "Italy", "Campania",       "Salerno",           "metro",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "non_partisan",0.62),
    ("Alessia Marchetti",  31, "female", "Italy", "Toscana",        "Livorno",           "tier2",    "other",          1, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "non_partisan",0.40),
]

_NETHERLANDS_GENERAL_POOL = [
    # pvv ~25% (5/20) — working-class, peripheral, anti-Islam populist
    ("Jan van den Berg",   52, "male",   "Netherlands", "Zuid-Holland",  "Rotterdam",  "metro",    "nuclear",        4, "lower-middle", True,  "late-career",   "high-school",   "full-time",     "pvv",         0.25),
    ("Ria de Vries",       48, "female", "Netherlands", "Gelderland",    "Arnhem",     "tier2",    "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "pvv",         0.22),
    ("Henk Bakker",        55, "male",   "Netherlands", "Noord-Brabant", "Tilburg",    "metro",    "couple-no-kids", 2, "lower-middle", False, "late-career",   "high-school",   "full-time",     "pvv",         0.28),
    ("Wilma Smeets",       44, "female", "Netherlands", "Limburg",       "Maastricht", "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "pvv",         0.30),
    ("Klaas Mulder",       61, "male",   "Netherlands", "Friesland",     "Leeuwarden", "tier2",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "pvv",         0.32),
    # vvd_nsc ~15% (3/20) — urban professional, liberal conservative
    ("Pieter Janssen",     46, "male",   "Netherlands", "Noord-Holland", "Amsterdam",  "metro",    "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "vvd_nsc",     0.18),
    ("Marieke van Leeuwen",40, "female", "Netherlands", "Zuid-Holland",  "The Hague",  "metro",    "couple-no-kids", 2, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "vvd_nsc",     0.22),
    ("Bram de Graaf",      54, "male",   "Netherlands", "Utrecht",       "Utrecht",    "metro",    "nuclear",        3, "upper-middle", True,  "late-career",   "undergraduate", "self-employed", "vvd_nsc",     0.28),
    # d66_gl_pvda ~25% (5/20) — urban, highly educated, very secular progressive
    ("Emma Vissers",       29, "female", "Netherlands", "Noord-Holland", "Amsterdam",  "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "d66_gl_pvda", 0.12),
    ("Thomas Kuijpers",    33, "male",   "Netherlands", "Noord-Holland", "Amsterdam",  "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "d66_gl_pvda", 0.10),
    ("Lisa Hendriksen",    38, "female", "Netherlands", "Utrecht",       "Utrecht",    "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "d66_gl_pvda", 0.15),
    ("Sander Wolff",       44, "male",   "Netherlands", "Zuid-Holland",  "Delft",      "metro",    "couple-no-kids", 2, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "d66_gl_pvda", 0.12),
    ("Anke Posthuma",      26, "female", "Netherlands", "Groningen",     "Groningen",  "metro",    "other",          3, "lower-middle", False, "early-career",  "postgraduate",  "part-time",     "d66_gl_pvda", 0.10),
    # cda_other ~10% (2/20) — Christian-democratic, some Bible Belt
    ("Gerrit van Dijk",    58, "male",   "Netherlands", "Zeeland",       "Middelburg", "tier2",    "nuclear",        4, "lower-middle", False, "late-career",   "undergraduate", "full-time",     "cda_other",   0.72),
    ("Corrie Boersma",     52, "female", "Netherlands", "Gelderland",    "Nijmegen",   "metro",    "nuclear",        3, "lower-middle", True,  "late-career",   "undergraduate", "part-time",     "cda_other",   0.58),
    # non_partisan ~25% (5/20) — fragmented, pragmatic
    ("Dirk Lammers",       50, "male",   "Netherlands", "Noord-Brabant", "Eindhoven",  "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "non_partisan",0.25),
    ("Tineke Hartman",     36, "female", "Netherlands", "Zuid-Holland",  "Rotterdam",  "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "non_partisan",0.22),
    ("Mohammed Bouazza",   31, "male",   "Netherlands", "Noord-Holland", "Amsterdam",  "metro",    "nuclear",        4, "lower-middle", True,  "early-career",  "undergraduate", "full-time",     "non_partisan",0.68),
    ("Joke Vermeer",       65, "female", "Netherlands", "Zuid-Holland",  "The Hague",  "metro",    "couple-no-kids", 2, "middle",       False, "retired",       "undergraduate", "retired",       "non_partisan",0.32),
    ("Bas Hofman",         27, "male",   "Netherlands", "Noord-Holland", "Amsterdam",  "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "non_partisan",0.10),
]

_POLAND_GENERAL_POOL = [
    # ko ~30% (6/20) — urban, educated, pro-EU
    ("Marek Kowalski",        44, "male",   "Poland", "Masovian",          "Warsaw",    "metro",    "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "ko",          0.50),
    ("Anna Wiśniewska",       38, "female", "Poland", "Masovian",          "Warsaw",    "metro",    "other",          1, "upper-middle", False, "mid-career",    "postgraduate",  "full-time",     "ko",          0.42),
    ("Piotr Jankowski",       50, "male",   "Poland", "Lower Silesia",     "Wrocław",   "metro",    "nuclear",        3, "upper-middle", True,  "late-career",   "postgraduate",  "full-time",     "ko",          0.55),
    ("Katarzyna Nowak",       33, "female", "Poland", "Lesser Poland",     "Kraków",    "metro",    "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "ko",          0.48),
    ("Tomasz Zielinski",      47, "male",   "Poland", "Pomerania",         "Gdańsk",    "metro",    "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "ko",          0.60),
    ("Agnieszka Lewandowska", 41, "female", "Poland", "Greater Poland",    "Poznań",    "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "ko",          0.52),
    # pis ~35% (7/20) — rural/small town, devout Catholic, national conservative
    ("Jan Wojcik",            55, "male",   "Poland", "Subcarpathian",     "Rzeszów",   "metro",    "nuclear",        5, "lower-middle", False, "late-career",   "high-school",   "full-time",     "pis",         0.88),
    ("Maria Kowalczyk",       48, "female", "Poland", "Lublin",            "Lublin",    "metro",    "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "pis",         0.85),
    ("Krzysztof Szymanski",   60, "male",   "Poland", "Lesser Poland",     "Tarnów",    "tier2",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "pis",         0.90),
    ("Malgorzata Dabrowska",  52, "female", "Poland", "Masovian",          "Radom",     "tier2",    "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "part-time",     "pis",         0.82),
    ("Michal Kaczmarek",      42, "male",   "Poland", "Silesia",           "Katowice",  "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "pis",         0.78),
    ("Joanna Piotrowska",     35, "female", "Poland", "Łódź",              "Łódź",      "metro",    "nuclear",        3, "lower-middle", True,  "mid-career",    "undergraduate", "full-time",     "pis",         0.72),
    ("Adam Grabowski",        58, "male",   "Poland", "Kuyavian-Pomeranian","Bydgoszcz","metro",    "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "pis",         0.82),
    # td_lewica ~20% (4/20) — coalition: centrist-agrarian + secular urban left
    ("Pawel Wisniewski",      46, "male",   "Poland", "Lesser Poland",     "Kraków",    "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "td_lewica",   0.60),
    ("Barbara Majewska",      39, "female", "Poland", "Masovian",          "Warsaw",    "metro",    "other",          2, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "td_lewica",   0.38),
    ("Robert Krawczyk",       53, "male",   "Poland", "Greater Poland",    "Poznań",    "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "td_lewica",   0.55),
    ("Monika Olszewska",      28, "female", "Poland", "Lower Silesia",     "Wrocław",   "metro",    "other",          1, "lower-middle", False, "early-career",  "postgraduate",  "full-time",     "td_lewica",   0.28),
    # konfederacja ~5% (1/20) — young, libertarian-nationalist, very low IT
    ("Grzegorz Kalinowski",   27, "male",   "Poland", "Masovian",          "Warsaw",    "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "konfederacja",0.45),
    # non_partisan ~10% (2/20)
    ("Beata Michalska",       57, "female", "Poland", "Silesia",           "Gliwice",   "metro",    "couple-no-kids", 2, "lower-middle", False, "late-career",   "high-school",   "full-time",     "non_partisan",0.68),
    ("Zbigniew Ostrowski",    62, "male",   "Poland", "Łódź",              "Łódź",      "metro",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "non_partisan",0.75),
]

_SPAIN_GENERAL_POOL = [
    # pp ~30% (6/20) — centre-right, urban middle class, cultural Catholic
    ("Manuel Garcia",      52, "male",   "Spain", "Comunidad de Madrid",  "Madrid",     "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "pp",          0.48),
    ("Carmen Rodriguez",   48, "female", "Spain", "Andalucía",            "Seville",    "metro",    "nuclear",        3, "lower-middle", False, "mid-career",    "undergraduate", "full-time",     "pp",          0.55),
    ("Antonio Lopez",      60, "male",   "Spain", "Castilla y León",      "Valladolid", "metro",    "couple-no-kids", 2, "middle",       False, "late-career",   "undergraduate", "full-time",     "pp",          0.62),
    ("Maria Gonzalez",     44, "female", "Spain", "Comunidad Valenciana", "Valencia",   "metro",    "nuclear",        4, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "pp",          0.52),
    ("Jose Martinez",      55, "male",   "Spain", "Galicia",              "Vigo",       "metro",    "nuclear",        4, "lower-middle", True,  "late-career",   "high-school",   "self-employed", "pp",          0.58),
    ("Ana Fernandez",      40, "female", "Spain", "Comunidad de Madrid",  "Madrid",     "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "postgraduate",  "full-time",     "pp",          0.42),
    # psoe ~30% (6/20) — urban, public sector, progressive
    ("Juan Sanchez",       46, "male",   "Spain", "Andalucía",            "Málaga",     "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "undergraduate", "full-time",     "psoe",        0.38),
    ("Isabel Perez",       34, "female", "Spain", "Comunidad de Madrid",  "Madrid",     "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "psoe",        0.25),
    ("Francisco Diaz",     55, "male",   "Spain", "Andalucía",            "Granada",    "metro",    "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "psoe",        0.48),
    ("Pilar Torres",       41, "female", "Spain", "Castilla-La Mancha",   "Albacete",   "tier2",    "nuclear",        3, "lower-middle", True,  "mid-career",    "high-school",   "part-time",     "psoe",        0.42),
    ("Luis Moreno",        38, "male",   "Spain", "País Vasco",           "Bilbao",     "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "psoe",        0.28),
    ("Rosa Jimenez",       29, "female", "Spain", "Cataluña",             "Barcelona",  "metro",    "other",          2, "middle",       False, "early-career",  "postgraduate",  "full-time",     "psoe",        0.20),
    # sumar_podemos ~10% (2/20) — urban young, radical left, secular
    ("David Ruiz",         27, "male",   "Spain", "Comunidad de Madrid",  "Madrid",     "metro",    "other",          1, "lower-middle", False, "early-career",  "postgraduate",  "part-time",     "sumar_podemos",0.12),
    ("Marta Castillo",     32, "female", "Spain", "Cataluña",             "Barcelona",  "metro",    "other",          3, "lower-middle", False, "early-career",  "postgraduate",  "full-time",     "sumar_podemos",0.15),
    # vox ~15% (3/20) — nationalist, anti-immigration, traditional values
    ("Carlos Navarro",     50, "male",   "Spain", "Comunidad de Madrid",  "Madrid",     "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "vox",         0.65),
    ("Sofia Hernandez",    43, "female", "Spain", "Andalucía",            "Córdoba",    "metro",    "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "vox",         0.70),
    ("Javier Ramos",       35, "male",   "Spain", "Comunidad Valenciana", "Alicante",   "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "vox",         0.62),
    # non_partisan ~15% (3/20) — regional voters, pragmatic
    ("Pablo Alonso",       57, "male",   "Spain", "Aragón",               "Zaragoza",   "metro",    "nuclear",        4, "middle",       False, "late-career",   "undergraduate", "full-time",     "non_partisan",0.45),
    ("Laura Vega",         36, "female", "Spain", "Cataluña",             "Barcelona",  "metro",    "other",          2, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "non_partisan",0.22),
    ("Miguel Rubio",       62, "male",   "Spain", "Galicia",              "La Coruña",  "metro",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "non_partisan",0.55),
]

_SWEDEN_GENERAL_POOL = [
    # sap ~30% (6/20) — social democratic, working class, industrial Sweden
    ("Erik Lindqvist",     48, "male",   "Sweden", "Västra Götaland", "Gothenburg", "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "undergraduate", "full-time",     "sap",             0.12),
    ("Anna Johansson",     42, "female", "Sweden", "Stockholm",       "Stockholm",  "metro",    "other",          2, "middle",       False, "mid-career",    "undergraduate", "full-time",     "sap",             0.10),
    ("Lars Svensson",      57, "male",   "Sweden", "Skåne",           "Malmö",      "metro",    "nuclear",        4, "lower-middle", True,  "late-career",   "high-school",   "full-time",     "sap",             0.14),
    ("Kristina Berg",      36, "female", "Sweden", "Stockholm",       "Stockholm",  "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "sap",             0.10),
    ("Johan Andersson",    50, "male",   "Sweden", "Norrland",        "Sundsvall",  "tier2",    "nuclear",        3, "lower-middle", True,  "late-career",   "high-school",   "full-time",     "sap",             0.18),
    ("Maria Nilsson",      44, "female", "Sweden", "Västra Götaland", "Gothenburg", "metro",    "nuclear",        3, "lower-middle", True,  "mid-career",    "undergraduate", "full-time",     "sap",             0.12),
    # m_kristersson ~20% (4/20) — urban professional, centre-right, high IT
    ("Mikael Larsson",     52, "male",   "Sweden", "Stockholm",       "Stockholm",  "metro",    "nuclear",        3, "upper-middle", True,  "late-career",   "postgraduate",  "full-time",     "m_kristersson",   0.15),
    ("Karin Pettersson",   45, "female", "Sweden", "Skåne",           "Helsingborg","metro",    "nuclear",        3, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "m_kristersson",   0.18),
    ("Stefan Olsson",      58, "male",   "Sweden", "Östergötland",    "Linköping",  "metro",    "couple-no-kids", 2, "upper-middle", False, "late-career",   "undergraduate", "full-time",     "m_kristersson",   0.22),
    ("Annika Persson",     39, "female", "Sweden", "Uppsala",         "Uppsala",    "metro",    "couple-no-kids", 2, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "m_kristersson",   0.14),
    # sd ~20% (4/20) — nationalist, working class, peripheral Sweden, nativist
    ("Peter Karlsson",     45, "male",   "Sweden", "Skåne",           "Kristianstad","tier2",   "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "sd",              0.22),
    ("Birgitta Eriksson",  53, "female", "Sweden", "Norrland",        "Umeå",       "metro",    "nuclear",        3, "lower-middle", False, "late-career",   "high-school",   "full-time",     "sd",              0.25),
    ("Henrik Gustafsson",  38, "male",   "Sweden", "Dalarna",         "Falun",      "tier2",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "self-employed", "sd",              0.28),
    ("Cecilia Magnusson",  42, "female", "Sweden", "Västra Götaland", "Borås",      "tier2",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "sd",              0.20),
    # left_green ~15% (3/20) — urban, highly educated, very progressive
    ("Gunnar Lund",        34, "male",   "Sweden", "Stockholm",       "Stockholm",  "metro",    "other",          1, "middle",       False, "early-career",  "postgraduate",  "full-time",     "left_green",      0.08),
    ("Astrid Holm",        29, "female", "Sweden", "Uppsala",         "Uppsala",    "metro",    "other",          3, "lower-middle", False, "early-career",  "postgraduate",  "part-time",     "left_green",      0.05),
    ("Ola Bergstrom",      46, "male",   "Sweden", "Västra Götaland", "Gothenburg", "metro",    "other",          2, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "left_green",      0.10),
    # non_partisan ~15% (3/20) — pragmatic, high IT (secular welfare state default)
    ("Eva Lindstrom",      55, "female", "Sweden", "Stockholm",       "Stockholm",  "metro",    "couple-no-kids", 2, "middle",       False, "late-career",   "undergraduate", "full-time",     "non_partisan",    0.14),
    ("Anders Henriksson",  61, "male",   "Sweden", "Skåne",           "Malmö",      "metro",    "couple-no-kids", 2, "middle",       False, "late-career",   "undergraduate", "full-time",     "non_partisan",    0.20),
    ("Ingrid Wallin",      33, "female", "Sweden", "Västra Götaland", "Gothenburg", "metro",    "other",          1, "lower-middle", False, "early-career",  "undergraduate", "full-time",     "non_partisan",    0.12),
]

_GERMANY_GENERAL_POOL = [
    # cdu_csu ~31% (6/20) — centre-right, traditional Christian-democratic, West/South Germany
    # Calibrated: CDU/CSU 31% (2025 snap election), stronger in Bayern, BW, NRW
    ("Hans-Jürgen Müller",  57, "male",   "Germany", "Bayern",              "Munich",     "metro",    "nuclear",        4, "upper-middle", True,  "late-career",   "undergraduate", "full-time",     "cdu_csu",     0.48),
    ("Ursula Becker",       51, "female", "Germany", "Baden-Württemberg",   "Stuttgart",  "metro",    "nuclear",        3, "middle",       False, "late-career",   "undergraduate", "full-time",     "cdu_csu",     0.52),
    ("Wolfgang Braun",      63, "male",   "Germany", "Nordrhein-Westfalen", "Cologne",    "metro",    "couple-no-kids", 2, "middle",       False, "retired",       "high-school",   "retired",       "cdu_csu",     0.55),
    ("Heike Zimmermann",    45, "female", "Germany", "Nordrhein-Westfalen", "Düsseldorf", "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "cdu_csu",     0.42),
    ("Klaus Hoffmann",      54, "male",   "Germany", "Niedersachsen",       "Hannover",   "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "cdu_csu",     0.45),
    ("Sabine Fischer",      41, "female", "Germany", "Bayern",              "Nuremberg",  "metro",    "nuclear",        3, "middle",       True,  "mid-career",    "undergraduate", "full-time",     "cdu_csu",     0.50),
    # afd ~20% (4/20) — populist nationalist, predominantly East Germany, economic anxiety
    # Higher in Sachsen, Thüringen, Sachsen-Anhalt, Brandenburg
    ("Dieter Schulze",      49, "male",   "Germany", "Sachsen",             "Dresden",    "metro",    "nuclear",        3, "lower-middle", True,  "mid-career",    "high-school",   "full-time",     "afd",         0.38),
    ("Petra Vogel",         52, "female", "Germany", "Sachsen-Anhalt",      "Magdeburg",  "metro",    "nuclear",        4, "lower-middle", False, "late-career",   "high-school",   "full-time",     "afd",         0.35),
    ("Rainer Koch",         44, "male",   "Germany", "Thüringen",           "Erfurt",     "metro",    "nuclear",        4, "lower-middle", True,  "mid-career",    "high-school",   "self-employed", "afd",         0.30),
    ("Manuela Richter",     47, "female", "Germany", "Brandenburg",         "Potsdam",    "metro",    "nuclear",        3, "lower-middle", False, "mid-career",    "high-school",   "part-time",     "afd",         0.28),
    # spd ~16% (3/20) — centre-left, trade union, public sector, West Germany
    ("Thomas Wagner",       50, "male",   "Germany", "Nordrhein-Westfalen", "Dortmund",   "metro",    "nuclear",        4, "lower-middle", True,  "late-career",   "undergraduate", "full-time",     "spd",         0.22),
    ("Karin Schmidt",       44, "female", "Germany", "Hamburg",             "Hamburg",    "metro",    "other",          2, "middle",       False, "mid-career",    "postgraduate",  "full-time",     "spd",         0.18),
    ("Martin Werner",       55, "male",   "Germany", "Bremen",              "Bremen",     "metro",    "nuclear",        3, "lower-middle", True,  "late-career",   "undergraduate", "full-time",     "spd",         0.25),
    # greens ~12% (3/20) — urban professional, highly educated, very secular
    ("Lena Neumann",        33, "female", "Germany", "Berlin",              "Berlin",     "metro",    "other",          1, "upper-middle", False, "early-career",  "postgraduate",  "full-time",     "greens",      0.08),
    ("Felix Krause",        37, "male",   "Germany", "Hamburg",             "Hamburg",    "metro",    "other",          2, "upper-middle", False, "mid-career",    "postgraduate",  "full-time",     "greens",      0.10),
    ("Julia Hartmann",      29, "female", "Germany", "Berlin",              "Berlin",     "metro",    "other",          3, "middle",       False, "early-career",  "postgraduate",  "part-time",     "greens",      0.06),
    # fdp ~5% (1/20) — liberal, high income, business-oriented
    ("Andreas Weber",       46, "male",   "Germany", "Hessen",              "Frankfurt",  "metro",    "nuclear",        2, "upper-middle", True,  "mid-career",    "postgraduate",  "full-time",     "fdp",         0.15),
    # non_partisan ~16% (3/20) — pragmatic, often East German, disengaged
    ("Günter Lehmann",      61, "male",   "Germany", "Sachsen",             "Leipzig",    "metro",    "couple-no-kids", 2, "lower-middle", False, "retired",       "high-school",   "retired",       "non_partisan",0.20),
    ("Birgit Schäfer",      38, "female", "Germany", "Nordrhein-Westfalen", "Essen",      "metro",    "nuclear",        4, "lower-middle", False, "mid-career",    "high-school",   "full-time",     "non_partisan",0.30),
    ("Michael Bauer",       53, "male",   "Germany", "Bayern",              "Augsburg",   "metro",    "nuclear",        4, "middle",       True,  "late-career",   "undergraduate", "full-time",     "non_partisan",0.35),
]

# WorldviewAnchor base dimensions per European country + archetype.
# (institutional_trust, social_change_pace, collectivism_score, economic_security_priority)
# Calibrated against Pew Spring 2024 national surveys and electoral context.
_EUROPE_WORLDVIEW_DIMS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "uk_general": {
        "reform":          (0.22, 0.22, 0.45, 0.72),  # anti-establishment, economic anxiety
        "conservative":    (0.48, 0.30, 0.52, 0.58),  # traditional, moderate IT, pro-market
        "labour":          (0.55, 0.72, 0.62, 0.68),  # pro-welfare, progressive
        "lib_dem":         (0.65, 0.75, 0.38, 0.48),  # pro-EU, individualist, high IT
        "snp_plaid_green": (0.55, 0.78, 0.52, 0.55),  # nationalist-left, progressive
        "non_partisan":    (0.52, 0.52, 0.48, 0.56),  # median UK
    },
    "france_general": {
        "rn":          (0.28, 0.20, 0.52, 0.70),  # nativist, anti-establishment
        "renaissance": (0.58, 0.55, 0.35, 0.52),  # pro-EU centrist
        "lfi":         (0.22, 0.82, 0.58, 0.72),  # radical left, very low IT
        "lr":          (0.55, 0.28, 0.48, 0.55),  # traditional right
        "ps":          (0.55, 0.70, 0.55, 0.65),  # centre-left, pro-welfare
        "non_partisan":(0.45, 0.52, 0.45, 0.58),  # median French
    },
    "greece_general": {
        "nd":          (0.58, 0.30, 0.62, 0.60),  # centre-right, pro-EU
        "syriza":      (0.35, 0.72, 0.55, 0.70),  # radical left
        "pasok":       (0.48, 0.58, 0.58, 0.65),  # social democratic
        "kkm_other":   (0.25, 0.82, 0.65, 0.75),  # KKE communist / nationalist hard
        "non_partisan":(0.42, 0.55, 0.60, 0.65),  # median Greek
    },
    "hungary_general": {
        "fidesz":      (0.72, 0.18, 0.75, 0.60),  # high IT (Fidesz governs), low SCP
        "opposition":  (0.32, 0.72, 0.45, 0.55),  # low IT in current govt, pro-liberal
        "non_partisan":(0.48, 0.45, 0.60, 0.58),  # median Hungarian
    },
    "italy_general": {
        "fdi":         (0.58, 0.20, 0.68, 0.60),  # national conservative
        "pd":          (0.60, 0.72, 0.50, 0.62),  # centre-left, pro-EU
        "m5s":         (0.22, 0.52, 0.55, 0.72),  # populist, very low IT
        "lega_fi":     (0.52, 0.28, 0.62, 0.58),  # right nationalist
        "non_partisan":(0.35, 0.48, 0.55, 0.65),  # disengaged, lower IT
    },
    "netherlands_general": {
        "pvv":         (0.28, 0.22, 0.50, 0.68),  # anti-Islam populist, very low IT
        "vvd_nsc":     (0.72, 0.50, 0.32, 0.50),  # liberal-conservative, high IT
        "d66_gl_pvda": (0.78, 0.82, 0.28, 0.42),  # progressive, very high IT + SCP
        "cda_other":   (0.58, 0.45, 0.52, 0.55),  # Christian-democratic, moderate
        "non_partisan":(0.52, 0.55, 0.42, 0.52),  # pragmatic median
    },
    "poland_general": {
        "ko":          (0.62, 0.62, 0.52, 0.55),  # pro-EU liberal
        "pis":         (0.52, 0.18, 0.72, 0.58),  # national-conservative, low SCP
        "td_lewica":   (0.55, 0.65, 0.55, 0.58),  # centrist-left coalition
        "konfederacja":(0.22, 0.30, 0.48, 0.55),  # libertarian-nationalist, very low IT
        "non_partisan":(0.50, 0.50, 0.58, 0.58),  # median Polish
    },
    "spain_general": {
        "pp":           (0.52, 0.28, 0.55, 0.58),  # centre-right
        "psoe":         (0.58, 0.70, 0.52, 0.62),  # centre-left
        "sumar_podemos":(0.22, 0.85, 0.55, 0.72),  # radical left, very low IT
        "vox":          (0.32, 0.18, 0.65, 0.58),  # far-right, low IT
        "non_partisan": (0.48, 0.52, 0.52, 0.58),  # median Spanish
    },
    "sweden_general": {
        "sap":           (0.62, 0.65, 0.62, 0.55),  # social democratic, high IT
        "m_kristersson": (0.65, 0.45, 0.42, 0.50),  # centre-right, high IT
        "sd":            (0.40, 0.18, 0.55, 0.60),  # nationalist, anti-immigration
        "left_green":    (0.55, 0.85, 0.52, 0.55),  # radical left/green
        "non_partisan":  (0.65, 0.58, 0.45, 0.52),  # high IT (secular welfare state)
    },
    "germany_general": {
        "cdu_csu":     (0.62, 0.38, 0.48, 0.55),  # Christian-democratic, moderate IT, pro-market
        "afd":         (0.22, 0.15, 0.52, 0.72),  # anti-establishment, very low IT, economic anxiety
        "spd":         (0.58, 0.60, 0.65, 0.62),  # social democratic, pro-welfare, moderate IT
        "greens":      (0.72, 0.82, 0.55, 0.45),  # high IT, high SCP, post-materialist
        "fdp":         (0.70, 0.55, 0.28, 0.42),  # high IT, liberal, anti-collectivist
        "non_partisan":(0.48, 0.48, 0.52, 0.60),  # pragmatic, often disengaged (esp. East Germany)
    },
}

# Political era strings for European countries (Pew Spring 2024 context).
_EUROPE_POLITICAL_ERA: dict[str, str] = {
    "uk_general":          "Conservative government in power (Sunak, 2022–2024); Labour landslide July 2024 (Starmer)",
    "france_general":      "Macron second term (Renaissance/centrist, 2022–); minority govt, RN dominant opposition",
    "greece_general":      "New Democracy majority government (Mitsotakis, 2023–)",
    "hungary_general":     "Fidesz supermajority government (Orbán, 2010–; re-elected 2022)",
    "italy_general":       "FdI-led right coalition government (Giorgia Meloni, Oct 2022–)",
    "netherlands_general": "PVV-largest-party coalition forming (2024); Schoof PM",
    "poland_general":      "PiS opposition, KO-led coalition government (Donald Tusk, Dec 2023–)",
    "spain_general":       "PSOE minority government (Sánchez, 2023–)",
    "sweden_general":      "Tidö centre-right coalition (Kristersson PM, Oct 2022–)",
    "germany_general":     "Traffic light coalition collapsed Nov 2024; CDU/CSU-led coalition forming (Merz, 2025–); AfD second-largest party",
}

# ── UAE / Gulf Muslim pool ────────────────────────────────────────────────────
# Used when anchor_overrides contains location: "UAE" or "United Arab Emirates".
# Mix of Emirati nationals and Gulf South Asian expats. Ages 28–45. High religious salience.
# 14-field format (no political_lean — UAE has no competitive elections):
# (name, age, gender, country, region, city, urban_tier,
#  structure, size, income_bracket, dual_income,
#  life_stage, education, employment)
_UAE_GULF_MUSLIM_POOL = [
    ("Hessa Al Mazrouei",  33, "female", "UAE", "Abu Dhabi",  "Abu Dhabi",  "metro", "joint",     5, "upper-middle", False, "early-family", "undergraduate",  "full-time"),
    ("Rima Khalaf",        37, "female", "UAE", "Dubai",      "Dubai",      "metro", "nuclear",   3, "upper-middle", True,  "mid-career",   "postgraduate",   "full-time"),
    ("Yasmine Aziz",       31, "female", "UAE", "Dubai",      "Dubai",      "metro", "other",     1, "middle",       False, "early-career", "postgraduate",   "full-time"),
    ("Sana Al Hashimi",    35, "female", "UAE", "Dubai",      "Dubai",      "metro", "nuclear",   3, "upper-middle", True,  "mid-career",   "postgraduate",   "full-time"),
    ("Hamdan Al Suwaidi",  38, "male",   "UAE", "Dubai",      "Dubai",      "metro", "nuclear",   4, "upper-middle", False, "mid-career",   "postgraduate",   "full-time"),
    ("Tariq Mahmood",      29, "male",   "UAE", "Sharjah",    "Sharjah",    "metro", "other",     1, "middle",       False, "early-career", "undergraduate",  "full-time"),
    ("Maryam Al Suwaidi",  42, "female", "UAE", "Abu Dhabi",  "Abu Dhabi",  "metro", "joint",     6, "upper-middle", False, "mid-career",   "undergraduate",  "full-time"),
    ("Khalid Al Mansouri", 44, "male",   "UAE", "Dubai",      "Dubai",      "metro", "nuclear",   4, "upper-middle", True,  "mid-career",   "postgraduate",   "full-time"),
    # ── South Asian expat ICP entries (pool_index 8–10) ──────────────────────
    ("Zara Sheikh",        32, "female", "UAE", "Dubai",      "Dubai",      "metro", "nuclear",   2, "upper-middle", True,  "mid-career",   "postgraduate",   "full-time"),
    ("Imran Siddiqui",     29, "male",   "UAE", "Dubai",      "Dubai",      "metro", "other",     1, "middle",       False, "early-career", "postgraduate",   "full-time"),
    ("Nadia Rahman",       27, "female", "UAE", "Sharjah",    "Sharjah",    "metro", "other",     1, "lower-middle", False, "early-career", "undergraduate",  "full-time"),
]

# ── UK South Asian Muslim pool ────────────────────────────────────────────────
# Used when anchor_overrides location is "United Kingdom"/"UK" + muslim religiosity.
# British Pakistani, Bangladeshi, Indian Muslim demographics. Ages 24–45. High religious salience.
# 16-field format matching UK general pool (includes political_lean and religious_salience_base):
# (name, age, gender, country, region, city, urban_tier,
#  structure, size, income_bracket, dual_income,
#  life_stage, education, employment, political_lean, religious_salience_base)
_UK_SOUTH_ASIAN_MUSLIM_POOL = [
    ("Amina Hussain",   28, "female", "United Kingdom", "England", "Birmingham",  "metro", "nuclear",   4, "lower-middle", False, "early-career", "undergraduate", "full-time",     "labour", 0.84),
    ("Tariq Rashid",    41, "male",   "United Kingdom", "England", "London",      "metro", "nuclear",   3, "upper-middle", True,  "mid-career",   "postgraduate",  "full-time",     "labour", 0.72),
    ("Saima Ahmed",     33, "female", "United Kingdom", "England", "Manchester",  "metro", "nuclear",   3, "middle",       True,  "mid-career",   "undergraduate", "full-time",     "labour", 0.68),
    ("Yasmin Patel",    30, "female", "United Kingdom", "England", "London",      "metro", "other",     1, "middle",       False, "early-career", "postgraduate",  "full-time",     "labour", 0.58),
    ("Imaan Begum",     36, "female", "United Kingdom", "England", "Bradford",    "metro", "joint",     5, "lower-middle", False, "mid-career",   "undergraduate", "part-time",     "labour", 0.88),
    ("Usman Iqbal",     24, "male",   "United Kingdom", "England", "Birmingham",  "metro", "nuclear",   4, "lower-middle", False, "early-career", "undergraduate", "full-time",     "labour", 0.82),
    ("Fatima Chaudhry", 39, "female", "United Kingdom", "England", "Leicester",   "metro", "nuclear",   4, "middle",       True,  "mid-career",   "postgraduate",  "full-time",     "labour", 0.76),
    ("Zafar Ali",       45, "male",   "United Kingdom", "England", "London",      "metro", "nuclear",   5, "middle",       True,  "late-career",  "undergraduate", "self-employed", "labour", 0.79),
]

# ── US South Asian Muslim diaspora pool ───────────────────────────────────────
# Used when anchor_overrides contains location: "United States".
# 14 unique entries — covers the generator's 2× candidate pool without repeats.
# Cities: major South Asian Muslim hubs. Ages 28–40. 3 income brackets.
# (name, age, gender, country, region, city, urban_tier,
#  structure, size, income_bracket, dual_income,
#  life_stage, education, employment)
_US_SOUTH_ASIAN_MUSLIM_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment, political_lean)
    # Cities: major South Asian Muslim hubs. Ages 28–40. 3 income brackets.
    # political_lean: "moderate" — South Asian Muslim diaspora professionals lean moderate
    # per Pew 2017 survey (55% Dem, 26% Ind, 11% Rep → centrist practical lean).
    ("Zara Ahmed",      32, "female", "USA", "New Jersey",     "Edison",       "metro", "nuclear",   3, "upper-middle", True,  "early-family", "postgraduate",  "full-time",  "moderate"),
    ("Imran Sheikh",    38, "male",   "USA", "Illinois",       "Chicago",      "metro", "nuclear",   4, "upper-middle", True,  "mid-career",   "postgraduate",  "full-time",  "moderate"),
    ("Fatima Siddiqui", 29, "female", "USA", "Texas",          "Houston",      "metro", "other",     1, "middle",       False, "early-career", "postgraduate",  "full-time",  "lean_progressive"),
    ("Sana Mirza",      35, "female", "USA", "California",     "Fremont",      "metro", "nuclear",   3, "middle",       True,  "early-family", "undergraduate", "full-time",  "moderate"),
    ("Nadia Rahman",    28, "female", "USA", "New York",       "New York",     "metro", "other",     2, "middle",       False, "early-career", "postgraduate",  "full-time",  "lean_progressive"),
    ("Tariq Hussain",   40, "male",   "USA", "Michigan",       "Dearborn",     "metro", "nuclear",   4, "upper-middle", True,  "mid-career",   "undergraduate", "full-time",  "moderate"),
    ("Ayesha Malik",    33, "female", "USA", "Georgia",        "Atlanta",      "metro", "nuclear",   3, "middle",       True,  "early-family", "postgraduate",  "full-time",  "lean_progressive"),
    ("Ruqayyah Patel",  39, "female", "USA", "Texas",          "Dallas",       "metro", "nuclear",   4, "upper-middle", True,  "mid-career",   "postgraduate",  "full-time",  "moderate"),
    ("Hamza Qureshi",   30, "male",   "USA", "Virginia",       "Sterling",     "metro", "other",     1, "lower-middle", False, "early-career", "undergraduate", "full-time",  "moderate"),
    ("Maryam Chaudhry", 37, "female", "USA", "Pennsylvania",   "Philadelphia", "metro", "nuclear",   3, "middle",       True,  "mid-career",   "postgraduate",  "full-time",  "lean_progressive"),
    ("Safia Begum",     28, "female", "USA", "Washington",     "Seattle",      "metro", "other",     2, "lower-middle", False, "early-career", "postgraduate",  "full-time",  "lean_progressive"),
    ("Yusuf Iqbal",     40, "male",   "USA", "North Carolina", "Durham",       "metro", "nuclear",   4, "upper-middle", True,  "mid-career",   "postgraduate",  "full-time",  "moderate"),
    ("Hana Syed",       34, "female", "USA", "Massachusetts",  "Boston",       "metro", "other",     2, "middle",       False, "early-career", "postgraduate",  "full-time",  "lean_progressive"),
    ("Omar Shaikh",     36, "male",   "USA", "California",     "Los Angeles",  "metro", "nuclear",   3, "middle",       False, "mid-career",   "undergraduate", "full-time",  "moderate"),
]

# Devout South Asian Muslim diaspora pool — waswasa / authority-trust ICP.
# High religious_salience anchored in _US_GENERAL_RELIGIOUS_SALIENCE (0.82–0.85).
# Distinctly observant names. Same 15-field format as _US_SOUTH_ASIAN_MUSLIM_POOL.
_US_SOUTH_ASIAN_MUSLIM_DEVOUT_POOL = [
    ("Amina Hassan",      35, "female", "USA", "New Jersey",     "Paterson",     "metro", "nuclear",   3, "middle",       True,  "early-family", "postgraduate",  "full-time",  "moderate"),
    ("Khadija Rahman",    31, "female", "USA", "Texas",          "Irving",       "metro", "nuclear",   2, "middle",       False, "early-career", "undergraduate", "full-time",  "moderate"),
    ("Safiya Abdullah",   38, "female", "USA", "Michigan",       "Dearborn",     "metro", "nuclear",   4, "upper-middle", True,  "mid-career",   "postgraduate",  "full-time",  "moderate"),
    ("Ibrahim Al-Rashid", 34, "male",   "USA", "Virginia",       "Alexandria",   "metro", "nuclear",   3, "middle",       True,  "early-family", "postgraduate",  "full-time",  "moderate"),
    ("Sumayyah Okafor",   29, "female", "USA", "Georgia",        "Stone Mountain","metro","other",     1, "lower-middle", False, "early-career", "undergraduate", "full-time",  "moderate"),
    ("Bilal Mahmood",     40, "male",   "USA", "California",     "Anaheim",      "metro", "nuclear",   4, "upper-middle", True,  "mid-career",   "postgraduate",  "full-time",  "moderate"),
]

_DOMAIN_POOLS = {
    "cpg": _US_GENERAL_POOL,       # Default CPG to US general pool
    "us_cpg": _US_GENERAL_POOL,    # Explicit US CPG
    "india_cpg": _CPG_POOL,        # Explicit India CPG
    "saas": _SAAS_POOL,
    "general": _US_GENERAL_POOL,
    "health_wellness": _US_GENERAL_POOL,
    "lofoods_fmcg": _LOFOODS_FMCG_POOL,
    "us_general": _US_GENERAL_POOL,
    "india_general": _INDIA_GENERAL_POOL,
    "bengal_general":            _BENGAL_GENERAL_POOL,
    # Bengal Constituency Cluster Pools — B-WB-6
    "bengal_murshidabad":        _BENGAL_MURSHIDABAD_POOL,
    "bengal_malda":              _BENGAL_MALDA_POOL,
    "bengal_matua_belt":         _BENGAL_MATUA_BELT_POOL,
    "bengal_jungle_mahal":       _BENGAL_JUNGLE_MAHAL_POOL,
    "bengal_north_bengal":       _BENGAL_NORTH_BENGAL_POOL,
    "bengal_kolkata_urban":      _BENGAL_KOLKATA_URBAN_POOL,
    "bengal_south_rural":        _BENGAL_SOUTH_RURAL_POOL,
    "bengal_burdwan_industrial": _BENGAL_BURDWAN_INDUSTRIAL_POOL,
    "bengal_presidency_suburbs": _BENGAL_PRESIDENCY_SUBURBS_POOL,
    "bengal_darjeeling_hills":   _BENGAL_DARJEELING_HILLS_POOL,
    # Europe Benchmark v2
    "uk_general":          _UK_GENERAL_POOL,
    "france_general":      _FRANCE_GENERAL_POOL,
    "germany_general":     _GERMANY_GENERAL_POOL,
    "greece_general":      _GREECE_GENERAL_POOL,
    "hungary_general":     _HUNGARY_GENERAL_POOL,
    "italy_general":       _ITALY_GENERAL_POOL,
    "netherlands_general": _NETHERLANDS_GENERAL_POOL,
    "poland_general":      _POLAND_GENERAL_POOL,
    "spain_general":       _SPAIN_GENERAL_POOL,
    "sweden_general":      _SWEDEN_GENERAL_POOL,
}

_EUROPE_GENERAL_DOMAINS = frozenset({
    "uk_general", "france_general", "germany_general", "greece_general",
    "hungary_general", "italy_general", "netherlands_general", "poland_general",
    "spain_general", "sweden_general",
})


def sample_demographic_anchor(
    domain: str,
    index: int,
    seed: int | None = None,
    anchor_overrides: dict | None = None,
) -> Any:
    """Sample a DemographicAnchor for persona generation.

    Uses round-robin from a domain-specific pool to maximise diversity.
    The index parameter ensures different personas in the same cohort get
    different demographics.

    Args:
        domain: Domain key (cpg, saas, general, health_wellness).
        index: Persona index within the cohort (0-based). Used for pool cycling.
        seed: Optional random seed for reproducibility.
        anchor_overrides: Optional dict from the brief. If it contains a
            'location' key, routes to the matching geographic pool.
            If it contains 'age_min'/'age_max', filters the pool to that range.

    Returns:
        A DemographicAnchor instance.
    """
    from src.schema.persona import DemographicAnchor, Location, Household
    from src.schema.worldview import WorldviewAnchor, PoliticalProfile
    from src.worldview.registry import get_political_registry
    _pol_registry = get_political_registry()

    anchor_overrides = anchor_overrides or {}
    location_hint = anchor_overrides.get("location", "").lower()
    age_min = anchor_overrides.get("age_min", 0)
    age_max = anchor_overrides.get("age_max", 100)

    # Location routing — pick pool based on location anchor_override.
    # Falls back to domain pool if no location is specified.
    religiosity_hint = anchor_overrides.get("religiosity", "").lower()
    if "united states" in location_hint or location_hint in ("usa", "us"):
        if religiosity_hint == "devout":
            pool = _US_SOUTH_ASIAN_MUSLIM_DEVOUT_POOL
        elif religiosity_hint in ("muslim", "south_asian_muslim"):
            pool = _US_SOUTH_ASIAN_MUSLIM_POOL
        else:
            pool = _US_GENERAL_POOL
    elif "delhi" in location_hint or location_hint == "dl":
        pool = _DELHI_GENERAL_POOL
    elif "west bengal" in location_hint or "bengal" in location_hint or location_hint in ("wb", "wbl"):
        pool = _BENGAL_GENERAL_POOL
    elif "india" in location_hint or location_hint in ("ind", "in"):
        pool = _INDIA_GENERAL_POOL
    elif "united arab emirates" in location_hint or location_hint in ("uae", "gulf"):
        pool = _UAE_GULF_MUSLIM_POOL
    elif "united kingdom" in location_hint or location_hint in ("uk", "britain", "england"):
        if religiosity_hint in ("devout", "high", "moderate-high", "moderate", "muslim"):
            pool = _UK_SOUTH_ASIAN_MUSLIM_POOL
        else:
            pool = _UK_GENERAL_POOL
    elif "france" in location_hint or location_hint == "fr":
        pool = _FRANCE_GENERAL_POOL
    elif "germany" in location_hint or location_hint in ("de", "deutschland"):
        pool = _GERMANY_GENERAL_POOL
    elif "spain" in location_hint or location_hint == "es":
        pool = _SPAIN_GENERAL_POOL
    elif "italy" in location_hint or location_hint == "it":
        pool = _ITALY_GENERAL_POOL
    elif "netherlands" in location_hint or location_hint in ("nl", "holland"):
        pool = _NETHERLANDS_GENERAL_POOL
    elif "poland" in location_hint or location_hint == "pl":
        pool = _POLAND_GENERAL_POOL
    elif "sweden" in location_hint or location_hint == "se":
        pool = _SWEDEN_GENERAL_POOL
    elif "greece" in location_hint or location_hint == "gr":
        pool = _GREECE_GENERAL_POOL
    elif "hungary" in location_hint or location_hint == "hu":
        pool = _HUNGARY_GENERAL_POOL
    else:
        pool = _DOMAIN_POOLS.get(domain.lower(), _GENERAL_POOL)

    # Religion-based sub-filtering for India pool.
    # The India pool tuple format includes _religion at index 15.
    # When anchor_overrides specifies religiosity (e.g. 'hindu', 'muslim', 'sikh'),
    # restrict to entries of that religion so the LLM receives a demographically
    # appropriate anchor (names, caste, context encode religion implicitly).
    # Falls back to full pool if the filtered sub-pool is empty.
    if "india" in location_hint or "delhi" in location_hint or "bengal" in location_hint or location_hint in ("ind", "in", "dl", "wb", "wbl"):
        rel_filter = religiosity_hint.lower() if religiosity_hint else ""
        if rel_filter in ("hindu", "muslim", "sikh", "christian"):
            filtered_rel = [e for e in pool if len(e) > 15 and e[15] == rel_filter]
            if filtered_rel:
                pool = filtered_rel
        elif rel_filter == "other":
            filtered_rel = [e for e in pool if len(e) > 15 and e[15] not in ("hindu", "muslim")]
            if filtered_rel:
                pool = filtered_rel

        # Income band filtering: map PopScale bands (low/middle/high) to pool
        # income_bracket labels (lower/middle/upper).  Index 9 in India pool tuple.
        income_band = anchor_overrides.get("income_band", "").lower()
        if income_band:
            _INC_MAP = {"low": ("lower",), "middle": ("middle",), "high": ("upper",)}
            allowed_brackets = _INC_MAP.get(income_band, ())
            if allowed_brackets:
                filtered_inc = [e for e in pool if len(e) > 9 and e[9] in allowed_brackets]
                if filtered_inc:
                    pool = filtered_inc

    # Save original pool reference before any sub-filtering.
    # Identity checks below (is_us_general, is_india_general, etc.) depend on
    # this pointing to the base pool constant, not a filtered slice.
    _original_pool = pool

    # Political lean sub-filtering for US pool.
    # The US pool tuple has political_lean at index 14.
    # When anchor_overrides specifies political_lean_hint, restrict pool to
    # matching entries so that state-level partisan skew can be calibrated.
    # Falls back to full pool if the filtered sub-pool is empty.
    if "united states" in location_hint or location_hint in ("usa", "us"):
        political_lean_hint = anchor_overrides.get("political_lean_hint", "").lower()
        if political_lean_hint in ("conservative", "lean_conservative", "moderate", "lean_progressive", "progressive"):
            filtered_lean = [e for e in pool if len(e) > 14 and e[14] == political_lean_hint]
            if filtered_lean:
                pool = filtered_lean
        elif political_lean_hint in ("republican", "trump", "r_lean"):
            filtered_lean = [e for e in pool if len(e) > 14 and e[14] in ("conservative", "lean_conservative")]
            if filtered_lean:
                pool = filtered_lean
        elif political_lean_hint in ("democrat", "harris", "democratic", "d_lean"):
            filtered_lean = [e for e in pool if len(e) > 14 and e[14] in ("lean_progressive", "progressive")]
            if filtered_lean:
                pool = filtered_lean

    # Age filtering — restrict pool to entries within age_min/age_max.
    # The age field is index 1 in every pool tuple format.
    if age_min > 0 or age_max < 100:
        filtered = [e for e in pool if age_min <= e[1] <= age_max]
        if filtered:
            pool = filtered

    # Pool-start-index offset — allows different segments/sub-batches in PopScale
    # to cycle through different pool entries rather than all starting at index 0.
    # Passed as anchor_overrides["_pool_start_index"] (underscore prefix = internal).
    pool_start = int(anchor_overrides.get("_pool_start_index", 0))

    # Round-robin through pool — ensures diversity within a cohort
    entry = pool[(index + pool_start) % len(pool)]

    _US_GENERAL_DOMAINS = {"us_general", "us_cpg", "cpg", "general", "health_wellness"}
    is_uae_muslim = _original_pool is _UAE_GULF_MUSLIM_POOL
    is_uk_south_asian_muslim = _original_pool is _UK_SOUTH_ASIAN_MUSLIM_POOL
    is_us_general = (domain.lower() in _US_GENERAL_DOMAINS or _original_pool is _US_GENERAL_POOL) and not is_uae_muslim and not is_uk_south_asian_muslim
    _BENGAL_CLUSTER_DOMAINS = {
        "bengal_murshidabad", "bengal_malda", "bengal_matua_belt",
        "bengal_jungle_mahal", "bengal_north_bengal", "bengal_kolkata_urban",
        "bengal_south_rural", "bengal_burdwan_industrial",
        "bengal_presidency_suburbs", "bengal_darjeeling_hills",
    }
    _BENGAL_CLUSTER_POOLS = (
        _BENGAL_MURSHIDABAD_POOL, _BENGAL_MALDA_POOL, _BENGAL_MATUA_BELT_POOL,
        _BENGAL_JUNGLE_MAHAL_POOL, _BENGAL_NORTH_BENGAL_POOL, _BENGAL_KOLKATA_URBAN_POOL,
        _BENGAL_SOUTH_RURAL_POOL, _BENGAL_BURDWAN_INDUSTRIAL_POOL,
        _BENGAL_PRESIDENCY_SUBURBS_POOL, _BENGAL_DARJEELING_HILLS_POOL,
    )
    is_india_general = (
        domain.lower() in {"india_general", "india_cpg", "bengal_general"} | _BENGAL_CLUSTER_DOMAINS
        or _original_pool is _INDIA_GENERAL_POOL
        or _original_pool is _DELHI_GENERAL_POOL
        or _original_pool is _BENGAL_GENERAL_POOL
        or any(_original_pool is p for p in _BENGAL_CLUSTER_POOLS)
    ) and not is_uae_muslim and not is_uk_south_asian_muslim
    _EU_LOCATION_POOLS = (
        _FRANCE_GENERAL_POOL, _GERMANY_GENERAL_POOL, _GREECE_GENERAL_POOL,
        _HUNGARY_GENERAL_POOL, _ITALY_GENERAL_POOL, _NETHERLANDS_GENERAL_POOL,
        _POLAND_GENERAL_POOL, _SPAIN_GENERAL_POOL, _SWEDEN_GENERAL_POOL,
        _UK_GENERAL_POOL,
    )
    is_europe_general = (
        domain.lower() in _EUROPE_GENERAL_DOMAINS
        or any(_original_pool is p for p in _EU_LOCATION_POOLS)
    ) and not is_uae_muslim and not is_uk_south_asian_muslim

    # Defensive unpacking: determine field count from actual entry, not just domain.
    # This guards against domain detection bugs and pool structure changes.
    entry_len = len(entry)

    if entry_len >= 17:
        # 17+ fields: India/Bengal pool (includes religion, caste, or other extra fields)
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean,
         _religion, _caste, *_extras) = entry
    elif entry_len == 16:
        # 16 fields: Europe or UK South Asian Muslim pool
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean,
         _religious_salience_base) = entry
    elif entry_len == 15:
        # 15 fields: US General pool
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean) = entry
    else:
        # 14 or fewer fields: UAE/Gulf or legacy pool (no political_lean)
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment) = entry
        political_lean = None

    # Optional: add small age variation (+/-3 years) for diversity when wrapping
    if seed is not None and index >= len(pool):
        rng = random.Random(seed + index)
        age = max(18, min(65, age + rng.randint(-3, 3)))

    # Build WorldviewAnchor for US and India general domains.
    # Other domains leave worldview as None — zero impact on existing behaviour.
    worldview = None
    if political_lean is not None:
        # Use region-specific worldview dimensions
        if is_us_general:
            base = _WORLDVIEW_BASE_DIMS.get(political_lean)
        elif is_india_general:
            base = _INDIA_WORLDVIEW_BASE_DIMS.get(political_lean)
        else:
            base = None

        if base is not None:
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

            # Brief-level override — allows slots with distinct religiosity levels
            # (moderate, less-practicing, cultural Muslim) to be set precisely
            # rather than inheriting the pool's default range.
            rs_override = anchor_overrides.get("religious_salience_override")
            if rs_override is not None:
                religious_salience = float(rs_override)

            worldview = WorldviewAnchor(
                institutional_trust=jitter(inst_trust),
                social_change_pace=jitter(change_pace),
                collectivism_score=jitter(collectivism),
                economic_security_priority=jitter(econ_security),
                political_profile=PoliticalProfile(
                    country="USA" if is_us_general else "India",
                    archetype=political_lean,
                    description=(_pol_registry.get_description("USA", political_lean) if is_us_general
                                 else _pol_registry.get_description("India", political_lean)),
                ),
                political_era=_US_POLITICAL_ERA if is_us_general else _INDIA_POLITICAL_ERA,
                religious_salience=religious_salience,
            )

    elif is_europe_general and political_lean is not None:
        # Europe Benchmark v2: country-specific WorldviewAnchor.
        # Uses per-country + per-archetype base dimensions.
        country_dims = _EUROPE_WORLDVIEW_DIMS.get(domain.lower(), {})
        base = country_dims.get(political_lean, (0.50, 0.50, 0.50, 0.55))
        inst_trust, change_pace, collectivism, econ_security = base

        persona_seed = abs(hash(name)) % 10000
        rng = random.Random(persona_seed)
        jitter = lambda v: round(max(0.0, min(1.0, v + rng.uniform(-0.04, 0.04))), 2)  # noqa: E731

        # Religious salience from pool tuple (field 16, 0-indexed as _religious_salience_base)
        religious_salience = round(
            max(0.0, min(1.0, _religious_salience_base + rng.uniform(-0.03, 0.03))), 2
        )

        political_era = _EUROPE_POLITICAL_ERA.get(domain.lower(), "")

        worldview = WorldviewAnchor(
            institutional_trust=jitter(inst_trust),
            social_change_pace=jitter(change_pace),
            collectivism_score=jitter(collectivism),
            economic_security_priority=jitter(econ_security),
            political_profile=PoliticalProfile(
                country=country,
                archetype=political_lean,
                description=_pol_registry.get_description(country, political_lean),
            ),
            political_era=political_era,
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
