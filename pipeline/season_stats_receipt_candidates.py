"""Finds candidate Repertoire receipts cells for the season-stats receipt leads (issue #116).

A lead is a stats category (season, city, family[, venue]) whose performance COUNT matches
the Repertoire exactly but whose receipts sum differs by delta = stats - Repertoire. For each
lead this lists every Repertoire event in the group whose printed receipts figure would
account for delta exactly under ONE of these single-slip hypotheses:
  - one digit misread (any position, rubles or kopecks);
  - two adjacent digits swapped.
A candidate is only a place to look: the scan decides, and the stats page itself may be the
one that's wrong. Groups use the same classification as pipeline/compare_season_stats.py.

Usage:
    uv run python pipeline/season_stats_receipt_candidates.py --db outputs/full_run/imperial_theaters.duckdb \
        --family-totals outputs/season_stats_compare/family_totals.csv --out outputs/season_stats_compare/receipt_candidates.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent))
import compare_season_stats as cs  # noqa: E402

EVENT_SQL = """
select e.event_id, e.season, e.city, t.canonical_name, e.receipts_total_kopecks,
       a.page_id, a.date_text, a.time_of_day, a.receipts_text, a.printed_page_number,
       p.verbatim_title, coalesce(w.canonical_genre, p.verbatim_genre)
from research.event e join research.theater t using (theater_id)
join analysis.event_entry a using (event_id)
left join research.performance p using (event_id) left join research.work w using (work_id)
where e.event_status = 'performed'
order by e.event_id, p.performance_order
"""


def variants(k: int):
    """Yield (new_value, description) for single-digit slips of a kopeck amount, shown as rubles.kopecks."""
    s = f"{k // 100}{k % 100:02d}"          # digits: rubles then 2 kopeck digits
    for i, ch in enumerate(s):
        for d in "0123456789":
            if d != ch and not (i == 0 and d == "0"):
                yield int(s[:i] + d + s[i + 1:]), f"digit {i + 1}/{len(s)} {ch}->{d}"
    for i in range(len(s) - 1):
        if s[i] != s[i + 1] and not (i == 0 and s[i + 1] == "0"):
            yield int(s[:i] + s[i + 1] + s[i] + s[i + 2:]), f"swap digits {i + 1}-{i + 2}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--family-totals", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    con = duckdb.connect(a.db, read_only=True)
    ev = {}
    for eid, season, city, th, k, page, date, tod, rtext, pp, title, genre in con.execute(EVENT_SQL).fetchall():
        e = ev.setdefault(eid, dict(season=season, city=city, theater=th, k=k, page=page, date=date,
                                    tod=tod, rtext=rtext, pp=pp, fams=[], titles=[]))
        if title is not None:
            e["fams"].append(cs.classify_work(title, genre))
            e["titles"].append(title)
    for e in ev.values():
        c = cs.classify_event(e["fams"])
        e["family"] = "mixed" if c.startswith("mixed:") else c
    leads = [r for r in csv.DictReader(open(a.family_totals, encoding="utf-8"))
             if r["diff"] == "0" and r["diff_receipts_rub"] not in ("", "0.0")]
    out_rows, summary = [], []
    for r in leads:
        delta = round(-float(r["diff_receipts_rub"]) * 100)   # stats - Repertoire, kopecks
        group = [e for e in ev.values() if e["season"] == r["season"] and e["city"] == r["city"]
                 and e["family"] == r["family"] and (not r["venue"] or e["theater"] == r["venue"])]
        n = 0
        for eid, e in sorted((x for x in ev.items() if x[1] in group), key=lambda x: (x[1]["page"], x[1]["date"] or "")):
            if e["k"] is None:
                continue
            for new, how in variants(int(e["k"])):
                if new - int(e["k"]) == delta:
                    n += 1
                    out_rows.append({
                        "season": r["season"], "city": r["city"], "family": r["family"], "venue": r["venue"],
                        "delta_rub": delta / 100, "event_id": eid, "page_id": e["page"], "printed_page": e["pp"],
                        "date_text": e["date"], "time_of_day": e["tod"], "theater": e["theater"],
                        "receipts_text": e["rtext"], "rep_rub": e["k"] / 100, "would_be_rub": new / 100,
                        "slip": how, "titles": " / ".join(e["titles"])[:120],
                    })
        summary.append((r["season"], r["city"], r["family"], r["venue"], delta / 100, len(group), n))
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]) if out_rows else ["season"])
        w.writeheader(); w.writerows(out_rows)
    for s in summary:
        print(f"{s[0]} {s[1]:6} {s[2]:13} {s[3]:16} Δ{s[4]:>+11.2f}  events {s[5]:>4}  candidates {s[6]}")
    print(f"\n{len(leads)} leads, {sum(1 for s in summary if s[6])} with candidates, "
          f"{sum(1 for s in summary if s[6] == 1)} with exactly one; {len(out_rows)} candidate cells -> {a.out}")


if __name__ == "__main__":
    main()
