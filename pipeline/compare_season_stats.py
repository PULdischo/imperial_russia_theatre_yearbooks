"""Compares the yearbooks' season production-stats pages (docs/season_stats/) with
the Repertoire tables (research.event), as a season checksum.

Level 1 -- city totals, per season. It needs no category or venue mapping:
  - stats count: sum of every printed line except subtotals (subtotals repeat
    their venue/part lines);
  - Repertoire count, two ways, to test how the yearbook counted a day with
    both a morning and an evening performance:
      sessions  = performed events (each утро/веч. row counted separately),
      days      = distinct (theater, date) among performed events;
    and, since later stats pages seem to leave out unreceipted performances,
      with_receipts = performed events that print receipts;
  - receipts: stats sum over lines that print receipts, vs the sum of
    research.event.receipts_total_kopecks. From 1898-99 the stats footnote says
    its receipts EXCLUDE charity performances, so the Repertoire receipts of
    events whose annotation contains "въ пользу" are reported alongside
    (information only, not subtracted: which events the yearbook treated as
    charity is not assumed).

Usage:
    uv run python pipeline/compare_season_stats.py --db outputs/full_run/imperial_theaters.duckdb \
        --out-dir outputs/season_stats_compare
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import duckdb

STATS_DIR = Path(__file__).resolve().parent.parent / "docs" / "season_stats"
CITY = {"С.-Петербургъ": "SP", "Москва": "Moscow"}


def stats_totals():
    tot = {}
    for r in csv.DictReader(open(STATS_DIR / "lines.csv", encoding="utf-8")):
        if r["line_kind"] == "subtotal":
            continue
        k = (r["season"], CITY[r["city"]])
        t = tot.setdefault(k, {"count": 0, "count_with_receipts": 0, "count_without_receipts": 0,
                               "receipts_kopecks": 0.0, "lines": 0})
        n = int(r["count"])
        t["count"] += n
        t["lines"] += 1
        if r["receipts_kopecks"] != "":
            t["receipts_kopecks"] += float(r["receipts_kopecks"])
            t["count_with_receipts"] += n
        else:
            t["count_without_receipts"] += n
    return tot


REP_SQL = """
with ev as (
  select e.season, e.city, e.event_id, e.theater_id, coalesce(e.date, e.event_id) as day_key,
         e.receipts_total_kopecks as k,
         coalesce(regexp_matches(lower(a.annotation), 'въ пользу'), false) as charity_text
  from research.event e
  left join analysis.event_entry a using (event_id)
  where e.event_status = 'performed'
)
select season, city,
       count(*) as sessions,
       count(distinct (theater_id, day_key)) as days,
       count(k) as sessions_with_receipts,
       coalesce(sum(k), 0) as receipts_kopecks,
       coalesce(sum(k) filter (where charity_text), 0) as receipts_charity_text_kopecks,
       count(*) filter (where charity_text) as sessions_charity_text
from ev group by all
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    con = duckdb.connect(a.db, read_only=True)
    rep = {(r[0], r[1]): r[2:] for r in con.execute(REP_SQL).fetchall()}
    st = stats_totals()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for (season, city) in sorted(st):
        s = st[(season, city)]
        sessions, days, n_rec, rk, rk_ch, n_ch = rep.get((season, city), (0,) * 6)
        rows.append({
            "season": season, "city": city,
            "stats_count": s["count"], "rep_sessions": sessions, "rep_days": days,
            "diff_sessions": sessions - s["count"], "diff_days": days - s["count"],
            "stats_count_with_receipts": s["count_with_receipts"],
            "stats_count_without_receipts": s["count_without_receipts"],
            "stats_receipts_rub": round(s["receipts_kopecks"] / 100, 2) if s["count_with_receipts"] else "",
            "rep_receipts_rub": round(rk / 100, 2),
            "diff_receipts_rub": round((rk - s["receipts_kopecks"]) / 100, 2) if s["count_with_receipts"] else "",
            "rep_sessions_with_receipts": n_rec,
            "diff_sessions_with_receipts": n_rec - s["count"],
            "rep_charity_text_sessions": n_ch,
            "rep_charity_text_receipts_rub": round(rk_ch / 100, 2),
        })
    out = a.out_dir / "city_totals.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{'season':8} {'city':6} {'stats':>5} {'sess':>5} {'days':>5} {'Δsess':>6} {'Δdays':>6} {'Δrec':>5} "
          f"{'stats rub':>12} {'rep rub':>12} {'Δ rub':>11} {'charity-text rub':>16}")
    for r in rows:
        print(f"{r['season']:8} {r['city']:6} {r['stats_count']:5} {r['rep_sessions']:5} {r['rep_days']:5} "
              f"{r['diff_sessions']:+6} {r['diff_days']:+6} {r['diff_sessions_with_receipts']:+5} {str(r['stats_receipts_rub']):>12} "
              f"{r['rep_receipts_rub']:12} {str(r['diff_receipts_rub']):>11} {r['rep_charity_text_receipts_rub']:16}")
    exact = sum(1 for r in rows if r["diff_sessions"] == 0)
    exact_d = sum(1 for r in rows if r["diff_days"] == 0)
    print(f"\n{len(rows)} city-seasons; exact count match: sessions {exact}, days {exact_d}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
