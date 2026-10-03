"""Link the ballet productions lists' creator credits to persons (issue #133, step 2).

Inputs (hand-curated, versioned in git):
    pipeline/entity_curation/production_creators.csv
        one row per creator: creator_key, display_name (nominative, pre-reform;
        only for creators NOT on the roster), roster_person_id, roster_link_status,
        evidence
    pipeline/entity_curation/production_creator_forms.csv
        one row per printed form: name_printed, role_category (blank = any role;
        set only where the same printed form is two people, e.g. "Перро" as
        author = Jules Perrot vs as source = Charles Perrault), creator_key,
        form_status, evidence

Outputs (entities schema, additive, CREATE OR REPLACE on these two tables only):
    entities.creator_person         creators who are NOT linked to a roster person.
                                    person_id = uuid5(NAMESPACE, "production_creator:<key>"),
                                    so it is stable across re-runs. Kept outside
                                    entities.person on purpose: build_entities.py
                                    rebuilds that table from roster entries only and
                                    would drop anyone it can't see.
    entities.production_credit_link one row per non-group credit -> person_id
                                    (a roster person, or a creator_person).

Status values (never silently upgraded):
    form_status          confirmed: the printed form is a case or initial variant of
                                    the same creator on the same or continuing works.
                         proposed:  a plausible identification that RG has not ruled
                                    on yet (Гершеля = Гертель?, К. В. = Вальцъ?, …).
    roster_link_status   confirmed: initials and job agree with a single roster person.
                         rg_identified: RG's identification (Г⁂ = Всеволожскій).
                         proposed:  initials agree but the identity is unconfirmed;
                                    the creator stays a creator_person, with
                                    proposed_roster_person_id recorded.

A roster person_id that has since been superseded (merged) is followed to its
survivor. A roster person_id that no longer exists is an error.

Usage:
    python pipeline/link_production_creators.py --db outputs/full_run/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
import csv
import uuid
from pathlib import Path

import duckdb

from build_entities import NAMESPACE

CUR = Path(__file__).parent / "entity_curation"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()

    creators = {r["creator_key"]: r for r in csv.DictReader(open(CUR / "production_creators.csv"))}
    forms = list(csv.DictReader(open(CUR / "production_creator_forms.csv")))
    by_form = {(f["name_printed"], f["role_category"]): f for f in forms}

    con = duckdb.connect(str(args.db))
    superseded = dict(con.execute(
        "SELECT person_id::VARCHAR, superseded_by_person_id::VARCHAR FROM entities.person").fetchall())

    def resolve(pid: str) -> str:
        if pid not in superseded:
            raise SystemExit(f"roster person_id {pid} not in entities.person")
        seen = set()
        while superseded.get(pid):
            if pid in seen:
                raise SystemExit(f"supersede cycle at {pid}")
            seen.add(pid)
            pid = superseded[pid]
        return pid

    creator_rows, creator_pid = [], {}
    for k, c in creators.items():
        roster_ok = c["roster_person_id"] and c["roster_link_status"] in ("confirmed", "rg_identified")
        if roster_ok:
            creator_pid[k] = (resolve(c["roster_person_id"]), "roster")
        else:
            pid = str(uuid.uuid5(NAMESPACE, f"production_creator:{k}"))
            creator_pid[k] = (pid, "creator")
            proposed = resolve(c["roster_person_id"]) if c["roster_person_id"] else None
            creator_rows.append((pid, k, c["display_name"], proposed, c["evidence"] or None))

    credits = con.execute("""
        SELECT credit_id, name_printed, role_category FROM analysis.production_entry_credit
        WHERE NOT is_collective ORDER BY credit_id""").fetchall()
    link_rows, unmapped = [], []
    for credit_id, name, role in credits:
        f = by_form.get((name, role)) or by_form.get((name, ""))
        if f is None:
            unmapped.append((name, role))
            continue
        k = f["creator_key"]
        pid, src = creator_pid[k]
        link_rows.append((credit_id, pid, k, src, f["form_status"],
                          creators[k]["roster_link_status"] or None))
    if unmapped:
        raise SystemExit(f"unmapped printed forms (add to production_creator_forms.csv): {sorted(set(unmapped))}")

    con.execute("""
        CREATE OR REPLACE TABLE entities.creator_person (
            person_id UUID PRIMARY KEY,
            creator_key VARCHAR NOT NULL UNIQUE,
            display_name VARCHAR NOT NULL,
            proposed_roster_person_id UUID,
            evidence VARCHAR)""")
    con.executemany("INSERT INTO entities.creator_person VALUES (?, ?, ?, ?, ?)", creator_rows)
    con.execute("""
        CREATE OR REPLACE TABLE entities.production_credit_link (
            credit_id VARCHAR PRIMARY KEY,
            person_id UUID NOT NULL,
            creator_key VARCHAR NOT NULL,
            link_source VARCHAR NOT NULL,      -- 'roster' (entities.person) | 'creator' (entities.creator_person)
            form_status VARCHAR NOT NULL,      -- confirmed | proposed
            roster_link_status VARCHAR)""")
    con.executemany("INSERT INTO entities.production_credit_link VALUES (?, ?, ?, ?, ?, ?)", link_rows)

    n_roster = sum(1 for r in link_rows if r[3] == "roster")
    print(f"entities.creator_person: {len(creator_rows)} creators not linked to the roster "
          f"({sum(1 for r in creator_rows if r[3])} with a proposed roster match)")
    print(f"entities.production_credit_link: {len(link_rows)} credits -> "
          f"{len({r[1] for r in link_rows})} persons; {n_roster} credits to roster persons "
          f"({len({r[1] for r in link_rows if r[3] == 'roster'})} people); "
          f"{sum(1 for r in link_rows if r[4] == 'proposed')} credits via a proposed form")
    con.close()


if __name__ == "__main__":
    main()
