"""Stage 6: export the `research` schema -- the final, simplified,
directly-queryable layer (pipeline/build_research_model.py,
docs/entity_centric_model.md) -- to a standalone SQLite file for Datasette
(Datasette doesn't read DuckDB directly). Bridges through pandas rather
than DuckDB's sqlite extension -- that extension needs a network download
of a prebuilt binary per platform, which is a flaky external dependency
for something this project can do with a library already in use elsewhere
in the pipeline (build_excel_workbook.py).

This got simpler, not more complex, once the `research` schema landed
(exactly as docs/entity_centric_model.md predicted it would): every table
here is a straight copy, no query-time joins needed at all, because
`research.event`/`research.performance` already have their foreign keys
baked in. The working `entities` schema (crosswalks, review queues,
merge logs) is deliberately NOT exported here -- it's the pipeline's own
internal/audit layer, not the published research artifact. Anyone who
needs it can still query the DuckDB file directly.

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


TABLES = ["theater", "work", "person", "event", "performance", "person_appearance"]

# Explicit CREATE TABLE per table, PRIMARY KEY + FOREIGN KEY declared --
# pandas' to_sql(if_exists="replace") would otherwise create schema-less
# tables (no PK/FK at all), which works for browsing but loses Datasette's
# best feature: clean per-record URLs and automatic clickable links
# between related tables. to_sql(if_exists="append") below only does the
# INSERT, matching columns by name against the schema created here.
SCHEMAS = {
    "theater": """
        CREATE TABLE theater (
            theater_id TEXT PRIMARY KEY, canonical_name TEXT, city TEXT,
            active_from_season TEXT
        )""",
    "work": """
        CREATE TABLE work (
            work_id TEXT PRIMARY KEY, canonical_title TEXT, canonical_genre TEXT,
            appearance_count INTEGER, excerpt_of_work_id TEXT REFERENCES work(work_id),
            excerpt_note TEXT
        )""",
    "person": """
        CREATE TABLE person (
            person_id TEXT PRIMARY KEY, display_name TEXT, canonical_family_name TEXT,
            canonical_first_name TEXT, canonical_patronymic TEXT, ordinal_suffix TEXT,
            first_attested_season TEXT, last_attested_season TEXT,
            wikidata_qid TEXT, wikidata_label TEXT, wikidata_description TEXT
        )""",
    "event": """
        CREATE TABLE event (
            event_id TEXT PRIMARY KEY, theater_id TEXT REFERENCES theater(theater_id),
            season TEXT, city TEXT, date_verbatim TEXT, date_undate TEXT,
            date TEXT, date_confidence TEXT, event_status TEXT,
            receipts_total_kopecks INTEGER
        )""",
    "performance": """
        CREATE TABLE performance (
            performance_id TEXT PRIMARY KEY, event_id TEXT REFERENCES event(event_id),
            work_id TEXT REFERENCES work(work_id), performance_order TEXT,
            verbatim_title TEXT, verbatim_genre TEXT
        )""",
    "person_appearance": """
        CREATE TABLE person_appearance (
            appearance_id TEXT PRIMARY KEY, person_id TEXT REFERENCES person(person_id),
            season TEXT, city TEXT, entity_type TEXT, institution TEXT,
            heading_path TEXT, rank_or_title TEXT, service_class TEXT,
            instrument TEXT, subject_taught TEXT, tenure_note_text TEXT
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

    # theater/work/person first -- event/performance/person_appearance's
    # FK declarations reference them, and sqlite3 (even with foreign_keys
    # off) still validates the referenced table exists at CREATE TABLE time.
    ordered = ["theater", "work", "person"] + [t for t in TABLES if t not in ("theater", "work", "person")]
    for table in ordered:
        sqlite_con.execute(SCHEMAS[table])

    for table in TABLES:
        exists = con.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'research' AND table_name = ?",
            [table],
        ).fetchone()
        if not exists:
            # research.* is built by pipeline/build_research_model.py, a
            # separate script -- an empty sqlite table still gets created
            # above so the schema/relationships stay stable either way.
            print(f"{table}: 0 rows (research.{table} doesn't exist in the source db yet)")
            continue
        df = _stringify_uuids(con.execute(f"SELECT * FROM research.{table}").fetch_df())
        df.to_sql(table, sqlite_con, index=False, if_exists="append")
        print(f"{table}: {len(df)} rows")

    sqlite_con.commit()
    sqlite_con.close()
    con.close()
    print(f"\n{args.out} ready for Datasette")


if __name__ == "__main__":
    main()
