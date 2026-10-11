#!/usr/bin/env python3
"""People the ballet reviews name whom no people list in the corpus carries.

A third people source, after the rosters (`entities.person`) and the ballet
production lists (`entities.creator_person`, issue #133). Same shape as the
creators: a UUID5 id, a stable key, a display name, and the evidence that
put them here. They land in `research.person` with
`person_source = 'review'`.

Who qualifies, and who does NOT
-------------------------------
Only the rows of `docs/eval/review_people_not_in_rosters.csv` carrying the
`D current-season dancer, absent` verdict -- a gender contradiction against
the only family the database holds, confirmed current-season, and
**checked against the page scan one by one**. That check is not a
formality: of the sixteen names the hand-built worklist put in bucket D,
seven turned out to be something else entirely --

  * `Рождественская`  a 1912-13 graduate (the Спесивцева class), so she
                      joins the stage AFTER the last roster we hold
  * `Петровскій`      drama-review bleed above the ballet heading
  * `Кусковъ`         a genuine print typo for `Кусовъ`
  * `Шульгина`        a retrospective on «Наяда» (1843)
  * `Лядова`          a retrospective on an older «Конекъ-горбунокъ»
  * `Харитонова`, `Зыбина`
                      the drama cast of the féerie «Кольцо любви»

so minting entities straight off the worklist would have invented seven
dancers who never existed.

These records are thin on purpose: a surname and, where printed, an
ordinal. No first name, no patronymic -- the reviews print none. They will
not merge cleanly with a roster person later without new evidence, which
is the honest state of the knowledge.

    uv run python pipeline/build_review_persons.py --db <db>
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import uuid
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from build_entities import NAMESPACE                      # noqa: E402
from match_review_mentions import key_of                  # noqa: E402

csv.field_size_limit(10 ** 9)

#: The APPROVED list, append-only and persistent. Deliberately NOT the
#: triage worklist: the moment a person is created their mentions resolve,
#: so they drop off that worklist -- and a second run would then delete
#: them. (Found the hard way on 2026-10-11, when re-running cut the eight
#: existing dancers down to three.) The worklist decides WHO qualifies; this
#: file records who was approved, and the facts come from the database.
APPROVED = Path("docs/eval/review_person_approved.csv")
ORDINAL = re.compile(r"\s*(\d+)\s*-?\s*([ейя])\s*$")


def split_name(printed: str) -> tuple[str, str | None]:
    """Family name and ordinal suffix, as the review prints them."""
    m = ORDINAL.search(printed)
    if m:
        return printed[: m.start()].strip(), f"{m.group(1)}-{m.group(2)}"
    return printed.strip(), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--approved", default=APPROVED, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    names = [(r["printed_in_review"], r["evidence"])
             for r in csv.DictReader(open(a.approved, encoding="utf-8"))
             if r.get("printed_in_review")]

    con = duckdb.connect(a.db, read_only=a.dry_run)
    out = []
    for printed, evidence in names:
        fam, ordinal = split_name(printed)
        key = key_of(printed)
        pid = str(uuid.uuid5(NAMESPACE, f"review_person:{key}"))
        facts = con.execute("""
            SELECT min(season), max(season), string_agg(DISTINCT city, '|'),
                   count(*), string_agg(DISTINCT page_id, '|')
            FROM entities.review_mention
            WHERE mention_type = 'person' AND surface = ?
        """, [printed]).fetchone()
        if not facts or facts[3] == 0:
            raise SystemExit(f"{printed!r} has no mentions -- refusing to mint a "
                             f"person with no evidence in the corpus")
        out.append((pid, key, printed, fam, ordinal, facts[0], facts[1],
                    facts[2], facts[3], facts[4], "", evidence))

    if a.dry_run:
        print(f"{len(out)} review-only person(s) would be created:\n")
        for o in out:
            print(f"  {o[2]:16s} {o[5]}–{o[6]} {o[7]:8s} x{o[8]:<2} {o[0]}")
        return 0

    con.execute("""
        CREATE OR REPLACE TABLE entities.review_person (
            person_id UUID PRIMARY KEY,
            review_key VARCHAR NOT NULL UNIQUE,
            printed_form VARCHAR NOT NULL,
            canonical_family_name VARCHAR NOT NULL,
            ordinal_suffix VARCHAR,
            first_attested_season VARCHAR NOT NULL,
            last_attested_season VARCHAR NOT NULL,
            cities VARCHAR,
            n_mentions INTEGER,
            pages VARCHAR,
            same_family_in_db VARCHAR,
            evidence VARCHAR)""")
    con.executemany(
        "INSERT INTO entities.review_person VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", out)
    print(f"entities.review_person: {len(out)} people the reviews name and no "
          f"people list in the corpus carries")
    for o in out:
        print(f"  {o[2]:16s} {o[5]}–{o[6]}  {o[7]:8s} x{o[8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
