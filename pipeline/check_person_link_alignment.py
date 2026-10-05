"""Gold-free integrity check: is every entities.person_link row attached to a
person whose name matches the entry it is attached to?

Why this exists (docs/eval/known_issues.md, issue #131): entities.person_link is
keyed by entry_id (`<page_id>__eNNN`), and `eNNN` is just a row's position in
the page's raw JSON `entries` array. If a row is inserted into or removed from
the MIDDLE of a page's array after the links were made, every later row on the
page silently inherits the previous row's person -- no error, no flag, and
the whole tail of the page points at the wrong people. build_entities.py keeps
links by entry_id, so the damage survives every rebuild. Found by accident
while inserting a dropped conductor row (2026-10-02): four pages already had
a whole tail shifted by one.

What it reports:
  SHIFT BLOCK (error, exit code 1): a run of >= MIN_RUN consecutive entries on
    one page where each entry's name does NOT match its own person but DOES
    match the person linked to a NEIGHBOURING entry -- the next one (the
    "inherits the previous row's person" signature of the bug above, i.e. a
    row was removed or links were not renumbered) or the previous one (the
    mirror image: each row carries the person of the row AFTER it, which is
    what an insertion above the block, or a realign applied in the wrong
    direction, leaves behind; found on theaterschoolstaff_1896-97_p000
    e013-e022, 2026-10-05, because the first version of this check looked in
    one direction only and reported 0 blocks).
  Other name mismatches (informational): spelling variants that were merged on
    purpose, or something else wrong -- worth a look, not necessarily a bug.

Rule for raw edits (so this stays clean): after any insertion/removal in a
page's `entries` array, either append at the END of the array, or renumber
entities.person_link for the shifted rows BEFORE running build_entities.py; for
an inserted row, pre-seed its link to the intended existing person (an
unlinked entry is otherwise given a brand-new person UUID and the long-lived
person is tombstoned in its favour).

Usage:
    python pipeline/check_person_link_alignment.py --db outputs/full_run/imperial_theaters.duckdb \
        [--out outputs/full_run/person_link_alignment.csv]
"""
from __future__ import annotations

import argparse
import csv
import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

import duckdb

MIN_RUN = 3          # consecutive shifted entries needed to call it a shift block
NAME_MATCH = 0.75    # family-name similarity at/above which a link is "name-consistent"


def _norm(s: str | None) -> str:
    s = (s or "").lower()
    for a, b in (("ъ", ""), ("ь", ""), ("ѣ", "е"), ("і", "и"), ("ѳ", "ф"), ("ё", "е")):
        s = s.replace(a, b)
    s = re.sub(r"\d-?[йя]", "", s)          # ordinal suffixes: "1-й", "2-я"
    return re.sub(r"[^а-яa-z]", "", s)


def _sim(a: str | None, b: str | None) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def load(con) -> dict[str, list[tuple]]:
    rows = con.execute("""
        SELECT l.entry_id, e.page_id, e.family_name, e.first_name, e.list_number,
               l.person_id, p.canonical_family_name, p.canonical_first_name
        FROM entities.person_link l
        JOIN raw.person_entry e USING (entry_id)
        JOIN entities.person p ON p.person_id = l.person_id
    """).fetchall()
    pages: dict[str, list[tuple]] = defaultdict(list)
    for r in rows:
        pages[r[1]].append(r)
    for rs in pages.values():
        rs.sort(key=lambda r: int(r[0].rsplit("__e", 1)[1]))
    return pages


def find_shift_blocks(rs: list[tuple], step: int = 1) -> list[tuple[int, int]]:
    """Return (start, end) index pairs of runs where entry i matches the person of
    entry i+step (step=+1: persons lag one row behind the entries; step=-1: persons
    run one row ahead of the entries) but not its own."""
    flags = []
    for i, r in enumerate(rs):
        own = _sim(r[2], r[6]) >= NAME_MATCH
        j = i + step
        nxt = 0 <= j < len(rs) and _sim(r[2], rs[j][6]) >= NAME_MATCH
        flags.append((not own) and nxt)
    blocks, i = [], 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            if j - i + 1 >= MIN_RUN:
                blocks.append((i, j + 1) if step > 0 else (i - 1, j))   # the entry with no person of its own sits at the far end
            i = j + 1
        else:
            i += 1
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=None, help="write every name-mismatched link to this CSV")
    args = ap.parse_args()

    con = duckdb.connect(str(args.db), read_only=True)
    pages = load(con)
    n_links = sum(len(v) for v in pages.values())

    shift_blocks, mismatches = [], []
    for page, rs in sorted(pages.items()):
        for r in rs:
            if _sim(r[2], r[6]) < NAME_MATCH:
                mismatches.append(r)
        for step in (1, -1):
            for s, e in find_shift_blocks(rs, step):
                s, e = max(s, 0), min(e, len(rs) - 1)
                shift_blocks.append((page, rs[s][0], rs[e][0], e - s + 1))

    print(f"person_link: {n_links} links checked; {len(mismatches)} name-mismatched "
          f"(informational); {len(shift_blocks)} SHIFT BLOCK(S)")
    for page, first, last, n in shift_blocks:
        print(f"  ERROR shift block on {page}: {first.rsplit('__', 1)[1]}..{last.rsplit('__', 1)[1]} "
              f"({n} entries each carrying a neighbouring entry's person)")
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["entry_id", "page_id", "entry_family", "entry_first", "list_number",
                        "person_id", "person_family", "person_first"])
            w.writerows(mismatches)
        print(f"  mismatch list -> {args.out}")
    return 1 if shift_blocks else 0


if __name__ == "__main__":
    sys.exit(main())
