"""Fold hand-verified dates from a filled worksheet CSV back into the catalogue.

Hand-read dates rank alongside RGIA's own: both are authoritative, unlike the
scan-derived ones (60.6% exact / 29% wrong -- see rgia_dates_merge.py). A
manual date therefore MAY exclude a дело, which a scan date never may.

Fill in dates_to_verify.csv (from rgia_date_worksheet.py): one row per дело,
with delo_no and dates_verbatim; year_start/year_end are derived if left blank.
Extra blank rows are ignored, so add as many rows per image as the page needs.

Usage:
    python pipeline/rgia_dates_ingest.py --range 1885-1916
"""
from __future__ import annotations

import argparse, csv, re
from pathlib import Path


def years(s: str) -> tuple[int | None, int | None]:
    ys = [int(y) for y in re.findall(r"\b(1[6-9]\d\d)\b", s or "")]
    return (min(ys), max(ys)) if ys else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worksheet", type=Path,
                    default=Path("outputs/rgia_worksheet/dates_to_verify.csv"))
    ap.add_argument("--target", type=Path,
                    default=Path("outputs/rgia_catalogue/opis18_dela_filled.csv"))
    ap.add_argument("--range", default="1885-1916")
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.range.split("-"))

    manual: dict[int, dict] = {}
    for r in csv.DictReader(open(args.worksheet, encoding="utf-8")):
        dn = (r.get("delo_no") or "").strip()
        if not dn.isdigit():
            continue
        raw = (r.get("dates_verbatim") or "").strip()
        ys = (r.get("year_start") or "").strip()
        ye = (r.get("year_end") or "").strip()
        if not raw and not ys:
            continue
        a, b = (int(ys), int(ye or ys)) if ys.isdigit() else years(raw)
        manual[int(dn)] = {"raw": raw, "ys": a, "ye": b,
                           "notes": (r.get("notes") or "").strip()}
    if not manual:
        raise SystemExit(f"no filled rows found in {args.worksheet}")

    rows = list(csv.DictReader(open(args.target, encoding="utf-8")))
    cols = list(rows[0].keys())
    for c in ("manual_dates_raw", "manual_notes"):
        if c not in cols: cols.append(c)

    applied = conflicts = 0
    for r in rows:
        r.setdefault("manual_dates_raw", ""); r.setdefault("manual_notes", "")
        dn = (r.get("delo_no") or "").strip()
        if not dn.isdigit() or int(dn) not in manual:
            continue
        m = manual[int(dn)]
        # if RGIA already dates it, keep RGIA's but record the disagreement
        if r.get("date_source") == "catalogue":
            if m["ys"] and str(m["ys"]) != r.get("year_start"):
                r["manual_notes"] = (r["manual_notes"] + " | disagrees with RGIA: "
                                     f"{m['ys']}-{m['ye']}").strip(" |")
                conflicts += 1
            continue
        r["year_start"] = m["ys"] if m["ys"] is not None else ""
        r["year_end"] = m["ye"] if m["ye"] is not None else ""
        r["manual_dates_raw"] = m["raw"]
        r["manual_notes"] = m["notes"]
        r["date_source"] = "manual_verified"
        if m["ys"] is None:
            r["in_research_range"] = "unknown"
        else:
            r["in_research_range"] = "yes" if m["ys"] <= hi and m["ye"] >= lo else "no"
        applied += 1

    with open(args.target, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in cols})

    from collections import Counter
    print(f"applied {applied} hand-verified dates -> {args.target}")
    if conflicts:
        print(f"  {conflicts} disagree with RGIA's own date (RGIA kept, noted)")
    print("  date_source:", dict(Counter(r["date_source"] for r in rows)))
    print("  in range   :", dict(Counter(r["in_research_range"] for r in rows)))


if __name__ == "__main__":
    main()
