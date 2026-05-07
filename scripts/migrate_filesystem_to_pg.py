"""Backfill cohort JSON files from STORE_DIR into Postgres.

Usage:
    DATABASE_URL=... python scripts/migrate_filesystem_to_pg.py \\
        --store-dir /tmp/simulatte_cohorts --tenant-id legacy

Each *.json file in --store-dir is read as a CohortEnvelope dict and inserted
into the cohorts + personas tables via persist_cohort(). Existing rows are NOT
updated; the script creates a fresh row per file (the legacy cohort_id is
stored in summary.cohort_id_legacy).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.cohort_persistence import persist_cohort  # noqa: E402
from src.db.session import get_session_sync, init_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-dir", required=True)
    parser.add_argument("--tenant-id", default="legacy")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    init_engine()

    store = Path(args.store_dir)
    if not store.exists():
        print(f"store dir not found: {store}", file=sys.stderr)
        return 1

    files = sorted(store.glob("*.json"))
    print(f"Found {len(files)} cohort files")
    if args.dry_run:
        for f in files:
            print(f"  would migrate: {f.name}")
        return 0

    migrated = 0
    for f in files:
        try:
            envelope = json.loads(f.read_text())
        except Exception as exc:  # noqa: BLE001
            print(f"skip {f.name}: {exc}")
            continue
        with get_session_sync() as session:
            try:
                cohort = persist_cohort(
                    session,
                    tenant_id=args.tenant_id,
                    brief={"source_file": f.name},
                    cohort_envelope=envelope,
                    cost_usd=None,
                    generator_version="legacy-fs-import",
                    created_by_module="migrate_filesystem_to_pg",
                )
                migrated += 1
                print(f"migrated {f.name} → {cohort.id}")
            except Exception as exc:  # noqa: BLE001
                print(f"failed {f.name}: {exc}")
    print(f"Done. Migrated {migrated}/{len(files)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
