"""Stage 6a: builds a `research` schema -- the final, simplified,
directly-queryable layer docs/entity_centric_model.md proposed: Person,
Work, Theater, Event, Performance, Person_appearance, with foreign keys
baked in directly rather than crosswalked at query time. This is the
layer meant to be published/browsed. The working `entities` schema
(person_link, work_link, person_candidate, person_merge_log,
person_wikidata_link, work_genre_candidate) is untouched by this script --
it stays exactly as it is, the pipeline's own audit/working layer
underneath, same relationship `entities` itself has to `raw`/`analysis`.

Six tables, six decisions each already made and checked against the real
data before building (docs/entity_centric_model.md, and the conversation
that resolved its two open questions):

- `person`: only currently-active (non-superseded) people -- the merge
  decision itself (`superseded_by_person_id`, `person_merge_log`) is
  pipeline history, not something a researcher browsing the final table
  needs to see. `wikidata_qid`/`wikidata_label`/`wikidata_description`
  are inlined directly (1:1 today, so no separate link table is needed)
  rather than kept as their own table.
- `work`: unchanged from entities.work -- already the clean output of
  docs/work_normalization.md.
- `theater`: unchanged from entities.theater.
- `event` kept distinct from `performance` deliberately: 6,158 of
  17,345 events (35%) list more than one work, and receipts are printed
  once per event, not once per work -- flattening them into one row per
  (work, event) would silently duplicate receipts on every multi-work
  night. Receipts live ONLY on `event`, so `SUM(receipts_total_kopecks)`
  over `event` is always safe; `performance` never carries receipts at
  all, precisely so summing it can't overcount. (Renamed from `session`/
  `performance_session` per RG's docs/schema.md revision -- "session" was
  ambiguous with a login/browser session, "event" matches the
  raw.event_entry naming this now derives from.)
- `event.date` is the best-available date: the run-corroborated
  correction from docs/performance_normalization.md when there is one,
  otherwise the original computed date. `date_confidence` always travels
  alongside it (never silently hidden), including a distinct
  'synthesized_gap' value for the not_captured completeness placeholders
  analysis.event_entry already synthesizes -- those never went
  through date validation (they have no real printed date_text to
  validate against) and calling them 'unparseable' would misrepresent a
  deliberate completeness signal as a data-quality failure.
- `performance`'s own PK is `performance_id`, distinct from `work_id` --
  raw.event_entry_performance's own PK is also named `performance_id`,
  and reusing `work_id` here would collide with entities.work.work_id's
  different meaning (the exact collision docs/entity_centric_model.md
  flagged and this project already worked around once by aliasing to
  `raw_performance_id` on entities.work_link).
- `person_appearance` kept as its own table (not folded into `person` as
  a nested column, not merged into `performance`): a roster appearance is
  a season-level employment fact, not tied to a specific work performance
  at all, and a person can have many of them -- a real many-to-many
  relationship between person and their printed appearances, not a
  property of the person record itself.

Usage:
    python pipeline/build_research_model.py --db outputs/full_run/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

# docs/eval/known_issues.md #26/#28/#30/#33: confirmed non-person
# entities.person records -- role/department headings, footnote
# fragments, and resignation-note text that the extraction captured as
# if each were its own person. entities.person/entities.person_link are
# left exactly as-is (same "tag rather than delete, raw/entities stay
# untouched" policy as issue #26 always intended) -- these five UUIDs are
# excluded only here, at the point where the *published* research layer
# is built, so a future query against entities can still find them if
# ever useful. This is a deliberately small, hand-verified seed list, not
# the full backlog issue #26 originally estimated at 40+ raw rows (most
# of those, in Graduates, were never individually confirmed against a
# person_id the way these five were) -- extend it here as more are
# confirmed, rather than re-solving this from scratch each time.
NON_PERSON_IDS = [
    "5d9f7500-2be2-408e-a983-a01183626b09",  # "Священникъ" (Priest) -- a role heading, TheaterSchoolStaff, not a person
    "785816e3-1a1d-4df7-81b4-fcddc4b2d7d2",  # "Дьяконъ" (Deacon) -- a role heading, TheaterSchoolStaff, not a person
    "d4eaea08-f4d3-4413-8ff8-0d381a8395d5",  # "Оставилъ службу" -- issue #28's orphaned resignation note, TheaterSchoolStaff
    "23bf557c-76fe-497b-9fab-ebf1fdd7eab3",  # "†" -- an orphaned death-marker footnote, TheaterSchoolStaff (issue #30)
    "2e495ee0-94af-4350-9a7a-b9471f4de613",  # "И." -- a mangled "и.д. фельдшерицы" role heading, TheaterSchoolStaff (issue #30)
    "37dd8b11-7b83-4cb0-9d86-f5f34e611859",  # "Прикомандированъ къ Монтіровочной части..." -- a job-duty description captured as if it were a name, BalletArtists (issue #36); a single isolated entry_id (balletartists_1899-00_SP_p000__e008), confirmed via entities.person_link before excluding
]


# Research-layer-only page date fixes (RG, 2026-09-26, docs/eval/known_issues.md
# #93): pages whose printed header genuinely can't be parsed, so raw/analysis
# leave date_undate NULL (verbatim, deliberately not bent around in
# parse_and_validate.py). Maps page_id -> (year, month) for the whole page;
# research.event.date is then built from each row's own printed day number.
# Only for pages that do NOT cross a month boundary -- a crossing page would
# need a per-row month, not a page-wide one.
RESEARCH_PAGE_MONTH_OVERRIDES = {
    # header printed "8 сен тября. 1908 г. 17 сентября." -- a type gap inside
    # the month word; 8-17 Sep 1908, single month (scan-verified).
    "repertoire_1908-09_p003": (1908, 9),
}


#: Pages left out of the research layer entirely (raw/analysis keep them verbatim).
#: Only for a page that is superfluous in the print itself, never for a page
#: that is merely hard to read. page_id -> reason. The build warns if a page_id
#: is not in analysis.event_entry, so a renamed page doesn't go unnoticed.
RESEARCH_EXCLUDED_PAGES = {
    # Why (scan-checked by RG; NOT a duplicate of p. 56). In 1910-11's May pages each date range runs
    # as a St Petersburg page followed by a Moscow page: p. 54 = SP 1-9 May, p. 55 = Moscow 1-9 May
    # (all dashes), p. 56 = SP 10-19 May. Moscow's 10-19 May page belongs at p. 57, but p. 57 carries
    # the SP heading and columns with every cell a dash; its Mikhailovsky cells are empty where p. 56
    # has performances on 10-15 May, and its typesetting differs from p. 56. Most likely it is Moscow's
    # blank page printed from the SP form by mistake. Faint show-through from its back appears to be
    # the season totals, so it is the last page of the tables. This is an INFERENCE from page order and
    # layout, not something the print states.
    "repertoire_1910-11_p056": (
        "printed p. 57: SP heading and columns, every cell a dash, Mikhailovsky empty where p. 56 has "
        "performances on 10-15 May; most likely Moscow's blank 10-19 May page printed from the SP form "
        "by mistake (inference from page order and layout; not a duplicate of p. 56). Kept verbatim "
        "in raw (RG, 2026-10-06; reason re-recorded 2026-10-09)"),
}


#: Research-layer-only genre assignments by work title (RG, 2026-09-29, issue
#: #114). The raw tier keeps the printed genre verbatim -- a ballet
#: divertissement is printed with no genre abbreviation at all ("Балетный
#: дивертиссементъ."), and raw stays that way -- but research.work gives it
#: the ballet genre. Each rule is (regex on entities.work.canonical_title,
#: canonical_genre to assign, reason). Anchored on the title's own word
#: "Балетный", so a mixed "Концертный и балетный дивертиссемент" or a plain
#: "Дивертиссементъ" is NOT caught (those are open questions, not ballet by
#: default). The build fails if a rule matches no work.
RESEARCH_GENRE_RULES = [
    (r"^Балетный дивертисс?е?ментъ?\.?$", "бал.",
     "ballet divertissement: printed without a genre; ballet assigned in the research layer (RG, issue #114)"),
]


#: Research-layer-only work-title corrections for confirmed genuine print
#: typos (RG, 2026-09-30, issue #119). The raw tier keeps the exact printed
#: letterform verbatim -- e.g. "Шоиеніана" is what's actually printed on
#: repertoire_1909-10_p047 (RG re-read the scan directly: the disputed
#: letter is и, not ж or п) -- but research.work canonicalizes to the
#: intended title. Each entry is (verbatim entities.work.canonical_title,
#: corrected title, reason). The build fails if an entry matches no work,
#: so a title that's since changed (re-canonicalized, fixed upstream) is
#: caught rather than silently orphaned.
RESEARCH_TITLE_CORRECTIONS = {
    "Шоиеніана": ("Шопеніана",
                  "genuine print typo (и for п); Fokine's ballet \"Chopiniana\", "
                  "Mariinsky, premiered 1907 -- no ballet named \"Шоиеніана\" exists"),
}


#: Research-layer display override for a person (RG, 2026-10-05): entities.person
#: recomputes display_name by majority vote of the printed spellings on every
#: build_entities run, so a hand-chosen form cannot live there. Raw stays verbatim.
#: person_id -> (display_name, canonical_first_name, reason). The build fails if the
#: id is not a live person, so a later merge/split cannot silently orphan an entry.
RESEARCH_PERSON_DISPLAY_OVERRIDES = {
    "09350cda-ddf5-44b3-8b3e-d0db2e5e1259": (
        "Чекетти, Энрико Цезаревичъ", "Энрико",
        "Enrico Cecchetti: the company lists (BalletArtists, 19 entries) print the Russianized "
        "\"Генрихъ\", the school staff lists (8 entries) print \"Энрико\"; one man, merged 2026-10-05; "
        "RG chose the Italian form, the one used in Wikidata and the literature"),
}


#: Parent genre (RG, 2026-09-30; the name may change). A work that the yearbook
#: prints in its ballet productions lists ("Списокъ пьесъ … Балетъ", 1890-91 to
#: 1904-05) has parent genre "ballet", whatever its printed genre -- e.g. Кольцо
#: любви, printed "феерія" in the Repertoire and "Волшебная сказка" in the list.
#: The printed genre stays in canonical_genre. A work counts as listed when a
#: Repertoire performance of it falls on one of the list's dates in the same
#: city under the list's title: equal after compare_productions_repertoire.norm,
#: or an excerpt of it (its parent work, or the list title inside its own title).
#: Nothing fuzzy. RG's rule also covers the season's ballet review; that half
#: needs mention detection, which doesn't exist yet.
PARENT_GENRE_BALLET_NOTE = "printed in the ballet productions list(s) {seasons}"

#: Same ballet, spelled differently in the list and the Repertoire: only the
#: scan-confirmed title disagreements C1-C7 of
#: docs/eval/ballet_list_repertoire_disagreements.md, plus three awaiting RG's
#: physical check of the spelling (the work itself isn't in doubt). List title ->
#: Repertoire spellings; compared after norm().
BALLET_LIST_TITLE_ALIASES = {
    "Волшебныя грёзы": ["Волшебные грезы"],                            # C1
    "Привалъ кавалеріи": ["Привалъ кавалерія", "Пригалъ кавалеріи"],    # C2; Пригалъ awaits physical check
    "Маркобомба": ["Маркабомба"],                                       # C3
    "Фіаметта": ["Фіамметта", "Фіаметто"],                              # C4-C6
    "Граціелла": ["Граціела"],                                          # C7
    "Наяда и рыбакъ": ["Паяда и рыбакъ"],                               # awaits physical check
    "Баядерка": ["Ваядерка"],                                           # awaits physical check
    "Ученики Дюпрэ": ["Les élèves de Dupré"],                          # same work, Russian vs French title (1900-01 SP)
    "Донъ-Кихотъ Ламанчскій": ["Донъ-Кихотъ"],                          # 1908-10 SP: list prints the full title, Маріинскій Repertoire the short one; dates agree
    "Ѳетида и Пелей": ["Ѳемида и Пелей"],                               # 1908-09 SP, 8 Apr 1909; Repertoire spelling not scan-checked
    "Конекъ-горбунокъ и Царь-дѣвица": ["Конекъ-горбунокъ"],             # 1907-08 SP list prints "и" where every other year prints "или" (scan-confirmed, genuine print typo); the norm() "или" split doesn't fire
}


def ballet_list_matches(con: duckdb.DuckDBPyConnection) -> list:
    """Every (list date, Repertoire performance) pair that names the same ballet.

    Returns tuples (season, city, date 'YYYY-MM-DD', list_title, list_note, event_id,
    work_id, parent_work_id_if_matched_via_parent). Matching: same city and date, and
    the title equal after norm() (or a curated alias), or the work is an excerpt of
    it. Shared by ballet_list_work_ids (parent genre) and
    pipeline/compare_season_stats.py (ballet counts).
    """
    from compare_productions_repertoire import norm, contains
    lst = con.execute("""
        SELECT e.season, e.city, e.title, strftime(p.date, '%Y-%m-%d'), p.note
        FROM raw.production_entry_performance p JOIN raw.production_entry e USING (production_entry_id)
        WHERE p.date IS NOT NULL
    """).fetchall()
    rep = con.execute("""
        SELECT ae.city, coalesce(dc.corrected_date_undate, ae.date_undate) AS d, eep.event_id,
               wl.work_id, eep.performance_title, w.canonical_title, w.excerpt_of_work_id, pw.canonical_title
        FROM raw.event_entry_performance eep
        JOIN entities.work_link wl ON wl.raw_performance_id = eep.performance_id
        JOIN analysis.event_entry ae ON ae.event_id = eep.event_id
        LEFT JOIN analysis.event_entry_date_check dc ON dc.event_id = ae.event_id
        LEFT JOIN entities.work w ON w.work_id = wl.work_id
        LEFT JOIN entities.work pw ON pw.work_id = w.excerpt_of_work_id
        WHERE ae.event_status = 'performed'
    """).fetchall()
    by_day = {}
    for city, d, eid, wid, vt, ct, parent_id, pt in rep:
        by_day.setdefault((city, d), []).append((eid, wid, {norm(vt), norm(ct)} - {""}, norm(pt), parent_id))
    aliases = {norm(k): {norm(v) for v in vs} for k, vs in BALLET_LIST_TITLE_ALIASES.items()}
    out = []
    for season, city, title, d, note in lst:
        lkeys = {norm(title)} | aliases.get(norm(title), set())
        for eid, wid, keys, pkey, parent_id in by_day.get((city, d), []):
            if (lkeys & keys) or (pkey and pkey in lkeys) or any(contains(k, lk) for k in keys for lk in lkeys):
                out.append((season, city, d, title, note, eid, wid,
                            parent_id if (parent_id is not None and pkey in lkeys) else None))
    return out


def ballet_list_work_ids(con: duckdb.DuckDBPyConnection) -> dict:
    """work_id -> sorted list of list seasons, for works matched to a ballet-list date."""
    out = {}
    for season, _city, _d, _title, _note, _eid, wid, parent_id in ballet_list_matches(con):
        out.setdefault(wid, set()).add(season)
        if parent_id is not None:
            out.setdefault(parent_id, set()).add(season)
    return {w: sorted(s) for w, s in out.items()}


#: Curated research-layer correction for receipts figures whose PRINT is a
#: confirmed typo in the rubles/kopecks marker (e.g. "876 к. 18 к.",
#: "1225 q. 27 к.", "3049 р. 78 р."). RG's rule (2026-09-25): the raw tier
#: stays verbatim and its parsing regex is never widened for print typos;
#: the intended numeric value is applied HERE, in SQL, one reviewed row at a
#: time. Each row is keyed on page_id + date_text + theater + time_of_day
#: AND the verbatim receipts_text, so it can never attach to a different
#: figure, and the build fails if a row doesn't match exactly one entry
#: (e.g. after the transcription changes). Only scan-confirmed typos go in
#: (docs/eval/genuine_print_typos.md). Issue #109.
RECEIPTS_PRINT_TYPOS_CSV = Path(__file__).parent / "research_corrections" / "receipts_print_typos.csv"


def load_receipts_corrections(con: duckdb.DuckDBPyConnection) -> int:
    import csv as _csv
    con.execute("""CREATE OR REPLACE TEMP TABLE receipts_correction (
        page_id VARCHAR, date_text VARCHAR, theater VARCHAR, time_of_day VARCHAR,
        receipts_text_verbatim VARCHAR, corrected_total_kopecks INTEGER, basis VARCHAR)""")
    rows = list(_csv.DictReader(open(RECEIPTS_PRINT_TYPOS_CSV, encoding="utf-8"))) \
        if RECEIPTS_PRINT_TYPOS_CSV.exists() else []
    if rows:
        con.executemany("INSERT INTO receipts_correction VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [(r["page_id"], r["date_text"], r["theater"], r["time_of_day"],
                          r["receipts_text_verbatim"], int(r["corrected_total_kopecks"]), r["basis"])
                         for r in rows])
    bad = con.execute("""
        SELECT rc.page_id, rc.date_text, rc.theater, rc.receipts_text_verbatim, count(ae.event_id) AS n
        FROM receipts_correction rc
        LEFT JOIN analysis.event_entry ae
          ON ae.page_id = rc.page_id AND ae.date_text = rc.date_text AND ae.theater = rc.theater
         AND ae.time_of_day = rc.time_of_day AND ae.receipts_text = rc.receipts_text_verbatim
        GROUP BY ALL HAVING count(ae.event_id) <> 1
    """).fetchall()
    if bad:
        raise SystemExit(f"receipts_print_typos.csv rows not matching exactly one entry: {bad}")
    return len(rows)


def build_productions(con: duckdb.DuckDBPyConnection) -> None:
    """The ballet productions lists as research tables (issue #133).

    research.production        one row per list entry: a ballet as staged in one
                               season and city (list number, premiere flag, the
                               list's own printed total).
    research.production_work   every work the entry's dates matched in the
                               Repertoire (ballet_list_matches), with the number of
                               matched dates. Kept because entities.work still holds
                               several work_ids for some ballets (spelling variants,
                               misreads, excerpt rows not linked to their parent);
                               nothing here hides that.
    research.production.work_id the best single match: an excerpt is credited to
                               its parent, a work whose title equals the list title
                               wins, then the most matched dates. NULL when no date
                               matched.
    research.production_credit one row per printed creator credit -> person, with
                               the role and the printed form verbatim. Group
                               credits ("и др.", "разныхъ авторовъ") are left out:
                               they name no person.
    """
    from compare_productions_repertoire import norm
    import collections
    excerpt_parent = dict(con.execute(
        "SELECT work_id::VARCHAR, excerpt_of_work_id::VARCHAR FROM entities.work").fetchall())
    titles = dict(con.execute("SELECT work_id::VARCHAR, canonical_title FROM entities.work").fetchall())
    matched = collections.defaultdict(collections.Counter)
    for season, city, _d, title, _note, _eid, wid, parent in ballet_list_matches(con):
        w = str(parent or wid)
        matched[(season, city, title)][excerpt_parent.get(w) or w] += 1
    entries = con.execute("""SELECT production_entry_id, season, city, title FROM raw.production_entry""").fetchall()
    prod_work, best = [], {}
    for pid, season, city, title in entries:
        cnt = matched.get((season, city, title))
        if not cnt:
            continue
        for w, n in cnt.items():
            prod_work.append((pid, w, n))
        best[pid] = max(cnt, key=lambda w: (norm(titles.get(w) or "") == norm(title), cnt[w]))

    con.execute("""
        CREATE TABLE research.production (
            production_id VARCHAR PRIMARY KEY,
            work_id UUID REFERENCES research.work(work_id),
            season VARCHAR, city VARCHAR,
            list_title VARCHAR, list_number VARCHAR, is_premiere BOOLEAN,
            description_text VARCHAR,
            printed_total INTEGER, n_dates INTEGER,
            n_matched_works INTEGER,
            printed_page_number VARCHAR, source_file VARCHAR
        )""")
    con.execute("CREATE OR REPLACE TEMP TABLE prod_best (production_id VARCHAR, work_id UUID)")
    con.executemany("INSERT INTO prod_best VALUES (?, ?)", list(best.items()))
    con.execute("CREATE OR REPLACE TEMP TABLE prod_work (production_id VARCHAR, work_id UUID, n_matched_dates INTEGER)")
    con.executemany("INSERT INTO prod_work VALUES (?, ?, ?)", prod_work)
    con.execute("""
        INSERT INTO research.production
        SELECT e.production_entry_id, b.work_id, e.season, e.city, e.title, e.list_number, e.is_premiere,
               e.description_text, e.total_count, e.n_dates,
               (SELECT count(*) FROM prod_work pw WHERE pw.production_id = e.production_entry_id),
               e.printed_page_number, e.source_file
        FROM raw.production_entry e LEFT JOIN prod_best b ON b.production_id = e.production_entry_id
    """)
    con.execute("""
        CREATE TABLE research.production_work (
            production_id VARCHAR REFERENCES research.production(production_id),
            work_id UUID REFERENCES research.work(work_id),
            n_matched_dates INTEGER,
            PRIMARY KEY (production_id, work_id)
        )""")
    con.execute("INSERT INTO research.production_work SELECT * FROM prod_work")
    con.execute("""
        CREATE TABLE research.production_credit (
            credit_id VARCHAR PRIMARY KEY,
            production_id VARCHAR REFERENCES research.production(production_id),
            person_id UUID REFERENCES research.person(person_id),
            credit_order INTEGER,
            role_category VARCHAR,
            role_text VARCHAR,
            name_printed VARCHAR,
            honorific_printed VARCHAR,
            qualifier_printed VARCHAR,
            is_pseudonym BOOLEAN,
            identification_status VARCHAR
        )""")
    con.execute("""
        INSERT INTO research.production_credit
        SELECT c.credit_id, c.production_entry_id, l.person_id, c.credit_order, c.role_category, c.role_text,
               c.name_printed, c.honorific_printed, c.qualifier_printed, c.is_pseudonym,
               l.form_status
        FROM analysis.production_entry_credit c
        JOIN entities.production_credit_link l USING (credit_id)
    """)
    orphans = con.execute("""SELECT count(*) FROM research.production_credit pc
        LEFT JOIN research.person p USING (person_id) WHERE p.person_id IS NULL""").fetchone()[0]
    if orphans:
        raise SystemExit(f"research.production_credit: {orphans} credits point at no research.person")


def build_season_stats(con: duckdb.DuckDBPyConnection) -> None:
    """The yearbook's printed season totals as research tables (loaded by
    load_season_stats.py from the hand transcription in docs/season_stats/).

    research.season_stat_check     one row per (season, city) with a printed totals page:
                                   the printed counts and receipts next to the same figures
                                   computed from research.event. A checksum on the Repertoire,
                                   not a correction of it.
    research.season_stat_line      the printed lines (category, theater, count, receipts), verbatim
                                   plus the city as SP/Moscow.
    research.season_stat_footnote  the printed footnotes, verbatim.

    Counting rules (both sides, stated so a difference is read correctly):
      printed_count      every printed line that carries a number EXCEPT the ruled subtotals
                         (subtotals repeat their venue/part lines);
      repertoire_sessions  performed events (a morning and an evening row count twice);
      repertoire_days      distinct (theater, date) among performed events, to test how the
                         yearbook counted a day with two performances;
      receipts           printed: sum of the lines that print receipts; Repertoire: the sum of
                         research.event.receipts_total_kopecks. From 1898-99 the page's own
                         footnote says its receipts EXCLUDE charity performances, so the
                         Repertoire receipts of events whose annotation says "въ пользу" are
                         reported beside them (not subtracted: which events the yearbook treated
                         as charity is not assumed).
    The genre/theater-level comparison (families, ballet three ways) stays in
    pipeline/compare_season_stats.py, because it needs judgment-based classification.
    """
    for t in ("season_stat_check", "season_stat_line", "season_stat_footnote"):
        con.execute(f"DROP TABLE IF EXISTS research.{t}")
    con.execute("""
        CREATE TABLE research.season_stat_line (
            season VARCHAR, city VARCHAR, line_no INTEGER, line_kind VARCHAR,
            category_verbatim VARCHAR, category VARCHAR, venue_verbatim VARCHAR,
            qualifier_verbatim VARCHAR, count INTEGER, receipts_verbatim VARCHAR,
            receipts_kopecks DECIMAL(18, 1), footnote_refs VARCHAR, note VARCHAR,
            PRIMARY KEY (season, city, line_no)
        )""")
    con.execute("""
        INSERT INTO research.season_stat_line
        SELECT season,
               CASE city_verbatim WHEN 'С.-Петербургъ' THEN 'SP' WHEN 'Москва' THEN 'Moscow' END,
               line_no, line_kind, category_verbatim, category, venue_verbatim, qualifier_verbatim,
               count, receipts_verbatim, receipts_kopecks, footnote_refs, note
        FROM raw.season_stat_line""")
    bad = con.execute("SELECT count(*) FROM research.season_stat_line WHERE city IS NULL").fetchone()[0]
    if bad:
        raise SystemExit(f"research.season_stat_line: {bad} lines with a city that is not С.-Петербургъ / Москва")
    con.execute("""
        CREATE TABLE research.season_stat_footnote (
            season VARCHAR, footnote_no INTEGER, text_verbatim VARCHAR, note VARCHAR,
            PRIMARY KEY (season, footnote_no)
        )""")
    con.execute("INSERT INTO research.season_stat_footnote SELECT season, footnote_no, text_verbatim, note FROM raw.season_stat_footnote")
    con.execute("""
        CREATE TABLE research.season_stat_check (
            season VARCHAR, city VARCHAR, stats_format VARCHAR, stats_printed_page VARCHAR,
            printed_count INTEGER, printed_count_with_receipts INTEGER, printed_receipts_kopecks DECIMAL(18, 1),
            repertoire_sessions INTEGER, repertoire_days INTEGER, repertoire_sessions_with_receipts INTEGER,
            repertoire_receipts_kopecks BIGINT,
            repertoire_charity_text_sessions INTEGER, repertoire_charity_text_receipts_kopecks BIGINT,
            sessions_minus_printed INTEGER, days_minus_printed INTEGER,
            receipts_minus_printed_kopecks DECIMAL(18, 1),
            PRIMARY KEY (season, city)
        )""")
    con.execute("""
        INSERT INTO research.season_stat_check
        WITH printed AS (
            SELECT season, city, sum(count) AS n,
                   coalesce(sum(count) FILTER (WHERE receipts_kopecks IS NOT NULL), 0) AS n_rec,
                   sum(receipts_kopecks) AS rec   -- NULL when the page prints no receipts (1891-93)
            FROM research.season_stat_line WHERE line_kind <> 'subtotal' GROUP BY season, city
        ), rep AS (
            SELECT e.season, e.city, count(*) AS sessions,
                   count(DISTINCT (e.theater_id, coalesce(e.date, e.event_id))) AS days,
                   count(e.receipts_total_kopecks) AS sessions_rec,
                   coalesce(sum(e.receipts_total_kopecks), 0) AS rec,
                   count(*) FILTER (WHERE coalesce(regexp_matches(lower(a.annotation), 'въ пользу'), false)) AS ch_n,
                   coalesce(sum(e.receipts_total_kopecks) FILTER
                            (WHERE coalesce(regexp_matches(lower(a.annotation), 'въ пользу'), false)), 0) AS ch_rec
            FROM research.event e LEFT JOIN analysis.event_entry a USING (event_id)
            WHERE e.event_status = 'performed' GROUP BY e.season, e.city
        )
        SELECT p.season, p.city, pg.format, pg.printed_page,
               p.n, p.n_rec, p.rec,
               coalesce(r.sessions, 0), coalesce(r.days, 0), coalesce(r.sessions_rec, 0), coalesce(r.rec, 0),
               coalesce(r.ch_n, 0), coalesce(r.ch_rec, 0),
               coalesce(r.sessions, 0) - p.n, coalesce(r.days, 0) - p.n, coalesce(r.rec, 0) - p.rec  -- NULL with p.rec
        FROM printed p
        JOIN raw.season_stat_page pg USING (season)
        LEFT JOIN rep r ON r.season = p.season AND r.city = p.city
        ORDER BY p.season, p.city""")


def build_research_model(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS research")

    # Drop in FK-dependency order (performance/person_appearance/event
    # depend on person/work/theater) so CREATE OR REPLACE below never
    # trips the same "blocked by a dependent table" issue build_entities.py
    # already documents for entities.person/entities.work. DuckDB has no
    # ALTER TABLE ADD FOREIGN KEY (confirmed by hitting
    # NotImplementedException directly) -- every constraint here has to be
    # declared inline on CREATE TABLE, so each table is CREATEd with its
    # full schema first and populated via a separate INSERT INTO ... SELECT,
    # same two-step pattern build_entities.py already uses.
    for t in ["season_stat_check", "season_stat_line", "season_stat_footnote",
              "production_credit", "production_work", "production",
              "performance", "event", "person_appearance", "person", "work", "theater"]:
        con.execute(f"DROP TABLE IF EXISTS research.{t}")

    con.execute("""
        CREATE TABLE research.theater (
            theater_id UUID PRIMARY KEY,
            canonical_name VARCHAR,
            city VARCHAR,
            active_from_season VARCHAR
        )
    """)
    con.execute("INSERT INTO research.theater SELECT * FROM entities.theater")

    con.execute("""
        CREATE TABLE research.work (
            work_id UUID PRIMARY KEY,
            canonical_title VARCHAR,
            canonical_genre VARCHAR,
            appearance_count INTEGER,
            excerpt_of_work_id UUID,
            excerpt_note VARCHAR,
            genre_source VARCHAR,
            genre_note VARCHAR,
            parent_genre VARCHAR,
            parent_genre_note VARCHAR
        )
    """)
    # excerpt_of_work_id deliberately has no REFERENCES clause -- same
    # reasoning as entities.work: it's self-referential, and DuckDB's FK
    # enforcement rejects a later UPDATE on a table whose PK has any
    # incoming FK. Not an issue here (this is a single INSERT, not an
    # UPDATE), but kept consistent with entities.work's own schema so a
    # future change to one doesn't silently diverge from the other.
    # RESEARCH_GENRE_RULES are applied inside the INSERT for the same
    # reason (no UPDATE once research.performance references research.work).
    con.execute("CREATE OR REPLACE TEMP TABLE genre_rule (pattern VARCHAR, genre VARCHAR, note VARCHAR)")
    con.executemany("INSERT INTO genre_rule VALUES (?, ?, ?)", RESEARCH_GENRE_RULES)
    for pattern, _, _ in RESEARCH_GENRE_RULES:
        n = con.execute("SELECT count(*) FROM entities.work WHERE regexp_matches(canonical_title, ?)",
                        [pattern]).fetchone()[0]
        if n == 0:
            raise SystemExit(f"RESEARCH_GENRE_RULES: pattern {pattern!r} matches no entities.work row")
    listed = ballet_list_work_ids(con)
    con.execute("CREATE OR REPLACE TEMP TABLE parent_genre_ballet (work_id UUID, note VARCHAR)")
    con.executemany("INSERT INTO parent_genre_ballet VALUES (?, ?)",
                    [(w, PARENT_GENRE_BALLET_NOTE.format(seasons=", ".join(s))) for w, s in listed.items()])
    con.execute("CREATE OR REPLACE TEMP TABLE title_correction (verbatim_title VARCHAR, corrected_title VARCHAR, note VARCHAR)")
    con.executemany("INSERT INTO title_correction VALUES (?, ?, ?)",
                    [(verbatim, corrected, note) for verbatim, (corrected, note) in RESEARCH_TITLE_CORRECTIONS.items()])
    for verbatim in RESEARCH_TITLE_CORRECTIONS:
        n = con.execute("SELECT count(*) FROM entities.work WHERE canonical_title = ?", [verbatim]).fetchone()[0]
        if n == 0:
            raise SystemExit(f"RESEARCH_TITLE_CORRECTIONS: {verbatim!r} matches no entities.work row")
    con.execute("""
        INSERT INTO research.work
        SELECT w.work_id, coalesce(tc.corrected_title, w.canonical_title) AS canonical_title,
               coalesce(g.genre, w.canonical_genre) AS canonical_genre,
               w.appearance_count, w.excerpt_of_work_id, w.excerpt_note,
               CASE WHEN g.genre IS NOT NULL THEN 'research_rule'
                    WHEN w.canonical_genre IS NOT NULL THEN 'printed' END AS genre_source,
               g.note AS genre_note,
               CASE WHEN pg.work_id IS NOT NULL THEN 'ballet' END AS parent_genre,
               pg.note AS parent_genre_note
        FROM entities.work w
        LEFT JOIN genre_rule g ON regexp_matches(w.canonical_title, g.pattern)
        LEFT JOIN parent_genre_ballet pg ON pg.work_id = w.work_id
        LEFT JOIN title_correction tc ON tc.verbatim_title = w.canonical_title
    """)

    con.execute("""
        CREATE TABLE research.person (
            person_id UUID PRIMARY KEY,
            display_name VARCHAR,
            canonical_family_name VARCHAR,
            canonical_first_name VARCHAR,
            canonical_patronymic VARCHAR,
            ordinal_suffix VARCHAR,
            first_attested_season VARCHAR,
            last_attested_season VARCHAR,
            wikidata_qid VARCHAR,
            wikidata_label VARCHAR,
            wikidata_description VARCHAR,
            person_source VARCHAR,
            wikidata_source VARCHAR
        )
    """)
    has_creators = con.execute("""SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'entities' AND table_name = 'creator_person'""").fetchone()[0] > 0
    if not has_creators:
        con.execute("CREATE OR REPLACE TEMP TABLE cwl (person_id UUID, wikidata_qid VARCHAR, wikidata_label VARCHAR, wikidata_description VARCHAR)")
    else:
        con.execute("CREATE OR REPLACE TEMP VIEW cwl AS SELECT person_id, wikidata_qid, wikidata_label, wikidata_description FROM entities.creator_wikidata_link")
    non_person_list = ", ".join(f"'{pid}'" for pid in NON_PERSON_IDS)
    # A Wikidata link made against a person who has since been merged must follow
    # the merge to the live survivor (entities.person.superseded_by_person_id chain),
    # or the QID silently drops out of research.person (2026-10-06: 15 links had
    # gone stale this way; the 1910-11 merges would have dropped 4 more QIDs --
    # Полякова, Шолларъ, Кучера, Крушевскій). Two links reaching one survivor with
    # different QIDs is a real conflict and stops the build rather than guess.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE wd_live AS
        WITH RECURSIVE ch(link_pid, cur, depth) AS (
            SELECT person_id, person_id, 0 FROM entities.person_wikidata_link
            UNION ALL
            SELECT ch.link_pid, p.superseded_by_person_id, ch.depth + 1
            FROM ch JOIN entities.person p ON p.person_id = ch.cur
            WHERE p.superseded_by_person_id IS NOT NULL AND ch.depth < 50
        ),
        survivor AS (
            SELECT link_pid, arg_max(cur, depth) AS live_pid FROM ch GROUP BY link_pid
        )
        SELECT s.live_pid AS person_id,
               any_value(w.wikidata_qid) AS wikidata_qid,
               any_value(w.wikidata_label) AS wikidata_label,
               any_value(w.wikidata_description) AS wikidata_description,
               count(DISTINCT w.wikidata_qid) AS n_qids
        FROM entities.person_wikidata_link w JOIN survivor s ON s.link_pid = w.person_id
        GROUP BY s.live_pid
    """)
    conflicts = con.execute("SELECT person_id FROM wd_live WHERE n_qids > 1").fetchall()
    if conflicts:
        raise SystemExit(f"person_wikidata_link: merged persons carry conflicting QIDs: {conflicts}")
    con.execute(f"""
        INSERT INTO research.person
        SELECT
            p.person_id, p.display_name, p.canonical_family_name,
            p.canonical_first_name, p.canonical_patronymic, p.ordinal_suffix,
            p.first_attested_season, p.last_attested_season,
            coalesce(wd.wikidata_qid, cw.wikidata_qid),
            coalesce(wd.wikidata_label, cw.wikidata_label),
            coalesce(wd.wikidata_description, cw.wikidata_description),
            'roster' AS person_source,
            CASE WHEN wd.wikidata_qid IS NOT NULL THEN 'link_wikidata'
                 WHEN cw.wikidata_qid IS NOT NULL THEN 'rg_review' END AS wikidata_source
        FROM entities.person p
        LEFT JOIN wd_live wd ON wd.person_id = p.person_id
        LEFT JOIN cwl cw ON cw.person_id = p.person_id
        WHERE p.superseded_by_person_id IS NULL
          AND p.person_id NOT IN ({non_person_list})
    """)
    if has_creators:
        # Creators named only in the ballet productions lists (issue #133): not on
        # the roster, so they come from entities.creator_person. Their attested
        # seasons are the list seasons that credit them; the name parts are split
        # from the curated nominative display_name; canonical_first_name only when a
        # full first name is printed ("Адамъ, Адольфъ"), never initials or a title.
        con.execute("""
            INSERT INTO research.person
            SELECT cp.person_id, cp.display_name,
                   trim(split_part(cp.display_name, ',', 1)),
                   CASE WHEN regexp_matches(trim(split_part(cp.display_name, ',', 2)), '^[А-ЯЁІѲѢ][а-яёіѳѣъь]+$')
                         AND trim(split_part(cp.display_name, ',', 2)) NOT IN ('лордъ', 'князь', 'баронъ')
                        THEN trim(split_part(cp.display_name, ',', 2)) END, NULL, NULL,
                   min(e.season), max(e.season),
                   cw.wikidata_qid, cw.wikidata_label, cw.wikidata_description,
                   'production_list',
                   CASE WHEN cw.wikidata_qid IS NOT NULL THEN 'rg_review' END
            FROM entities.creator_person cp
            JOIN entities.production_credit_link l ON l.person_id = cp.person_id
            JOIN analysis.production_entry_credit c USING (credit_id)
            JOIN raw.production_entry e USING (production_entry_id)
            LEFT JOIN cwl cw ON cw.person_id = cp.person_id
            GROUP BY ALL
        """)

    for pid, (disp, first, _why) in RESEARCH_PERSON_DISPLAY_OVERRIDES.items():
        n = con.execute("SELECT count(*) FROM research.person WHERE person_id = ?", [pid]).fetchone()[0]
        if n != 1:
            raise SystemExit(f"RESEARCH_PERSON_DISPLAY_OVERRIDES: {pid} is not a live research.person")
        con.execute("UPDATE research.person SET display_name = ?, canonical_first_name = ? WHERE person_id = ?",
                    [disp, first, pid])

    con.execute("""
        CREATE TABLE research.event (
            event_id VARCHAR PRIMARY KEY,
            theater_id UUID REFERENCES research.theater(theater_id),
            season VARCHAR,
            city VARCHAR,
            date_verbatim VARCHAR,
            date_undate VARCHAR,
            date VARCHAR,
            date_confidence VARCHAR,
            event_status VARCHAR,
            receipts_total_kopecks INTEGER,
            receipts_source VARCHAR,
            receipts_correction_note VARCHAR,
            printed_page_number VARCHAR
        )
    """)
    n_corr = load_receipts_corrections(con)
    for p in RESEARCH_EXCLUDED_PAGES:
        if not con.execute("SELECT 1 FROM analysis.event_entry WHERE page_id = ? LIMIT 1", [p]).fetchone():
            # a warning, not a failure: a database built before the page's season
            # was added must still build (parallel sessions rebuild production)
            print(f"  WARNING: RESEARCH_EXCLUDED_PAGES: {p} not found in analysis.event_entry")
    con.execute("CREATE OR REPLACE TEMP TABLE excluded_page (page_id VARCHAR)")
    if RESEARCH_EXCLUDED_PAGES:
        con.executemany("INSERT INTO excluded_page VALUES (?)", [(p,) for p in RESEARCH_EXCLUDED_PAGES])
    con.execute("CREATE OR REPLACE TEMP TABLE page_month_override (page_id VARCHAR, y INTEGER, m INTEGER)")
    if RESEARCH_PAGE_MONTH_OVERRIDES:
        con.executemany("INSERT INTO page_month_override VALUES (?, ?, ?)",
                        [(p, y, m) for p, (y, m) in RESEARCH_PAGE_MONTH_OVERRIDES.items()])
    # `resolved` = every event with its best-available date. A not_captured
    # placeholder means "no real event was found for this theater/date on
    # this page"; when the resolved dates show a real event there after all
    # (e.g. a page override above, or a manual/weekday date correction moving
    # a misprinted row onto its true day), the placeholder is spurious and is
    # left out of research.event -- analysis.event_entry keeps it untouched.
    con.execute("""
        INSERT INTO research.event
        WITH resolved AS (
            SELECT
                ae.*,
                coalesce(
                    dc.corrected_date_undate,
                    ae.date_undate,
                    CASE WHEN pmo.page_id IS NOT NULL AND ae.event_status <> 'not_captured'
                         THEN strftime(make_date(pmo.y, pmo.m,
                                  TRY_CAST(regexp_extract(ae.date_text, '^\\s*(\\d+)', 1) AS INTEGER)),
                              '%Y-%m-%d')
                    END
                ) AS resolved_date,
                CASE WHEN dc.corrected_date_undate IS NULL AND ae.date_undate IS NULL
                          AND pmo.page_id IS NOT NULL AND ae.event_status <> 'not_captured'
                     THEN 'corrected_manual'
                     ELSE coalesce(
                         dc.date_confidence,
                         CASE WHEN ae.event_status = 'not_captured' THEN 'synthesized_gap'
                              ELSE 'unparseable' END)
                END AS resolved_confidence
            FROM analysis.event_entry ae
            LEFT JOIN analysis.event_entry_date_check dc ON dc.event_id = ae.event_id
            LEFT JOIN page_month_override pmo ON pmo.page_id = ae.page_id
        )
        SELECT
            r.event_id,
            t.theater_id,
            r.season, r.city,
            r.date_text AS date_verbatim,
            r.date_undate,
            r.resolved_date AS date,
            r.resolved_confidence AS date_confidence,
            r.event_status,
            coalesce(rc.corrected_total_kopecks, r.receipts_total_kopecks) AS receipts_total_kopecks,
            CASE WHEN rc.page_id IS NOT NULL THEN 'corrected_print_typo'
                 WHEN r.receipts_total_kopecks IS NOT NULL THEN 'parsed' END AS receipts_source,
            CASE WHEN rc.page_id IS NOT NULL
                 THEN 'printed "' || r.receipts_text || '": ' || rc.basis END AS receipts_correction_note,
            r.printed_page_number
        FROM resolved r
        LEFT JOIN entities.theater t ON t.canonical_name = r.theater_canonical
        LEFT JOIN receipts_correction rc
          ON rc.page_id = r.page_id AND rc.date_text = r.date_text AND rc.theater = r.theater
         AND rc.time_of_day = r.time_of_day AND rc.receipts_text_verbatim = r.receipts_text
        WHERE r.page_id NOT IN (SELECT page_id FROM excluded_page)
          AND NOT (
            r.event_status = 'not_captured' AND EXISTS (
                SELECT 1 FROM resolved x
                WHERE x.event_status <> 'not_captured'
                  AND x.page_id = r.page_id
                  AND x.theater_canonical = r.theater_canonical
                  AND x.resolved_date = r.resolved_date
            )
        )
    """)

    con.execute("""
        CREATE TABLE research.performance (
            performance_id VARCHAR PRIMARY KEY,
            event_id VARCHAR REFERENCES research.event(event_id),
            work_id UUID REFERENCES research.work(work_id),
            performance_order VARCHAR,
            verbatim_title VARCHAR,
            verbatim_genre VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO research.performance
        SELECT
            eep.performance_id,
            eep.event_id,
            wl.work_id,
            eep.performance_order,
            eep.performance_title AS verbatim_title,
            eep.genre AS verbatim_genre
        FROM raw.event_entry_performance eep
        JOIN entities.work_link wl ON wl.raw_performance_id = eep.performance_id
        WHERE eep.event_id NOT IN (SELECT e.event_id FROM analysis.event_entry e
                                   JOIN excluded_page x USING (page_id))
    """)

    con.execute("""
        CREATE TABLE research.person_appearance (
            appearance_id VARCHAR PRIMARY KEY,
            person_id UUID REFERENCES research.person(person_id),
            season VARCHAR,
            city VARCHAR,
            entity_type VARCHAR,
            institution VARCHAR,
            heading_path VARCHAR,
            rank VARCHAR,
            title VARCHAR,
            service_class VARCHAR,
            instrument VARCHAR,
            subject_taught VARCHAR,
            tenure_note_text VARCHAR
        )
    """)
    con.execute(f"""
        INSERT INTO research.person_appearance
        SELECT
            r.entry_id AS appearance_id,
            pl.person_id,
            sp.season, sp.city,
            r.entity_type, r.institution, r.heading_path,
            r.rank_clean, r.title_clean, r.service_class, r.instrument_clean,
            r.subject_taught, r.tenure_note_text_clean
        FROM analysis.person_entry r
        JOIN entities.person_link pl ON pl.entry_id = r.entry_id
        JOIN raw.source_pages sp ON sp.page_id = r.page_id
        WHERE pl.person_id NOT IN ({non_person_list})
    """)

    if has_creators:
        build_productions(con)

    # printed season totals: only when load_season_stats.py has populated the raw tables
    if con.execute("""SELECT count(*) FROM information_schema.tables
                      WHERE table_schema = 'raw' AND table_name = 'season_stat_line'""").fetchone()[0]:
        build_season_stats(con)

    counts = {
        t: con.execute(f"SELECT count(*) FROM research.{t}").fetchone()[0]
        for t in ["theater", "work", "person", "event", "performance", "person_appearance",
                  "production", "production_work", "production_credit",
                  "season_stat_check", "season_stat_line", "season_stat_footnote"]
        if con.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'research' AND table_name = ?",
                       [t]).fetchone()[0]
    }
    print("research schema built:")
    for t, n in counts.items():
        print(f"  research.{t}: {n} rows")
    n_applied = con.execute(
        "SELECT count(*) FROM research.event WHERE receipts_source = 'corrected_print_typo'").fetchone()[0]
    print(f"  receipts corrected from confirmed print typos: {n_applied} "
          f"(of {n_corr} rows in {RECEIPTS_PRINT_TYPOS_CSV.name})")

    # Sanity check: receipts must live only on event, never on
    # performance -- the entire point of keeping them distinct.
    perf_cols = {c[0] for c in con.execute("DESCRIBE research.performance").fetchall()}
    assert not any("receipt" in c for c in perf_cols), \
        "receipts leaked onto research.performance -- multi-work events would double-count"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()

    con = duckdb.connect(str(args.db))
    build_research_model(con)
    con.close()
    print(f"\nresearch schema updated in {args.db}")


if __name__ == "__main__":
    main()
