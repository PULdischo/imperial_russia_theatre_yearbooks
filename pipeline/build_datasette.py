"""Stage 6 (partial): export the `entities` research layer to a standalone
SQLite file for Datasette (Datasette doesn't read DuckDB directly). Bridges
through pandas rather than DuckDB's sqlite extension -- that extension
needs a network download of a prebuilt binary per platform, which is a
flaky external dependency for something this project can do with a
library already in use elsewhere in the pipeline (build_excel_workbook.py).

Exports the entities tables as-is, plus two joined "browsing" views
materialized as real tables (person_appearances, work_performances) --
Datasette facets/filters on live tables, not on entities.person_link's
bare foreign keys, so the joins need to already be flattened for faceting
to be useful (e.g. facet person_appearances by season or entity_type).

Usage:
    python pipeline/build_datasette.py --db outputs/full_run/imperial_theaters.duckdb \
        --out outputs/full_run/research_dataset.sqlite
"""
from __future__ import annotations

import argparse
import sqlite3
import uuid
from pathlib import Path

import duckdb


def _stringify_uuids(df):
    # sqlite3 (via pandas' to_sql) can't bind Python's uuid.UUID objects --
    # DuckDB's UUID columns come back from fetch_df() as UUID instances,
    # not strings, unlike everywhere else in this pipeline where UUIDs are
    # str()'d immediately (see build_entities.py). Cast here instead of
    # pushing CAST(... AS VARCHAR) into every query above.
    for col in df.columns:
        if df[col].dtype == object and df[col].apply(lambda v: isinstance(v, uuid.UUID)).any():
            df[col] = df[col].apply(lambda v: str(v) if isinstance(v, uuid.UUID) else v)
    return df

TABLES = ["theater", "work", "person", "person_link", "work_link", "person_candidate",
          "person_merge_log", "person_wikidata_link"]

PERSON_APPEARANCES_SQL = """
    SELECT
        r.entry_id, pl.person_id, p.display_name, p.ordinal_suffix,
        r.page_id, sp.season, sp.city, r.entity_type,
        r.heading_path, r.rank_or_title, r.service_class,
        r.instrument, r.subject_taught, r.tenure_note_text
    FROM entities.person_link pl
    JOIN entities.person p ON p.person_id = pl.person_id
    JOIN raw.roster_entry r ON r.entry_id = pl.entry_id
    JOIN raw.source_pages sp ON sp.page_id = r.page_id
"""

WORK_PERFORMANCES_SQL = """
    SELECT
        pw.work_id AS raw_work_id, wl.work_id, w.canonical_title, w.canonical_genre,
        ps.session_id, ps.page_id, ps.season, ps.city,
        ps.theater, ps.date_text, ps.month_text, ps.year_text, ps.date_undate,
        ps.session_status, ps.receipts_text
    FROM entities.work_link wl
    JOIN entities.work w ON w.work_id = wl.work_id
    JOIN raw.performance_work pw ON pw.work_id = wl.raw_work_id
    JOIN raw.performance_session ps ON ps.session_id = pw.session_id
"""

# Explicit CREATE TABLE per table/view, PRIMARY KEY + FOREIGN KEY declared --
# pandas' to_sql(if_exists="replace") would otherwise create schema-less
# tables (no PK/FK at all), which works for browsing but loses Datasette's
# best feature: clean per-record URLs and automatic clickable links between
# related tables. to_sql(if_exists="append") below only does the INSERT,
# matching columns by name against the schema created here.
SCHEMAS = {
    "theater": """
        CREATE TABLE theater (
            theater_id TEXT PRIMARY KEY, canonical_name TEXT, city TEXT,
            active_from_season TEXT
        )""",
    "work": """
        CREATE TABLE work (
            work_id TEXT PRIMARY KEY, canonical_title TEXT, canonical_genre TEXT,
            appearance_count INTEGER
        )""",
    "person": """
        CREATE TABLE person (
            person_id TEXT PRIMARY KEY, display_name TEXT, canonical_family_name TEXT,
            canonical_first_name TEXT, canonical_patronymic TEXT, ordinal_suffix TEXT,
            first_attested_season TEXT, last_attested_season TEXT, tier1_key TEXT,
            superseded_by_person_id TEXT REFERENCES person(person_id)
        )""",
    "person_link": """
        CREATE TABLE person_link (
            entry_id TEXT PRIMARY KEY, person_id TEXT REFERENCES person(person_id),
            match_method TEXT, match_confidence REAL
        )""",
    "work_link": """
        CREATE TABLE work_link (
            raw_work_id TEXT PRIMARY KEY, work_id TEXT REFERENCES work(work_id)
        )""",
    "person_candidate": """
        CREATE TABLE person_candidate (
            candidate_id TEXT PRIMARY KEY,
            person_id_1 TEXT REFERENCES person(person_id),
            person_id_2 TEXT REFERENCES person(person_id),
            display_1 TEXT, display_2 TEXT, similarity_score REAL,
            match_reason TEXT, status TEXT,
            tenure_signal TEXT, tenure_evidence TEXT
        )""",
    "person_merge_log": """
        CREATE TABLE person_merge_log (
            candidate_id TEXT PRIMARY KEY,
            person_id_1 TEXT, person_id_2 TEXT,
            display_1 TEXT, display_2 TEXT, similarity_score REAL,
            match_reason TEXT, status TEXT,
            tenure_signal TEXT, tenure_evidence TEXT
        )""",
    "person_wikidata_link": """
        CREATE TABLE person_wikidata_link (
            person_id TEXT PRIMARY KEY REFERENCES person(person_id),
            wikidata_qid TEXT, wikidata_label TEXT, wikidata_description TEXT,
            match_evidence TEXT
        )""",
    "person_appearances": """
        CREATE TABLE person_appearances (
            entry_id TEXT PRIMARY KEY, person_id TEXT REFERENCES person(person_id),
            display_name TEXT, ordinal_suffix TEXT, page_id TEXT, season TEXT, city TEXT,
            entity_type TEXT, heading_path TEXT, rank_or_title TEXT, service_class TEXT,
            instrument TEXT, subject_taught TEXT, tenure_note_text TEXT
        )""",
    "work_performances": """
        CREATE TABLE work_performances (
            raw_work_id TEXT PRIMARY KEY, work_id TEXT REFERENCES work(work_id),
            canonical_title TEXT, canonical_genre TEXT, session_id TEXT, page_id TEXT,
            season TEXT, city TEXT, theater TEXT, date_text TEXT, month_text TEXT,
            year_text TEXT, date_undate TEXT, session_status TEXT, receipts_text TEXT
        )""",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    con = duckdb.connect(str(args.db), read_only=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.unlink(missing_ok=True)  # sqlite3 won't overwrite cleanly otherwise
    sqlite_con = sqlite3.connect(str(args.out))
    sqlite_con.execute("PRAGMA foreign_keys = OFF")  # load order isn't dependency-safe; enforce later if ever needed

    # person and work first -- everything else's FK declaration references them,
    # and sqlite3 (even with foreign_keys off) still validates the referenced
    # table exists at CREATE TABLE time.
    ordered = ["person", "work"] + [t for t in SCHEMAS if t not in ("person", "work")]
    for table in ordered:
        sqlite_con.execute(SCHEMAS[table])

    for table in TABLES:
        exists = con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'entities' AND table_name = ?",
            [table],
        ).fetchone()
        if not exists:
            # person_wikidata_link (and, on an older db, person_merge_log) are
            # created by their own separate scripts, not build_entities.py's
            # core rebuild -- an empty sqlite table still gets created above
            # so the schema/relationships stay stable either way.
            print(f"{table}: 0 rows (entities.{table} doesn't exist in the source db yet)")
            continue
        df = _stringify_uuids(con.execute(f"SELECT * FROM entities.{table}").fetch_df())
        df.to_sql(table, sqlite_con, index=False, if_exists="append")
        print(f"{table}: {len(df)} rows")

    for name, sql in [("person_appearances", PERSON_APPEARANCES_SQL),
                       ("work_performances", WORK_PERFORMANCES_SQL)]:
        df = _stringify_uuids(con.execute(sql).fetch_df())
        df.to_sql(name, sqlite_con, index=False, if_exists="append")
        print(f"{name}: {len(df)} rows (joined view)")

    sqlite_con.commit()
    sqlite_con.close()
    con.close()
    print(f"\n{args.out} ready for Datasette")


if __name__ == "__main__":
    main()
