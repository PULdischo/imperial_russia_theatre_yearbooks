#!/usr/bin/env python3
"""Works the ballet reviews name that the Repertoire never staged (1890-1911).

The work-side counterpart of `build_review_persons.py`: ballets, operas and
concert pieces a critic names -- Фокинъ's «Papillons» and «Исламей» after the
Repertoire's last season, Perrot's ballet «Фаустъ», Milon's 1855 «Свадьба
Гамаша», Tchaikovsky's «Коронаціонная кантата» -- so their mentions can link
and later be connected to the repertoire works they bear on (RG, 2026-10-26).
Literary and artistic sources («Quo vadis?», Andersen's «Свинопасъ», Léopold
Robert's paintings) are deliberately NOT works here (RG: "leave the literary
and artistic sources alone").

They land in `research.work` with `work_source = 'review'` and
`appearance_count = 0`, so performance counts never see them. Their mentions
are linked by explicit rows in docs/eval/review_work_mention_links.csv, never
by title: a ballet «Фаустъ» must not capture mentions of Gounod's opera.

    uv run python pipeline/build_review_works.py --db <db>
"""
from __future__ import annotations

import argparse
import csv
import sys
import uuid
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
from build_entities import NAMESPACE                      # noqa: E402
from match_review_mentions import key_of                  # noqa: E402

#: The APPROVED list, append-only: one row per work, with the review evidence.
APPROVED = Path("docs/eval/review_work_approved.csv")


def work_id(title: str, kind: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"review_work:{kind}:{key_of(title)}"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--approved", default=APPROVED, type=Path)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.approved, encoding="utf-8")))
    out = [(work_id(r["canonical_title"], r["work_kind"]), r["canonical_title"], r["canonical_genre"],
            r["work_kind"], r["evidence"]) for r in rows]
    if len({o[0] for o in out}) != len(out):
        raise SystemExit("review_work_approved.csv: duplicate title/kind")
    con = duckdb.connect(a.db)
    con.execute("""
        CREATE OR REPLACE TABLE entities.review_work (
            work_id UUID PRIMARY KEY,
            canonical_title VARCHAR NOT NULL,
            canonical_genre VARCHAR,
            work_kind VARCHAR NOT NULL,
            evidence VARCHAR NOT NULL)""")
    con.executemany("INSERT INTO entities.review_work VALUES (?,?,?,?,?)", out)
    print(f"entities.review_work: {len(out)} works the reviews name and the Repertoire never staged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
