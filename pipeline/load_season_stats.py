"""Load the hand-transcribed season production-stats pages (docs/season_stats/)
into the DuckDB raw tier as four tables:

    raw.season_stat_page       one row per printed totals page (season, printed page, heading, format)
    raw.season_stat_line       one row per printed line that carries a number
    raw.season_stat_footnote   one row per printed footnote
    raw.season_stat_dated_note one row per printed jubilee/benefit line (from 1909-10)

The CSVs are the verbatim transcription (docs/season_stats/_build.py is the
source of truth: edit the data there, regenerate the CSVs, re-run this). Nothing
is derived here; the printed-versus-Repertoire comparison is built from these
tables by build_research_model.build_season_stats.

Additive and safe to re-run: CREATE OR REPLACE on these four tables only.
build_duckdb.py's own rebuild leaves them alone (same as raw.production_entry).

Usage:
    uv run python pipeline/load_season_stats.py --db outputs/full_run/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

STATS_DIR = Path(__file__).resolve().parent.parent / "docs" / "season_stats"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--stats-dir", type=Path, default=STATS_DIR)
    args = ap.parse_args()

    csv = {n: args.stats_dir / f"{n}.csv" for n in ("pages", "lines", "footnotes", "dated_notes")}
    for p in csv.values():
        if not p.exists():
            raise SystemExit(f"missing {p}; run docs/season_stats/_build.py first")

    con = duckdb.connect(str(args.db))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    # all_varchar + explicit casts: printed text columns are never type-sniffed
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.season_stat_page AS
        SELECT season, source_file, printed_page, heading_verbatim,
               NULLIF(heading_footnote, '') AS heading_footnote, format, NULLIF(note, '') AS note
        FROM read_csv('{csv["pages"]}', all_varchar = true, header = true)
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.season_stat_line AS
        SELECT season, city AS city_verbatim, CAST(line_no AS INTEGER) AS line_no, line_kind,
               category_verbatim, category,
               NULLIF(venue_verbatim, '') AS venue_verbatim,
               NULLIF(qualifier_verbatim, '') AS qualifier_verbatim,
               CAST(count AS INTEGER) AS count,
               NULLIF(receipts_verbatim, '') AS receipts_verbatim,
               CAST(NULLIF(receipts_kopecks, '') AS DECIMAL(18, 1)) AS receipts_kopecks,
               NULLIF(footnote_refs, '') AS footnote_refs, NULLIF(note, '') AS note
        FROM read_csv('{csv["lines"]}', all_varchar = true, header = true)
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.season_stat_footnote AS
        SELECT season, CAST(footnote_no AS INTEGER) AS footnote_no, text_verbatim, NULLIF(note, '') AS note
        FROM read_csv('{csv["footnotes"]}', all_varchar = true, header = true)
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE raw.season_stat_dated_note AS
        SELECT season, city AS city_verbatim, CAST(note_no AS INTEGER) AS note_no, text_verbatim, NULLIF(note, '') AS note
        FROM read_csv('{csv["dated_notes"]}', all_varchar = true, header = true)
    """)

    # integrity: every line/footnote belongs to a loaded page; (season, city, line_no) is unique
    orphan_lines = con.execute("""SELECT count(*) FROM raw.season_stat_line l
        LEFT JOIN raw.season_stat_page p USING (season) WHERE p.season IS NULL""").fetchone()[0]
    orphan_notes = con.execute("""SELECT count(*) FROM raw.season_stat_footnote f
        LEFT JOIN raw.season_stat_page p USING (season) WHERE p.season IS NULL""").fetchone()[0]
    dup = con.execute("""SELECT count(*) FROM (SELECT 1 FROM raw.season_stat_line
        GROUP BY season, city_verbatim, line_no HAVING count(*) > 1)""").fetchone()[0]
    if orphan_lines or orphan_notes or dup:
        raise SystemExit(f"season stats: {orphan_lines} orphan lines, {orphan_notes} orphan footnotes, {dup} duplicate line keys")
    for t in ("page", "line", "footnote", "dated_note"):
        n = con.execute(f"SELECT count(*) FROM raw.season_stat_{t}").fetchone()[0]
        print(f"raw.season_stat_{t}: {n} rows")
    con.close()


if __name__ == "__main__":
    main()
