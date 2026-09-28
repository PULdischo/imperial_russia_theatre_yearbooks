"""Parse the raw *.raw.json responses for the productions lists (списокъ
пьесъ; BalletProductions so far) into two combined CSVs:

    production_entry.csv              one row per printed entry
    production_entry_performance.csv  one row per printed performance date

and print the gold-free structural checks:

  - list_number continuity per (season, city): 1..N, no gaps/duplicates
  - date_count_mismatch: number of printed dates != printed "Всего" -- either
    a misread (fix against the scan) or a genuine print inconsistency
    (leave verbatim, record in docs/eval/genuine_print_typos.md)
  - unparsed_date: a date that parse_russian_date couldn't turn into ISO

An entry split across a page break comes back as two fragments (the model
marks the first "continues" and the second "continued"); they are merged
here into one entry, keeping the first fragment's page_id and ID.

Usage:
    python pipeline/parse_productions.py --manifest outputs/<run>/manifest.csv \
        --raw-dir outputs/<run>/raw_full --out-dir outputs/<run>/parsed
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import ProductionsPage, flatten_productions_page
from extract import _strip_code_fence


def _write(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _join(a, b):
    return " ".join(x for x in (a, b) if x) or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    manifest = [r for r in csv.DictReader(open(args.manifest, encoding="utf-8"))
                if r["entity_type"] == "BalletProductions"]
    manifest.sort(key=lambda r: (r["season"], r["city"], int(r["source_page_index"])))

    entries, perfs, missing = [], [], []
    for row in manifest:
        raw_path = args.raw_dir / f"{row['page_id']}.raw.json"
        if not raw_path.exists():
            missing.append(row["page_id"])
            continue
        page = ProductionsPage.model_validate(
            json.loads(_strip_code_fence(raw_path.read_text(encoding="utf-8"))))
        t = flatten_productions_page(row["page_id"], row["season"], row["city"], page)
        for e in t["production_entry"]:
            e["source_file"] = row["source_file"]
            e["source_page_index"] = row["source_page_index"]
        entries += t["production_entry"]
        perfs += t["production_entry_performance"]

    # merge page-break fragments: a "continued" entry is the tail of the
    # previous entry in the same (season, city) list
    merged, drop = [], set()
    for e in entries:
        if e["fragment"] == "continued" and merged and \
                (merged[-1]["season"], merged[-1]["city"]) == (e["season"], e["city"]):
            head = merged[-1]
            for k in ("description_text", "performed_text"):
                head[k] = _join(head[k], e[k])
            if e["total_text"]:
                head["total_text"], head["total_count"] = e["total_text"], e["total_count"]
            n = head["n_dates"]
            for p in perfs:
                if p["production_entry_id"] == e["production_entry_id"]:
                    n += 1
                    p["production_entry_id"] = head["production_entry_id"]
                    p["date_order"] = n
                    p["production_performance_id"] = f"{head['production_entry_id']}__d{n:03d}"
            head["n_dates"] = n
            head["fragment"] = "merged"
            drop.add(e["production_entry_id"])
            continue
        merged.append(e)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    _write(merged, args.out_dir / "production_entry.csv")
    _write(perfs, args.out_dir / "production_entry_performance.csv")
    print(f"{len(merged)} entries, {len(perfs)} performance dates -> {args.out_dir}")
    if missing:
        print(f"MISSING raw JSON for {len(missing)} page(s): {missing}")

    # --- structural checks ---
    by_list = defaultdict(list)
    for e in merged:
        by_list[(e["season"], e["city"])].append(e)
    print("\nlist_number continuity:")
    for (season, city), es in sorted(by_list.items()):
        nums = [e["list_number"] for e in es]
        ints = [int(n) for n in nums if (n or "").isdigit()]
        expected = list(range(1, len(es) + 1))
        ok = ints == expected
        print(f"  {season} {city:6} {len(es):3} entries  "
              f"{'ok' if ok else 'PROBLEM: ' + ','.join(str(n) for n in nums)}")

    print("\ndate_count_mismatch (printed dates != printed Всего):")
    for e in merged:
        if e["total_count"] is None or int(e["total_count"]) != e["n_dates"]:
            print(f"  {e['production_entry_id']}  {e['list_number']}. {e['title']}  "
                  f"dates={e['n_dates']} total={e['total_count']}  [{e['total_text']}]")

    bad = [p for p in perfs if not p["date"]]
    print(f"\nunparsed_date: {len(bad)}")
    for p in bad:
        print(f"  {p['production_performance_id']}  {p['day_text']} {p['month_text']} {p['year_text']}")

    # a season runs roughly August (first year) to July (second year); a date
    # outside that window is either a misread or a print error (e.g. a year
    # not reprinted after the New Year) -- never corrected here, only listed
    season_of = {e["production_entry_id"]: e["season"] for e in merged}
    print("\nout_of_season_date:")
    for p in perfs:
        if not p["date"]:
            continue
        first = int(season_of[p["production_entry_id"]][:4])
        if not (f"{first}-08-01" <= p["date"] <= f"{first + 1}-07-31"):
            print(f"  {p['production_performance_id']}  {p['day_text']} {p['month_text']} "
                  f"{p['year_text']} -> {p['date']}")

    print("\npost_total consistency (post_total_text <-> outside_total dates):")
    outside = defaultdict(int)
    for p in perfs:
        if p["outside_total"]:
            outside[p["production_entry_id"]] += 1
    for e in merged:
        has_text, n_out = bool(e["post_total_text"]), outside[e["production_entry_id"]]
        if has_text != bool(n_out) or "исполн" in (e["total_text"] or "").lower():
            print(f"  {e['production_entry_id']}  post_total_text={e['post_total_text']!r} "
                  f"outside_total_dates={n_out} total_text={e['total_text']!r}")

    frags = [e for e in merged if e["fragment"] not in (None, "", "merged")]
    print(f"\nunmerged fragments: {len(frags)}")
    for e in frags:
        print(f"  {e['production_entry_id']} {e['fragment']} {e['title']}")


if __name__ == "__main__":
    main()
