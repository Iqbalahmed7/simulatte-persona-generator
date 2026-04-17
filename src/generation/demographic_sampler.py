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
    ("Vinod Kapoor",    55, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "upper",  False, "late-career",  "postgraduate", "self-employed",   "bjp_supporter", "hindu",  "general"),
    # BJP leaners (4) — soft BJP, Modi economy / cultural identity
    ("Ravi Kumar",      35, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "lower",  False, "mid-career",   "high-school",  "full-time",       "bjp_lean",      "hindu",  "obc"),
    ("Manoj Gupta",     48, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 4, "middle", False, "mid-career",   "undergraduate","self-employed",   "bjp_lean",      "hindu",  "general"),
    ("Sanjay Khanna",   52, "male",   "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "middle", False, "late-career",  "undergraduate","retired",         "bjp_lean",      "hindu",  "general"),
    ("Deepika Arora",   38, "female", "India", "Delhi", "New Delhi",   "metro", "nuclear", 3, "upper",  True,  "mid-career",   "postgraduate", "full-time",       "bjp_lean",      "hindu",  "general"),
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
    if "india" in location_hint or "delhi" in location_hint or location_hint in ("ind", "in", "dl"):
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

    # Save original pool reference before age filtering (identity checks below depend on it)
    _original_pool = pool

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
    is_india_general = (domain.lower() in {"india_general", "india_cpg"} or _original_pool is _INDIA_GENERAL_POOL or _original_pool is _DELHI_GENERAL_POOL) and not is_uae_muslim and not is_uk_south_asian_muslim
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

    if is_us_general:
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean) = entry
    elif is_india_general:
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean,
         _religion, _caste) = entry
    elif is_europe_general or is_uk_south_asian_muslim:
        (name, age, gender, country, region, city, urban_tier,
         structure, size, income_bracket, dual_income,
         life_stage, education, employment, political_lean,
         _religious_salience_base) = entry
    else:
        # UAE/Gulf or any 14-field pool (no political_lean)
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
                country="USA",
                archetype=political_lean,
                description=_pol_registry.get_description("USA", political_lean),
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
                description=_pol_registry.get_description("India", political_lean),
            ),
            political_era=_INDIA_POLITICAL_ERA,
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
