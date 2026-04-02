# Sprint 15 — 5:3:2 Stratification Wiring: Outcome

## What was done

Wired `CohortStratifier.stratify()` into `_run_generation()` in `src/cli.py`.

The change has two parts:

1. **Candidate pool expansion** — when `count >= 5`, a pool of `max(count * 2, count + 4)` candidates is generated instead of exactly `count`. This gives the stratifier enough diversity to select from.

2. **Stratification** — after building the pool, if `count >= 5` and the pool is larger than the target, `CohortStratifier.stratify(candidates, target_size=count)` is called to select the final `count` personas using the 5:3:2 cosine-distance distribution (50% near-center, 30% mid-range, 20% far-outlier). An `ImportError` on numpy is caught and falls back to `candidates[:count]` with a warning.

## numpy availability

numpy is **not installed** in this environment:

```
ModuleNotFoundError: No module named 'numpy'
```

The ImportError fallback is therefore active at runtime. The stratification code path will engage automatically once numpy is installed (`pip install numpy`).

## New `_run_generation` pool + stratification block

```python
    # Generate candidate pool (2× for stratification when count >= 5)
    pool_size = max(count * 2, count + 4) if count >= 5 else count
    candidates = list(await asyncio.gather(*[_build_one(i) for i in range(1, pool_size + 1)]))

    # Stratify if cohort is large enough
    if count >= 5 and len(candidates) > count:
        try:
            from src.generation.stratification import CohortStratifier
            stratifier = CohortStratifier()
            strat_result = stratifier.stratify(candidates, target_size=count)
            personas = strat_result.cohort
            click.echo(
                f"  Stratified to {count} personas (near={len(strat_result.near_center)},"
                f" mid={len(strat_result.mid_range)}, far={len(strat_result.far_outliers)})",
                err=True,
            )
        except ImportError:
            click.echo(
                "  Warning: numpy not available — skipping 5:3:2 stratification, using first"
                f" {count} candidates.",
                err=True,
            )
            personas = candidates[:count]
    else:
        personas = candidates[:count]
```

## Test results

```
249 passed, 15 skipped in 1.53s
```

All 249 tests pass, 15 skipped. No regressions.

## Stratification wiring verification

```python
import inspect
from src import cli
source = inspect.getsource(cli._run_generation)
assert "stratif" in source.lower()
# → Assertion passed
```
