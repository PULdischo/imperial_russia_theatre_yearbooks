"""Compare the blind column-structure reads (align/reports/align_NN.csv) with the stored sessions (issue #151 follow-up 15).

    uv run python docs/eval/title_check_2026-10-10/align/compare_structure.py

Key = (page_id, theater, date label, occurrence), where the label is normalised to day number + first three letters of the
weekday and `occurrence` counts repeats of the same label within that theater in page order (a spread can print «7 Суббота»
twice). Read side: `subcells` (a dash cell, 0, counts as 1 because the stored data keeps a dark session for it). Stored side:
number of sessions of that theater with that label, from outputs/full_run/imperial_theaters.duckdb raw.event_entry in
event_id order. Writes align/discrepancies.csv (one row per differing key) and align/discrepant_columns.csv (page x theater).
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
TH = (("мар", "Мариинскій"), ("александр", "Александринскій"), ("михайл", "Михайловскій"), ("больш", "Большой"), ("мал", "Малый"), ("нов", "Новый"))


def theater(s: str) -> str:
    t = (s or "").lower().replace("ё", "е")
    for k, v in TH:
        if k in t:
            return v
    return (s or "").strip()


def norm_label(s: str) -> str:
    """Day number only: spread sessions are not stored in print order, and some stored labels carry a month name
    instead of a weekday. A day number can recur on one page (Dec 7 / Jan 7); both sides then sum over the repeats."""
    m = re.match(r"\s*(\d+)", (s or ""))
    return m.group(1) if m else (s or "").strip().lower()


def load_reads():
    """All report rows; where a page appears in more than one report (a re-read), the highest-numbered report wins."""
    by_page = {}
    for f in sorted(glob.glob(str(HERE / "reports" / "align_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r.get("page_id"):
                by_page.setdefault(r["page_id"], {}).setdefault(Path(f).name, []).append(r)
    rows = []
    for pid, files in by_page.items():
        fn = sorted(files)[-1]
        rows.extend((fn, r) for r in files[fn])
    return rows


def main():
    reads = load_reads()
    pages = sorted({r["page_id"] for _, r in reads})
    con = duckdb.connect(str(ROOT / "outputs/full_run/imperial_theaters.duckdb"), read_only=True)
    stored = defaultdict(list)  # (page, theater) -> [(label, event_id, time_of_day)]
    # pages photographed separately were stored under their own page id; their dates belong to the printed spread
    # image that carries them (1890-91: p015 = 28 Dec-2 Jan of pair014; p023 = 24-29 Mar of pair022, 30 Mar-12 Apr of pair024)
    def alias(pid, date):
        if pid == "repertoire_1890-91_p015":
            return "repertoire_1890-91_pair014"
        if pid == "repertoire_1890-91_p023":
            return "repertoire_1890-91_pair022" if str(date) <= "1891-03-29" else "repertoire_1890-91_pair024"
        return pid
    want = set(pages) | {"repertoire_1890-91_p015", "repertoire_1890-91_p023"}
    for pid, th, dt, ev, tod, du in con.execute(
        "select page_id, theater, date_text, event_id, time_of_day, date_undate from raw.event_entry where page_id in (select unnest(?)) order by event_id",
        [sorted(want)]).fetchall():
        stored[(alias(pid, du), theater(th))].append((norm_label(dt), ev, tod))
    read = defaultdict(list)
    for fn, r in reads:
        try:
            n = int(r["subcells"])
        except (TypeError, ValueError):
            n = 1
        read[(r["page_id"], theater(r["theater"]))].append((norm_label(r["date_label"]), max(n, 1), r.get("kind", ""), r.get("note", ""), r["date_label"]))
    disc, cols = [], defaultdict(list)
    for key in sorted(set(read) | set(stored)):
        pid, th = key
        if pid not in pages:
            continue
        R, S = defaultdict(list), defaultdict(list)
        for x in read.get(key, []):
            R[(x[0], 1)].append(x)
        for x in stored.get(key, []):
            S[(x[0], 1)].append(x)
        for k in sorted(set(R) | set(S), key=lambda x: int(x[0]) if x[0].isdigit() else 99):
            rn = sum(x[1] for x in R[k]) if k in R else None          # read: total sub-cells (dash counts 1)
            sn = len(S[k]) if k in S else None                          # stored: total sessions
            if sn is None and k in R and all(x[2] == "dash" for x in R[k]):
                continue                                                # a printed dash: the stored layer synthesises dark days later
            if rn != sn:
                kind = ",".join(sorted({x[2] for x in R[k]})) if k in R else ""
                note = " / ".join(x[3] for x in R[k] if x[3])[:80] if k in R else ""
                evs = ",".join(e.split("__")[-1] + ":" + (t or "") for _, e, t in S[k]) if k in S else ""
                disc.append((pid, th, k[0], k[1], rn, sn, kind, evs, note))
                cols[(pid, th)].append(k[0])
    with open(HERE / "discrepancies.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["page_id", "theater", "label", "occ", "read_subcells", "stored_sessions", "read_kind", "stored_events", "read_note"]); w.writerows(disc)
    with open(HERE / "discrepant_columns.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["page_id", "theater", "n_rows_differ", "labels"])
        for (pid, th), labs in sorted(cols.items()):
            w.writerow([pid, th, len(labs), " | ".join(labs)])
    print(f"{len(pages)} pages read; {len(read)} page-columns; {len(disc)} differing rows in {len(cols)} page-columns")


if __name__ == "__main__":
    main()
