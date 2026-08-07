"""Gold-free structural self-consistency checks.

The 12-page gold set catches real errors, but it's 12 pages out of ~1,300 --
most of a full run will have no ground truth to compare against. These
checks don't need any: they look for internally-inconsistent or
structurally-implausible patterns in a single page's own extracted output,
which is exactly where the known VLM failure modes from the pilot run show
up (see docs/eval/known_issues.md):

- non-deterministic recall (dark/blank cells silently dropped)
- heading_path re-including the institution name
- a rank-class token left inside heading_path instead of service_class
- arithmetic inconsistency between category-total credits and their stated sum
- duplicate rows (possible double-extraction)
- inconsistent verbatim spelling of the same theater within one page

None of these prove an error on their own -- a page can legitimately have no
dark cells, or credit categories can legitimately not sum to the total if the
source itself doesn't (e.g. mixed seasons). They're triage signals: flagged
pages are exactly the ones worth a human glance before trusting them, so the
review budget for a full run goes to the highest-risk pages instead of a
uniform random sample.

Usage:
    python pipeline/quality_checks.py --parsed-dir outputs/pilot/parsed \
        --out outputs/pilot/quality_flags.csv
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

RANK_CLASS_RE = re.compile(r",?\s*[IVXLC]+\s*кл\.?:?\s*$", re.IGNORECASE)


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8")))


def by_page(rows: list[dict]) -> dict[str, list[dict]]:
    d = defaultdict(list)
    for r in rows:
        d[r["page_id"]].append(r)
    return d


def check_roster(parsed_dir: Path) -> list[dict]:
    flags = []
    entries = load(parsed_dir / "person_entry.csv")
    credits = load(parsed_dir / "person_entry_credit.csv")
    credits_by_entry = defaultdict(list)
    for c in credits:
        credits_by_entry[c["entry_id"]].append(c)

    seen_in_page = defaultdict(set)  # page_id -> {(family, first, patronymic)}
    for e in entries:
        page_id, entry_id = e["page_id"], e["entry_id"]
        heading_path, institution = e.get("heading_path", ""), e.get("institution", "")
        family, first, patr = e.get("family_name", ""), e.get("first_name", ""), e.get("patronymic", "")

        if institution and heading_path and institution.strip() in heading_path:
            flags.append(dict(page_id=page_id, table="person_entry", row_id=entry_id,
                               flag="institution_duplicated_in_heading_path",
                               detail=f"institution={institution!r} heading_path={heading_path!r}"))

        if RANK_CLASS_RE.search(heading_path or "") and not e.get("service_class", "").strip():
            flags.append(dict(page_id=page_id, table="person_entry", row_id=entry_id,
                               flag="rank_class_left_in_heading_path",
                               detail=f"heading_path={heading_path!r}"))

        key = (family.strip(), first.strip(), patr.strip())
        if family.strip() and key in seen_in_page[page_id]:
            flags.append(dict(page_id=page_id, table="person_entry", row_id=entry_id,
                               flag="duplicate_person_on_page", detail=str(key)))
        seen_in_page[page_id].add(key)

    for entry_id, rows in credits_by_entry.items():
        totals = {r["label"]: r for r in rows if r["credit_type"] == "category_totals"}
        stated_total = totals.get("Всего")
        components = [r for label, r in totals.items() if label != "Всего"]
        if stated_total and components:
            try:
                component_sum = sum(int(r["category_credit_count"]) for r in components if r["category_credit_count"])
                stated = int(stated_total["category_credit_count"])
                if component_sum != stated:
                    page_id = rows[0]["entry_id"].split("__e")[0]
                    flags.append(dict(page_id=page_id, table="person_entry_credit", row_id=entry_id,
                                       flag="credit_sum_mismatch",
                                       detail=f"components sum to {component_sum}, stated Всего={stated}"))
            except (ValueError, KeyError):
                pass  # non-numeric count -- a different problem, not this check's job

    return flags


def check_repertoire(parsed_dir: Path) -> list[dict]:
    flags = []
    events = by_page(load(parsed_dir / "event_entry.csv"))

    KNOWN_THEATERS = ["Маріинскій", "Александринскій", "Михайловскій", "Большой", "Малый", "Новый"]

    for page_id, rows in events.items():
        dark_count = sum(1 for r in rows if r.get("event_status", "").strip() == "no_performance")
        days = {r["date_text"].split()[0] for r in rows if r.get("date_text")}
        if dark_count == 0 and len(days) >= 6:
            flags.append(dict(page_id=page_id, table="event_entry", row_id="",
                               flag="zero_dark_cells_on_multiweek_page",
                               detail=f"{len(rows)} events across {len(days)} distinct days, none dark -- "
                                      f"real tables almost always have at least one dark day (e.g. Saturdays); "
                                      f"suspect the model silently dropped blank cells this run"))

        seen_keys = set()
        for r in rows:
            key = (r["date_text"].strip(), r["theater"].strip(), r["time_of_day"])
            if key in seen_keys:
                flags.append(dict(page_id=page_id, table="event_entry", row_id=r["event_id"],
                                   flag="duplicate_event_key", detail=str(key)))
            seen_keys.add(key)

            if r.get("receipts_text", "").strip() and not r.get("receipts_rubles", "").strip():
                flags.append(dict(page_id=page_id, table="event_entry", row_id=r["event_id"],
                                   flag="receipts_parse_failed",
                                   detail=f"receipts_text={r['receipts_text']!r} but receipts_rubles is empty"))

        theater_variants = defaultdict(set)
        for r in rows:
            t = r["theater"].strip()
            for name in KNOWN_THEATERS:
                if t.startswith(name):
                    theater_variants[name].add(t)
        for name, variants in theater_variants.items():
            if len(variants) > 1:
                flags.append(dict(page_id=page_id, table="event_entry", row_id="",
                                   flag="inconsistent_theater_spelling_on_page",
                                   detail=f"{name}: saw {sorted(variants)} within the same page"))

    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    flags = check_roster(args.parsed_dir) + check_repertoire(args.parsed_dir)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page_id", "table", "row_id", "flag", "detail"])
        w.writeheader()
        w.writerows(flags)

    by_flag = defaultdict(int)
    for fl in flags:
        by_flag[fl["flag"]] += 1
    print(f"{len(flags)} flags -> {args.out}")
    for flag_type, n in sorted(by_flag.items(), key=lambda x: -x[1]):
        print(f"  {flag_type}: {n}")


if __name__ == "__main__":
    main()
