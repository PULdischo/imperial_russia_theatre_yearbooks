"""Stage 5: load parsed CSVs (from parse_and_validate.py) into a DuckDB file
with two schemas -- `raw` (verbatim, exactly as parsed, the reproducibility
guarantee) and `analysis` (normalized/derived, built from `raw` via SQL,
never hand-edited). See docs/research_questions.md for the two-layer
rationale and docs/pipeline.md for the full stage sketch.

Usage:
    python pipeline/build_duckdb.py --parsed-dir outputs/pilot/parsed \
        --manifest docs/eval/gold/source_pages.csv \
        --db outputs/pilot/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

# tables that may legitimately be empty/absent for a given run (e.g. a pilot
# with no BalletArtists page would have zero roster_entry_credit rows)
RAW_TABLES = [
    "source_pages", "roster_entry", "service_period", "roster_entry_credit",
    "performance_session", "performance_work",
]


def load_raw_schema(con: duckdb.DuckDBPyConnection, parsed_dir: Path, manifest: Path) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    # source_pages comes from the manifest, not outputs/parsed (parse_and_validate.py
    # doesn't touch it -- it's Stage 1/2 output, already schema-conformant)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.source_pages AS
        SELECT * FROM read_csv_auto('{manifest.as_posix()}', header=true)
    """)
    for table in RAW_TABLES:
        if table == "source_pages":
            continue
        csv_path = parsed_dir / f"{table}.csv"
        if not csv_path.exists():
            print(f"skip (no data yet): {table}")
            continue
        con.execute(f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_csv_auto('{csv_path.as_posix()}', header=true, all_varchar=true)
        """)
        n = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        print(f"raw.{table}: {n} rows")


def build_analysis_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Derived layer. Kept intentionally small for now -- add normalization/
    entity-resolution rules here as they're developed (see
    docs/research_questions.md), always as new columns/tables on top of
    `raw`, never overwriting it."""
    con.execute("CREATE SCHEMA IF NOT EXISTS analysis")

    tables = [t[0] for t in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'"
    ).fetchall()]

    if "roster_entry" in tables:
        # Two known, recurring VLM output quirks (docs/eval/known_issues.md
        # #2 and #3) turned out NOT to respond to prompt fixes on re-test --
        # both are mechanical/regex-shaped, so they're normalized here in the
        # analysis layer instead of chased further in the prompt. raw.roster_entry
        # keeps the model's literal heading_path untouched.
        con.execute(r"""
            CREATE OR REPLACE TABLE analysis.roster_entry AS
            WITH step1 AS (
                SELECT *,
                    regexp_extract(heading_path, '[,:]?\s*([IVXLC]+\.?\s*кл\.?):?\s*$', 1)
                        AS _extracted_class,
                    regexp_replace(heading_path, '[,:]?\s*([IVXLC]+\.?\s*кл\.?):?\s*$', '')
                        AS _heading_no_class
                FROM raw.roster_entry
            ),
            step2 AS (
                SELECT * EXCLUDE (_extracted_class, _heading_no_class),
                    CASE WHEN trim(service_class) <> '' THEN service_class
                         WHEN _extracted_class <> '' THEN _extracted_class
                         ELSE service_class END AS service_class_clean,
                    CASE WHEN _extracted_class <> '' THEN _heading_no_class
                         ELSE heading_path END AS _heading_step2
                FROM step1
            ),
            step3 AS (
                SELECT * EXCLUDE (_heading_step2),
                    CASE WHEN institution <> '' AND starts_with(_heading_step2, institution || ' / ')
                         THEN substr(_heading_step2, length(institution) + 4)
                         ELSE _heading_step2
                    END AS heading_path_clean
                FROM step2
            )
            SELECT *,
                -- best-effort single "role" value, derived from the cleaned
                -- breadcrumb rather than asking the model to split it (see
                -- docs/schema.md's heading_path note on why that split was
                -- collapsed after the roster extraction smoke test)
                trim(list_extract(str_split(heading_path_clean, ' / '),
                     len(str_split(heading_path_clean, ' / ')))) AS role_normalized
            FROM step3
        """)
        print("analysis.roster_entry built (+ heading_path_clean, service_class_clean, role_normalized)")

    if "performance_session" in tables and "source_pages" in tables:
        # Completeness reconciliation (docs/schema.md's session_status note).
        # A model recall failure produces no row at all for a (date, theater)
        # cell, which is indistinguishable from "nothing happened here" if
        # you only look at raw.performance_session -- this makes that gap
        # queryable instead of invisible, by comparing what was captured
        # against an expected date x theater grid and inserting a
        # session_status='not_captured' placeholder for anything missing.
        # Two real data-quality bugs were found and fixed getting here (both
        # upstream of this query, not worked around inside it): parse_russian_date
        # was assigning the wrong calendar year for season-spanning printed
        # ranges like "1896-1897 гг." (schemas/dates.py), and theater names
        # need prefix/alias normalization -- post-1898-99 pages consistently
        # append "театръ"/"театр", and "Маріинскій" is sometimes spelled without
        # its pre-reform "і" ("Мариинскій") -- both handled by theater_canonical
        # below rather than by touching the verbatim raw.theater column.
        con.execute(r"""
            CREATE OR REPLACE TABLE analysis.performance_session AS
            WITH base AS (
                SELECT *,
                       TRY_CAST(receipts_rubles AS INTEGER) * 100
                           + TRY_CAST(receipts_kopecks AS INTEGER) AS receipts_total_kopecks,
                       TRY_CAST(date_undate AS DATE) AS date_parsed,
                       CASE
                           WHEN starts_with(theater, 'Маріинскій') OR starts_with(theater, 'Мариинскій')
                               THEN 'Маріинскій'
                           WHEN starts_with(theater, 'Александринскій') THEN 'Александринскій'
                           WHEN starts_with(theater, 'Михайловскій') THEN 'Михайловскій'
                           WHEN starts_with(theater, 'Большой') THEN 'Большой'
                           WHEN starts_with(theater, 'Малый') THEN 'Малый'
                           WHEN starts_with(theater, 'Новый') THEN 'Новый'
                           ELSE NULL
                       END AS theater_canonical
                FROM raw.performance_session
            ),
            -- Which of the 6 known theaters existed for a given season --
            -- SP's 3 theaters run the whole 1890/91-1907/08 span; Moscow's
            -- third venue (Новый театръ) only from 1898-99 on, per
            -- docs/structural_survey.md.
            season_years AS (
                SELECT DISTINCT season, TRY_CAST(left(season, 4) AS INTEGER) AS start_year
                FROM raw.source_pages WHERE entity_type = 'Repertoire'
            ),
            theater_roster AS (
                SELECT season, theater, city FROM season_years, (VALUES
                    ('Маріинскій', 'SP'), ('Александринскій', 'SP'), ('Михайловскій', 'SP'),
                    ('Большой', 'Moscow'), ('Малый', 'Moscow')
                ) AS t(theater, city)
                UNION ALL
                SELECT season, 'Новый', 'Moscow' FROM season_years WHERE start_year >= 1898
            ),
            -- Expected city set per page: pre-1898-99 pages combine both
            -- cities' theaters (hardcoded -- true regardless of what
            -- survived extraction); 1898-99-on pages are single-city blocks,
            -- so the expected city is whichever city's sessions actually
            -- appear for that page. Known limit: if a post-split page lost
            -- 100% of its sessions, there's no surviving evidence of which
            -- city it was, so no gaps can be synthesized for it.
            page_cities AS (
                SELECT sp.page_id, sp.season,
                    CASE WHEN sy.start_year < 1898 THEN ['SP', 'Moscow']
                         ELSE (SELECT list(DISTINCT b.city) FROM base b WHERE b.page_id = sp.page_id)
                    END AS expected_cities
                FROM raw.source_pages sp
                JOIN season_years sy USING (season)
                WHERE sp.entity_type = 'Repertoire'
            ),
            -- Expected date range per page: min/max of its own captured
            -- dates, assuming (per docs/schema.md) the source prints one
            -- row per calendar day with no skipped days in between.
            page_dates AS (
                SELECT page_id, min(date_parsed) AS min_date, max(date_parsed) AS max_date
                FROM base WHERE date_parsed IS NOT NULL
                GROUP BY page_id
            ),
            expected_grid AS (
                SELECT pc.page_id, pc.season, CAST(gs.d AS DATE) AS date_parsed,
                       tr.theater, tr.city
                FROM page_cities pc
                JOIN page_dates pd USING (page_id)
                JOIN theater_roster tr
                    ON tr.season = pc.season AND list_contains(pc.expected_cities, tr.city)
                , LATERAL (SELECT unnest(generate_series(pd.min_date, pd.max_date, INTERVAL 1 DAY)) AS d) AS gs
            ),
            covered AS (
                SELECT DISTINCT page_id, date_parsed, theater_canonical AS theater
                FROM base
                WHERE date_parsed IS NOT NULL AND theater_canonical IS NOT NULL
            ),
            gap_rows AS (
                SELECT
                    eg.page_id || '__gap_' || strftime(eg.date_parsed, '%Y%m%d') || '_' || eg.theater
                        AS session_id,
                    eg.page_id, eg.season, eg.city,
                    '' AS date_text, '' AS month_text, '' AS year_text,
                    strftime(eg.date_parsed, '%Y-%m-%d') AS date_undate,
                    'day' AS session, eg.theater,
                    'not_captured' AS session_status,
                    '' AS receipts_text, NULL::INTEGER AS receipts_rubles,
                    NULL::INTEGER AS receipts_kopecks, '' AS annotation,
                    NULL::INTEGER AS receipts_total_kopecks, eg.date_parsed,
                    eg.theater AS theater_canonical
                FROM expected_grid eg
                LEFT JOIN covered c
                    ON c.page_id = eg.page_id AND c.date_parsed = eg.date_parsed AND c.theater = eg.theater
                WHERE c.page_id IS NULL
            )
            SELECT * EXCLUDE (date_parsed) FROM base
            UNION ALL BY NAME
            SELECT * EXCLUDE (date_parsed) FROM gap_rows
        """)
        n_gaps = con.execute(
            "SELECT count(*) FROM analysis.performance_session WHERE session_status = 'not_captured'"
        ).fetchone()[0]
        print(f"analysis.performance_session built (+ receipts_total_kopecks, theater_canonical, "
              f"{n_gaps} not_captured completeness gaps)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(args.db))

    load_raw_schema(con, args.parsed_dir, args.manifest)
    build_analysis_schema(con)

    con.close()
    print(f"\nBuilt {args.db} -- copy this off scratch/temp storage, it's the deliverable.")


if __name__ == "__main__":
    main()
