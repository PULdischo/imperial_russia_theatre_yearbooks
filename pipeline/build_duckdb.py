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

    if "performance_session" in tables:
        con.execute("""
            CREATE OR REPLACE TABLE analysis.performance_session AS
            SELECT *,
                   TRY_CAST(receipts_rubles AS INTEGER) * 100
                       + TRY_CAST(receipts_kopecks AS INTEGER) AS receipts_total_kopecks
            FROM raw.performance_session
        """)
        print("analysis.performance_session built (+ receipts_total_kopecks)")


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
