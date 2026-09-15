"""Carry person identity across a page_id relabel, BEFORE re-running
build_entities.py.

build_person_tier1 reuses person UUIDs by entry membership: "which person_id
is this exact entry_id linked to in entities.person_link right now" (the #41
continuity fix). That survives any change to name-cleaning logic, but not a
change to the entry_id itself -- a relabelled entry looks like never-seen raw
data, gets a fresh UUID, and every merge decision ever made against its old
person is orphaned. Confirmed on the 1899-90/1905-07 season-typo fix
(docs/eval/known_issues.md #71): a rebuild without this step split 20
reviewed people in two.

entry_ids embed page_id (`<page_id>__eNNN`), so a page relabel is a pure
1:1 string rename of the page_id prefix. entities.person_link is the only
table carrying entry_ids that survives a rebuild (merge log and candidate
queue are keyed on person_id; raw/analysis are regenerated from the parsed
CSVs), so it is the only thing rewritten here.

Usage (run against a COPY of the production DB, then build_duckdb.py ->
build_entities.py -> validate_performance_dates.py -> build_research_model.py):
    python pipeline/remap_entry_ids.py --db outputs/<run>/imperial_theaters.duckdb \
        --rename theaterschoolstaff_1899-90_:theaterschoolstaff_1899-00_ \
        --rename theaterschoolstaff_1905-07_:theaterschoolstaff_1905-06_
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--rename", action="append", required=True, metavar="OLD_PREFIX:NEW_PREFIX",
                     help="page_id prefix rename, e.g. theaterschoolstaff_1905-07_:theaterschoolstaff_1905-06_")
    args = ap.parse_args()

    con = duckdb.connect(str(args.db))
    for spec in args.rename:
        old, new = spec.split(":")
        n_old = con.execute("SELECT count(*) FROM entities.person_link WHERE starts_with(entry_id, ?)",
                            [old]).fetchone()[0]
        n_clash = con.execute("SELECT count(*) FROM entities.person_link WHERE starts_with(entry_id, ?)",
                              [new]).fetchone()[0]
        if n_clash:
            raise SystemExit(f"{n_clash} entry_id(s) already start with {new!r} -- refusing to merge two pages")
        con.execute("""
            UPDATE entities.person_link
            SET entry_id = ? || substr(entry_id, length(?) + 1)
            WHERE starts_with(entry_id, ?)
        """, [new, old, old])
        print(f"entities.person_link: {n_old} entry_id(s) {old}* -> {new}*")
    con.close()


if __name__ == "__main__":
    main()
