"""Diff the detail reads (align/reports_detail/detail_NN.csv) against the stored sessions of the same cell
(issue #151 follow-up 15).

    uv run python docs/eval/title_check_2026-10-10/align/compare_detail.py

For every (page, theater, day) cell in chunks_detail/: the printed sub-cells (receipts, lines) are matched to the stored
sessions of that theater and day by receipts figure first, then by title overlap. Writes align/detail_verdicts.csv:

  OK_COUNT        same number of sub-cells and sessions, every one matched (the structure difference was a label/rule question)
  FALSE_SPLIT     one printed block holds the works of two stored sessions
  EXTRA_STORED    one printed block, two stored sessions, only one matches (the other is a duplicate / displaced cell)
  MERGED          one stored session holds the works (or receipts) of two printed sub-cells
  MISSING         a printed sub-cell with content matches no stored session
  CHECK           anything else, read the rows
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
TH = (("мар", "Мар"), ("александр", "Але"), ("михайл", "Мих"), ("больш", "Бол"), ("мал", "Мал"), ("нов", "Нов"))


def th_key(s):
    t = (s or "").lower().replace("ё", "е")
    for k, v in TH:
        if k in t:
            return v
    return t[:3]


def money(s):
    m = re.search(r"(\d[\d\s]*)\s*р\.?\s*(\d+|—|-)?", s or "")
    if not m:
        return None
    rub = re.sub(r"\s", "", m.group(1))
    kop = m.group(2) if m.group(2) not in (None, "—", "-") else "0"
    return (int(rub), int(kop))


_PAGE_CACHE = {}


def page_figures(pid):
    """money tuple -> [(event_id, date_text, theater)] for every stored session of the page."""
    if pid not in _PAGE_CACHE:
        d = defaultdict(list)
        for ev, dt, th, rc in con.execute("select event_id, date_text, theater, receipts_text from raw.event_entry where page_id=?", [pid]).fetchall():
            m = money(rc)
            if m and m != (0, 0):
                d[m].append((ev.split("__")[-1], dt, th))
        _PAGE_CACHE[pid] = d
    return _PAGE_CACHE[pid]


def norm(t):
    t = (t or "").lower().replace("ё", "е").replace("ѣ", "е").replace("і", "и").replace("ѳ", "ф")
    t = re.sub(r"[^\w]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def stem(t):
    n = norm(t)
    n = re.sub(r"\b(ком|др|оп|бал|вод|сц|ш|карт|пьеса|фарс|тр|траг|com|vaud|drame|drame|pièce|piece)\b\s*$", "", n).strip()
    return n[:14]


def main():
    cells = []
    for f in sorted(glob.glob(str(HERE / "chunks_detail" / "detail_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            cells.append((Path(f).name.replace(".csv", ""), r["page_id"], r["theater"], r["date_label"]))
    reads_by_file = defaultdict(lambda: defaultdict(list))   # cell -> report file -> sub-cell rows
    for f in sorted(glob.glob(str(HERE / "reports_detail" / "detail_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            reads_by_file[(r["page_id"], th_key(r["theater"]), re.match(r"\s*(\d+)", r["date_label"]).group(1))][Path(f).name].append(r)
    reads = {k: v[sorted(v)[0]] for k, v in reads_by_file.items()}          # first read decides the verdict

    def sig(rows):
        return sorted((str(money(r["receipts"])), tuple(sorted({stem(x) for x in (r["lines"] or "").split("|") if stem(x)}))) for r in rows)
    out = []
    for chunk, pid, th, label in cells:
        day = re.match(r"\s*(\d+)", label).group(1)
        sub = reads.get((pid, th_key(th), day))
        if not sub:
            out.append((chunk, pid, th, label, "NOT_READ", "", "", "", "", ""))
            continue
        # stored sessions of that cell
        sts = []
        for ev, tod, rc, ann in con.execute(
            "select event_id, time_of_day, receipts_text, annotation from raw.event_entry where page_id=? and regexp_matches(date_text, ?) order by event_id",
            [pid, r"^\s*" + day + r"\b"]).fetchall():
            if th_key(con.execute("select theater from raw.event_entry where event_id=?", [ev]).fetchone()[0]) != th_key(th):
                continue
            titles = [t for (t,) in con.execute("select performance_title from raw.event_entry_performance where event_id=? order by performance_order", [ev]).fetchall()]
            sts.append({"ev": ev, "tod": tod, "rc": money(rc), "rct": rc, "titles": titles, "stems": {stem(t) for t in titles if stem(t)}, "ann": ann})
        subs = []
        for r in sub:
            lines = [x.strip() for x in (r["lines"] or "").split("|")]
            subs.append({"label": r["label"], "rc": money(r["receipts"]), "rct": r["receipts"], "lines": lines,
                         "stems": {stem(x) for x in lines if stem(x)}, "dash": (r["lines"] or "").strip() in ("—", "-", "")})
        # which stored sessions does each print sub-cell match?
        def matches(sc, st):
            if sc["rc"] and st["rc"] and sc["rc"] == st["rc"]:
                return True
            return any(a[:10] and a[:10] == b[:10] for a in sc["stems"] for b in st["stems"])
        M = {i: [j for j, st in enumerate(sts) if matches(sc, st)] for i, sc in enumerate(subs)}
        content = [i for i, sc in enumerate(subs) if not sc["dash"]]
        n_p, n_s = len(subs), len(sts)
        # which print sub-cells each stored session matches
        back = {j: [i for i in range(len(subs)) if j in M[i]] for j in range(n_s)}
        verdict = "CHECK"
        if any(not M[i] for i in content):
            verdict = "MISSING"
        elif any(len(v) >= 2 for v in back.values()):
            verdict = "MERGED"
        elif n_p == 1 and n_s >= 2 and len(M[0]) >= 2:
            verdict = "FALSE_SPLIT"
        elif n_p == 1 and n_s >= 2 and len(M[0]) == 1:
            verdict = "EXTRA_STORED"
        elif n_p == n_s:
            verdict = "OK_COUNT"
        elif n_p > n_s and all(M[i] for i in content):
            verdict = "OK_COUNT" if len(content) <= n_s else "MERGED"
        where = []
        for i, sc in enumerate(subs):
            if sc["rc"] and not any(sc["rc"] == st["rc"] for st in sts):
                hits = [h for h in page_figures(pid).get(sc["rc"], [])]
                where.append(f"{sc['rct']} -> " + ("; ".join(f"{h[0]} '{h[1]}' {h[2][:5]}" for h in hits) if hits else "NOT ON PAGE"))
        files = reads_by_file[(pid, th_key(th), day)]
        agree = "single read"
        if len(files) >= 2:
            sigs = [sig(v) for _, v in sorted(files.items())]
            agree = "reads agree" if all(x == sigs[0] for x in sigs[1:]) else "READS DISAGREE"
        verdict = verdict + " | " + agree
        out.append((chunk, pid, th, label, verdict, n_p, n_s,
                    " // ".join(f"[{sc['label'] or '-'}] {sc['rct'] or '-'} :: {' | '.join(sc['lines'])[:70]}" for sc in subs),
                    " // ".join(f"{st['ev'].split('__')[-1]}:{st['tod']} {st['rct'] or '-'} :: {' | '.join(st['titles'])[:60]}" for st in sts),
                    " ; ".join(where)))
    with open(HERE / "detail_verdicts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chunk", "page_id", "theater", "day", "verdict", "n_print", "n_stored", "print", "stored", "unmatched_figures_elsewhere_on_page"])
        w.writerows(out)
    import collections
    print(collections.Counter(r[4] for r in out))


if __name__ == "__main__":
    main()
