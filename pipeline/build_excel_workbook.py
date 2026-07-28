"""Stage 5b: package the verbatim/raw layer as a single Excel workbook --
one sheet per table, exactly matching raw.* in build_duckdb.py (Stage 5).
See docs/verbatim_deliverables.md for why this format exists alongside the
DuckDB file: it's the handoff for a Sheets/Excel-comfortable researcher who
wants pivot tables and filters, not a SQL client.

Deliberately verbatim-layer only, same scope as build_duckdb.py's `raw`
schema -- no analysis-layer derived columns (heading_path_clean,
theater_canonical, not_captured completeness rows, etc.). A workbook mixing
"exactly what was transcribed" with "what we inferred on top of it" would
undermine the whole reason the raw layer exists.

Usage:
    python pipeline/build_excel_workbook.py --parsed-dir outputs/full_run/parsed \
        --manifest outputs/full_run/manifest.csv --out outputs/full_run/imperial_theaters.xlsx
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

TABLES = [
    "roster_entry", "service_period", "roster_entry_credit",
    "performance_session", "performance_work",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(args.out, engine="openpyxl") as writer:
        source_pages = pd.read_csv(args.manifest, dtype=str)
        source_pages.to_excel(writer, sheet_name="source_pages", index=False)
        print(f"source_pages: {len(source_pages)} rows")

        for table in TABLES:
            csv_path = args.parsed_dir / f"{table}.csv"
            if not csv_path.exists():
                print(f"skip (no data yet): {table}")
                continue
            df = pd.read_csv(csv_path, dtype=str)
            # Excel sheet names cap at 31 chars -- all our table names fit,
            # this is just a guard in case a future table name doesn't.
            df.to_excel(writer, sheet_name=table[:31], index=False)
            print(f"{table}: {len(df)} rows")

    print(f"\nBuilt {args.out}")


if __name__ == "__main__":
    main()
