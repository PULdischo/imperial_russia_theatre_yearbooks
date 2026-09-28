"""Audit the Repertoire tables against the scan-verified productions lists
(raw.production_entry / raw.production_entry_performance, known_issues.md
#101). Read-only against the DuckDB file; writes CSVs for review.

The two sources are independent transcriptions of different parts of the
same yearbook, so a disagreement is a lead, not a verdict: it can be a
Repertoire misread, a list misread, a genuine print disagreement inside the
yearbook, or a matching limitation here. Nothing is corrected automatically.

Direction 1, list -> Repertoire (one row per printed list date):
  exact            same city, same date, same work
  excerpt          same date, matched through an excerpt row (Repertoire
                   work linked to the list's work via excerpt_of_work_id,
                   or a title containing the list title, e.g. "2-е д. бал.
                   Фіаметта")
  fuzzy            same date, only a near-identical title (difflib >= .8) --
                   a likely misread in one of the two sources
  nearby_date      not on that date, but the same work within +-3 days in
                   the same city (date misread or date-shift in either source)
  other_titles     the Repertoire has that city/date, but not this work
  no_event         the Repertoire has no performance at all that city/date
  impossible_date  the printed list date doesn't exist ("38 декабря")

Direction 2, Repertoire -> list (one row per Repertoire performance that the
lists don't account for), restricted to seasons/cities with a list:
  title_in_list_other_date   the work is on that season's list, but this date isn't
  ballet_not_in_list         a ballet-genre performance whose work isn't on the list

Usage:
    python pipeline/compare_productions_repertoire.py \
        --db outputs/full_run/imperial_theaters.duckdb \
        --out-dir outputs/ballet_productions_pilot/compare
"""
from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

import duckdb

_FOLD = str.maketrans({"ѣ": "е", "і": "и", "ѳ": "ф", "ё": "е", "ѵ": "и", "i": "и"})


def norm(title: str | None) -> str:
    """Comparison key only -- never written back. Folds pre-reform letters,
    drops final ъ, parentheticals, act/scene prefixes and punctuation, and
    keeps the part before an alternative title ("… или …")."""
    t = unicodedata.normalize("NFC", (title or "").lower()).translate(_FOLD)
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.split(r"\s+или\s+", t)[0]
    t = re.sub(r"ъ\b", "", t)
    t = re.sub(r"[^а-яa-z\s-]", " ", t)
    t = t.replace("-", " ")
    return re.sub(r"\s+", " ", t).strip()


def contains(big: str, small: str) -> bool:
    return len(small) >= 4 and re.search(rf"(^|\s){re.escape(small)}($|\s)", big) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    con = duckdb.connect(str(args.db), read_only=True)

    lst = con.execute("""
        SELECT e.production_entry_id, e.season, e.city, e.list_number, e.title,
               e.page_id, e.printed_page_number,
               p.production_performance_id, p.year_text, p.month_text, p.day_text,
               p.note, p.outside_total, CAST(p.date AS VARCHAR) AS date
        FROM raw.production_entry e JOIN raw.production_entry_performance p USING (production_entry_id)
        ORDER BY e.season, e.city, e.entry_order, p.date_order
    """).fetchall()
    lcols = ["production_entry_id", "season", "city", "list_number", "title", "page_id",
             "printed_page_number", "production_performance_id", "year_text", "month_text",
             "day_text", "note", "outside_total", "date"]
    lst = [dict(zip(lcols, r)) for r in lst]

    rep = con.execute("""
        SELECT e.event_id, e.season, e.city, t.canonical_name AS theater, e.date,
               e.date_verbatim, e.printed_page_number, p.performance_id,
               p.performance_order, p.verbatim_title, p.verbatim_genre,
               w.canonical_title, w.canonical_genre, pw.canonical_title AS parent_title
        FROM research.performance p
        JOIN research.event e USING (event_id)
        JOIN research.theater t ON t.theater_id = e.theater_id
        JOIN research.work w USING (work_id)
        LEFT JOIN research.work pw ON pw.work_id = w.excerpt_of_work_id
    """).fetchall()
    rcols = ["event_id", "season", "city", "theater", "date", "date_verbatim",
             "rep_printed_page", "performance_id", "performance_order", "verbatim_title",
             "verbatim_genre", "canonical_title", "canonical_genre", "parent_title"]
    rep = [dict(zip(rcols, r)) for r in rep]
    for r in rep:
        r["k_self"] = {norm(r["verbatim_title"]), norm(r["canonical_title"])} - {""}
        r["k_parent"] = norm(r["parent_title"])
    by_city_date = defaultdict(list)
    for r in rep:
        by_city_date[(r["city"], r["date"])].append(r)

    def how(list_key: str, r: dict) -> str | None:
        if list_key in r["k_self"]:
            return "exact"
        if r["k_parent"] and r["k_parent"] == list_key:
            return "excerpt"
        if any(contains(k, list_key) for k in r["k_self"]):
            return "excerpt"
        # the list's title is the fuller form ("Донъ-Кихотъ Ламанчскій" vs
        # the Repertoire's "Донъ-Кихотъ"): the Repertoire key starts it
        if any(len(k) >= 5 and list_key.startswith(k + " ") for k in r["k_self"]):
            return "exact"
        if any(SequenceMatcher(None, list_key, k).ratio() >= 0.8 for k in r["k_self"]):
            return "fuzzy"
        # a misspelled title inside an excerpt label ("2-е д. бал. Фіамметта")
        for k in r["k_self"]:
            words = k.split()
            n = len(list_key.split())
            for i in range(len(words) - n + 1):
                if SequenceMatcher(None, list_key, " ".join(words[i:i + n])).ratio() >= 0.8:
                    return "fuzzy"
        return None

    rank = {"exact": 0, "excerpt": 1, "fuzzy": 2}
    out1, claimed = [], set()
    for L in lst:
        key = norm(L["title"])
        row = dict(L, category="", rep_theater="", rep_title="", rep_date="",
                   rep_printed_page="", date_offset="", rep_titles_that_day="")
        if not L["date"]:
            row["category"] = "impossible_date"
            out1.append(row)
            continue
        hits = [(how(key, r), r) for r in by_city_date.get((L["city"], L["date"]), [])]
        hits = sorted([h for h in hits if h[0]], key=lambda h: rank[h[0]])
        if hits:
            kind, r = hits[0]
            claimed.add(r["performance_id"])
            row.update(category=kind, rep_theater=r["theater"], rep_title=r["verbatim_title"],
                       rep_date=r["date"], rep_printed_page=r["rep_printed_page"], date_offset=0)
        else:
            d0 = date.fromisoformat(L["date"])
            near = None
            for off in (1, -1, 2, -2, 3, -3):
                ds = (d0 + timedelta(days=off)).isoformat()
                for r in by_city_date.get((L["city"], ds), []):
                    k = how(key, r)
                    if k in ("exact", "excerpt"):
                        near = (off, r)
                        break
                if near:
                    break
            same_day = by_city_date.get((L["city"], L["date"]), [])
            row["rep_titles_that_day"] = " | ".join(
                f"{r['theater']}: {r['verbatim_title']}" for r in same_day)
            if near:
                off, r = near
                row.update(category="nearby_date", rep_theater=r["theater"],
                           rep_title=r["verbatim_title"], rep_date=r["date"],
                           rep_printed_page=r["rep_printed_page"], date_offset=off)
            elif same_day:
                row["category"] = "other_titles"
            else:
                row["category"] = "no_event"
        out1.append(row)

    # Direction 2: Repertoire performances the lists don't account for
    list_keys = defaultdict(set)
    for L in lst:
        list_keys[(L["season"], L["city"])].add(norm(L["title"]))
    covered = set(list_keys)
    near_claimed = {(r["rep_date"], r["rep_title"]) for r in out1 if r["category"] == "nearby_date"}
    out2 = []
    for r in rep:
        if (r["season"], r["city"]) not in covered or r["performance_id"] in claimed:
            continue
        if (r["date"], r["verbatim_title"]) in near_claimed:
            continue
        keys = list_keys[(r["season"], r["city"])]
        on_list = next((k for k in keys if how(k, r) in ("exact", "excerpt")), None)
        is_ballet = "бал" in ((r["verbatim_genre"] or "") + (r["canonical_genre"] or "")).lower()
        if on_list:
            cat = "title_in_list_other_date"
        elif is_ballet:
            cat = "ballet_not_in_list"
        else:
            continue
        out2.append({k: r[k] for k in rcols} | {"category": cat, "matched_list_key": on_list or ""})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("list_dates_vs_repertoire.csv", out1),
                       ("repertoire_not_in_lists.csv", out2)):
        with open(args.out_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    c1 = Counter(r["category"] for r in out1)
    c2 = Counter(r["category"] for r in out2)
    print(f"list dates: {len(out1)}  " + ", ".join(f"{k}={v}" for k, v in c1.most_common()))
    print(f"repertoire not accounted for: {len(out2)}  " + ", ".join(f"{k}={v}" for k, v in c2.most_common()))
    per = defaultdict(Counter)
    for r in out1:
        per[(r["season"], r["city"])][r["category"]] += 1
    print("\nper list (list dates): season city  n  exact+excerpt  fuzzy nearby other no_event")
    for (s, c), k in sorted(per.items()):
        n = sum(k.values())
        print(f"  {s} {c:6} {n:4} {k['exact'] + k['excerpt']:4}  {k['fuzzy']:3} {k['nearby_date']:3} "
              f"{k['other_titles']:3} {k['no_event']:3}")


if __name__ == "__main__":
    main()
