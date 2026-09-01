"""Re-filter the scraped оп. 18 catalogue to a different research date range,
offline. The scrape is the expensive part and never needs repeating just to
change a date window.

Entries with no date in RGIA's catalogue stay "unknown" at any range -- they
are NOT excluded, because a missing date must never silently hide a relevant
дело. Their dates live only in the scan's handwritten крайние даты column.

Usage:
    python pipeline/rgia_opis_filter.py --range 1885-1916
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def in_range(r: dict, lo: int, hi: int) -> str:
    ys = r.get("year_start") or ""
    ye = r.get("year_end") or ""
    if not ys and not ye:
        return "unknown"
    ys = int(ys or ye)
    ye = int(ye or ys)
    return "yes" if ys <= hi and ye >= lo else "no"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=Path("outputs/rgia_catalogue/opis18_dela.csv"))
    ap.add_argument("--range", default="1885-1916")
    ap.add_argument("--out-dir", type=Path, default=Path("outputs/rgia_catalogue"))
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.range.split("-"))

    rows = list(csv.DictReader(open(args.src, encoding="utf-8")))
    cols = list(rows[0].keys())
    prev = {r["shifr"]: r["in_research_range"] for r in rows}
    for r in rows:
        r["in_research_range"] = in_range(r, lo, hi)

    tag = f"{lo}_{hi}"
    def dump(name, sel):
        p = args.out_dir / name
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(sel)
        print(f"  {p}: {len(sel)}")

    yes = [r for r in rows if r["in_research_range"] == "yes"]
    dump(f"opis18_dela_{tag}.csv", rows)
    dump(f"opis18_in_range_{tag}.csv", yes)

    newly = [r for r in rows if r["in_research_range"] == "yes" and prev.get(r["shifr"]) != "yes"]
    print(f"\nrange {lo}-{hi}: {len(yes)} in range, "
          f"{sum(1 for r in rows if r['in_research_range']=='no')} out, "
          f"{sum(1 for r in rows if r['in_research_range']=='unknown')} undated")
    print(f"newly included vs the previous run: {len(newly)}")
    for r in sorted(newly, key=lambda r: int(r['delo_no'] or 0)):
        print(f"  Д.{r['delo_no']:<5} [{r['dates_raw'][:38]:<38}] {r['title_ru'][:78]}")


if __name__ == "__main__":
    main()
