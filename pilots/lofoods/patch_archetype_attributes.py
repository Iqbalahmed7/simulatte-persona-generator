"""patch_archetype_attributes.py — Post-process Lo! Foods cohorts.

Corrects key attribute values that drift from archetype spec due to the
demographic sampler using population priors instead of archetype-specific
key_signals.

Run after generation, before simulation:
    python3 pilots/lofoods/patch_archetype_attributes.py

Idempotent — safe to re-run. Backs up originals with .pre_patch suffix.
"""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

PERSONAS_DIR = Path(__file__).resolve().parent / "personas"

# ---------------------------------------------------------------------------
# Archetype attribute targets
# Each entry: attribute_path -> (min_value, max_value)
# attribute_path is "category.attribute_name"
# ---------------------------------------------------------------------------

ARCHETYPE_TARGETS: dict[str, dict[str, tuple[float, float]]] = {
    "C1": {
        # Metro health-conscious mainstream — moderate protein awareness, low keto
        "values.keto_diet_adherence":         (0.03, 0.18),
        "values.protein_consciousness":        (0.35, 0.65),
        "values.clean_label_importance":       (0.30, 0.60),
        "values.functional_food_trust":        (0.30, 0.55),
        "social.quick_commerce_adoption":      (0.45, 0.80),
        "psychology.premium_price_tolerance":  (0.30, 0.60),
        "psychology.indian_startup_brand_trust": (0.30, 0.55),
    },
    "C2": {
        # Keto lifestyle follower — HIGH keto, high clean label, high premium tolerance
        "values.keto_diet_adherence":         (0.65, 0.95),
        "values.clean_label_importance":       (0.65, 0.92),
        "values.functional_food_trust":        (0.25, 0.55),
        "values.protein_consciousness":        (0.40, 0.70),
        "psychology.premium_price_tolerance":  (0.55, 0.85),
        "psychology.indian_startup_brand_trust": (0.20, 0.50),
        "psychology.weight_management_drive":  (0.60, 0.90),
    },
    "C3": {
        # Mainstream fitness enthusiast — HIGH protein, low keto
        "values.protein_consciousness":        (0.60, 0.90),
        "values.keto_diet_adherence":         (0.02, 0.15),
        "values.clean_label_importance":       (0.30, 0.60),
        "social.quick_commerce_adoption":      (0.50, 0.85),
        "psychology.premium_price_tolerance":  (0.30, 0.60),
        "psychology.doctor_endorsement_weight": (0.10, 0.40),
        "psychology.weight_management_drive":  (0.45, 0.75),
    },
    "C4": {
        # Regular bread buyer — low health consciousness, price sensitive
        "values.protein_consciousness":        (0.05, 0.25),
        "values.keto_diet_adherence":         (0.01, 0.08),
        "values.clean_label_importance":       (0.05, 0.30),
        "values.functional_food_trust":        (0.05, 0.30),
        "psychology.premium_price_tolerance":  (0.05, 0.25),
        "psychology.indian_startup_brand_trust": (0.05, 0.25),
    },
    "C5": {
        # Quick commerce power user — high adoption, medium trust
        "social.quick_commerce_adoption":      (0.70, 0.98),
        "social.quick_commerce_trust":         (0.25, 0.55),
        "social.d2c_comfort":                  (0.55, 0.85),
        "psychology.premium_price_tolerance":  (0.30, 0.60),
    },
    "C6": {
        # Parent / family health decision-maker
        "values.clean_label_importance":       (0.55, 0.85),
        "psychology.doctor_endorsement_weight": (0.60, 0.90),
        "values.functional_food_trust":        (0.35, 0.65),
        "psychology.premium_price_tolerance":  (0.35, 0.65),
        "values.subscription_tolerance":       (0.25, 0.55),
    },
    "C7": {
        # Type 2 diabetic patient
        "psychology.diabetic_status":          (0.75, 1.00),
        "psychology.doctor_endorsement_weight": (0.75, 0.98),
        "values.clean_label_importance":       (0.60, 0.90),
        "psychology.premium_price_tolerance":  (0.25, 0.55),
        "psychology.indian_startup_brand_trust": (0.10, 0.40),
    },
    "C8": {
        # Diabetic caretaker / spouse
        "psychology.diabetic_status":          (0.30, 0.60),
        "psychology.doctor_endorsement_weight": (0.70, 0.95),
        "values.clean_label_importance":       (0.60, 0.88),
        "psychology.indian_startup_brand_trust": (0.05, 0.30),
    },
    "C9": {
        # Tier 2 city health-aware consumer
        "values.tier2_health_aspiration":     (0.55, 0.88),
        "values.keto_diet_adherence":         (0.01, 0.10),
        "values.protein_consciousness":        (0.20, 0.55),
        "psychology.premium_price_tolerance":  (0.10, 0.35),
        "psychology.indian_startup_brand_trust": (0.05, 0.25),
    },
    "C10": {
        # Clinically diagnosed celiac
        "psychology.gluten_sensitivity_belief": (0.80, 1.00),
        "psychology.doctor_endorsement_weight": (0.60, 0.90),
        "values.clean_label_importance":       (0.75, 0.98),
        "psychology.premium_price_tolerance":  (0.55, 0.88),
    },
    "C11": {
        # Gluten-free trend follower (lifestyle)
        "psychology.gluten_sensitivity_belief": (0.35, 0.65),
        "values.clean_label_importance":       (0.55, 0.85),
        "values.functional_food_trust":        (0.45, 0.75),
        "psychology.premium_price_tolerance":  (0.40, 0.70),
    },
    "C12": {
        # Social media active health shopper
        "values.protein_consciousness":        (0.40, 0.70),
        "values.clean_label_importance":       (0.45, 0.75),
        "values.functional_food_trust":        (0.45, 0.75),
        "social.quick_commerce_adoption":      (0.55, 0.85),
        "psychology.indian_startup_brand_trust": (0.45, 0.75),
    },
    "C13": {
        # Amazon regular grocery shopper
        "values.protein_consciousness":        (0.10, 0.40),
        "values.clean_label_importance":       (0.10, 0.40),
        "psychology.premium_price_tolerance":  (0.15, 0.45),
        "social.d2c_comfort":                  (0.25, 0.55),
    },
    "C14": {
        # First-time health product trial buyer
        "values.functional_food_trust":        (0.15, 0.45),
        "psychology.premium_price_tolerance":  (0.15, 0.45),
        "values.subscription_tolerance":       (0.05, 0.25),
        "psychology.indian_startup_brand_trust": (0.15, 0.40),
    },
    "C15": {
        # Cloud kitchen customer
        "values.keto_diet_adherence":         (0.40, 0.80),
        "values.clean_label_importance":       (0.60, 0.90),
        "psychology.premium_price_tolerance":  (0.60, 0.90),
        "values.subscription_tolerance":       (0.55, 0.85),
        "values.functional_food_trust":        (0.60, 0.90),
    },
    "P1": {
        # Hospital dietitian
        "values.functional_food_trust":        (0.15, 0.45),
        "values.clean_label_importance":       (0.75, 0.98),
        "psychology.indian_startup_brand_trust": (0.05, 0.25),
    },
    "P2": {
        # GP / endocrinologist
        "values.functional_food_trust":        (0.10, 0.40),
        "psychology.indian_startup_brand_trust": (0.05, 0.20),
        "values.clean_label_importance":       (0.65, 0.90),
    },
    "P3": {
        # Corporate wellness / HR manager
        "values.functional_food_trust":        (0.35, 0.65),
        "psychology.premium_price_tolerance":  (0.25, 0.55),
    },
    "P4": {
        # Cafeteria / institutional food operator
        "psychology.premium_price_tolerance":  (0.05, 0.25),
        "values.functional_food_trust":        (0.25, 0.55),
        "psychology.indian_startup_brand_trust": (0.10, 0.35),
    },
}


def _get_nested(attrs: dict, path: str):
    """Get attrs[category][attr_name] from 'category.attr_name' path."""
    cat, attr = path.split(".", 1)
    return attrs.get(cat, {}).get(attr)


def _set_nested(attrs: dict, path: str, value: float):
    """Set attrs[category][attr_name] from 'category.attr_name' path."""
    cat, attr = path.split(".", 1)
    if cat not in attrs:
        return
    if attr not in attrs[cat]:
        return
    entry = attrs[cat][attr]
    if isinstance(entry, dict):
        entry["value"] = value
    else:
        attrs[cat][attr] = value


def patch_cohort(archetype: str, dry_run: bool = False) -> dict:
    """Patch key attribute values for a generated cohort file.

    Returns summary dict with counts.
    """
    cohort_path = PERSONAS_DIR / f"cohort_{archetype}.json"
    if not cohort_path.exists():
        return {"archetype": archetype, "status": "skipped", "reason": "file not found"}

    targets = ARCHETYPE_TARGETS.get(archetype, {})
    if not targets:
        return {"archetype": archetype, "status": "skipped", "reason": "no targets defined"}

    with open(cohort_path) as f:
        data = json.load(f)

    personas = data["envelope"]["personas"]
    rng = random.Random(42 + sum(ord(c) for c in archetype))

    patched_count = 0
    for persona in personas:
        attrs = persona.get("attributes", {})
        for path, (lo, hi) in targets.items():
            current = _get_nested(attrs, path)
            if current is None:
                continue
            current_val = current["value"] if isinstance(current, dict) else current
            # Only patch if outside target range
            if not (lo <= current_val <= hi):
                new_val = round(rng.uniform(lo, hi), 4)
                if not dry_run:
                    _set_nested(attrs, path, new_val)
                patched_count += 1

    if not dry_run:
        # Backup original
        backup = cohort_path.with_suffix(".json.pre_patch")
        if not backup.exists():
            shutil.copy2(cohort_path, backup)

        with open(cohort_path, "w") as f:
            json.dump(data, f, indent=2)

    return {
        "archetype": archetype,
        "status": "patched" if not dry_run else "dry_run",
        "personas": len(personas),
        "attributes_corrected": patched_count,
    }


def main():
    print("=== Lo! Foods Archetype Attribute Patch ===\n")
    archetypes = list(ARCHETYPE_TARGETS.keys())
    results = []
    for a in archetypes:
        r = patch_cohort(a)
        results.append(r)
        status = r["status"]
        if status == "patched":
            print(f"  {a}: patched {r['attributes_corrected']} attribute values across {r['personas']} personas")
        elif status == "skipped":
            print(f"  {a}: skipped ({r['reason']})")

    print(f"\nDone. {sum(1 for r in results if r['status'] == 'patched')} cohorts patched.")


if __name__ == "__main__":
    main()
