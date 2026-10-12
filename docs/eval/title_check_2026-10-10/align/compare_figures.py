"""Compare the blind figure reads (align/reports_figures/figures_NN.csv) with the stored receipts figures (issue #151 follow-up 17).

    uv run python docs/eval/title_check_2026-10-10/align/compare_figures.py

Per (page, theater, day) the printed blocks (subcell order) are paired with the stored sessions (morning, evening, unspecified order)
and the figures compared in kopecks (half-kopecks kept). Writes align/figure_diffs.csv:
  FIG          both have a figure and they differ
  READ_ONLY    the scan prints a figure, the stored session has none
  STORED_ONLY  the stored session has a figure the reader did not see
  COUNT        a different number of blocks and sessions on that day (the rows are listed for a look)
and prints per-theater totals read vs stored for each page and for the two seasons.
"""
from __future__ import annotations

import csv
import glob
import re
from collections import defaultdict
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
con = duckdb.connect(str(ROOT / "outputs/full_run/imperial_theaters.duckdb"), read_only=True)
TH = (("мар", "MAR"), ("александр", "ALX"), ("михайл", "MIH"))


def th_key(s):
    t = (s or "").lower().replace("ё", "е")
    for k, v in TH:
        if k in t:
            return v
    return t[:3]


def money(s):
    """kopecks (float: a half-kopeck is .5) or None. Accepts `2789 р. 30 к.`, `2789 р. 30`, `55¹/₂ к.`, `1660 р.`, `605 р. — к.`."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    m = re.search(r"(\d[\d\s,.]*?)\s*р", s)
    if not m:
        return None
    rub = int(re.sub(r"[\s,.]", "", m.group(1)))
    rest = s[m.end():].lstrip(". ")
    k = re.match(r"(\d+)\s*(1/2|½|¹/₂|¹/2|\u00b9/\u2082)?", rest)
    kop = int(k.group(1)) if k else 0
    half = 0.5 if (k and k.group(2)) else (0.5 if re.search(r"(½|¹/₂|1/2)", rest) else 0.0)
    return rub * 100 + kop + half


def day(label):
    m = re.match(r"\s*(\d+)", label or "")
    return m.group(1) if m else None


def main():
    reads = defaultdict(list)       # (page, th, day) -> [(subcell, receipts, first_line, note, label)]
    pages = []
    for f in sorted(glob.glob(str(HERE / "reports_figures" / "figures_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if not r.get("page_id"):
                continue
            pages.append(r["page_id"])
            try:
                sc = int(r["subcell"])
            except (TypeError, ValueError):
                sc = 1
            reads[(r["page_id"], th_key(r["theater"]), day(r["date_label"]))].append(
                (sc, r["receipts"], r["first_line"], r["note"], r["date_label"]))
    pages = sorted(set(pages))
    order = {"morning": 0, "unspecified": 1, "evening": 2}
    stored = defaultdict(list)
    for pid, th, dt, ev, tod, rc in con.execute(
        "select page_id, theater, date_text, event_id, time_of_day, receipts_text from raw.event_entry where page_id in (select unnest(?)) order by event_id",
        [pages]).fetchall():
        stored[(pid, th_key(th), day(dt))].append((order.get(tod, 1), ev, rc))
    diffs = []
    tot_read = defaultdict(float)
    tot_st = defaultdict(float)
    keys = sorted(set(reads) | set(stored), key=lambda k: (k[0], k[1], int(k[2]) if k[2] and k[2].isdigit() else 0))
    for k in keys:
        if k[0] not in pages:
            continue
        R = sorted(reads.get(k, []), key=lambda x: x[0])
        S = sorted(stored.get(k, []), key=lambda x: (x[0], x[1]))
        for r in R:
            v = money(r[1])
            if v:
                tot_read[(k[0], k[1])] += v
        for s in S:
            v = money(s[2])
            if v:
                tot_st[(k[0], k[1])] += v
        # a dash cell stored as one empty session: nothing to compare
        rf = [r for r in R if (r[1] or "").strip() or (r[2] or "").strip() not in ("", "—", "-")]
        if len(R) == len(S) or (len(rf) == len(S)):
            use = R if len(R) == len(S) else rf
            for r, s in zip(use, S):
                a, b = money(r[1]), money(s[2])
                if a != b:
                    if a is not None and b is not None:
                        kind = "FIG"
                    elif a is not None:
                        kind = "READ_ONLY"
                    else:
                        kind = "STORED_ONLY"
                    diffs.append((kind, k[0], k[1], r[4], r[0], r[1], s[2], s[1].split("__")[-1], r[2], r[3]))
        else:
            diffs.append(("COUNT", k[0], k[1], (R[0][4] if R else k[2]), "", " ; ".join(f"{x[1]}" for x in R),
                          " ; ".join(f"{x[2]}" for x in S), ",".join(x[1].split("__")[-1] for x in S), "", ""))
    with open(HERE / "figure_diffs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "page_id", "theater", "date_label", "subcell", "read", "stored", "event", "first_line", "note"])
        w.writerows(diffs)
    n = defaultdict(int)
    for d in diffs:
        n[d[0]] += 1
    print(f"{len(pages)} pages read; differences: {dict(n)}")
    by_season = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    for (p, t) in set(tot_read) | set(tot_st):
        season = p.split("_")[1]
        by_season[season][t][0] += tot_read.get((p, t), 0)
        by_season[season][t][1] += tot_st.get((p, t), 0)
    for season, d in sorted(by_season.items()):
        print(season, {t: f"read {v[0]/100:,.2f} stored {v[1]/100:,.2f} (stored-read {(v[1]-v[0])/100:+,.2f})" for t, v in d.items()})


if __name__ == "__main__":
    main()
