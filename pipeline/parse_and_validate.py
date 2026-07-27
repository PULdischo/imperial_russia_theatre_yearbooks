"""Stage 3: parse + validate raw model JSON (from run_pilot.py / extract.py)
into the flat, schema-conformant tables from docs/schema.md, merged across
every page in the manifest. Rows that fail validation are logged to
validation_errors.csv, never silently dropped -- and never crash the run for
every OTHER page.

Usage:
    python pipeline/parse_and_validate.py --manifest docs/eval/gold/source_pages.csv \
        --raw-dir outputs/pilot/raw --out-dir outputs/pilot/parsed
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import RosterPage, RepertoirePage, flatten_roster_page, flatten_repertoire_page

ROSTER_KINDS = {"Administration", "BalletArtists", "Musicians", "ProductionTeam",
                "TheaterSchoolStaff", "Graduates"}


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))

    merged = {
        "roster_entry": [], "service_period": [], "roster_entry_credit": [],
        "performance_session": [], "performance_work": [],
    }
    errors = []

    for row in rows:
        page_id = row["page_id"]
        raw_path = args.raw_dir / f"{page_id}.raw.json"
        if not raw_path.exists():
            errors.append({"page_id": page_id, "stage": "missing_raw",
                            "error": f"no raw JSON at {raw_path}"})
            continue

        kind = "roster" if row["entity_type"] in ROSTER_KINDS else "repertoire"
        try:
            raw_text = raw_path.read_text(encoding="utf-8")
            parsed_json = json.loads(_strip_code_fence(raw_text))

            if kind == "roster":
                page = RosterPage.model_validate(parsed_json)
                tables = flatten_roster_page(page_id, row["entity_type"], page)
            else:
                page = RepertoirePage.model_validate(parsed_json)
                tables = flatten_repertoire_page(page_id, row["season"], row["city"], page)

            for table_name, table_rows in tables.items():
                merged[table_name].extend(table_rows)

        except Exception as e:
            errors.append({"page_id": page_id, "stage": "parse_or_validate", "error": str(e)})

    for table_name, table_rows in merged.items():
        out_path = args.out_dir / f"{table_name}.csv"
        write_csv(table_rows, out_path)
        print(f"{table_name}: {len(table_rows)} rows -> {out_path}")

    errors_path = args.out_dir / "validation_errors.csv"
    if errors:
        write_csv(errors, errors_path)
        print(f"\n{len(errors)} pages FAILED validation -> {errors_path}")
    else:
        print("\nno validation errors")


if __name__ == "__main__":
    main()
