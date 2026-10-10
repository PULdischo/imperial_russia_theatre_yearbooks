"""Apply the decisions a human wrote into the Wikidata review queue.

`link_wikidata.py` exports every candidate it would not accept on its own to
`wikidata_review_queue.csv` with a blank `decision (QID or No)` column -- and
until now nothing read that column back, so filling it in achieved nothing.
The August 2026 export sat with 221 rows and 0 decisions, which is very
likely why.

Two things happen here, and the second matters as much as the first:

**Accepted** rows go into `entities.person_wikidata_link`, the same table the
linker's own auto-accepts land in, so `build_research_model.py` picks them up
into `research.person.wikidata_qid` with no further change.

**Rejected** rows are RECORDED, in `entities.wikidata_decision`. The linker
skips anyone already linked but had no memory of a rejection, so every re-run
re-queried the same people and re-offered the same wrong candidate. A "No" is
a real finding and has to persist; `link_wikidata.py` now consults this table.

Append-only and re-runnable: a decision already recorded is left alone, so the
same CSV can be applied twice without duplicating anything.

Usage:
    uv run python pipeline/apply_wikidata_decisions.py \
        --db outputs/full_run/imperial_theaters.duckdb \
        --queue outputs/full_run/wikidata_review_queue.csv
    # --dry-run to see what would change
"""
from __future__ import annotations

import argparse
import csv
import datetime
from pathlib import Path

import duckdb

csv.field_size_limit(10_000_000)
DECISION_COL = "decision (QID or No)"

DDL = """
CREATE TABLE IF NOT EXISTS entities.wikidata_decision (
    person_id        VARCHAR NOT NULL,
    candidate_qid    VARCHAR,
    decision         VARCHAR NOT NULL,   -- a QID, or 'No'
    decided_on       VARCHAR NOT NULL,
    note             VARCHAR
)
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--queue", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    con = duckdb.connect(str(a.db))
    con.execute("CREATE SCHEMA IF NOT EXISTS entities")
    con.execute(DDL)
    con.execute("""
        CREATE TABLE IF NOT EXISTS entities.person_wikidata_link (
            person_id VARCHAR, wikidata_qid VARCHAR, wikidata_label VARCHAR,
            wikidata_description VARCHAR, match_evidence VARCHAR)
    """)

    with open(a.queue, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if DECISION_COL not in (rows[0].keys() if rows else {}):
        raise SystemExit(f"{a.queue} has no {DECISION_COL!r} column")

    linked = {str(r[0]) for r in
              con.execute("SELECT person_id FROM entities.person_wikidata_link").fetchall()}
    decided = {(str(r[0]), r[1]) for r in
               con.execute("SELECT person_id, decision FROM entities.wikidata_decision").fetchall()}
    today = datetime.date.today().isoformat()

    accepted = rejected = skipped = 0
    for r in rows:
        pid = (r.get("person_id") or "").strip()
        d = (r.get(DECISION_COL) or "").strip()
        if not pid or not d:
            continue
        if (pid, d) in decided:
            skipped += 1
            continue
        note = (r.get("reason") or "")
        if d.lower() in ("no", "none", "n"):
            if not a.dry_run:
                con.execute("INSERT INTO entities.wikidata_decision VALUES (?,?,?,?,?)",
                            [pid, r.get("candidate_qid"), "No", today, note])
            rejected += 1
            continue
        if not d.upper().startswith("Q"):
            print(f"  ! {r.get('display_name')}: decision {d!r} is neither a QID nor 'No', skipped")
            continue
        qid = d.upper()
        if pid in linked:
            print(f"  = {r.get('display_name')}: already linked, decision not re-applied")
            skipped += 1
            continue
        # label/description come from the row when the decision matches the
        # candidate offered; a human-supplied different QID carries neither,
        # and build_research_model tolerates nulls there.
        same = (r.get("candidate_qid") or "").upper() == qid
        if not a.dry_run:
            con.execute("INSERT INTO entities.person_wikidata_link VALUES (?,?,?,?,?)",
                        [pid, qid,
                         r.get("candidate_label") if same else None,
                         r.get("candidate_description") if same else None,
                         f"human decision from the review queue ({note})"])
            con.execute("INSERT INTO entities.wikidata_decision VALUES (?,?,?,?,?)",
                        [pid, r.get("candidate_qid"), qid, today, note])
        linked.add(pid)
        accepted += 1

    verb = "would be" if a.dry_run else ""
    print(f"{accepted} link(s) {verb} accepted -> entities.person_wikidata_link")
    print(f"{rejected} rejection(s) {verb} recorded -> entities.wikidata_decision")
    if skipped:
        print(f"{skipped} row(s) already applied, left alone")
    if not a.dry_run and accepted:
        print("\nRe-run build_research_model.py to surface these in research.person.")
    con.close()


if __name__ == "__main__":
    main()
