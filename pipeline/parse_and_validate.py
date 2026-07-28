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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import RosterPage, RepertoirePage, flatten_roster_page, flatten_repertoire_page

ROSTER_KINDS = {"Administration", "BalletArtists", "Musicians", "ProductionTeam",
                "TheaterSchoolStaff", "Graduates"}

# The model occasionally writes the printed Russian session label instead of
# the normalized English enum value the schema expects (rare: ~80/23000
# repertoire sessions). This is a categorical field, not verbatim text, so
# normalizing here is correct rather than a verbatim-preservation violation.
SESSION_LABEL_FIX = {"утро": "morning", "вечеръ": "evening", "день": "day"}

# Rare (~4/20000 roster entries) recurring model failure: when a row has no
# heading of its own to repeat, the model sometimes puts the person's full
# name ("Surname, First Patronymic") into heading_path and leaves
# family_name/first_name/patronymic empty, using the row's actual heading
# text as `institution` instead. Recoverable deterministically since the
# "Surname, First [Patronymic]" shape doesn't occur in real heading_path
# values (those are always institution/department/role segments).
NAME_IN_HEADING_RE = re.compile(
    r"^([А-ЯЁІѢѲѴ][а-яёіѣѳѵ\-]+(?:\s+\d+-(?:й|я|е))?),\s+"
    r"([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+)(?:\s+([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+))?$"
)


def _repair_repertoire(parsed: dict) -> dict:
    for s in parsed.get("sessions", []):
        val = s.get("session")
        if val in SESSION_LABEL_FIX:
            s["session"] = SESSION_LABEL_FIX[val]
    return parsed


def _repair_roster(parsed: dict) -> dict:
    for e in parsed.get("entries", []):
        if e.get("family_name"):
            continue
        heading = e.get("heading_path") or ""
        m = NAME_IN_HEADING_RE.match(heading.strip())
        if not m:
            continue
        e["family_name"] = m.group(1)
        e["first_name"] = m.group(2)
        e["patronymic"] = m.group(3)
        e["heading_path"] = None
    return parsed


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
                parsed_json = _repair_roster(parsed_json)
                page = RosterPage.model_validate(parsed_json)
                tables = flatten_roster_page(page_id, row["entity_type"], page)
            else:
                parsed_json = _repair_repertoire(parsed_json)
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
