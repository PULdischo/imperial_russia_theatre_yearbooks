"""Join scan-derived dates onto RGIA's catalogue, scoring the model against the
дела whose dates RGIA already publishes before trusting it on those it doesn't.

The catalogue is authoritative wherever it has a date: those 422 дела are used
ONLY as ground truth here, never overwritten.

MEASURED, 2026-08-27: scored against those 422, the scan-derived dates are
60.6% exact / 29% outright wrong, and only 72% correct even when both passes
agree. That is NOT good enough to filter research material. So a scan date is
never allowed to EXCLUDE a дело -- an over-broad candidate list costs a glance,
a wrongly excluded дело is lost silently. Scan dates can only move a дело from
"unknown" to "yes_unverified"; only RGIA's own dates can produce "no".

Usage:
    python pipeline/rgia_dates_merge.py --range 1885-1916
"""
from __future__ import annotations

import argparse, csv, json, re
from collections import defaultdict
from pathlib import Path


def load_scan_dates(raw_dir: Path) -> dict[int, list[dict]]:
    """delo_no -> [ {pass, image, dates_raw, year_start, year_end}, ... ]"""
    by_delo: dict[int, list[dict]] = defaultdict(list)
    for f in sorted(raw_dir.glob("img*.pass*.dates.json")):
        img = int(re.search(r"img(\d+)", f.name).group(1))
        pno = int(re.search(r"pass(\d+)", f.name).group(1))
        txt = f.read_text(encoding="utf-8").strip()
        if txt.startswith("```"):
            txt = "\n".join(txt.splitlines()[1:])
            if txt.rstrip().endswith("```"): txt = txt.rstrip()[:-3]
        try: page = json.loads(txt)
        except Exception: continue
        for e in page.get("entries", []):
            n = re.sub(r"\D", "", str(e.get("poryadkovy_nomer") or ""))
            if not n: continue
            by_delo[int(n)].append({
                "pass": pno, "image": img,
                "dates_raw": e.get("dates_raw"),
                "year_start": e.get("year_start"), "year_end": e.get("year_end"),
            })
    return by_delo


def vote(cands: list[dict]) -> tuple[object, object, str, str]:
    """Returns (year_start, year_end, agreement, dates_raw)."""
    pairs = [(c["year_start"], c["year_end"]) for c in cands]
    non_null = [p for p in pairs if p[0] is not None or p[1] is not None]
    if not non_null:
        return None, None, ("blank_agreed" if len(pairs) > 1 else "blank_single"), ""
    uniq = set(non_null)
    if len(uniq) == 1:
        ys, ye = non_null[0]
        agree = "agreed" if len(non_null) > 1 else "single_pass"
    else:
        # take the most common; report the conflict
        from collections import Counter
        (ys, ye), _ = Counter(non_null).most_common(1)[0]
        agree = "conflict"
    raw = next((c["dates_raw"] for c in cands
                if (c["year_start"], c["year_end"]) == (ys, ye) and c["dates_raw"]), "")
    return ys, ye, agree, raw or ""


def in_range(ys, ye, lo, hi) -> str:
    if ys is None and ye is None: return "unknown"
    ys, ye = ys or ye, ye or ys
    return "yes" if int(ys) <= hi and int(ye) >= lo else "no"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", type=Path,
                    default=Path("outputs/rgia_catalogue/opis18_dela.csv"))
    ap.add_argument("--raw-dir", type=Path, default=Path("outputs/rgia_dates/raw_dates"))
    ap.add_argument("--out", type=Path,
                    default=Path("outputs/rgia_catalogue/opis18_dela_filled.csv"))
    ap.add_argument("--range", default="1885-1916")
    args = ap.parse_args()
    lo, hi = (int(x) for x in args.range.split("-"))

    rows = list(csv.DictReader(open(args.catalogue, encoding="utf-8")))
    scan = load_scan_dates(args.raw_dir)

    # ---- EVAL against the дела RGIA already dates -------------------------
    exact = off_by_one = wrong = missed = 0
    examples = []
    for r in rows:
        if not r["dates_raw"] or not r["delo_no"]: continue
        c = scan.get(int(r["delo_no"]))
        if not c: continue
        ys, ye, _, _ = vote(c)
        if ys is None: missed += 1; continue
        cy, cye = int(r["year_start"]), int(r["year_end"])
        if (ys, ye) == (cy, cye): exact += 1
        elif abs(ys - cy) <= 1 and abs(ye - cye) <= 1: off_by_one += 1
        else:
            wrong += 1
            if len(examples) < 8:
                examples.append((r["delo_no"], f"{cy}-{cye}", f"{ys}-{ye}", r["title_ru"][:52]))
    scored = exact + off_by_one + wrong + missed
    print("=== scored against RGIA's own dates (ground truth) ===")
    if scored:
        print(f"  дела scored          : {scored}")
        print(f"  exact year match     : {exact} ({100*exact/scored:.1f}%)")
        print(f"  within 1 year        : {off_by_one} ({100*off_by_one/scored:.1f}%)")
        print(f"  wrong                : {wrong} ({100*wrong/scored:.1f}%)")
        print(f"  model found no date  : {missed} ({100*missed/scored:.1f}%)")
        if examples:
            print("  sample misses (delo, RGIA, model, title):")
            for e in examples: print(f"    Д.{e[0]:<5} {e[1]:<11} -> {e[2]:<11} {e[3]}")
    else:
        print("  (no overlap yet -- is the date run still going?)")

    # ---- FILL the ones RGIA leaves blank ----------------------------------
    cols = list(rows[0].keys()) + ["date_source", "scan_dates_raw", "scan_year_start",
                                   "scan_year_end", "scan_agreement", "scan_images"]
    filled = 0
    for r in rows:
        r["date_source"] = "catalogue" if r["dates_raw"] else ""
        r["scan_dates_raw"] = r["scan_agreement"] = r["scan_images"] = ""
        r["scan_year_start"] = r["scan_year_end"] = ""
        if r["dates_raw"] or not r["delo_no"]:
            r["in_research_range"] = in_range(
                r["year_start"] or None, r["year_end"] or None, lo, hi)
            continue
        c = scan.get(int(r["delo_no"]))
        if not c:
            r["in_research_range"] = "unknown"; continue
        ys, ye, agree, raw = vote(c)
        r["scan_agreement"] = agree
        r["scan_images"] = ",".join(sorted({str(x["image"]) for x in c}))
        if ys is None:
            r["date_source"] = "blank_on_scan"
            r["in_research_range"] = "unknown"
            continue
        # Record the scan's reading in its OWN columns -- never into year_start/
        # year_end, which stay reserved for RGIA's authoritative dates.
        r["scan_dates_raw"] = raw
        r["scan_year_start"], r["scan_year_end"] = ys, ye
        r["date_source"] = "scan_unverified"
        # asymmetric: may promote to a candidate, may never rule one out
        r["in_research_range"] = ("yes_unverified"
                                  if in_range(ys, ye, lo, hi) == "yes" else "unknown")
        filled += 1

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in cols})

    from collections import Counter
    print(f"\n=== merged ({lo}-{hi}) -> {args.out} ===")
    print("  date_source :", dict(Counter(r["date_source"] for r in rows)))
    print("  in range    :", dict(Counter(r["in_research_range"] for r in rows)))
    print(f"  surfaced as candidates by the scan: {filled} (unverified, never excluded)")


if __name__ == "__main__":
    main()
