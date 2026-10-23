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
import csv
import uuid
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
    (r"^Балетное отдѣленіе\.?$", "бал.",
     "the ballet section of a mixed gala (Маріинскій, 24 Jan 1904): printed without a genre; ballet assigned "
     "in the research layer (RG, 2026-10-13)"),
    (r"^Балетъ\.?$", "бал.",
     "an unnamed ballet item on a charity bill (Маріинскій, 22 Dec 1907): labelled ballet although the work is "
     "not known (RG, 2026-10-13)"),
]


#: Research-layer genres decided PER PERFORMANCE, for a title too generic for
#: a title rule. A plain "Дивертиссементъ" is printed without a genre and is
#: one entities.work row, but it is a ballet number on a ballet evening and
#: something unknown on a drama bill (RG, 2026-10-12, with the review
#: evidence in docs/query_log.md). Each row of the CSV names one printed
#: performance (season, city, date, theater, time of day, verbatim title) and
#: the genre it gets. The listed performances move to a second research.work
#: row with the same title and that genre (genre_source 'research_rule');
#: the unlisted ones stay on the original row, still without a genre. Raw is
#: untouched. The build fails if a row does not match exactly one performance.
#: Works that get parent genre "ballet" by RG's decision although they are in
#: no ballet productions list: (entities.work.canonical_title, note). The
#: genre itself is left as printed (here: none), so the work turns up in
#: ballet searches without being claimed as purely ballet. The build fails if
#: a title matches no work.
PARENT_GENRE_BALLET_TITLES = {
    "Концертный и балетный дивертиссемент":
        "the printed title names ballet and concert together (Маріинскій, 7 Jan 1906, charity evening); "
        "no single genre assigned, parent genre ballet (RG, 2026-10-12)",
}

#: ---------------------------------------------------------------------------
#: Art forms (RG, 2026-10-12; docs/eval/known_issues.md, "the art forms of the
#: research layer"). Five values, by COMPANY and not by printed genre label:
#: ballet, opera, Russian drama, French drama, visiting troupe. RG's test for
#: "visiting": the yearbook prints no productions list for the troupe. Assigned
#: per performance (research.performance.art_form) because one title can be
#: given by a house troupe and by a guest. A performance that fits none stays
#: NULL (RG: "we can review these later"); art_form_basis says which rule
#: decided, so every value can be traced and challenged. Raw is untouched.
ART_FORMS = ["ballet", "opera", "Russian drama", "French drama", "visiting troupe"]

#: ---------------------------------------------------------------------------
#: DISCIPLINE and COMPANY (RG, 2026-10-22; docs/schema.md, top). The output column
#: research.performance.discipline replaces art_form: the kind of performing art,
#: defined by its PERSONNEL (RG: Russian and French drama "don't feature the same
#: actors (unlike opera singers)"). ART_FORMS above stays the internal working set
#: of the rules below; its catch-all "visiting troupe" is resolved, per troupe, into
#: a discipline by the same personnel rule (VISITING_TROUPE_DISCIPLINE) and never
#: reaches the output. "opera", not "Russian opera" (RG: "they didn't call it
#: 'Russian opera'"). company = city + discipline for the Directorate's own troupes
#: (RG: troupe and company "are both defined by city + the type of art"); a visiting
#: troupe is its own company, by the name an annotation gives or a placeholder.
#: The output's genre_family is the internal item_kind (ITEM_KINDS below).
DIRECTORATE_DISCIPLINES = ["ballet", "opera", "Russian drama", "French drama"]
DISCIPLINES = DIRECTORATE_DISCIPLINES + ["German drama", "Italian drama", "Japanese drama",
                                         "Italian opera", "German opera", "German operetta", "Siamese dance"]
CITY_NAMES = {"SP": "St. Petersburg", "Moscow": "Moscow"}
#: troupe named by VISITING_ANNOTATION_RULES -> discipline (None = not decided yet)
VISITING_TROUPE_DISCIPLINE = {
    "Adele Sandrock and her troupe": "German drama",
    "Berlin Lessing-Theater": "German drama",
    "German guest season": "German drama",
    "Adolf Sonnenthal": "German drama",
    "Réjane and her troupe": "French drama",
    "Sarah Bernhardt": "French drama",
    "Eleonora Duse": "Italian drama",
    "Tina di Lorenzo": "Italian drama",
    "Japanese troupe of the Imperial court theatre, Tokyo": "Japanese drama",
    "Moscow Art Theatre": "Russian drama",
    "Italian opera under Угетти": "Italian opera",
    "opera troupe under Н. В. Любимовъ": "opera",  # Russian-language troupe
    "Vienna operetta troupe": "German operetta",
    "Siamese court troupe": "Siamese dance",  # RG, 2026-10-22; no performance in the data so far
}

#: A second axis, the KIND OF ITEM: what was happening on the stage, whoever
#: gave it (RG, 2026-10-13). research.performance.genre_family, summarised per
#: event in research.event.genre_families, in this order. discipline says which
#: company; item_kind says what it was. An operetta is "operetta" here whether
#: the opera or the drama company gave it; a divertissement is "divertissement"
#: whether or not it is known to have been danced; a storyteller's number is
#: "recitation / reading" although its company is Russian drama. Lecture,
#: pantomime and comedy-ballet are kinds of their own, and concert and cinema
#: live here and NOT in art_form (all RG, 2026-10-13). Play sub-types (comedy,
#: drama, vaudeville ...) are not normalised: read verbatim_genre for those.
ITEM_KINDS = ["ballet", "opera", "operetta", "play", "comedy-ballet", "pantomime", "divertissement",
              "concert", "recitation / reading", "lecture", "tableau / apotheosis", "cinema", "anthem"]
CINEMA_TITLE_RE = r"инематограф|^фотографія въ натуральн"
LECTURE_TITLE_RE = r"лекція|^рефератъ"
RECITATION_TITLE_RE = r"^сцена г\. |^чтеніе|отдѣленіе литературное|литературное отдѣленіе|отдѣленіе поэзіи"
TABLEAU_TITLE_RE = r"^апоѳеоз|^жив(ая|ыя) картин"
DIVERTISSEMENT_TITLE_RE = r"дивертис|дивертим"
DIVERTISSEMENT_GENRE_RE = r"^диверт|^див\."
OPERETTA_GENRE_RE_ANY = r"^(оперет|опер\.|operet|opéret|opéra-bouffe|шут\.-оперет|опера-вод|com\.-opér)"
OPERA_GENRE_RE_ANY = r"^(оп\.|op\.|oper\.|опера)"
PANTOMIME_GENRE_RE = r"^(pantomime|mimodrame)"
#: The printed title itself names dancing (so far only «чтеніе, пляска.»):
#: includes_dance, "direct".
DANCE_TITLE_RE = r"пляск"

#: "concert" is recognised here but is an item kind, not a company (it was a
#: sixth art-form value for one day, 2026-10-13). A performance is a concert
#: item when its printed title is one and nothing else has classed it
#: (lower-cased title, CONCERT_TITLE_RE), when its printed genre is «Кантата»,
#: or by art_form_by_title.csv; an evening with a heading and no titled work is
#: a concert evening when the heading names a concert (CONCERT_EVENT_RE).
#: «Литературное отдѣленіе» / «Отдѣленіе поэзіи» are recitation, not concert.
_CLASS_FORMS = ART_FORMS + ["concert"]
CONCERT_TITLE_RE = (r"^(концертное отдѣленіе|симфоническій концертъ|музыкальное( и декламаціонное)? отдѣленіе|"
                    r"концертъ( русской оперы)?\.?$|[0-9]+-й концертъ |реквіемъ|месса[- ]реквіемъ|кантата|"
                    r"музыкально-литературный вечеръ)")
#: Art form given to a title by hand where the print leaves no genre field to
#: read it from (first use, RG 2026-10-13: plays whose genre is printed inside
#: the title, «Трагедія о Гамлетѣ, принцѣ Датскомъ»; divertissements RG ruled
#: ballet, «Маскарадъ» [диверт.]). research.work title + genre (blank = the
#: work has none) -> art form, basis. Comes after the anthem, heading, visiting
#: and ballet rules and before every label rule.
#: The build fails if a title matches no work or the art form is not in ART_FORMS.
ART_FORM_BY_TITLE_CSV = Path(__file__).parent / "research_corrections" / "art_form_by_title.csv"
#: Company for ONE printed performance, where a source says who gave it although
#: the title does not (e.g. the season statistics count a gala's concert section as
#: "opera"). Keyed on the raw cell (page_id, date_text, theater, title); applied after
#: the concert step, so item_kind is untouched. The build fails if a row matches no
#: performance or names an art form outside ART_FORMS.
ART_FORM_BY_PERFORMANCE_CSV = Path(__file__).parent / "research_corrections" / "art_form_by_performance.csv"
#: RG's art-form rulings for work identity (build_entities.py); also applied to the
#: labels here, see apply_work_artform_overrides (known_issues.md #158).
WORK_ARTFORM_OVERRIDES_CSV = Path(__file__).parent / "entity_curation" / "work_artform_overrides.csv"
CONCERT_EVENT_RE = r"концерт|музыкально-литературн|литературно-музыкальн|вокально-инструментально"
#: Discipline and company for ONE annotation-only evening (no titled work), where a
#: source other than the annotation says who gave it -- e.g. the printed season
#: statistics counting two German charity evenings of March 1898 as German opera
#: (RG, 2026-10-23, known_issues.md #141). Keyed on season, city, date, theater and
#: time_of_day; applied after the visiting-troupe annotation rule. The build fails
#: if a row matches no evening or one that has titled works, or names a discipline
#: outside DISCIPLINES.
EVENT_LABELS_CSV = Path(__file__).parent / "research_corrections" / "event_labels.csv"

#: The anthem is "not a work, per se, but a ceremonial item" (RG, 2026-10-12):
#: it gets no art form and is left out of event.n_works / event.disciplines.
CEREMONIAL_TITLE_RE = r"^(Гимнъ|Hymne)"

#: A benefit or season heading that the print sets where a title would stand
#: and that is stored as a performance title. Not a work: no art form, not
#: counted in event.n_works; "Bénéfice" still sets event.is_benefit.
HEADING_TITLE_RE = r"^(Bénéfice |Clôture de la saison|Réouverture)"

#: Event annotations that name an outside troupe: (lower-case regex, troupe).
#: Deliberately explicit. A guest soloist appearing WITH a house troupe
#: ("Спектакль съ участіемъ г-жи Режанъ", "Съ участиемъ Томазо Сальвини",
#: "Avec le concours de ...") is not listed and falls to the ordinary rules.
VISITING_ANNOTATION_RULES = [
    (r"зандрокъ", "Adele Sandrock and her troupe"),
    (r"лессингъ-театра", "Berlin Lessing-Theater"),
    (r"режанъ съ ея трупп", "Réjane and her troupe"),
    (r"сарры бернаръ", "Sarah Bernhardt"),
    (r"сіамской придворной труппы", "Siamese court troupe"),
    (r"японской труппы", "Japanese troupe of the Imperial court theatre, Tokyo"),
    (r"вѣнск(ой|ая) оперет", "Vienna operetta troupe"),  # «Вѣнской Опереточной Труппы», «Вѣнской оперетты», «Вѣнская оперетка»
    (r"московскаго художественнаго театра", "Moscow Art Theatre"),
    (r"оперной труппы подъ управленіемъ", "opera troupe under Н. В. Любимовъ"),
    (r"итальянской оперы подъ управленіемъ", "Italian opera under Угетти"),
    (r"тины ди лоренцо", "Tina di Lorenzo"),
    (r"зонненталь", "Adolf Sonnenthal"),
    (r"eleonora duse", "Eleonora Duse"),
    (r"gastspiel", "German guest season"),
]

#: Comedy-ballets are dramas that contain dancers (RG, 2026-10-12: "classify them
#: as dramas, but note that they contain dancers. This is similar to operas").
#: Art form Russian drama; research.performance.includes_dance marks them.
COMEDY_BALLET_GENRE = "ком.-бал."

#: Operas and dramas known to contain dancers (RG, 2026-10-12). One row per
#: piece of evidence: work (title + printed genre, which picks the opera
#: «Фаустъ» and not the dramatic poem), season, city, optional date, source,
#: evidence. A performance is marked ONLY in a season and city for which there
#: is a row: "We can assume that all the performances of a production in one
#: season were similar, but not beyond that" (RG). includes_dance_basis reads
#: "direct: ..." when a row names that very date (or the printed genre is
#: «ком.-бал.») and "season: ..." when the evidence is for the work in that
#: season and city. The marker is TRUE or NULL, never FALSE. Excerpt rows of a
#: work are NOT marked (the excerpt need not be the act with the dances). Hand-checked: a dancer's role
#: in a title that is also a ballet («Донъ-Кихотъ», «Волшебная флейта»,
#: «Цыганка», the ballet «Млада») belongs to the ballet and is not listed.
#: The build fails if a row matches no work or more than one.
WORKS_WITH_DANCERS_CSV = Path(__file__).parent / "entity_curation" / "works_with_dancers.csv"

#: Printed genre labels (on the work or its excerpt parent).
OPERA_GENRE_RE = r"^(оп\.|опера$|опера-былина)"
OPERETTA_GENRE_RE = r"^(опер\.|оперет|шут\.-оперет|опера-вод)"
GERMAN_GENRE_RE = (r"^(Lustsp|Lustp|Lust\.|Schausp|Schwank|Schw\.|Oper|Posse|Trauersp|Volksst|Comödie|Komödie|Drama|"
                   r"Genrebild|Märchen|Charakter|Plauderei|Dr\.|Trag\.|Tragödie|dram\. Ged|dr\. Ged|Offiz|Rokoko|"
                   r"Scherz|Liebesdrama|Natur\.|ein |tragische|dramat\. Plauder)")
#: A Latin-script title that reads as German (lower-cased title).
GERMAN_TITLE_RE = r"(^|[ ,.!])(der|die|das|und|ein|eine|aus|von|zum|ich)([ ,.!]|$)"
#: Houses where an operetta counts as opera ("they go with the company that
#: performs them", RG 2026-10-12); at every other house it is Russian drama.
OPERA_HOUSES = ["Маріинскій", "Большой"]
#: Works the opera company gave under a label that is not an opera label:
#: canonical_title -> why. The build fails if a title matches no work.
OPERA_TITLE_OVERRIDES = {
    "Боярыня Вѣра Шелога": "printed «прологъ»: Rimsky-Korsakov's prologue to Псковитянка, given by the opera",
    "Гибель Фауста": "printed «драм. лег.»: Berlioz, La damnation de Faust, given by the opera",
    "Сказаніе о невидимомъ градѣ Китежѣ и дѣвѣ Февроніи":
        "Rimsky-Korsakov's opera; printed «оп.» in 1907-08, 1908-09 and 1910-11 but with no genre in its "
        "premiere season 1906-07, so classed by title (exception allowed by RG, 2026-10-12)",
}

#: Wording classes of the event annotation -> research.event flags. These
#: record what the annotation SAYS; they are not a judgement about prices.
EVENT_FLAG_RES = {
    "is_benefit": r"бенефис|bénéfice|benefi[sz]",
    # widened 2026-10-13 (RG: "yes"): fund-raising headings that name the beneficiary without «въ пользу»
    "is_charity": (r"[вб]ъ? пользу|благотворит|au profit|zum besten|wohlth[aä]tig|zu gunsten|"
                   r"для образованія фонда|на (усиленіе|основаніе|образованіе) (фонда|капиталовъ|средствъ)|"
                   r"съ отчисленіемъ части сбора|на памятникъ|pour élever un monument|"
                   r"попечительства о бѣдныхъ|общества попеченія|общества по устройству"),
    "is_free": r"безплатн|бесплатн",
    "is_student_performance": r"для учащ",
    "is_reduced_price": r"уменьшенн|prix r[ée]duits",
}


PERFORMANCE_GENRE_PATH = Path(__file__).parent / "entity_curation" / "research_performance_genre.csv"
PERFORMANCE_GENRE_NAMESPACE = uuid.UUID("5f0d3c1e-7a44-5b0e-9d5b-2c6f6b0a9e11")


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


#: List dates that are confirmed print typos (a misprinted month, an impossible day,
#: or a wrong digit that still parses). The raw tier keeps the print verbatim; the
#: intended date is supplied here, in the research layer only (RG's rule for genuine
#: print typos), and replaces the parsed one where raw has a date.
#: production_performance_id -> (ISO date, what the scan prints).
LIST_DATE_PRINT_TYPOS = {
    "balletproductions_1910-11_SP_p001__e009__d001": (
        "1911-02-13", "printed «Исполненъ: 1911 г.—феваля 13.» (no р; scan-checked 2026-10-11). "
        "Фіаметта, SP 1910-11; the Repertoire prints the same bill on 13 February 1911"),
    "balletproductions_1897-98_SP_p000__e002__d002": (
        "1897-11-14", "printed «ноября … 24» between 9 and 16 (scan-read twice, 2026-09-28); the Repertoire has "
        "«Дочь микадо» on 14 Nov 1897 (morning) and not on the 24th; one-digit slip (RG, 2026-10-15)"),
    "balletproductions_1897-98_SP_p000__e002__d006": (
        "1897-12-28", "printed «декабря 38» (impossible day; scan-read twice, 2026-09-28); the Repertoire has "
        "«Дочь микадо» on 28 Dec 1897 (evening); one-digit slip (RG, 2026-10-15)"),
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
    for perf_id, (iso, _why) in LIST_DATE_PRINT_TYPOS.items():
        row = con.execute("""
            SELECT e.season, e.city, e.title, p.note, p.date
            FROM raw.production_entry_performance p JOIN raw.production_entry e USING (production_entry_id)
            WHERE p.production_performance_id = ?""", [perf_id]).fetchone()
        if row is None:
            print(f"  WARNING: LIST_DATE_PRINT_TYPOS: {perf_id} not found in raw.production_entry_performance")
        else:                         # unparsed in raw, or parsed from the misprint: use the intended date
            if row[4] is not None:
                printed = (row[0], row[1], row[2], row[4].strftime('%Y-%m-%d'), row[3])
                if printed in lst:
                    lst.remove(printed)
            lst.append((row[0], row[1], row[2], iso, row[3]))
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
        SELECT e.production_entry_id, coalesce(m.to_id, b.work_id), e.season, e.city, e.title, e.list_number, e.is_premiere,
               e.description_text, e.total_count, e.n_dates,
               (SELECT count(*) FROM prod_work pw WHERE pw.production_id = e.production_entry_id),
               e.printed_page_number, e.source_file
        FROM raw.production_entry e
        LEFT JOIN prod_best b ON b.production_id = e.production_entry_id
        LEFT JOIN work_merge m ON m.from_id = b.work_id
    """)
    con.execute("""
        CREATE TABLE research.production_work (
            production_id VARCHAR REFERENCES research.production(production_id),
            work_id UUID REFERENCES research.work(work_id),
            n_matched_dates INTEGER,
            PRIMARY KEY (production_id, work_id)
        )""")
    # production_work's PK is (production_id, work_id), so a merge can make
    # two rows collide -- sum their matched dates rather than failing.
    con.execute("""
        INSERT INTO research.production_work
        SELECT pw.production_id, coalesce(m.to_id, pw.work_id) AS work_id,
               sum(pw.n_matched_dates)
        FROM prod_work pw LEFT JOIN work_merge m ON m.from_id = pw.work_id
        GROUP BY 1, 2
    """)
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
      repertoire_events    performed events (a morning and an evening row count twice);
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
            repertoire_events INTEGER, repertoire_days INTEGER, repertoire_events_with_receipts INTEGER,
            repertoire_receipts_kopecks BIGINT,
            repertoire_charity_text_events INTEGER, repertoire_charity_text_receipts_kopecks BIGINT,
            events_minus_printed INTEGER, days_minus_printed INTEGER,
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
            SELECT e.season, e.city, count(*) AS events,
                   count(DISTINCT (e.theater_id, coalesce(e.date, e.event_id))) AS days,
                   count(e.receipts_total_kopecks) AS events_rec,
                   coalesce(sum(e.receipts_total_kopecks), 0) AS rec,
                   count(*) FILTER (WHERE coalesce(regexp_matches(lower(a.annotation), 'въ пользу'), false)) AS ch_n,
                   coalesce(sum(e.receipts_total_kopecks) FILTER
                            (WHERE coalesce(regexp_matches(lower(a.annotation), 'въ пользу'), false)), 0) AS ch_rec
            FROM research.event e LEFT JOIN analysis.event_entry a USING (event_id)
            WHERE e.event_status = 'performed' GROUP BY e.season, e.city
        )
        SELECT p.season, p.city, pg.format, pg.printed_page,
               p.n, p.n_rec, p.rec,
               coalesce(r.events, 0), coalesce(r.days, 0), coalesce(r.events_rec, 0), coalesce(r.rec, 0),
               coalesce(r.ch_n, 0), coalesce(r.ch_rec, 0),
               coalesce(r.events, 0) - p.n, coalesce(r.days, 0) - p.n, coalesce(r.rec, 0) - p.rec  -- NULL with p.rec
        FROM printed p
        JOIN raw.season_stat_page pg USING (season)
        LEFT JOIN rep r ON r.season = p.season AND r.city = p.city
        ORDER BY p.season, p.city""")


#: Performances the Repertoire cell does not name but another part of the same
#: yearbook does (RG, 2026-10-12: "the research layer should have this"). One
#: row per performance: the event (season, city, date, theater, time of day),
#: the research.work title, the source and the basis. Raw is untouched; the
#: research row has no verbatim title and performance_source says where it
#: comes from. The build fails if a row does not match exactly one event, if
#: that event has a titled work in the Repertoire after all, or if the title
#: does not match exactly one research.work.
SUPPLIED_PERFORMANCES_CSV = Path(__file__).parent / "research_corrections" / "supplied_performances.csv"
FREE_PERIOD_NOTES_CSV = Path(__file__).parent / "research_corrections" / "free_period_notes.csv"


def load_supplied_performances(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("""CREATE OR REPLACE TEMP TABLE supplied_perf
                   (performance_id VARCHAR, event_id VARCHAR, work_id UUID, source VARCHAR, basis VARCHAR)""")
    if not SUPPLIED_PERFORMANCES_CSV.exists():
        return 0
    out = []
    for row in csv.DictReader(open(SUPPLIED_PERFORMANCES_CSV, encoding="utf-8")):
        ev = con.execute("""
            SELECT e.event_id FROM research.event e JOIN research.theater t USING (theater_id)
            WHERE e.season = ? AND e.city = ? AND CAST(e.date AS VARCHAR) = ? AND t.canonical_name = ?
              AND e.time_of_day = ?""",
            [row["season"], row["city"], row["date"], row["theater"], row["time_of_day"]]).fetchall()
        if len(ev) != 1:
            raise SystemExit(f"supplied_performances.csv: {row['date']} {row['theater']} matches {len(ev)} events")
        event_id = ev[0][0]
        titled = con.execute("""SELECT count(*) FROM raw.event_entry_performance
                                WHERE event_id = ? AND trim(coalesce(performance_title, '')) <> ''""",
                             [event_id]).fetchone()[0]
        if titled:
            raise SystemExit(f"supplied_performances.csv: {event_id} now has {titled} titled work(s) in the "
                             f"Repertoire; drop the row or check it")
        w = con.execute("""SELECT work_id FROM research.work
                           WHERE canonical_title = ? AND excerpt_of_work_id IS NULL""", [row["work_title"]]).fetchall()
        if len(w) != 1:
            raise SystemExit(f"supplied_performances.csv: {row['work_title']!r} matches {len(w)} works")
        n = sum(1 for o in out if o[1] == event_id) + 1
        out.append((f"{event_id}__supplied{n}", event_id, w[0][0], row["source"], row["basis"]))
    if out:
        con.executemany("INSERT INTO supplied_perf VALUES (?, ?, ?, ?, ?)", out)
    return len(out)


#: Performances whose WORK the research layer takes from another part of the
#: yearbook although the Repertoire names one (RG, 2026-10-13, first case: the
#: Repertoire prints «бал. Пахита» on a three-item bill, the ballet list says
#: «3-е дѣйствіе», "the research layer should show the 3rd act only"). One row
#: per performance: the event, the title as the Repertoire prints it, and the
#: research.work title it is shown under. Raw keeps the printed wording, and so
#: does research.performance.verbatim_title; performance_source says the work
#: was taken from elsewhere. The build fails unless a row matches exactly one
#: performance and one work.
PERFORMANCE_WORK_OVERRIDES_CSV = Path(__file__).parent / "research_corrections" / "performance_work_overrides.csv"


def load_performance_work_overrides(con: duckdb.DuckDBPyConnection) -> int:
    """Temp table perf_rework + the appearance counts of the two works. Must run
    after the per-performance genre splits and before research.performance is
    created (research.work is UPDATEd)."""
    con.execute("""CREATE OR REPLACE TEMP TABLE perf_rework
                   (performance_id VARCHAR, base_work_id UUID, target_work_id UUID, source VARCHAR, basis VARCHAR)""")
    if not PERFORMANCE_WORK_OVERRIDES_CSV.exists():
        return 0
    out = []
    for row in csv.DictReader(open(PERFORMANCE_WORK_OVERRIDES_CSV, encoding="utf-8")):
        hits = con.execute("""
            SELECT eep.performance_id, coalesce(ps.split_work_id, m.to_id, wl.work_id)
            FROM research.event e
            JOIN research.theater t USING (theater_id)
            JOIN raw.event_entry_performance eep ON eep.event_id = e.event_id
            JOIN entities.work_link wl ON wl.raw_performance_id = eep.performance_id
            LEFT JOIN work_merge m ON m.from_id = wl.work_id
            LEFT JOIN perf_split ps ON ps.performance_id = eep.performance_id
            WHERE e.season = ? AND e.city = ? AND CAST(e.date AS VARCHAR) = ? AND t.canonical_name = ?
              AND e.time_of_day = ? AND eep.performance_title = ?""",
            [row["season"], row["city"], row["date"], row["theater"], row["time_of_day"],
             row["verbatim_title"]]).fetchall()
        target = con.execute("SELECT work_id FROM research.work WHERE canonical_title = ?",
                             [row["research_work_title"]]).fetchall()
        if len(hits) != 1 or len(target) != 1:
            raise SystemExit(f"performance_work_overrides.csv: {row['date']} {row['theater']} "
                             f"{row['verbatim_title']!r} matches {len(hits)} performances, "
                             f"{row['research_work_title']!r} matches {len(target)} works")
        out.append((hits[0][0], hits[0][1], target[0][0], row["source"], row["basis"]))
    if out:
        con.executemany("INSERT INTO perf_rework VALUES (?, ?, ?, ?, ?)", out)
        con.execute("""UPDATE research.work SET appearance_count = appearance_count
                           - (SELECT count(*) FROM perf_rework r WHERE r.base_work_id = research.work.work_id)
                           + (SELECT count(*) FROM perf_rework r WHERE r.target_work_id = research.work.work_id)
                       WHERE work_id IN (SELECT base_work_id FROM perf_rework UNION SELECT target_work_id FROM perf_rework)""")
    return len(out)


def apply_work_artform_overrides(con: duckdb.DuckDBPyConnection) -> int:
    """RG's rulings in entity_curation/work_artform_overrides.csv (printed title +
    printed genre -> the work's real art form) decide work IDENTITY in
    build_entities.py. Until 2026-10-22 (known_issues.md #158) the labels here did
    not read them, so Massenet's «Донъ-Кихотъ, героич. ком.» was one opera work but
    its 12 performances were labelled Russian drama / play. Applied to perf_art after
    every other rule, with the identity step's own title/genre key, and only where
    the ruling changes art_form or item_kind; anthem, heading and visiting-troupe
    rows are left alone. An operetta goes with the company of the house that gave it,
    as the label rules above do. Returns the number of performances changed."""
    if not WORK_ARTFORM_OVERRIDES_CSV.exists():
        return 0
    from build_entities import _fold_genre, _match_key, _strip_genre_suffix, _title_key

    def key(title, genre):
        return (_match_key(_title_key(_strip_genre_suffix(title or ""))), _fold_genre(genre))

    rulings = {key(r["printed_title"], r["printed_genre"]): r
               for r in csv.DictReader(open(WORK_ARTFORM_OVERRIDES_CSV, encoding="utf-8"))}
    rows = con.execute("""
        SELECT pa.performance_id, pb.title, nullif(eep.genre, ''), pb.theater, pa.art_form, pa.item_kind
        FROM perf_art pa JOIN perf_base pb USING (performance_id)
        JOIN raw.event_entry_performance eep USING (performance_id)
        WHERE NOT coalesce(pa.is_ceremonial, false) AND NOT coalesce(pa.is_heading, false)
          AND pa.art_form IS DISTINCT FROM 'visiting troupe'""").fetchall()
    changed = 0
    for pid, title, genre, theater, art, kind in rows:
        r = rulings.get(key(title, genre))
        if r is None:
            continue
        ruling = r["treat_as_art_form"]
        if ruling == "operetta":
            new_art, new_kind = ("opera" if theater in OPERA_HOUSES else "Russian drama"), "operetta"
        elif ruling == "spoken":
            new_art, new_kind = (art if art in ("Russian drama", "French drama") else "Russian drama"), "play"
        elif ruling in ("ballet", "opera"):
            new_art, new_kind = ruling, ruling
        else:
            raise SystemExit(f"work_artform_overrides.csv: unknown treat_as_art_form {ruling!r}")
        if (new_art, new_kind) == (art, kind):
            continue
        why = f"work_artform_overrides.csv ({ruling}): {r['basis']}"
        con.execute("""UPDATE perf_art SET art_form = ?, art_form_basis = ?, item_kind = ?, item_kind_basis = ?
                       WHERE performance_id = ?""", [new_art, why, new_kind, why, pid])
        changed += 1
    print(f"  performances relabelled by work_artform_overrides.csv: {changed}")
    return changed


def resolve_discipline_and_company(con: duckdb.DuckDBPyConnection) -> None:
    """perf_art.discipline / discipline_basis / company from the internal art_form
    (DISCIPLINE and COMPANY above). Runs after every art-form and kind rule. A
    visiting troupe named by an annotation takes its troupe's discipline; an unnamed
    German-language item takes German drama / opera / operetta by its kind; the
    Moscow seasons of operas with Latin-script titles (1893-94, 1896-97, all Italian
    titles) take Italian opera. A visiting item the kind rules could only call "play"
    (they ran while it was the catch-all) takes the kind of its troupe's discipline when
    that is opera or operetta: «4-o atto di op. Gli Ugonotti», «2-е д. оперет. Цыганскій
    баронъ»."""
    for name in {n for _, n in VISITING_ANNOTATION_RULES}:
        if name not in VISITING_TROUPE_DISCIPLINE:
            raise SystemExit(f"VISITING_TROUPE_DISCIPLINE: no discipline entry for troupe {name!r}")
    for col in ("discipline", "discipline_basis", "company"):
        con.execute(f"ALTER TABLE perf_art ADD COLUMN {col} VARCHAR")
    con.execute("CREATE OR REPLACE TEMP TABLE troupe_discipline (troupe VARCHAR, discipline VARCHAR)")
    con.executemany("INSERT INTO troupe_discipline VALUES (?, ?)", list(VISITING_TROUPE_DISCIPLINE.items()))
    con.execute("CREATE OR REPLACE TEMP TABLE city_name (city VARCHAR, name VARCHAR)")
    con.executemany("INSERT INTO city_name VALUES (?, ?)", list(CITY_NAMES.items()))
    # the Directorate's own troupes: company = city + discipline
    con.execute("""
        UPDATE perf_art SET discipline = perf_art.art_form, discipline_basis = perf_art.art_form_basis,
               company = cn.name || ' ' || perf_art.art_form
        FROM perf_base pb JOIN city_name cn ON cn.city = pb.city
        WHERE pb.performance_id = perf_art.performance_id AND perf_art.art_form IS NOT NULL
          AND perf_art.art_form <> 'visiting troupe'""")
    # visiting troupes
    con.execute("""
        CREATE OR REPLACE TEMP TABLE visiting_resolved AS
        SELECT performance_id, discipline, art_form_basis || '; ' || why AS basis,
               coalesce(visiting_troupe, 'visiting ' || discipline || ' troupe, ' || city_label) AS company
        FROM (
            SELECT pa.performance_id, pa.art_form_basis, pb.visiting_troupe, cn.name AS city_label,
                   CASE WHEN pb.visiting_troupe IS NOT NULL THEN td.discipline
                        WHEN pa.art_form_basis LIKE 'opera with a Latin-script title%' THEN 'Italian opera'
                        WHEN pa.item_kind = 'opera' THEN 'German opera'
                        WHEN pa.item_kind = 'operetta' THEN 'German operetta'
                        ELSE 'German drama' END AS discipline,
                   CASE WHEN pb.visiting_troupe IS NOT NULL
                        THEN 'visiting troupe (' || pb.visiting_troupe || '): discipline by its personnel (RG, 2026-10-22)'
                        WHEN pa.art_form_basis LIKE 'opera with a Latin-script title%'
                        THEN 'unnamed visiting opera season, Italian titles: Italian opera (RG, 2026-10-22)'
                        ELSE 'unnamed German-language visiting troupe: German drama, opera or operetta by the kind of item (RG, 2026-10-22)'
                   END AS why
            FROM perf_art pa JOIN perf_base pb USING (performance_id)
            LEFT JOIN troupe_discipline td ON td.troupe = pb.visiting_troupe
            LEFT JOIN city_name cn ON cn.city = pb.city
            WHERE pa.art_form = 'visiting troupe'
        )""")
    con.execute("""
        UPDATE perf_art SET discipline = v.discipline, discipline_basis = v.basis, company = v.company
        FROM visiting_resolved v WHERE v.performance_id = perf_art.performance_id""")
    con.execute("""
        UPDATE perf_art SET
            item_kind = CASE discipline WHEN 'German operetta' THEN 'operetta' ELSE 'opera' END,
            item_kind_basis = 'the troupe''s discipline (' || discipline || '); the label rules alone gave play'
        WHERE art_form = 'visiting troupe' AND item_kind = 'play'
          AND discipline IN ('Italian opera', 'German opera', 'German operetta', 'opera')""")
    bad = con.execute("SELECT count(*) FROM perf_art WHERE discipline IS NOT NULL AND discipline NOT IN ("
                      + ", ".join("'" + d + "'" for d in DISCIPLINES) + ")").fetchone()[0]
    assert bad == 0, "perf_art holds a discipline outside DISCIPLINES"
    left = con.execute("SELECT count(*) FROM perf_art WHERE art_form IS NOT NULL AND discipline IS NULL").fetchone()[0]
    print(f"  performances with an art form but no discipline (troupe not decided): {left}")


def build_art_forms(con: duckdb.DuckDBPyConnection) -> None:
    """Temp table perf_art: one row per research performance with its art form
    (see ART_FORMS above), then the event-level summary columns. Must run after
    research.event and the per-performance work splits, and BEFORE
    research.performance is created: research.event is UPDATEd here, which
    DuckDB rejects once a table references it."""
    def lit(x: str) -> str:
        return "'" + x.replace("'", "''") + "'"

    visiting_case = "CASE " + " ".join(
        f"WHEN regexp_matches(lower(coalesce(annotation, '')), {lit(rx)}) THEN {lit(name)}"
        for rx, name in VISITING_ANNOTATION_RULES) + " END"
    con.execute("CREATE OR REPLACE TEMP TABLE opera_title (title VARCHAR, why VARCHAR)")
    con.executemany("INSERT INTO opera_title VALUES (?, ?)", list(OPERA_TITLE_OVERRIDES.items()))
    for title in OPERA_TITLE_OVERRIDES:
        if not con.execute("SELECT 1 FROM research.work WHERE canonical_title = ? LIMIT 1", [title]).fetchone():
            raise SystemExit(f"OPERA_TITLE_OVERRIDES: {title!r} matches no research.work")
    houses = ", ".join(lit(h) for h in OPERA_HOUSES)
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE perf_base AS
        SELECT eep.performance_id, eep.event_id, eep.performance_title AS title,
               w.canonical_title, coalesce(w.canonical_genre, par.canonical_genre) AS g,
               -- the label as printed on THIS performance: decides the language of a
               -- Latin-script item (a merged work's canonical genre can be the other language's)
               coalesce(nullif(eep.genre, ''), w.canonical_genre, par.canonical_genre) AS vg,
               (w.work_id IN (SELECT work_id FROM work_ballet)
                OR coalesce(par.work_id IN (SELECT work_id FROM work_ballet), false)) AS parent_ballet,
               coalesce(ot.why, pot.why) AS opera_override,
               t.canonical_name AS theater,
               w.work_id, e.season, e.city, CAST(e.date AS VARCHAR) AS ev_date,
               -- a Cyrillic genre label marks a Russian-language performance even
               -- under a Latin-script title («Tête-à-tête, ком.»)
               regexp_matches(coalesce(eep.performance_title, '') || ' ' ||
                              coalesce(nullif(eep.genre, ''), w.canonical_genre, par.canonical_genre, ''),
                              '[А-Яа-яѣѢіІѳѲѵѴ]') AS cyr,
               regexp_matches(coalesce(eep.performance_title, '') || ' ' ||
                              coalesce(nullif(eep.genre, ''), w.canonical_genre, par.canonical_genre, ''),
                              '[A-Za-z]') AS lat,
               {visiting_case.replace('annotation', 'a.annotation')} AS visiting_troupe
        FROM raw.event_entry_performance eep
        JOIN entities.work_link wl ON wl.raw_performance_id = eep.performance_id
        LEFT JOIN work_merge m ON m.from_id = wl.work_id
        LEFT JOIN perf_split ps ON ps.performance_id = eep.performance_id
        LEFT JOIN perf_rework pr ON pr.performance_id = eep.performance_id
        JOIN research.work w ON w.work_id = coalesce(pr.target_work_id, ps.split_work_id, m.to_id, wl.work_id)
        LEFT JOIN research.work par ON par.work_id = w.excerpt_of_work_id
        LEFT JOIN opera_title ot ON ot.title = w.canonical_title
        LEFT JOIN opera_title pot ON pot.title = par.canonical_title
        JOIN research.event e ON e.event_id = eep.event_id
        JOIN analysis.event_entry a ON a.event_id = eep.event_id
        LEFT JOIN research.theater t ON t.theater_id = e.theater_id
    """)
    # supplied performances: classed by their work alone (no printed title or label)
    con.execute("""
        INSERT INTO perf_base
        SELECT sp.performance_id, sp.event_id, NULL, w.canonical_title, w.canonical_genre, w.canonical_genre,
               w.work_id IN (SELECT work_id FROM work_ballet), NULL, t.canonical_name,
               w.work_id, e.season, e.city, CAST(e.date AS VARCHAR), true, false, NULL
        FROM supplied_perf sp
        JOIN research.work w ON w.work_id = sp.work_id
        JOIN research.event e ON e.event_id = sp.event_id
        LEFT JOIN research.theater t ON t.theater_id = e.theater_id
    """)
    con.execute("CREATE OR REPLACE TEMP TABLE art_title (title VARCHAR, genre VARCHAR, art_form VARCHAR, basis VARCHAR)")
    if ART_FORM_BY_TITLE_CSV.exists():
        for row in csv.DictReader(open(ART_FORM_BY_TITLE_CSV, encoding="utf-8")):
            if row["art_form"] not in _CLASS_FORMS:
                raise SystemExit(f"art_form_by_title.csv: {row['art_form']!r} is not an art form")
            if not con.execute("""SELECT 1 FROM research.work WHERE canonical_title = ?
                                  AND coalesce(canonical_genre, '') = ? LIMIT 1""",
                               [row["canonical_title"], row["canonical_genre"]]).fetchone():
                raise SystemExit(f"art_form_by_title.csv: {row['canonical_title']!r} "
                                 f"[{row['canonical_genre']}] matches no research.work")
            con.execute("INSERT INTO art_title VALUES (?, ?, ?, ?)",
                        [row["canonical_title"], row["canonical_genre"], row["art_form"], row["basis"]])
    con.execute("ALTER TABLE perf_base ADD COLUMN title_form VARCHAR")
    con.execute("ALTER TABLE perf_base ADD COLUMN title_basis VARCHAR")
    con.execute("""UPDATE perf_base SET title_form = a.art_form, title_basis = a.basis
                   FROM art_title a, research.work w
                   WHERE w.work_id = perf_base.work_id AND a.title = w.canonical_title
                     AND a.genre = coalesce(w.canonical_genre, '')""")

    # A work with no canonical genre (the majority of its printings carry none):
    # a performance takes the genre printed on it, and failing that the genre
    # printed for the same work in the SAME SEASON -- not beyond (RG, 2026-10-12:
    # "yes, as long as they are in the same season"). «Сказаніе о невидимомъ градѣ
    # Китежѣ» is printed «оп.» on 11 of 33 performances, none of them in 1906-07.
    con.execute("ALTER TABLE perf_base ADD COLUMN g_from_season BOOLEAN DEFAULT false")
    con.execute("UPDATE perf_base SET g = vg WHERE g IS NULL AND vg IS NOT NULL")
    con.execute("""
        CREATE OR REPLACE TEMP TABLE season_genre AS
        SELECT work_id, season, mode(vg) AS g FROM perf_base WHERE vg IS NOT NULL GROUP BY 1, 2""")
    con.execute("""
        UPDATE perf_base SET g = sg.g, vg = sg.g, g_from_season = true
        FROM season_genre sg
        WHERE perf_base.g IS NULL AND sg.work_id = perf_base.work_id AND sg.season = perf_base.season""")

    # One ordered list of rules; the first that applies decides. Each yields
    # (art_form, basis); art_form NULL = deliberately unassigned.
    rules = [
        (f"regexp_matches(canonical_title, {lit(CEREMONIAL_TITLE_RE)})",
         "NULL", "'ceremonial item (anthem): not a work, no art form (RG, 2026-10-12)'"),
        (f"regexp_matches(coalesce(title, ''), {lit(HEADING_TITLE_RE)})",
         "NULL", "'a benefit or season heading stored as a title: not a work'"),
        ("visiting_troupe IS NOT NULL",
         "'visiting troupe'", "'annotation names an outside troupe: ' || visiting_troupe"),
        # a title curated as a concert item outranks the ballet rule: an orchestral suite from a
        # ballet stays linked to its parent work but is not a ballet performance (RG, 2026-10-13)
        ("title_form = 'concert'", "title_form", "title_basis"),
        ("parent_ballet OR regexp_matches(coalesce(g, ''), '^(изъ )?бал')",
         "'ballet'", "CASE WHEN parent_ballet THEN 'in the ballet productions lists or ruled ballet (the work or its parent)' ELSE 'printed genre ' || g END"),
        ("title_form IS NOT NULL", "title_form", "title_basis"),
        (f"g = {lit(COMEDY_BALLET_GENRE)}", "'Russian drama'",
         "'comedy-ballet (ком.-бал.): a drama with dancers, given by the drama company (RG, 2026-10-12)'"),
        (f"regexp_matches(lower(coalesce(title, '')), {lit(CONCERT_TITLE_RE)}) AND (g IS NULL OR lower(g) LIKE 'кантат%')",
         "'concert'", "'concert item by its printed title (RG, 2026-10-13)'"),
        ("lower(coalesce(g, '')) LIKE 'кантат%'", "'concert'", "'printed genre ' || g || ': a cantata, classed as concert'"),
        ("regexp_matches(lower(coalesce(g, '')), '^диверт')",
         "NULL", "'divertissement: no art form assigned'"),
        (f"NOT cyr AND lat AND regexp_matches(coalesce(vg, ''), {lit(GERMAN_GENRE_RE)})",
         "'visiting troupe'", "'German-language performance (printed genre ' || vg || ')'"),
        ("NOT cyr AND lat AND (vg = 'op.' OR regexp_matches(lower(title), 'atto di op'))",
         "'visiting troupe'", "'opera with a Latin-script title: Italian or German opera season'"),
        (f"NOT cyr AND lat AND regexp_matches(lower(title), {lit(GERMAN_TITLE_RE)})",
         "'visiting troupe'", "'German-language performance (German title)'"),
        ("NOT cyr AND lat",
         "'French drama'", "'Latin-script title with no German marker' || coalesce(' (printed genre ' || vg || ')', '')"),
        ("NOT cyr", "NULL", "'title has no letters'"),
        ("opera_override IS NOT NULL", "'opera'", "opera_override"),
        (f"regexp_matches(coalesce(g, ''), {lit(OPERA_GENRE_RE)})", "'opera'", "'printed genre ' || g"),
        (f"regexp_matches(coalesce(g, ''), {lit(OPERETTA_GENRE_RE)}) AND theater IN ({houses})",
         "'opera'", "'operetta at an opera house: goes with the company that performs it (printed genre ' || g || ')'"),
        (f"regexp_matches(coalesce(g, ''), {lit(OPERETTA_GENRE_RE)})",
         "'Russian drama'", "'operetta at a drama house: goes with the company that performs it (printed genre ' || g || ')'"),
        ("g IS NULL", "NULL", "'no genre printed: art form not assigned'"),
        ("true", "'Russian drama'", "'Cyrillic title, printed genre ' || g"),
    ]
    form_case = "CASE " + " ".join(f"WHEN {c} THEN {f}" for c, f, _ in rules) + " END"
    basis_case = "CASE " + " ".join(f"WHEN {c} THEN {b}" for c, _, b in rules) + " END"
    # dancers in operas and dramas (WORKS_WITH_DANCERS_CSV)
    con.execute("""CREATE OR REPLACE TEMP TABLE dance_ev
                   (work_id UUID, season VARCHAR, city VARCHAR, ev_date VARCHAR, source VARCHAR, evidence VARCHAR)""")
    if WORKS_WITH_DANCERS_CSV.exists():
        ev_rows = []
        for row in csv.DictReader(open(WORKS_WITH_DANCERS_CSV, encoding="utf-8")):
            hit = con.execute("""SELECT work_id FROM research.work WHERE canonical_title = ? AND canonical_genre = ?
                                 AND excerpt_of_work_id IS NULL
                                 AND work_id NOT IN (SELECT work_id FROM work_ballet)""",
                              [row["work_title"], row["work_genre"]]).fetchall()
            if len(hit) != 1:
                raise SystemExit(f"works_with_dancers.csv: {row['work_title']!r} [{row['work_genre']}] "
                                 f"matches {len(hit)} works")
            ev_rows.append((hit[0][0], row["season"], row["city"], row.get("date") or None,
                            row["source"], row["evidence"]))
        con.executemany("INSERT INTO dance_ev VALUES (?, ?, ?, ?, ?, ?)", ev_rows)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE dance_season AS
        SELECT work_id, season, city, list(ev_date) FILTER (WHERE ev_date IS NOT NULL) AS dates,
               string_agg(source || ': ' || evidence, ' | ' ORDER BY source) AS evidence
        FROM dance_ev GROUP BY ALL""")
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE perf_art AS
        SELECT performance_id, event_id, {form_case} AS art_form, {basis_case} AS art_form_basis,
               coalesce(g = {lit(COMEDY_BALLET_GENRE)}, false) OR dd.work_id IS NOT NULL AS includes_dance,
               CASE WHEN g = {lit(COMEDY_BALLET_GENRE)} THEN 'direct: printed genre ком.-бал.'
                    WHEN dd.work_id IS NOT NULL AND list_contains(coalesce(dd.dates, []), pb.ev_date)
                    THEN 'direct: ' || dd.evidence
                    WHEN dd.work_id IS NOT NULL
                    THEN 'season: dancers attested in this work in this season and city (' || dd.evidence || ')'
               END AS includes_dance_basis,
               regexp_matches(canonical_title, {lit(CEREMONIAL_TITLE_RE)}) AS is_ceremonial,
               regexp_matches(coalesce(title, ''), {lit(HEADING_TITLE_RE)}) AS is_heading,

               regexp_matches(lower(coalesce(title, '')), 'bénéfice') AS title_benefit
        FROM perf_base pb
        LEFT JOIN dance_season dd ON dd.work_id = pb.work_id AND dd.season = pb.season AND dd.city = pb.city
    """)
    con.execute("""
        UPDATE perf_art SET art_form_basis = art_form_basis ||
               '; the genre is printed for this work elsewhere in the same season, not on this performance'
        WHERE art_form IS NOT NULL
          AND performance_id IN (SELECT performance_id FROM perf_base WHERE g_from_season)""")
    # A Latin-script item with no German marker of its own takes "visiting" from a
    # German-language item on the same bill (it would otherwise default to French).
    con.execute("""
        UPDATE perf_art SET art_form = 'visiting troupe',
               art_form_basis = 'Latin-script title with no German marker; the same bill has a German-language item'
        WHERE art_form = 'French drama'
          AND event_id IN (SELECT event_id FROM perf_art WHERE art_form_basis LIKE 'German-language%')
    """)
    bad = con.execute("SELECT count(*) FROM perf_art WHERE art_form IS NOT NULL AND art_form NOT IN ("
                      + ", ".join(lit(a) for a in _CLASS_FORMS) + ")").fetchone()[0]
    assert bad == 0, "perf_art holds an art form outside ART_FORMS + concert"

    # The kind of item (ITEM_KINDS). First rule that applies decides.
    kind_rules = [
        ("pa.is_ceremonial", "anthem", "the anthem"),
        ("pa.is_heading", None, None),
        (f"regexp_matches(lt, {lit(CINEMA_TITLE_RE)})", "cinema", "printed title"),
        (f"regexp_matches(lt, {lit(LECTURE_TITLE_RE)})", "lecture", "printed title"),
        (f"regexp_matches(lt, {lit(RECITATION_TITLE_RE)})", "recitation / reading", "printed title"),
        (f"regexp_matches(lt, {lit(TABLEAU_TITLE_RE)}) AND pa.art_form IS DISTINCT FROM 'concert'",
         "tableau / apotheosis", "printed title"),
        (f"regexp_matches(lt, {lit(DIVERTISSEMENT_TITLE_RE)}) OR regexp_matches(lab, {lit(DIVERTISSEMENT_GENRE_RE)})",
         "divertissement", "printed title or label"),
        ("pa.art_form = 'concert'", "concert", "concert item (title, label «Кантата», or art_form_by_title.csv)"),
        ("pa.art_form = 'ballet'", "ballet", "ballet"),
        (f"regexp_matches(lab, {lit(OPERETTA_GENRE_RE_ANY)}) OR regexp_matches(lt, ', оперетта$')",
         "operetta", "printed label or title"),
        (f"pa.art_form = 'opera' OR regexp_matches(lab, {lit(OPERA_GENRE_RE_ANY)})", "opera", "opera"),
        (f"lab = {lit(COMEDY_BALLET_GENRE)}", "comedy-ballet", "printed label ком.-бал."),
        (f"regexp_matches(lab, {lit(PANTOMIME_GENRE_RE)})", "pantomime", "printed label"),
        ("pa.art_form IN ('Russian drama', 'French drama', 'visiting troupe')", "play",
         "a spoken-drama item of that company"),
    ]
    kind_case = "CASE " + " ".join(f"WHEN {c} THEN {lit(k) if k else 'NULL'}" for c, k, _ in kind_rules) + " END"
    kbasis_case = "CASE " + " ".join(f"WHEN {c} THEN {lit(b) if b else 'NULL'}" for c, _, b in kind_rules) + " END"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE perf_kind AS
        SELECT pa.performance_id, {kind_case} AS item_kind, {kbasis_case} AS item_kind_basis,
               regexp_matches(lt, {lit(DANCE_TITLE_RE)}) AND pa.art_form IS DISTINCT FROM 'ballet' AS title_dance
        FROM perf_art pa
        JOIN (SELECT performance_id, lower(coalesce(title, '')) AS lt, lower(coalesce(vg, g, '')) AS lab
              FROM perf_base) pb USING (performance_id)
    """)
    con.execute("ALTER TABLE perf_art ADD COLUMN item_kind VARCHAR")
    con.execute("ALTER TABLE perf_art ADD COLUMN item_kind_basis VARCHAR")
    con.execute("""UPDATE perf_art SET item_kind = k.item_kind, item_kind_basis = k.item_kind_basis
                   FROM perf_kind k WHERE k.performance_id = perf_art.performance_id""")
    con.execute("""UPDATE perf_art SET includes_dance = true,
                          includes_dance_basis = 'direct: the printed title names a dance'
                   WHERE NOT coalesce(includes_dance, false)
                     AND performance_id IN (SELECT performance_id FROM perf_kind WHERE title_dance)""")
    bad = con.execute("SELECT count(*) FROM perf_art WHERE item_kind IS NOT NULL AND item_kind NOT IN ("
                      + ", ".join(lit(k) for k in ITEM_KINDS) + ")").fetchone()[0]
    assert bad == 0, "perf_art holds an item kind outside ITEM_KINDS"
    # concert is a kind of item, not a company: it leaves art_form here
    con.execute("""UPDATE perf_art SET art_form = NULL,
                          art_form_basis = 'concert item: a kind of item, not a company (see item_kind)'
                   WHERE art_form = 'concert'""")
    if ART_FORM_BY_PERFORMANCE_CSV.exists():
        for row in csv.DictReader(open(ART_FORM_BY_PERFORMANCE_CSV, encoding="utf-8")):
            if row["art_form"] not in ART_FORMS:
                raise SystemExit(f"art_form_by_performance.csv: {row['art_form']!r} is not in ART_FORMS")
            ids = [r[0] for r in con.execute("""
                SELECT p.performance_id FROM raw.event_entry_performance p JOIN raw.event_entry e USING (event_id)
                WHERE e.page_id = ? AND e.date_text = ? AND e.theater = ? AND p.performance_title = ?""",
                [row["page_id"], row["date_text"], row["theater"], row["performance_title"]]).fetchall()]
            if len(ids) != 1:
                raise SystemExit(f"art_form_by_performance.csv: {row['page_id']} {row['date_text']} "
                                 f"{row['performance_title']!r} matches {len(ids)} performances")
            con.execute("UPDATE perf_art SET art_form = ?, art_form_basis = ? WHERE performance_id = ?",
                        [row["art_form"], row["basis"], ids[0]])
    apply_work_artform_overrides(con)
    resolve_discipline_and_company(con)
    order_case = "CASE discipline " + " ".join(f"WHEN {lit(a)} THEN {i}" for i, a in enumerate(DISCIPLINES)) + " END"
    korder_case = "CASE item_kind " + " ".join(f"WHEN {lit(k)} THEN {i}" for i, k in enumerate(ITEM_KINDS)) + " END"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE event_art AS
        SELECT event_id,
               count(*) FILTER (WHERE NOT is_ceremonial AND NOT is_heading) AS n_works,
               (SELECT string_agg(af, '; ' ORDER BY o) FROM (
                    SELECT DISTINCT discipline AS af, {order_case} AS o FROM perf_art p2
                    WHERE p2.event_id = p.event_id AND discipline IS NOT NULL)) AS disciplines,
               (SELECT string_agg(co, '; ' ORDER BY o, co) FROM (
                    SELECT DISTINCT company AS co, {order_case} AS o FROM perf_art p2
                    WHERE p2.event_id = p.event_id AND company IS NOT NULL)) AS companies,
               (SELECT string_agg(ik, '; ' ORDER BY o) FROM (
                    SELECT DISTINCT item_kind AS ik, {korder_case} AS o FROM perf_art p2
                    WHERE p2.event_id = p.event_id AND item_kind IS NOT NULL)) AS item_kinds,
               bool_or(is_ceremonial) AS has_anthem,
               bool_or(title_benefit) AS title_benefit
        FROM perf_art p GROUP BY event_id
    """)
    con.execute(f"""
        UPDATE research.event SET
            n_works = coalesce((SELECT n_works FROM event_art x WHERE x.event_id = research.event.event_id), 0),
            disciplines = (SELECT disciplines FROM event_art x WHERE x.event_id = research.event.event_id),
            companies = (SELECT companies FROM event_art x WHERE x.event_id = research.event.event_id),
            genre_families = coalesce(
                (SELECT item_kinds FROM event_art x WHERE x.event_id = research.event.event_id),
                -- a concert evening the Repertoire gives as a heading only, with no titled work
                CASE WHEN event_status = 'performed'
                      AND NOT EXISTS (SELECT 1 FROM event_art x WHERE x.event_id = research.event.event_id AND x.n_works > 0)
                      AND regexp_matches(lower(coalesce(annotation, '')), '{CONCERT_EVENT_RE}')
                     THEN 'concert' END),
            has_anthem = coalesce((SELECT has_anthem FROM event_art x WHERE x.event_id = research.event.event_id), false),
            is_benefit = is_benefit OR coalesce(
                (SELECT title_benefit FROM event_art x WHERE x.event_id = research.event.event_id), false)
    """)
    # A visiting troupe's event the Repertoire gives as an annotation only, with no
    # titled work (the Siamese court troupe, 28-29 Oct 1900): the troupe's discipline
    # and company go on the event, as a concert heading's genre family does above.
    n_annot = 0
    for rx, name in VISITING_ANNOTATION_RULES:
        disc = VISITING_TROUPE_DISCIPLINE.get(name)
        if disc is None:
            continue
        n_annot += con.execute("""
            UPDATE research.event SET disciplines = ?, companies = ?
            WHERE event_status = 'performed' AND coalesce(n_works, 0) = 0 AND disciplines IS NULL
              AND regexp_matches(lower(coalesce(annotation, '')), ?)""", [disc, name, rx]).fetchone()[0]
    print(f"  events with no titled work given a visiting troupe's discipline from the annotation: {n_annot}")
    if EVENT_LABELS_CSV.exists():
        n_lab = 0
        for row in csv.DictReader(open(EVENT_LABELS_CSV, encoding="utf-8")):
            if row["discipline"] not in DISCIPLINES:
                raise SystemExit(f"event_labels.csv: {row['discipline']!r} is not in DISCIPLINES")
            hits = con.execute("""
                SELECT e.event_id, coalesce(e.n_works, 0) FROM research.event e
                JOIN research.theater t USING (theater_id)
                WHERE e.season = ? AND e.city = ? AND CAST(e.date AS VARCHAR) = ?
                  AND t.canonical_name = ? AND e.time_of_day = ? AND e.event_status = 'performed'""",
                [row["season"], row["city"], row["date"], row["theater"], row["time_of_day"]]).fetchall()
            if len(hits) != 1 or hits[0][1] != 0:
                raise SystemExit(f"event_labels.csv: {row['date']} {row['theater']} {row['time_of_day']} "
                                 f"matches {len(hits)} performed evening(s)"
                                 + (" with titled works" if hits and hits[0][1] else ""))
            con.execute("UPDATE research.event SET disciplines = ?, companies = ? WHERE event_id = ?",
                        [row["discipline"], row["company"], hits[0][0]])
            n_lab += 1
        print(f"  annotation-only evenings labelled from event_labels.csv: {n_lab}")
    print("  disciplines (performances):")
    for af, n in con.execute("SELECT discipline, count(*) FROM perf_art GROUP BY 1 ORDER BY 2 DESC").fetchall():
        print(f"    {af or '(none)'}: {n}")
    print("  companies (performances):")
    for co, n in con.execute("SELECT company, count(*) FROM perf_art GROUP BY 1 ORDER BY 2 DESC").fetchall():
        print(f"    {co or '(none)'}: {n}")
    print("  genre families (performances):")
    for k, n in con.execute("SELECT item_kind, count(*) FROM perf_art GROUP BY 1 ORDER BY 2 DESC").fetchall():
        print(f"    {k or '(none)'}: {n}")


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
              "performance", "event", "person_tenure_note", "person_appearance", "person", "work", "theater"]:
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
            genre_note VARCHAR
        )
    """)
    # research.work had parent_genre / parent_genre_note until 2026-10-13, when RG
    # dropped them ("we don't seem to need it"): art_form and item_kind on
    # research.performance say the same and more. The rule behind it is kept, as
    # the internal temp table work_ballet below: a work in a ballet productions
    # list (or ruled ballet by RG) is ballet whatever its printed genre.
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
    for title, note in PARENT_GENRE_BALLET_TITLES.items():
        ids = [r[0] for r in con.execute("SELECT work_id FROM entities.work WHERE canonical_title = ?", [title]).fetchall()]
        if not ids:
            raise SystemExit(f"PARENT_GENRE_BALLET_TITLES: {title!r} matches no entities.work row")
        con.executemany("INSERT INTO parent_genre_ballet VALUES (?, ?)",
                        [(w, note) for w in ids if w not in listed])
    con.execute("CREATE OR REPLACE TEMP TABLE title_correction (verbatim_title VARCHAR, corrected_title VARCHAR, note VARCHAR)")
    con.executemany("INSERT INTO title_correction VALUES (?, ?, ?)",
                    [(verbatim, corrected, note) for verbatim, (corrected, note) in RESEARCH_TITLE_CORRECTIONS.items()])
    for verbatim in RESEARCH_TITLE_CORRECTIONS:
        n = con.execute("SELECT count(*) FROM entities.work WHERE canonical_title = ?", [verbatim]).fetchone()[0]
        if n == 0:
            raise SystemExit(f"RESEARCH_TITLE_CORRECTIONS: {verbatim!r} matches no entities.work row")

    # A title correction renames a work; it must also MERGE it. "Шоиеніана"
    # is a genuine print typo for "Шопеніана" (docs/eval/genuine_print_typos.md),
    # so the raw layer keeps the typo and this layer shows the real title --
    # but before 2026-10-10 the corrected row kept its own work_id, so
    # research.work held TWO 'Шопеніана' rows and a researcher joining
    # through either got 11 performances or 1, never all 12. Identity has to
    # follow the title.
    #
    # Scoped deliberately to collisions a correction CREATES: entities.work
    # has no exact (title, genre) duplicates of its own, and merging
    # near-duplicate spellings is a separate, scan-checked judgment call, not
    # something a build script should decide.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE work_merge AS
        SELECT w.work_id AS from_id, t.work_id AS to_id
        FROM entities.work w
        JOIN title_correction tc ON tc.verbatim_title = w.canonical_title
        JOIN entities.work t
          ON t.canonical_title = tc.corrected_title
         AND t.canonical_genre IS NOT DISTINCT FROM w.canonical_genre
         AND t.work_id <> w.work_id
    """)
    merges = con.execute("SELECT count(*) FROM work_merge").fetchone()[0]
    if merges:
        for f, t, title in con.execute("""
                SELECT m.from_id, m.to_id, w.canonical_title FROM work_merge m
                JOIN entities.work w ON w.work_id = m.to_id""").fetchall():
            print(f"  title correction merges {f} -> {t} ({title})")
    # A work must not be merged away AND be a merge target.
    if con.execute("""SELECT count(*) FROM work_merge a JOIN work_merge b
                      ON a.to_id = b.from_id""").fetchone()[0]:
        raise SystemExit("work_merge is chained; resolve the chain before building")
    con.execute("""
        INSERT INTO research.work
        SELECT w.work_id, coalesce(tc.corrected_title, w.canonical_title) AS canonical_title,
               coalesce(g.genre, w.canonical_genre) AS canonical_genre,
               w.appearance_count + coalesce(
                   (SELECT sum(mw.appearance_count) FROM work_merge m
                    JOIN entities.work mw ON mw.work_id = m.from_id
                    WHERE m.to_id = w.work_id), 0) AS appearance_count,
               coalesce((SELECT m.to_id FROM work_merge m
                         WHERE m.from_id = w.excerpt_of_work_id),
                        w.excerpt_of_work_id) AS excerpt_of_work_id,
               w.excerpt_note,
               CASE WHEN g.genre IS NOT NULL THEN 'research_rule'
                    WHEN w.canonical_genre IS NOT NULL THEN 'printed' END AS genre_source,
               g.note AS genre_note
        FROM entities.work w
        LEFT JOIN genre_rule g ON regexp_matches(w.canonical_title, g.pattern)
        LEFT JOIN title_correction tc ON tc.verbatim_title = w.canonical_title
        WHERE w.work_id NOT IN (SELECT from_id FROM work_merge)
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE work_ballet AS
        SELECT pg.work_id, any_value(pg.note) AS note
        FROM parent_genre_ballet pg JOIN research.work w ON w.work_id = pg.work_id GROUP BY 1
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

    has_review_people = con.execute("""SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'entities' AND table_name = 'review_person'""").fetchone()[0] > 0
    if has_review_people:
        # A third people source: dancers the ballet reviews name whom no people
        # list in the corpus carries (pipeline/build_review_persons.py). Every
        # one was checked against the page scan -- seven of the sixteen the
        # worklist proposed turned out to be a graduate, drama bleed, a print
        # typo or a retrospective, so this list is deliberately short.
        #
        # Thin records by necessity: the reviews print a surname and sometimes
        # an ordinal, never a first name or patronymic. display_name is the
        # printed form, so a reader can see exactly what the source said.
        con.execute("""
            INSERT INTO research.person
            SELECT rp.person_id, rp.printed_form, rp.canonical_family_name,
                   NULL, NULL, rp.ordinal_suffix,
                   rp.first_attested_season, rp.last_attested_season,
                   NULL, NULL, NULL, 'review', NULL
            FROM entities.review_person rp
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
            printed_page_number VARCHAR,
            time_of_day VARCHAR,
            receipts_verbatim VARCHAR,
            annotation VARCHAR,
            is_benefit BOOLEAN,
            is_charity BOOLEAN,
            is_free BOOLEAN,
            is_student_performance BOOLEAN,
            is_reduced_price BOOLEAN,
            has_anthem BOOLEAN,
            n_works INTEGER,
            disciplines VARCHAR,
            companies VARCHAR,
            genre_families VARCHAR
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
    event_sql = """
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
            r.printed_page_number,
            r.time_of_day,
            nullif(r.receipts_text, '') AS receipts_verbatim,
            nullif(r.annotation, '') AS annotation,
            regexp_matches(lower(coalesce(r.annotation, '')), '{is_benefit}') AS is_benefit,
            regexp_matches(lower(coalesce(r.annotation, '')), '{is_charity}') AS is_charity,
            regexp_matches(lower(coalesce(r.annotation, '')), '{is_free}') AS is_free,
            regexp_matches(lower(coalesce(r.annotation, '')), '{is_student_performance}') AS is_student_performance,
            regexp_matches(lower(coalesce(r.annotation, '')), '{is_reduced_price}') AS is_reduced_price,
            false AS has_anthem,
            NULL AS n_works,
            NULL AS disciplines,
            NULL AS companies,
            NULL AS genre_families
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
    """
    # the annotation-wording flags (EVENT_FLAG_RES); placeholders, not an
    # f-string, because the SQL above contains regex braces of its own
    for flag, rx in EVENT_FLAG_RES.items():
        event_sql = event_sql.replace("{" + flag + "}", rx.replace("'", "''"))
    con.execute(event_sql)

    # A note printed once that covers a run of days (FREE_PERIOD_NOTES_CSV): the annotation
    # sits on the first cell only, so the wording flag would miss the later performances.
    if FREE_PERIOD_NOTES_CSV.exists():
        for row in csv.DictReader(open(FREE_PERIOD_NOTES_CSV, encoding="utf-8")):
            hit = con.execute("""
                UPDATE research.event SET is_free = TRUE
                WHERE event_status = 'performed' AND city = ? AND date BETWEEN ? AND ?
                  AND theater_id IN (SELECT theater_id FROM research.theater WHERE canonical_name = ?)
                  AND receipts_verbatim IS NULL
                RETURNING event_id""", [row["city"], row["date_from"], row["date_to"], row["theater"]]).fetchall()
            if not hit:
                raise SystemExit(f"free_period_notes.csv: {row['theater']} {row['date_from']} matches no event")

    # Per-performance research genres (PERFORMANCE_GENRE_PATH). Done here,
    # after research.event exists and BEFORE research.performance is created:
    # the base work's appearance_count is lowered with an UPDATE, which DuckDB
    # rejects once a table references research.work.
    con.execute("""CREATE OR REPLACE TEMP TABLE perf_split
                   (performance_id VARCHAR, base_work_id UUID, split_work_id UUID, genre VARCHAR, parent_genre VARCHAR, basis VARCHAR)""")
    if PERFORMANCE_GENRE_PATH.exists():
        split_rows = []
        for row in csv.DictReader(open(PERFORMANCE_GENRE_PATH, encoding="utf-8")):
            hits = con.execute("""
                SELECT eep.performance_id, coalesce(m.to_id, wl.work_id)
                FROM research.event e
                JOIN research.theater t USING (theater_id)
                JOIN analysis.event_entry a ON a.event_id = e.event_id
                JOIN raw.event_entry_performance eep ON eep.event_id = e.event_id
                JOIN entities.work_link wl ON wl.raw_performance_id = eep.performance_id
                LEFT JOIN work_merge m ON m.from_id = wl.work_id
                WHERE e.season = ? AND e.city = ? AND CAST(e.date AS VARCHAR) = ? AND t.canonical_name = ?
                  AND a.time_of_day = ? AND eep.performance_title = ?""",
                [row["season"], row["city"], row["date"], row["theater"], row["time_of_day"],
                 row["verbatim_title"]]).fetchall()
            if len(hits) != 1:
                raise SystemExit(f"research_performance_genre.csv: {row['date']} {row['theater']} "
                                 f"{row['verbatim_title']!r} matches {len(hits)} performances")
            perf_id, base = hits[0]
            genre = row["research_genre"] or None
            parent = row.get("research_parent_genre") or None
            if not genre and not parent:
                raise SystemExit(f"research_performance_genre.csv: {row['date']} {row['theater']} assigns nothing")
            # the key keeps the genre-only form it had before parent genres were added, so those ids are stable
            split = uuid.uuid5(PERFORMANCE_GENRE_NAMESPACE,
                               f"{base}|{genre}" if not parent else f"{base}|{genre or ''}|parent:{parent}")
            split_rows.append((perf_id, base, split, genre, parent, row["basis"]))
        con.executemany("INSERT INTO perf_split VALUES (?, ?, ?, ?, ?, ?)", split_rows)
        con.execute("""
            INSERT INTO research.work
            SELECT s.split_work_id, w.canonical_title, s.genre, count(*), NULL, NULL,
                   CASE WHEN s.genre IS NOT NULL THEN 'research_rule' END,
                   CASE WHEN s.genre IS NOT NULL THEN
                       'genre assigned per performance (' || count(*) || ' of ' || w.appearance_count ||
                       ' printings of this title): pipeline/entity_curation/research_performance_genre.csv' END
            FROM perf_split s JOIN research.work w ON w.work_id = s.base_work_id
            GROUP BY s.split_work_id, w.canonical_title, s.genre, s.parent_genre, w.appearance_count
        """)
        con.execute("""
            INSERT INTO work_ballet
            SELECT DISTINCT s.split_work_id,
                   'ballet assigned per performance: pipeline/entity_curation/research_performance_genre.csv'
            FROM perf_split s WHERE s.parent_genre = 'ballet'
              AND s.split_work_id NOT IN (SELECT work_id FROM work_ballet)
        """)
        con.execute("""
            UPDATE research.work SET appearance_count = appearance_count -
                (SELECT count(*) FROM perf_split s WHERE s.base_work_id = research.work.work_id)
            WHERE work_id IN (SELECT base_work_id FROM perf_split)
        """)
        # A base row whose every printing moved is left with no performance: drop it
        # (unless it is an excerpt parent), so the title is not listed twice.
        con.execute("""
            DELETE FROM research.work
            WHERE work_id IN (SELECT base_work_id FROM perf_split) AND appearance_count = 0
              AND work_id NOT IN (SELECT excerpt_of_work_id FROM research.work WHERE excerpt_of_work_id IS NOT NULL)
        """)
        print(f"  per-performance genres: {len(split_rows)} performances moved to "
              f"{len({r[2] for r in split_rows})} research-rule work row(s)")

    n_reworked = load_performance_work_overrides(con)
    print(f"  performances shown under a work taken from another part of the yearbook: {n_reworked}")
    n_supplied = load_supplied_performances(con)
    build_art_forms(con)

    con.execute("""
        CREATE TABLE research.performance (
            performance_id VARCHAR PRIMARY KEY,
            event_id VARCHAR REFERENCES research.event(event_id),
            work_id UUID REFERENCES research.work(work_id),
            performance_order VARCHAR,
            verbatim_title VARCHAR,
            verbatim_genre VARCHAR,
            discipline VARCHAR,
            discipline_basis VARCHAR,
            company VARCHAR,
            is_ceremonial BOOLEAN,
            includes_dance BOOLEAN,
            includes_dance_basis VARCHAR,
            performance_source VARCHAR,
            performance_source_note VARCHAR,
            genre_family VARCHAR,
            genre_family_basis VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO research.performance
        SELECT
            eep.performance_id,
            eep.event_id,
            coalesce(pr.target_work_id, ps.split_work_id, m.to_id, wl.work_id) AS work_id,
            eep.performance_order,
            eep.performance_title AS verbatim_title,
            eep.genre AS verbatim_genre,
            pa.discipline, pa.discipline_basis, pa.company, coalesce(pa.is_ceremonial, false),
            -- TRUE or NULL, never FALSE: blank means "not known" (RG, 2026-10-12: "the options are yes or blank")
            CASE WHEN pa.includes_dance THEN true END, pa.includes_dance_basis,
            CASE WHEN pr.performance_id IS NOT NULL THEN 'repertoire; work from ' || pr.source ELSE 'repertoire' END,
            pr.basis,
            pa.item_kind, pa.item_kind_basis
        FROM raw.event_entry_performance eep
        JOIN entities.work_link wl ON wl.raw_performance_id = eep.performance_id
        LEFT JOIN work_merge m ON m.from_id = wl.work_id
        LEFT JOIN perf_split ps ON ps.performance_id = eep.performance_id
        LEFT JOIN perf_art pa ON pa.performance_id = eep.performance_id
        LEFT JOIN perf_rework pr ON pr.performance_id = eep.performance_id
        WHERE eep.event_id NOT IN (SELECT e.event_id FROM analysis.event_entry e
                                   JOIN excluded_page x USING (page_id))
    """)
    # Performances supplied from another part of the yearbook (SUPPLIED_PERFORMANCES_CSV):
    # no verbatim title or genre, ordered after the cell's own lines.
    con.execute("""
        INSERT INTO research.performance
        SELECT sp.performance_id, sp.event_id, sp.work_id, NULL, NULL, NULL,
               pa.discipline, pa.discipline_basis, pa.company, false, NULL, NULL,
               'supplied: ' || sp.source, sp.basis,
               pa.item_kind, pa.item_kind_basis
        FROM supplied_perf sp LEFT JOIN perf_art pa ON pa.performance_id = sp.performance_id
    """)
    print(f"  performances supplied from other parts of the yearbook: {n_supplied}")

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

    n_tenure = build_person_tenure_notes(con)
    print(f"  person tenure discrepancies noted: {n_tenure}")

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


#: People whose printed leaving is contradicted by the later lists (RG, 2026-10-19, M9 scan checks,
#: docs/eval/person_audit_2026-10-19/): the research layer reads their service as CONTINUING to the
#: last listing -- research.person.last_attested_season already does -- and keeps the printed
#: statement here, with the discrepancy and what would corroborate it. Raw keeps the printed note
#: and its parsed end date untouched. `service_periods` is the research reading in seasons, ';' between
#: periods (Егорова 1-я: two). The build fails unless the person exists, prints that leaving date in
#: that list, and is listed in every season the periods name.
PERSON_TENURE_DISCREPANCIES_CSV = Path(__file__).parent / "research_corrections" / "person_tenure_discrepancies.csv"


def build_person_tenure_notes(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("""
        CREATE TABLE research.person_tenure_note (
            person_id UUID REFERENCES research.person(person_id),
            list VARCHAR,
            city VARCHAR,
            printed_leaving VARCHAR,
            printed_leaving_date DATE,
            printed_in_seasons VARCHAR,
            research_reading VARCHAR,
            service_periods VARCHAR,
            discrepancy VARCHAR,
            corroboration_found VARCHAR,
            corroboration_wanted VARCHAR,
            decided VARCHAR
        )
    """)
    if not PERSON_TENURE_DISCREPANCIES_CSV.exists():
        return 0
    seasons = [r[0] for r in con.execute(
        "SELECT DISTINCT season FROM raw.source_pages WHERE season IS NOT NULL ORDER BY 1").fetchall()]
    n = 0
    for row in csv.DictReader(open(PERSON_TENURE_DISCREPANCIES_CSV, encoding="utf-8")):
        pid, lst, city = row["person_id"], row["list"], row["city"]
        if not con.execute("SELECT count(*) FROM research.person WHERE person_id = ?", [pid]).fetchone()[0]:
            raise SystemExit(f"person_tenure_discrepancies.csv: {row['display_name']} {pid} is not in research.person")
        printed = con.execute("""
            SELECT count(*) FROM raw.person_entry_service s JOIN raw.person_entry pe USING (entry_id)
            JOIN raw.source_pages sp ON sp.page_id = pe.page_id JOIN entities.person_link pl USING (entry_id)
            WHERE pl.person_id = ? AND sp.entity_type = ? AND coalesce(sp.city, '') = ? AND CAST(s.end_date_undate AS VARCHAR) = ?""",
            [pid, lst, city, row["printed_leaving_date"]]).fetchone()[0]
        if not printed:
            raise SystemExit(f"person_tenure_discrepancies.csv: {row['display_name']} has no printed leaving "
                             f"{row['printed_leaving_date']} in {city}/{lst}")
        listed = {r[0] for r in con.execute(
            "SELECT DISTINCT season FROM research.person_appearance WHERE person_id = ? AND entity_type = ? AND coalesce(city, '') = ?",
            [pid, lst, city]).fetchall()}
        for period in row["service_periods"].split(";"):
            a, b = [x.strip() for x in period.split("..")]
            missing = [s for s in seasons[seasons.index(a):seasons.index(b) + 1] if s not in listed]
            if missing:
                raise SystemExit(f"person_tenure_discrepancies.csv: {row['display_name']} period {a}..{b} "
                                 f"includes unlisted season(s) {missing}")
        con.execute("INSERT INTO research.person_tenure_note VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [pid, lst, city, row["printed_leaving"], row["printed_leaving_date"], row["printed_in_seasons"],
                     row["research_reading"], row["service_periods"], row["discrepancy"],
                     row["corroboration_found"], row["corroboration_wanted"], row["decided"]])
        n += 1
    return n


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
