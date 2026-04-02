# Data Grounding Layer — Reference

## Purpose

This document specifies how real-world signals are transformed into behavioural parameters and attribute distributions for persona generation.

**Design principle:** Don't add more data. Build targeted signal extraction against four specific questions:
1. What drives purchase?
2. What drives churn/switching?
3. What is actual WTP distribution in this segment?
4. What information sources do buyers trust, and how much?

---

## Data Source Registry

### Tier 1: Highest Signal Quality

| Source | Signal Type | Access Method | Update Frequency |
|--------|------------|---------------|-----------------|
| App Store reviews (4-5★, Verified Purchase) | Purchase triggers | API / manual scrape | Per run |
| App Store reviews (1-3★) | Rejection, objections, churn triggers | API / manual scrape | Per run |
| Amazon Verified Purchase reviews | Purchase triggers + price sensitivity | API / manual scrape | Per run |
| G2 / Capterra / Trustpilot (by star rating) | B2B objections, switching, vendor trust | Manual scrape | Per run |
| Reddit (r/[industry], decision posts) | Purchase triggers, switching events, trust sources | Reddit API | Per run |
| Client CRM / purchase history (anonymised) | Ground truth purchase, churn, LTV | Client-provided | Per engagement |

### Tier 2: Calibration Anchors

| Source | Signal Type | Access Method | Update Frequency |
|--------|------------|---------------|-----------------|
| Mixpanel State of PLG report | SaaS conversion benchmarks | Public PDF | Annual |
| Recurly Subscription Economy Index | Subscription churn benchmarks | Public PDF | Annual |
| Amplitude Product Benchmarks | Engagement / retention benchmarks | Public PDF | Annual |
| Shopify Commerce Trends | E-commerce conversion benchmarks | Public PDF | Annual |
| Pew Research demographic surveys | Population demographic distributions | Public download | Annual |
| US Census ACS / Indian Census | Income, household, geography distributions | Public download | Annual |

### Tier 3: Domain-Specific Supplements

| Domain | Recommended Supplement |
|--------|----------------------|
| Child nutrition / FMCG India | BabyCenter India community posts, MomJunction forums |
| B2B SaaS | Reddit r/sysadmin, r/salesforce, Hacker News "Ask HN: tools you use" |
| Real estate | r/FirstTimeHomeBuyer, Housing.com reviews |
| Healthcare | Patient forums, WebMD community posts |
| EdTech | r/homeschooling, parent Facebook groups (public posts only) |
| Financial services | r/personalfinance, r/IndiaInvestments |

---

## Signal Extraction Pipeline

### Stage 1: Signal Extraction

**Input:** Raw text corpus (reviews, forum posts, support tickets)
**Output:** Labelled signal corpus

```
For each document in corpus:
  1. Tokenise into sentences
  2. Filter for sentences containing decision-language markers:

     PURCHASE TRIGGERS:
       "finally bought", "decided to buy", "went ahead with", "pulled the trigger",
       "worth it", "glad I bought", "switched to", "moved to"

     REJECTION / OBJECTIONS:
       "cancelled because", "too expensive", "not worth", "returned because",
       "disappointed", "won't buy again", "switched away", "cancelled my"

     SWITCHING EVENTS:
       "switched from X to Y", "moved from X to", "left X because",
       "X to Y because", "dumped X", "replaced X with"

     PRICE SIGNALS:
       "on sale", "wait for discount", "coupon", "cheaper than",
       "price dropped", "not worth the price", "found it for less"

     TRUST SOURCE CITATIONS:
       "my doctor said", "paediatrician recommended", "my friend told me",
       "saw it on YouTube", "influencer I follow", "company blog", "saw an ad",
       "read a review", "forum recommended", "community said"

  3. Tag each sentence with:
     - signal_type: [purchase_trigger | rejection | switching | price_signal | trust_citation]
     - source_platform: [app_store | amazon | reddit | g2 | trustpilot | forum]
     - star_rating: [1-5 | null]
     - trust_source_type: [expert | peer | brand | ad | community | influencer | null]

  4. Store in labelled corpus with metadata
```

**Minimum corpus size for reliable estimation:** 200 labelled sentences per signal type. Below this, use proxy estimation and mark `source: "proxy_estimated"`.

---

### Stage 2: Feature Construction

**Input:** Labelled signal corpus
**Output:** Feature vectors per review cluster (one vector per document or per cluster)

Compute these features per cluster:

```
price_salience_index         = count(price_signal sentences) / count(total sentences)
purchase_trigger_density     = count(purchase_trigger sentences) / count(total)
rejection_density            = count(rejection sentences) / count(total)
switching_mention_rate       = count(switching sentences) / count(total)

trust_source_distribution    = {
  expert:     count(trust_type=="expert") / count(all trust_citations),
  peer:       count(trust_type=="peer") / ...,
  brand:      count(trust_type=="brand") / ...,
  ad:         count(trust_type=="ad") / ...,
  community:  count(trust_type=="community") / ...,
  influencer: count(trust_type=="influencer") / ...
}

objection_cluster_frequency  = {
  price_vs_value:        count(sentences matching price objection pattern) / total,
  trust_deficit:         count(sentences matching trust objection) / total,
  need_more_info:        count(sentences matching research intent) / total,
  feature_gap:           count(sentences matching missing feature) / total
}

purchase_correlation_by_source = {
  for each trust_source_type:
    correlation(appears_in_doc, doc_star_rating >= 4)  # proxy for purchase
}
```

---

### Stage 3: Behavioural Cluster Derivation

**Input:** Feature vectors per document / cluster
**Output:** K behavioural archetypes with parameter distributions

```
1. Cluster on behavioural features (NOT demographics):
   Features to cluster on:
     - price_salience_index
     - trust_source_distribution (flattened)
     - switching_mention_rate
     - objection_cluster_frequency (flattened)

   Method: GMM (preferred) or k-means with k=4-8
   Evaluation: silhouette score ≥ 0.35 is acceptable

2. For each cluster, compute parameter estimates:

   price_elasticity estimate:
     = -(price_salience_index * 0.9 + switching_mention_rate * 0.4)
     clipped to [-1.2, -0.05]

   baseline_switch_rate estimate:
     = switching_mention_rate * 0.12
     (empirical: ~12% of switch-mentioning reviews → actual churn event)

   trust_vector estimates:
     = trust_source_distribution * purchase_correlation_by_source
     normalised so max weight = 1.0

   dominant_objection:
     = argmax(objection_cluster_frequency)

3. Cross-tabulate with demographics (if available):
   For each cluster: compute P(cluster | demographic_segment)
   This gives: "mid-career SaaS buyers in this cluster 65% of the time"
```

---

## Domain Data Handling in the Skill

When domain data is provided in Section 5 of the ICP Spec, the skill switches to **Grounded Mode** automatically. The processing sequence changes as follows:

### Standard Flow (no domain data):
```
ICP Spec → Taxonomy (LLM) → Attribute Sampling → Proxy Behavioural Params → Narrative
```

### Grounded Flow (domain data provided):
```
ICP Spec → Signal Extraction (Stage 1) → Feature Construction (Stage 2)
        → Cluster Derivation (Stage 3) → Empirical Parameter Estimation
        → Taxonomy (informed by cluster signals) → Attribute Sampling
        → Cluster-Estimated Behavioural Params → Narrative
```

The taxonomy construction in Step 2 of the skill is informed by the cluster signals:
- Objection types found in Stage 2 become leaf attributes in the `domain_specific` category
- Trust source citations become the basis for `social` category attributes
- Price salience informs whether `budget_consciousness` and `deal_seeking` need higher resolution

---

## Minimum Viable Data Set

When no domain-specific data is available, use this minimum set as a starting point:

### For SaaS / B2B:
- G2 reviews for 2-3 competing products (min 50 reviews each, mix of star ratings)
- Reddit r/[relevant_subreddit] — search for "switched from" and "cancelled" posts (min 30 posts)
- One public benchmark report (Mixpanel PLG or equivalent)

### For Consumer / FMCG:
- Amazon reviews for 2-3 competing products (min 100 reviews, use "most helpful" + "critical")
- One relevant subreddit — search for "bought" and "returned" posts (min 30 posts)
- One public benchmark (industry conversion rate or NPS benchmark)

### For Healthcare / EdTech:
- App Store reviews for 2-3 apps in category (min 50 reviews each)
- One relevant forum (min 30 discussion threads)
- Category-specific benchmark (if available from industry association)

---

## What This Layer Does NOT Do

- Does not replace the ICP Spec — the business problem still defines the domain
- Does not replace the taxonomy — it informs and refines it
- Does not generate personas directly — it produces parameters that are assigned to personas
- Does not require perfect data — proxy estimation is the fallback when data is thin
- Does not require real-time scraping — batch pipeline per domain, refreshed periodically

---

## Data Quality Flags

When using data from the pipeline, attach these flags to cluster estimates:

| Flag | Meaning |
|------|---------|
| `HIGH_CONFIDENCE` | ≥ 500 labelled sentences, silhouette ≥ 0.45 |
| `MEDIUM_CONFIDENCE` | 200-499 labelled sentences, silhouette ≥ 0.35 |
| `LOW_CONFIDENCE` | < 200 labelled sentences, silhouette < 0.35 |
| `PROXY_ONLY` | No domain data; proxy formulas used exclusively |

Personas generated from `LOW_CONFIDENCE` or `PROXY_ONLY` data must have `behavioural_params.mode: "proxy"` in their schema.
