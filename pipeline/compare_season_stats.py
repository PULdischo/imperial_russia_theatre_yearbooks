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

Level 2 -- families (the stats page's categories) and venues. Each performed
Repertoire session is sorted into a family by explicit rules (classify_work /
classify_event below), each derived from what the data shows, not assumed:
  - a Latin-script title is a foreign performance: genre "op."/"oper." = foreign
    opera (Italian opera at the Большой, German opera at the Маріинскій 1897-98);
    German genre words or German function words in the title = German; otherwise
    French;
  - Cyrillic: genre containing "бал" = ballet; "оп." (exactly, or starting "оп."
    but not "опер"/"оперет") = opera; "феер" = feerie; everything else = Russian
    drama. "опер." is operetta by the drama company (Александринскій/Малый titles
    such as "Не бывать бы счастью"), so it stays drama;
  - a title containing "концерт" is a concert part. It doesn't count as a family
    when other works share the bill (the 1897-98 "(русская драма, опера и балетъ)"
    line is Женитьба + Концертное отдѣленіе + Пахита); alone it makes a concert;
  - a genre-less work takes its family from an excerpt marker in its title
    ("3-е д. бал. Пахита"); otherwise it is neutral (benefit headings stored as
    works, "Гимнъ", "Дивертиссементъ"), and an event of only neutral works counts
    as drama;
  - an event whose works fall in more than one family is "mixed", and its
    combination is kept. (A "drama + opera/ballet counts as opera/ballet"
    convention was tried on 2026-09-30 and dropped: its apparent gain came from
    genre-less works defaulting to drama, and once those were classified it no
    no longer earned its place: 57 exact / total |difference| 710 without it,
    55 / 662 with it, and the remaining gain came from bills this classifier still
    misreads -- an opera's prologue printed "прологъ, др.", comedy-ballets
    ("ком.-бал."), an opera-vaudeville ("оп.-вод.").)
Stats lines map to families by their category text (STATS_FAMILY). Lines naming
a single guest company (Режанъ, Тина ди Лоренцо, Лессингъ-театръ), the drama-school
performance and the music-literary evenings go to "other".

Level 3 -- ballet performances per season-city, three ways (2026-09-30):
  - stats page: "Балетныхъ" + the "Смѣшанныхъ" lines whose qualifier includes
    балет + "Феерій" (only Кольцо любви, Moscow 1892-94). "Смѣшанныхъ" lines
    printed WITHOUT a qualifier (1898-99 SP, 1899-00 MSK, 1900-01 SP, 1901-02 MSK,
    1903-04 MSK, 1908-09 MSK) may or may not include a ballet; they are reported
    separately (stats_mixed_unqualified) with a second verdict counting them in.
    E.g. 1899-00 MSK footnote 12: the Bolshoi 75th anniversary + an "(опера и
    балетъ)" charity bill, both with a listed ballet in the Repertoire;
  - ballet productions list: performances implied by its dates. Per date, the
    larger of (a) what the list states itself -- the same ballet printed twice on
    one date (утро/вечеръ rows) or a "2 раза" note -- and (b) the number of
    separate Repertoire sessions that day playing one of that date's listed
    ballets, capped at the number of list rows for the date. (b) only decides
    whether entries sharing a date are one double bill or a matinée plus an
    evening; the cap means it can never add a performance the list doesn't print;
  - Repertoire: performed sessions that include a work with parent_genre ballet.
  Matching of list dates to Repertoire sessions is build_research_model.ballet_list_matches.

Usage:
    uv run python pipeline/compare_season_stats.py --db outputs/full_run/imperial_theaters.duckdb \
        --out-dir outputs/season_stats_compare
"""
from __future__ import annotations

import argparse
import csv
import re
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


STATS_FAMILY = {
    "Русскихъ драматическихъ": "drama",
    "Оперныхъ": "opera", "Русскихъ оперныхъ": "opera", "Оперныхъ въ Великомъ посту": "opera",
    "Балетныхъ": "ballet",
    "Французскихъ": "french",
    "Нѣмецкихъ": "german", "Нѣмецкихъ драматическихъ": "german",
    "Нѣмецкихъ оперныхъ": "foreign_opera", "Итальянскихъ оперныхъ": "foreign_opera",
    "Смѣшанныхъ": "mixed",
    "Концертовъ": "concert",
    "Феерій": "feerie",
}
VENUE = {"Александринскомъ": "Александринскій", "Михайловскомъ": "Михайловскій", "Маріинскомъ": "Маріинскій",
         "Маломъ": "Малый", "Большомъ": "Большой", "Новомъ": "Новый"}
LATIN = re.compile(r"^[\W\d]*[A-Za-zÀ-ÿ]")
GERMAN_GENRE = re.compile(r"lustsp|schausp|schwank|comöd|komöd|posse|trauersp|volksst|charakterb|genreb", re.I)
GERMAN_WORD = re.compile(r"\b(der|die|das|und|ein|eine|im|vom|zum|zur|dem|den)\b|[äöüß]", re.I)


def classify_work(title, genre):
    title, g = title or "", (genre or "").lower().strip()
    if "концерт" in title.lower():
        return "concert"
    # A Cyrillic genre decides the family even for a Latin title ("Viola tricolor,
    # ком." at the Малый, "Virtus antiqua, сказка" at the Александринскій are
    # Russian productions); only a Latin or missing genre falls to the Latin rule.
    if LATIN.match(title) and not re.search(r"[а-яё]", g):
        if g in ("op.", "oper.", "op", "oper"):
            return "foreign_opera"
        # German genre words are often printed inside the title ("Grossmama, Schwank")
        if GERMAN_GENRE.search(g) or GERMAN_GENRE.search(title) or GERMAN_WORD.search(title):
            return "german"
        return "french"
    if "бал" in g:
        return "ballet"
    if g == "оп." or g == "оп" or (g.startswith("оп.") and not g.startswith("опер")):
        return "opera"
    if "феер" in g:
        return "feerie"
    if not g:
        # No genre: an excerpt carries it inside the title ("3-е д. бал. Пахита",
        # "1-е д. оп. Невѣста-лунатикъ"); anything else genre-less (a benefit heading
        # stored as a work, "Гимнъ", "Дивертиссементъ", "Апоѳеозъ") is neutral and
        # doesn't decide the event's family.
        tl = title.lower()
        if re.search(r"\bбал(\.|ета)", tl):
            return "ballet"
        if re.search(r"\bоп(\.|еры)", tl):
            return "opera"
        return "unmarked"
    return "drama"


def classify_event(fams):
    fams = set(fams)
    core = fams - {"concert", "unmarked"}
    if not core:
        if "concert" in fams:
            return "concert"
        return "drama" if "unmarked" in fams else "no_works"
    if len(core) == 1:
        return next(iter(core))
    return "mixed:" + "+".join(sorted(core))


LEVEL2_SQL = """
select e.event_id, e.season, e.city, t.canonical_name, e.receipts_total_kopecks,
       p.verbatim_title, coalesce(w.canonical_genre, p.verbatim_genre)
from research.event e join research.theater t using (theater_id)
left join research.performance p using (event_id) left join research.work w using (work_id)
where e.event_status = 'performed'
"""


def level2(con, out_dir):
    ev = {}
    for eid, season, city, th, k, title, genre in con.execute(LEVEL2_SQL).fetchall():
        e = ev.setdefault(eid, {"season": season, "city": city, "theater": th, "k": k, "fams": []})
        if title is not None:
            e["fams"].append(classify_work(title, genre))
    rep = {}
    for e in ev.values():
        cls = classify_event(e["fams"])
        fam = "mixed" if cls.startswith("mixed:") else cls
        for key in [(e["season"], e["city"], fam, ""), (e["season"], e["city"], fam, e["theater"])]:
            r = rep.setdefault(key, {"n": 0, "k": 0, "n_k": 0, "combos": {}})
            r["n"] += 1
            if e["k"] is not None:
                r["k"] += e["k"]; r["n_k"] += 1
            if fam == "mixed":
                r["combos"][cls[6:]] = r["combos"].get(cls[6:], 0) + 1
    st = {}
    for r in csv.DictReader(open(STATS_DIR / "lines.csv", encoding="utf-8")):
        if r["line_kind"] == "subtotal":
            continue
        fam = STATS_FAMILY.get(r["category"], "other")
        city = CITY[r["city"]]
        venue = next((v for k, v in VENUE.items() if k in r["venue_verbatim"]), "")
        keys = [(r["season"], city, fam, "")] + ([(r["season"], city, fam, venue)] if venue else [])
        for key in keys:
            s = st.setdefault(key, {"n": 0, "k": 0.0, "n_k": 0, "labels": []})
            s["n"] += int(r["count"])
            if r["receipts_kopecks"] != "":
                s["k"] += float(r["receipts_kopecks"]); s["n_k"] += int(r["count"])
            s["labels"].append(r["category_verbatim"] + (" " + r["qualifier_verbatim"] if r["qualifier_verbatim"] else ""))
    seasons = {k[0] for k in st}
    rows = []
    # family rows: every family either side has, for stats seasons; venue rows: only where the stats print a venue line
    keys = {k for k in st} | {k for k in rep if k[0] in seasons and k[3] == ""}
    for key in sorted(keys):
        s = st.get(key, {"n": 0, "k": 0.0, "n_k": 0, "labels": []})
        r = rep.get(key, {"n": 0, "k": 0, "n_k": 0, "combos": {}})
        comparable_k = s["n_k"] > 0 and s["n_k"] == s["n"]
        rows.append({
            "season": key[0], "city": key[1], "family": key[2], "venue": key[3],
            "stats_count": s["n"], "rep_sessions": r["n"], "diff": r["n"] - s["n"],
            "stats_receipts_rub": round(s["k"] / 100, 2) if s["n_k"] else "",
            "rep_receipts_rub": round(r["k"] / 100, 2),
            "diff_receipts_rub": round((r["k"] - s["k"]) / 100, 2) if comparable_k else "",
            "rep_sessions_with_receipts": r["n_k"],
            "stats_lines": " | ".join(s["labels"]),
            "rep_mixed_combos": "; ".join(f"{c} {n}" for c, n in sorted(r["combos"].items(), key=lambda x: -x[1])),
        })
    out = out_dir / "family_totals.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    fam_rows = [r for r in rows if r["venue"] == ""]
    exact = sum(1 for r in fam_rows if r["diff"] == 0)
    print(f"\nlevel 2: {len(fam_rows)} season-city-family rows, {exact} exact; "
          f"{len(rows) - len(fam_rows)} venue rows, {sum(1 for r in rows if r['venue'] and r['diff'] == 0)} exact")
    print(f"wrote {out}")
    return rows


def ballet_counts(con, out_dir):
    from build_research_model import ballet_list_matches
    from collections import defaultdict
    rows_by_date = defaultdict(list)
    for season, city, d, title, note in con.execute("""
        SELECT e.season, e.city, strftime(p.date, '%Y-%m-%d'), e.title, p.note
        FROM raw.production_entry_performance p JOIN raw.production_entry e USING (production_entry_id)
        WHERE p.date IS NOT NULL AND NOT p.outside_total""").fetchall():
        rows_by_date[(season, city, d)].append((title, 2 if note and "2 раза" in note else 1))
    matched = defaultdict(set)
    for season, city, d, _title, _note, eid, _wid, _p in ballet_list_matches(con):
        matched[(season, city, d)].add(eid)
    list_perf = {}
    for k, rows in rows_by_date.items():
        per_title = defaultdict(int)
        for title, n in rows:
            per_title[title] += n
        explicit = max(per_title.values())
        n_rows = sum(n for _, n in rows)
        list_perf[k] = max(explicit, min(n_rows, len(matched.get(k, ()))))
    rep_by_date = defaultdict(list)
    for season, city, d, th, tod, titles in con.execute("""
        SELECT e.season, e.city, e.date, t.canonical_name, a.time_of_day, string_agg(DISTINCT p.verbatim_title, ' / ')
        FROM research.event e JOIN research.theater t USING (theater_id)
        JOIN analysis.event_entry a USING (event_id) JOIN research.performance p USING (event_id)
        JOIN research.work w USING (work_id)
        WHERE e.event_status = 'performed' AND w.parent_genre = 'ballet' GROUP BY ALL""").fetchall():
        rep_by_date[(season, city, d)].append(f"{th} {tod}: {titles}")
    st = defaultdict(lambda: [0, 0, 0, 0])
    for r in csv.DictReader(open(STATS_DIR / "lines.csv", encoding="utf-8")):
        if r["line_kind"] == "subtotal":
            continue
        k = (r["season"], CITY[r["city"]])
        if r["category"] == "Балетныхъ":
            st[k][0] += int(r["count"])
        elif r["category"] == "Смѣшанныхъ" and "балет" in r["qualifier_verbatim"]:
            st[k][1] += int(r["count"])
        elif r["category"] == "Смѣшанныхъ" and not r["qualifier_verbatim"]:
            st[k][3] += int(r["count"])
        elif r["category"] == "Феерій":
            st[k][2] += int(r["count"])
    seasons = sorted({(k[0], k[1]) for k in list_perf} & set(st))
    out, detail = [], []
    for season, city in seasons:
        L = sum(v for k, v in list_perf.items() if k[:2] == (season, city))
        R = sum(len(v) for k, v in rep_by_date.items() if k[:2] == (season, city))
        S = sum(st[(season, city)][:3])
        U = st[(season, city)][3]

        def verdict_for(s):
            return ("all agree" if s == L == R else "stats = list" if s == L else "list = Repertoire" if L == R
                    else "stats = Repertoire" if s == R else "all differ")
        verdict = verdict_for(S)
        out.append({"season": season, "city": city, "stats_ballet": st[(season, city)][0],
                    "stats_mixed_with_ballet": st[(season, city)][1], "stats_feerie": st[(season, city)][2],
                    "stats_total": S, "list_performances": L, "rep_sessions": R, "verdict": verdict,
                    "stats_mixed_unqualified": U,
                    "verdict_with_unqualified": verdict_for(S + U) if U else ""})
        for k in sorted({k for k in list(list_perf) + list(rep_by_date) if k[:2] == (season, city)}):
            lp, rp = list_perf.get(k, 0), len(rep_by_date.get(k, []))
            if lp != rp:
                detail.append({"season": season, "city": city, "date": k[2], "list_performances": lp,
                               "rep_sessions": rp, "list_titles": " / ".join(t for t, _ in rows_by_date.get(k, [])),
                               "rep_sessions_detail": " | ".join(rep_by_date.get(k, []))})
    for name, rows in (("ballet_counts.csv", out), ("ballet_count_dates.csv", detail)):
        with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    from collections import Counter
    print(f"\nlevel 3 (ballet counts): {len(out)} season-cities: {dict(Counter(r['verdict'] for r in out))}; "
          f"{len(detail)} dates where list and Repertoire differ")
    return out


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
    level2(con, a.out_dir)
    ballet_counts(con, a.out_dir)


if __name__ == "__main__":
    main()
