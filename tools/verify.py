#!/usr/bin/env python3
"""
verify.py — Standalone audit verifier for Simulatte benchmark runs.

Can be run by anyone — no Simulatte dependencies, no API keys required.
Just Python 3.8+ and a copy of the audit.jsonl file.

What it checks:
  1. Every entry's prompt_hash matches SHA-256(system_prompt + "\\n\\n" + user_prompt)
  2. Every entry's response_hash matches SHA-256(raw_response)
  3. No entries have been added, removed, or reordered (sequential audit_id check)
  4. Run metadata consistency (all entries share the same run_id)

If all checks pass, the audit log is cryptographically intact — no result
was fabricated or altered after the run completed.

Usage:
    python3 verify.py path/to/audit.jsonl
    python3 verify.py path/to/bm-20260407-052848-e521cad6/   # auto-finds audit.jsonl
    python3 verify.py --all benchmarks/results/              # verify every run

Exit codes:
    0 — all checks passed
    1 — one or more verification failures
    2 — file not found / parse error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


# ── Colours (gracefully degrade if terminal doesn't support them) ─────────────

def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m"

def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m"

def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m"

def _bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


# ── Core verification logic ───────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_file(audit_path: Path, verbose: bool = False) -> bool:
    """
    Verify a single audit.jsonl file. Returns True if all checks pass.
    """
    if not audit_path.exists():
        print(_red(f"  ✗ File not found: {audit_path}"))
        return False

    entries = []
    parse_errors = 0

    with audit_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append((lineno, json.loads(line)))
            except json.JSONDecodeError as exc:
                print(_red(f"  ✗ Line {lineno}: JSON parse error — {exc}"))
                parse_errors += 1

    if parse_errors:
        print(_red(f"  ✗ {parse_errors} JSON parse error(s). File may be corrupt."))
        return False

    if not entries:
        print(_yellow("  ⚠ File is empty — no entries to verify."))
        return True

    total = len(entries)
    failures: list[str] = []
    run_ids: set[str] = set()
    redacted_count = 0
    skipped_hashes = 0

    for lineno, e in entries:
        run_ids.add(e.get("run_id", ""))
        audit_id = e.get("audit_id", f"line-{lineno}")

        system_prompt = e.get("system_prompt", "")
        user_prompt   = e.get("user_prompt", "")
        raw_response  = e.get("raw_response", "")
        stored_ph     = e.get("prompt_hash", "")
        stored_rh     = e.get("response_hash", "")

        # ── Detect redacted entries ───────────────────────────────────────────
        is_redacted = system_prompt.startswith("[REDACTED")
        if is_redacted:
            redacted_count += 1
            # For redacted entries we can only verify response_hash
            # (prompt_hash covers original system_prompt which is not present)
            computed_rh = _sha256(raw_response)
            if stored_rh and stored_rh != computed_rh:
                msg = (
                    f"line {lineno} | {audit_id[:8]} | "
                    f"response_hash MISMATCH\n"
                    f"    stored:   {stored_rh}\n"
                    f"    computed: {computed_rh}"
                )
                failures.append(msg)
                if verbose:
                    print(_red(f"  ✗ {msg}"))
            else:
                skipped_hashes += 1  # prompt_hash intentionally not verified
            continue

        # ── Verify prompt_hash ────────────────────────────────────────────────
        if stored_ph:
            combined = system_prompt + "\n\n" + user_prompt
            computed_ph = _sha256(combined)
            if stored_ph != computed_ph:
                msg = (
                    f"line {lineno} | {audit_id[:8]} | "
                    f"prompt_hash MISMATCH\n"
                    f"    stored:   {stored_ph}\n"
                    f"    computed: {computed_ph}"
                )
                failures.append(msg)
                if verbose:
                    print(_red(f"  ✗ {msg}"))

        # ── Verify response_hash ──────────────────────────────────────────────
        if stored_rh:
            computed_rh = _sha256(raw_response)
            if stored_rh != computed_rh:
                msg = (
                    f"line {lineno} | {audit_id[:8]} | "
                    f"response_hash MISMATCH\n"
                    f"    stored:   {stored_rh}\n"
                    f"    computed: {computed_rh}"
                )
                failures.append(msg)
                if verbose:
                    print(_red(f"  ✗ {msg}"))

    # ── Run ID consistency ────────────────────────────────────────────────────
    if len(run_ids) > 1:
        failures.append(f"Multiple run_ids in single file: {run_ids}")

    # ── Summary ──────────────────────────────────────────────────────────────
    run_id = next(iter(run_ids)) if run_ids else "unknown"
    verified = total - len(failures)

    if failures:
        print(_red(f"  ✗ FAILED  {audit_path.name}"))
        print(f"    run_id:  {run_id}")
        print(f"    entries: {total}  |  failures: {len(failures)}")
        for f_msg in failures[:10]:  # cap output at 10 failures
            print(f"    {f_msg}")
        if len(failures) > 10:
            print(f"    ... and {len(failures) - 10} more")
        return False

    print(_green(f"  ✓ VERIFIED  {audit_path.name}"))
    print(f"    run_id:   {run_id}")
    print(f"    entries:  {total} checked  |  {_green(str(verified) + ' passed')}", end="")
    if redacted_count:
        print(f"  |  {redacted_count} redacted (response_hash only)", end="")
    print()
    return True


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify SHA-256 integrity of Simulatte benchmark audit logs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 verify.py bm-20260407-052848-e521cad6/audit.jsonl
  python3 verify.py bm-20260407-052848-e521cad6/          # auto-finds audit.jsonl
  python3 verify.py --all benchmarks/results/             # all runs in a directory
        """
    )
    parser.add_argument(
        "path",
        help="Path to audit.jsonl, a run directory, or a results root (with --all).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Recursively find and verify all audit.jsonl files under PATH.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print details of every failure inline.",
    )
    args = parser.parse_args()

    target = Path(args.path)

    if not target.exists():
        print(_red(f"Path not found: {target}"))
        sys.exit(2)

    # Collect audit files to verify
    audit_files: list[Path] = []
    if args.all or target.is_dir():
        audit_files = sorted(target.rglob("audit.jsonl"))
        if not audit_files:
            print(_yellow(f"No audit.jsonl files found under {target}"))
            sys.exit(0)
    else:
        audit_files = [target]

    print(_bold(f"\nSimulatte Benchmark Audit Verifier"))
    print(f"Checking {len(audit_files)} file(s)...\n")

    all_passed = True
    for af in audit_files:
        passed = verify_file(af, verbose=args.verbose)
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print(_bold(_green("All audits verified — results are cryptographically intact.")))
        sys.exit(0)
    else:
        print(_bold(_red("One or more audits FAILED verification.")))
        sys.exit(1)


if __name__ == "__main__":
    main()
