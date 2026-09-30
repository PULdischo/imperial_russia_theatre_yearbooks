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
}


def ballet_list_work_ids(con: duckdb.DuckDBPyConnection) -> dict:
    """work_id -> sorted list of list seasons, for works matched to a ballet-list date."""
    from compare_productions_repertoire import norm, contains
    lst = con.execute("""
        SELECT e.season, e.city, e.title, strftime(p.date, '%Y-%m-%d')
        FROM raw.production_entry_performance p JOIN raw.production_entry e USING (production_entry_id)
        WHERE p.date IS NOT NULL
    """).fetchall()
    rep = con.execute("""
        SELECT ae.city, coalesce(dc.corrected_date_undate, ae.date_undate) AS d,
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
    for city, d, wid, vt, ct, parent_id, pt in rep:
        by_day.setdefault((city, d), []).append((wid, {norm(vt), norm(ct)} - {""}, norm(pt), parent_id))
    aliases = {norm(k): {norm(v) for v in vs} for k, vs in BALLET_LIST_TITLE_ALIASES.items()}
    out = {}
    for season, city, title, d in lst:
        lkeys = {norm(title)} | aliases.get(norm(title), set())
        for wid, keys, pkey, parent_id in by_day.get((city, d), []):
            if (lkeys & keys) or (pkey and pkey in lkeys) or any(contains(k, lk) for k in keys for lk in lkeys):
                out.setdefault(wid, set()).add(season)
                if parent_id is not None and pkey in lkeys:
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
    for t in ["performance", "event", "person_appearance", "person", "work", "theater"]:
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
    con.execute("""
        INSERT INTO research.work
        SELECT w.work_id, w.canonical_title,
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
            wikidata_description VARCHAR
        )
    """)
    non_person_list = ", ".join(f"'{pid}'" for pid in NON_PERSON_IDS)
    con.execute(f"""
        INSERT INTO research.person
        SELECT
            p.person_id, p.display_name, p.canonical_family_name,
            p.canonical_first_name, p.canonical_patronymic, p.ordinal_suffix,
            p.first_attested_season, p.last_attested_season,
            wd.wikidata_qid, wd.wikidata_label, wd.wikidata_description
        FROM entities.person p
        LEFT JOIN entities.person_wikidata_link wd ON wd.person_id = p.person_id
        WHERE p.superseded_by_person_id IS NULL
          AND p.person_id NOT IN ({non_person_list})
    """)

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
        WHERE NOT (
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

    counts = {
        t: con.execute(f"SELECT count(*) FROM research.{t}").fetchone()[0]
        for t in ["theater", "work", "person", "event", "performance", "person_appearance"]
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
