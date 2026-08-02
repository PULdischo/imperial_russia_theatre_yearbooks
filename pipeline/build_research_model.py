"""Stage 6a: builds a `research` schema -- the final, simplified,
directly-queryable layer docs/entity_centric_model.md proposed: Person,
Work, Theater, Session, Performance, Person_appearance, with foreign keys
baked in directly rather than crosswalked at query time. This is the
layer meant to be published/browsed. The working `entities` schema
(person_link, work_link, person_candidate, person_merge_log,
person_wikidata_link, work_genre_candidate) is untouched by this script --
it stays exactly as it is, the pipeline's own audit/working layer
underneath, same relationship `entities` itself has to `raw`/`analysis`.

Six tables, six decisions each already made and checked against the real
data before building (docs/entity_centric_model.md, and the conversation
that resolved its two open questions):

- `person`: only currently-active (non-superseded) people -- the merge
  decision itself (`superseded_by_person_id`, `person_merge_log`) is
  pipeline history, not something a researcher browsing the final table
  needs to see. `wikidata_qid`/`wikidata_label`/`wikidata_description`
  are inlined directly (1:1 today, so no separate link table is needed)
  rather than kept as their own table.
- `work`: unchanged from entities.work -- already the clean output of
  docs/work_normalization.md.
- `theater`: unchanged from entities.theater.
- `session` kept distinct from `performance` deliberately: 6,158 of
  17,345 sessions (35%) list more than one work, and receipts are printed
  once per session, not once per work -- flattening them into one row per
  (work, session) would silently duplicate receipts on every multi-work
  night. Receipts live ONLY on `session`, so `SUM(receipts_total_kopecks)`
  over `session` is always safe; `performance` never carries receipts at
  all, precisely so summing it can't overcount.
- `session.date` is the best-available date: the run-corroborated
  correction from docs/performance_normalization.md when there is one,
  otherwise the original computed date. `date_confidence` always travels
  alongside it (never silently hidden), including a distinct
  'synthesized_gap' value for the not_captured completeness placeholders
  analysis.performance_session already synthesizes -- those never went
  through date validation (they have no real printed date_text to
  validate against) and calling them 'unparseable' would misrepresent a
  deliberate completeness signal as a data-quality failure.
- `performance`'s own PK is `performance_id`, not `work_id` --
  raw.performance_work's own PK is also (confusingly) named `work_id`,
  and reusing it here would collide with entities.work.work_id's
  different meaning (the exact collision docs/entity_centric_model.md
  flagged and this project already worked around once by aliasing to
  `raw_work_id` in build_datasette.py's joined views).
- `person_appearance` kept as its own table (not folded into `person` as
  a nested column, not merged into `performance`): a roster appearance is
  a season-level employment fact, not tied to a specific work performance
  at all, and a person can have many of them -- a real many-to-many
  relationship between person and their printed appearances, not a
  property of the person record itself.

Usage:
    python pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def build_research_model(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS research")

    # Drop in FK-dependency order (performance/person_appearance/session
    # depend on person/work/theater) so CREATE OR REPLACE below never
    # trips the same "blocked by a dependent table" issue build_entities.py
    # already documents for entities.person/entities.work. DuckDB has no
    # ALTER TABLE ADD FOREIGN KEY (confirmed by hitting
    # NotImplementedException directly) -- every constraint here has to be
    # declared inline on CREATE TABLE, so each table is CREATEd with its
    # full schema first and populated via a separate INSERT INTO ... SELECT,
    # same two-step pattern build_entities.py already uses.
    for t in ["performance", "session", "person_appearance", "person", "work", "theater"]:
        con.execute(f"DROP TABLE IF EXISTS research.{t}")

    con.execute("""
        CREATE TABLE research.theater (
            theater_id UUID PRIMARY KEY,
            canonical_name VARCHAR,
            city VARCHAR,
            active_from_season VARCHAR
        )
    """)
    con.execute("INSERT INTO research.theater SELECT * FROM entities.theater")

    con.execute("""
        CREATE TABLE research.work (
            work_id UUID PRIMARY KEY,
            canonical_title VARCHAR,
            canonical_genre VARCHAR,
            appearance_count INTEGER,
            excerpt_of_work_id UUID,
            excerpt_note VARCHAR
        )
    """)
    # excerpt_of_work_id deliberately has no REFERENCES clause -- same
    # reasoning as entities.work: it's self-referential, and DuckDB's FK
    # enforcement rejects a later UPDATE on a table whose PK has any
    # incoming FK. Not an issue here (this is a single INSERT, not an
    # UPDATE), but kept consistent with entities.work's own schema so a
    # future change to one doesn't silently diverge from the other.
    con.execute("INSERT INTO research.work SELECT * FROM entities.work")

    con.execute("""
        CREATE TABLE research.person (
            person_id UUID PRIMARY KEY,
            display_name VARCHAR,
            canonical_family_name VARCHAR,
            canonical_first_name VARCHAR,
            canonical_patronymic VARCHAR,
            ordinal_suffix VARCHAR,
            first_attested_season VARCHAR,
            last_attested_season VARCHAR,
            wikidata_qid VARCHAR,
            wikidata_label VARCHAR,
            wikidata_description VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO research.person
        SELECT
            p.person_id, p.display_name, p.canonical_family_name,
            p.canonical_first_name, p.canonical_patronymic, p.ordinal_suffix,
            p.first_attested_season, p.last_attested_season,
            wd.wikidata_qid, wd.wikidata_label, wd.wikidata_description
        FROM entities.person p
        LEFT JOIN entities.person_wikidata_link wd ON wd.person_id = p.person_id
        WHERE p.superseded_by_person_id IS NULL
    """)

    con.execute("""
        CREATE TABLE research.session (
            session_id VARCHAR PRIMARY KEY,
            theater_id UUID REFERENCES research.theater(theater_id),
            season VARCHAR,
            city VARCHAR,
            date_verbatim VARCHAR,
            date_undate VARCHAR,
            date VARCHAR,
            date_confidence VARCHAR,
            session_status VARCHAR,
            receipts_total_kopecks INTEGER
        )
    """)
    con.execute("""
        INSERT INTO research.session
        SELECT
            aps.session_id,
            t.theater_id,
            aps.season, aps.city,
            aps.date_text AS date_verbatim,
            aps.date_undate,
            coalesce(dc.corrected_date_undate, aps.date_undate) AS date,
            coalesce(
                dc.date_confidence,
                CASE WHEN aps.session_status = 'not_captured' THEN 'synthesized_gap'
                     ELSE 'unparseable' END
            ) AS date_confidence,
            aps.session_status,
            aps.receipts_total_kopecks
        FROM analysis.performance_session aps
        LEFT JOIN analysis.performance_session_date_check dc ON dc.session_id = aps.session_id
        LEFT JOIN entities.theater t ON t.canonical_name = aps.theater_canonical
    """)

    con.execute("""
        CREATE TABLE research.performance (
            performance_id VARCHAR PRIMARY KEY,
            session_id VARCHAR REFERENCES research.session(session_id),
            work_id UUID REFERENCES research.work(work_id),
            work_order VARCHAR,
            verbatim_title VARCHAR,
            verbatim_genre VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO research.performance
        SELECT
            pw.work_id AS performance_id,
            pw.session_id,
            wl.work_id,
            pw.work_order,
            pw.work_title AS verbatim_title,
            pw.genre AS verbatim_genre
        FROM raw.performance_work pw
        JOIN entities.work_link wl ON wl.raw_work_id = pw.work_id
    """)

    con.execute("""
        CREATE TABLE research.person_appearance (
            appearance_id VARCHAR PRIMARY KEY,
            person_id UUID REFERENCES research.person(person_id),
            season VARCHAR,
            city VARCHAR,
            entity_type VARCHAR,
            institution VARCHAR,
            heading_path VARCHAR,
            rank_or_title VARCHAR,
            service_class VARCHAR,
            instrument VARCHAR,
            subject_taught VARCHAR,
            tenure_note_text VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO research.person_appearance
        SELECT
            r.entry_id AS appearance_id,
            pl.person_id,
            sp.season, sp.city,
            r.entity_type, r.institution, r.heading_path,
            r.rank_or_title, r.service_class, r.instrument,
            r.subject_taught, r.tenure_note_text
        FROM raw.roster_entry r
        JOIN entities.person_link pl ON pl.entry_id = r.entry_id
        JOIN raw.source_pages sp ON sp.page_id = r.page_id
    """)

    counts = {
        t: con.execute(f"SELECT count(*) FROM research.{t}").fetchone()[0]
        for t in ["theater", "work", "person", "session", "performance", "person_appearance"]
    }
    print("research schema built:")
    for t, n in counts.items():
        print(f"  research.{t}: {n} rows")

    # Sanity check: receipts must live only on session, never on
    # performance -- the entire point of keeping them distinct.
    perf_cols = {c[0] for c in con.execute("DESCRIBE research.performance").fetchall()}
    assert not any("receipt" in c for c in perf_cols), \
        "receipts leaked onto research.performance -- multi-work sessions would double-count"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()

    con = duckdb.connect(str(args.db))
    build_research_model(con)
    con.close()
    print(f"\nresearch schema updated in {args.db}")


if __name__ == "__main__":
    main()
