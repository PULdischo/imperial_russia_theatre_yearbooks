"""Load the scan-verified productions lists (списокъ пьесъ; BalletProductions)
into the DuckDB raw tier as two tables:

    raw.production_entry              one row per printed entry
    raw.production_entry_performance  one row per printed performance date

Input is parse_productions.py's output over the scan-verified JSON
(`raw_verified/`), i.e. the verbatim transcription after hand verification
(known_issues.md #101). Additive and safe to re-run: CREATE OR REPLACE on
these two tables only; nothing else in the file is touched, and
build_duckdb.py's own rebuild (also CREATE OR REPLACE, table by table)
leaves them alone.

Usage:
    python pipeline/load_productions.py \
        --parsed-dir outputs/ballet_productions_pilot/parsed_verified \
        --db outputs/full_run/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()

    entry_csv = args.parsed_dir / "production_entry.csv"
    perf_csv = args.parsed_dir / "production_entry_performance.csv"
    con = duckdb.connect(str(args.db))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    # all_varchar + explicit casts: the verbatim text columns must never be
    # type-sniffed (a list_number or day_text is text as printed)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.production_entry AS
        SELECT production_entry_id, page_id, season, city, section_heading,
               printed_page_number, CAST(entry_order AS INTEGER) AS entry_order,
               list_number, CAST(is_premiere AS BOOLEAN) AS is_premiere,
               title, description_text, performed_text, total_text,
               CAST(NULLIF(total_count, '') AS INTEGER) AS total_count,
               NULLIF(post_total_text, '') AS post_total_text,
               CAST(n_dates AS INTEGER) AS n_dates,
               NULLIF(fragment, '') AS fragment, source_file,
               CAST(source_page_index AS INTEGER) AS source_page_index
        FROM read_csv('{entry_csv}', all_varchar = true, header = true)
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.production_entry_performance AS
        SELECT production_performance_id, production_entry_id,
               CAST(date_order AS INTEGER) AS date_order,
               year_text, month_text, day_text, NULLIF(note, '') AS note,
               CAST(outside_total AS BOOLEAN) AS outside_total,
               CAST(NULLIF(date, '') AS DATE) AS date
        FROM read_csv('{perf_csv}', all_varchar = true, header = true)
    """)
    for t in ("production_entry", "production_entry_performance"):
        n = con.execute(f"SELECT count(*) FROM raw.{t}").fetchone()[0]
        print(f"raw.{t}: {n} rows")
    orphans = con.execute("""
        SELECT count(*) FROM raw.production_entry_performance p
        LEFT JOIN raw.production_entry e USING (production_entry_id)
        WHERE e.production_entry_id IS NULL
    """).fetchone()[0]
    print(f"orphan performance rows: {orphans}")
    con.close()


if __name__ == "__main__":
    main()
