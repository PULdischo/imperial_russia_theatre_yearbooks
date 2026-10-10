#!/usr/bin/env python3
"""Apply scan-verified transcription corrections to the merged review text.

Why this exists as a re-runnable step rather than a hand-edit
-------------------------------------------------------------
The 2026-10-07 mixed-script repairs were applied directly to
`merged_full/review_block.csv` after the merge, which meant a re-merge
silently discarded them -- the lesson recorded at the time was "a re-merge
will NOT reproduce it, always diff a rebuild". This script closes that gap:
the corrections live in a CSV under docs/eval/, and rebuilding the review
text layer is `merge, then run this`. Running it twice is a no-op.

These are NOT rules and NOT a character mapping. Every row was taken by
looking at the page -- see the `evidence` column, and
docs/eval/review_caption_quality.md for why the caption layer needs them.
A correction here restores what the volume actually prints; it never
normalises away a spelling the print really carries. (`Талорачва` in a
p005 caption against `Толорагва` in the p020 body is genuine source
variation and is deliberately absent from the table.)

    uv run python pipeline/apply_review_text_corrections.py \
        --blocks outputs/reviews/merged_full/review_block.csv
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

csv.field_size_limit(10 ** 9)

CORRECTIONS = Path("docs/eval/review_text_corrections.csv")
FIELDS = ("text", "caption_text")


def load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", required=True, type=Path)
    ap.add_argument("--corrections", default=CORRECTIONS, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rules = load(a.corrections)
    with open(a.blocks, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = list(reader)

    total, failures = 0, []
    for rule in rules:
        find, repl = rule["find"], rule["replace"]
        prefix, expected = rule["scope_page_prefix"], int(rule["expected"])
        n, pages = 0, set()
        for r in rows:
            if not r["page_id"].startswith(prefix):
                continue
            for fld in FIELDS:
                v = r.get(fld) or ""
                if find in v:
                    n += v.count(find)
                    pages.add(r["page_id"])
                    if not a.dry_run:
                        r[fld] = v.replace(find, repl)
        total += n
        status = "ok" if n == expected else ("ALREADY APPLIED" if n == 0 else "COUNT MISMATCH")
        # A mismatch means the text moved under the correction: re-check the
        # scan before forcing it through, never just update `expected`.
        if n not in (expected, 0):
            failures.append((find, repl, expected, n))
        print(f"  {find!r} -> {repl!r}  [{prefix}]  {n}/{expected} on "
              f"{len(pages)} page(s)  {status}")

    if failures:
        print("\nCOUNT MISMATCH -- nothing written. Re-check the scan:", file=sys.stderr)
        for find, repl, exp, got in failures:
            print(f"  {find!r} -> {repl!r}: expected {exp}, found {got}", file=sys.stderr)
        return 1

    if a.dry_run:
        print(f"\ndry run: {total} replacement(s) would be made")
        return 0

    if total:
        shutil.copy2(a.blocks, a.blocks.with_suffix(".csv.bak"))
        with open(a.blocks, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"\n{total} replacement(s) written to {a.blocks} "
              f"(previous copy at {a.blocks.with_suffix('.csv.bak')})")
    else:
        print("\nnothing to do -- every correction is already applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
