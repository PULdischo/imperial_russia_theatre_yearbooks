"""Read creator and craft credits out of the ballet Season Reviews.

`соч. Ж. Перро`, `музыка Ц. Пуни`, `поставленъ балетмейстеромъ … Горскимъ`,
`Либретто составлено … Горскимъ`, `Сюжетъ заимствованъ изъ сказки Э. Гофмана`,
`Праздникъ огня, декорація А. Кваппа`, `Машины—К. Ѳ. Вальца`,
`Костюмы по рисункамъ … Е. Пономарева; женскіе— Е. Офицеровой`.

One row per person per role per printed credit, in `research.review_credit`,
alongside `review_assertion` (cast) and `review_solo` (instrument solos).
RG, 2026-10-26: one table for music, authorship, libretto, source, staging and
design, at the level of the scene where the print names one; "I want to give
craftspeople and artisans the same attention as creators like set designers,
choreographers, and costume designers" -- so costume making, machinery, props
and the other trades are roles of their own, not notes.

How a credit is read (rules, no model):

1. **Cue.** A credit word (`музыка`, `соч.`, `поставленъ`, `либретто`,
   `сюжетъ`, `декорація`, `костюмы`, `машины`, `аксессуарныя вещи` …) gives
   the role. Cues joined by `и` or a couple of words share their names
   (`сочиненіе и постановка балетмейстера М. М. Фокина` -> author + staging).
2. **Names.** The names after the cue, up to the end of the clause, a quotation,
   a bracket, a dash after a name (what follows a dash is a performer), or the
   next cue. A name is a person mention the matcher already found, or a
   capitalised surname it did not know (kept as printed, person NULL). A given
   name before a surname (`Іосифа Байера`) belongs to that surname.
3. **Scenery lists.** After a scenery cue, `«Облака» (2-я картина 1-го
   дѣйствія)—К. Ѳ. Вальцемъ` and `г. Шангина—«Оазисъ въ пустынѣ» (1-я картина
   пролога)` are scene-by-scene scenery credits.
4. **Work.** A caption names its work after the credit, in brackets
   (`декорація К. Ѳ. Вальца («Даита», балетъ …)`), so a caption takes the work
   after the cue. Elsewhere: a work named inside the cue (`балета «Шехерезада»
   Л. С. Бакста`), else just after the names (`балета Сенъ-Леона «Конекъ
   Горбунокъ»`), else earlier in the same clause, else works named after the
   credit in the same clause (`постановки г. Фокина: «Египетскія ночи»,
   «Шопеніана» и «Эвника»` -> three rows), else the nearest work earlier in the
   block, else the one work the page names, else the last work of the previous
   page (a list that runs over a page). Only works the matcher identified
   govern; an unidentified title never does.
5. **Person.** In this order: the person the productions lists credit on this
   work with that surname (preferring the same role; not for design, which the
   lists never credit); the same with a near-spelling (`Нюйтера`, `Гершелемъ`
   for Гертель), flagged `list-credit-spelling`; else a candidate the lists
   credit in that role on any work; else, for design and craft roles, the one
   candidate on the staff of the right department (decoration, wardrobe,
   machinists, props workshop: `research.person_appearance.heading_path`); else
   the matcher's own link; else unresolved, with the candidates kept.

Not credits, and skipped: the plate's own `Рисунокъ художника X` (the
Yearbook's illustrator), conductors (`дирижировалъ г. Дриго`), cast and
performers.

`context_flag` marks credits a reader must weigh before attaching them to the
season's production: `historical?` (the sentence names a year before the
season: an 1855 cast, a first staging in 1835) and `foreign?` (abroad, the
Дягилевъ company). They are hints, never filters.

Usage:
    uv run python pipeline/build_review_credits.py \
        --db outputs/full_run/imperial_theaters.duckdb \
        --out outputs/reviews/mentions/review_credit.csv
"""
from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from match_review_mentions import key_of, reflow, surname_forms  # noqa: E402
from build_review_assertions import (DATE_RE, first_page_skip, mask_periods,  # noqa: E402
                                     month_of, resolve_date, season_years)

UC = "А-ЯЀ-ЏІѲѴ"
LC = "а-яѣіѳѵъьё"
DOT = "․"     # mask_periods' placeholder for a period that ends no sentence

# ------------------------------------------------------------------ cues
# (pattern, role). Case-insensitive, on the reflowed text; overlapping matches
# keep the earliest and longest.
QUOTED = r"[«„][^»“]{1,80}[»“]"
CUES = [
    (r"симфоническ\w+\s+поэм\w*", "music"),
    (r"музык(?:а|и|у|ой|ою|ѣ)(?![а-яѣ])|муз\.", "music"),
    (r"композитор\w*", "music"),
    (r"оркестров\w*\.?|орк\.|инструментов\w*|инструментир\w*", "instrumentation"),
    (r"соч\.|сочин\.|сочинені[еяю]\w*|сочинен(?:ъ|а|ы|о|ный|ная|ные|наго|ныя|нымъ)(?![а-яѣ])|сочинил\w*",
     "author"),
    (r"либретто|программ[аыу](?![а-яѣ])", "libretto"),
    (r"сюж\.|сюжет\w*|заимствован\w*|эпиграф\w*|по\s+роману|по\s+повѣсти|по\s+сказк\w*|"
     r"(?<![а-яѣ\-])сказк[аиуе]\w*|(?<![а-яѣ\-])поэм[ыаеу]\w*|(?<![а-яѣ\-])роман[аъ]\w*|"
     r"(?<![а-яѣ\-])повѣст[иь]\w*|(?<![а-яѣ\-])легенд[ыа]\w*", "source"),
    (r"вновь\s+поставлен\w*|поставлен\w*\s+вновь|возобновлен\w*", "staging-revival"),
    (r"поставлен\w*|постановк\w*|поставил\w*", "staging"),
    (r"(?<![а-яѣ])танц(?:ы|евъ|овъ)(?![а-яѣ])", "choreography"),
    (r"декораці\w*|декоратор\w*|кисти|панорам\w*|(?<![а-яѣ])эскиз\w*", "scenery"),
    (r"костюм\w*", "costumes"),
    (r"(?<![а-яѣ])(?:женскі[ея]|мужскі[ея])(?![а-яѣ])", "costume-split"),
    (r"костюмерш\w*|костюмер(?:ъ|а|омъ|ы|ами)(?![а-яѣ])", "costume_making"),
    (r"головн\w+\s+убор\w*", "headwear"),
    (r"машин(?:ы|ъ|а|ами)(?![а-яѣ])|машинист\w*|машинн\w+\s+приспособлен\w*", "machinery"),
    (r"аксессуар\w*|бутафор\w*", "props"),
    (r"освѣщені\w*", "lighting"),
    (r"(?<![а-яѣ])парик\w*", "wigs"),
    (r"(?<![а-яѣ])обув\w*", "footwear"),
    (r"(?<![а-яѣ])раб\.|(?<![а-яѣ])работы(?![а-яѣ])|(?<![а-яѣ])написан[аыо]?(?![а-яѣ])", "work-of"),
    (r"(?<![а-яѣ])балет(?:ъ|а)\s+" + QUOTED, "ballet-by"),
    (r"(?<![а-яѣ])балетъ-[а-яѣ]+(?-i:(?=\s+(?:(?:князя|графа|барона|г\.|гг\.)\s+)?(?:[" + UC + r"]\.\s*)*[" + UC + r"][" + LC + r"]{2,}))", "ballet-by"),
    (r"(?<![а-яѣ])бал\.|(?<![а-яѣ])балет(?:ъ|а)(?-i:(?=\s+(?:(?:князя|графа|барона|г\.|гг\.)\s+)?(?:[" + UC + r"]\.\s*)*[" + UC + r"][" + LC + r"]{2,}))",
     "ballet-by"),
]
CUE_RE = [(re.compile(p, re.I), r) for p, r in CUES]
STOP_RE = re.compile(
    r"дирижир\w*|дирижер\w*|дирижёр\w*|капельмейстер\w*|(?<![а-яѣ])исп\.|исполн(?!ены\s+по\s)\w*|"
    r"(?<![а-яѣ])рол(?:ь|и|ью|ей|ямъ)(?![а-яѣ])|парті\w*|танцовал\w*|участв\w*|дебютир\w*|"
    r"бенефис\w*|ученик\w*|ученица\w*|воспитанни\w*|участі\w*|(?<![а-яѣ])игр[уаыо]\w*|"
    r"рисунокъ\s+художника|рисунокъ\s+худ\.|(?<![а-яѣ])въ\s+\w+\s+костюмахъ", re.I)
PLATE_ARTIST = re.compile(r"рисунокъ\s+(?:художника|худ\.)", re.I)
# abbreviations whose period ends no sentence (`соч. М. Петипа`, `раб. О. Аллегри`)
ABBREV_PERIOD = re.compile(
    r"(?<![а-яѣ])(соч|сочин|муз|бал|орк|оркестров|сюж|худ|раб|исп|ком|фант|дѣйств|карт|д|ст|"
    r"проф|акад|т|см|изд|кн|гр|бар|испр)\.(?=\s*[" + UC + r"0-9«„(])", re.I)

DESIGN = {"scenery", "costume_design", "costumes", "costume_making", "machinery",
          "props", "lighting", "wigs", "footwear", "headwear"}
DEPARTMENT = {
    "scenery": r"декораці|декоратор",
    "costume_design": r"гардероб|костюм|художник",
    "costumes": r"гардероб|костюм|художник",
    "costume_making": r"гардероб|костюм|портн|швея",
    "machinery": r"машинист|машин",
    "props": r"бутафор|скульпт|аксессуар",
    "lighting": r"освѣщ|электр|газ",
    "wigs": r"парик",
    "footwear": r"обув|сапож|башмач",
    "headwear": r"гардероб|модист|убор",
}
LIST_ROLE = {
    "music": {"music"}, "instrumentation": {"instrumentation", "music"},
    "author": {"author", "staging", "libretto"}, "ballet-by": {"author", "music"},
    "libretto": {"libretto", "author"}, "source": {"source"},
    "staging": {"staging", "author"}, "staging-revival": {"staging", "author"},
    "choreography": {"author", "staging"},
}

CAP_STOP = {key_of(w) for w in """
Императорскихъ Императорскаго Императорскій Императорской Императорскую Московскихъ Московскаго
Московской Московскую Московская Петербургскихъ Петербургскаго Петербургской С.-Петербургскихъ
Его Ея Величества Величеству Большомъ Большого Большой Маріинскомъ Маріинскаго Маріинскій
Михайловскомъ Александринскомъ Эрмитажномъ Россіи Парижѣ Москвѣ Петербургѣ Новая Новыя Новые
Новыхъ Декораціи Декорація Костюмы Музыка Машины Балетъ Балета Сцены Сцена Танцы Постановка
Сюжетъ Либретто Программа Аксессуарныя Бутафорскія Картина Дѣйствіе Актъ Прологъ Апоѳеозъ
Затѣмъ Роль Роли Нынѣ Этотъ Эта Эти Онъ Она Для Въ Изъ На По При Съ Со Къ Но И А Это Ихъ Всѣ
Первая Второй Третій Перваго Втораго Императоръ Государь Государыня Великій Великая Князь
Княгиня Театръ Театра Театровъ Театрахъ Училища Министерства Дирекціи Конторы Главные Главный
Художникъ Художника Академикъ Академика Солистъ Солиста Балетмейстеръ Балетмейстера Г Гг
Variation Pas Grand Valse Adagio Coda Polonaise Mazurka Danse
""".split()}

NAME_RE = re.compile(
    r"(?P<init>(?:[" + UC + r"][" + LC + r"]?" + DOT + r"\s*){0,3})"
    r"(?P<sur>[" + UC + r"][" + LC + r"'’]+(?:-?[" + UC + r"][" + LC + r"]+|-[" + LC + r"]+)?"
    r"(?:\s+[" + UC + r"][" + LC + r"'’]+(?:-[" + UC + r"]?[" + LC + r"]+)?)?"
    r"(?:\s+\d+-[йяе])?)")
ADJ_NOT_NAME = re.compile(r"(?:ск|цк|н)(?:ихъ|ую|ой|ое|ія|ыя|ыхъ)$")
ADJ_FORM = re.compile(r"(?:ск|цк)(?:аго|ая|ій|ое|ой|ую|ихъ)$")
PLACE_NOUN = re.compile(r"\s+(?:проспект|театр|сцен|трупп|училищ|улиц|площад|двор|сад|мост|полк|корпус|собор|монастыр)", re.I)
ANON = re.compile(r"⁂|\*\s*\*\s*\*|[" + UC + r"]\*\s*\*|\*\*\*")
CLAUSE_END = re.compile(r"[;\n]|\.(?=\s+[" + UC + r"0-9«„])|\.\s*$")
YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d)(?!\d)")
FOREIGN = re.compile(r"за\s+границ\w*|въ\s+Париж\w*|въ\s+Лондон\w*|въ\s+Милан\w*|въ\s+Вѣн\w*|"
                     r"въ\s+Берлин\w*|Дягилев\w*|заграниц\w*", re.I)
PART_WORDS = re.compile(r"картин|дѣйств|актъ|акт\.|прологъ|пролог|апоѳеоз|сцена|«|„", re.I)
# words that do not count towards the cue-to-name distance: titles and the
# act/scene count of a title line (`въ 4-хъ дѣйствіяхъ и 7-ми картинахъ`)
GAP_FREE = re.compile(r"хъ|ми|ти|мъ|съ|въ|изъ|дѣйстві\w*|картин\w*|акт\w*|прологом\w*|эпилогом\w*|"
                      r"апоѳеоз\w*|балетмейстер\w*|художник\w*|академик\w*|скульптор\w*|главн\w*|"
                      r"солист\w*|штатн\w*|декоратор\w*|профессор\w*|князя|графа|барона|мастер\w*")
NAME_JOIN = re.compile(r"[\s,]*(?:и|гг?" + DOT + r"|г-жи|г-жа|г-нъ|г-ну|г-жей)?[\s,]*")


def mask(body: str) -> str:
    return ABBREV_PERIOD.sub(lambda m: m.group(1) + DOT, mask_periods(body))


def clause_bounds(masked: str) -> list[tuple[int, int]]:
    out, a = [], 0
    for m in CLAUSE_END.finditer(masked):
        out.append((a, m.end()))
        a = m.end()
    if a < len(masked):
        out.append((a, len(masked)))
    return out


def find_cues(body: str) -> list[tuple[int, int, str]]:
    hits = []
    for rx, role in CUE_RE:
        for m in rx.finditer(body):
            # IGNORECASE would read `Парикова` as wigs: a capitalised cue counts
            # only where a sentence, a bracket or a dash starts it
            if m.group(0)[0].isupper() and not re.search(r"(?:^|[.;:(—–]|" + DOT + r")\s*$", body[:m.start()]):
                continue
            hits.append((m.start(), m.end(), role))
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    out = []
    for h in hits:
        if out and h[0] < out[-1][1]:
            continue
        out.append(h)
    return out


def initials_compatible(printed: str, display: str) -> bool | None:
    printed = printed.replace("Ѳ", "Ф")
    if not printed:
        return None
    after = display.split(",", 1)[1] if "," in display else ""
    mine = "".join(w[0] for w in re.findall(r"[" + UC + r"][" + LC + r"]*", after)).replace("Ѳ", "Ф")
    if not mine:
        return None
    return mine.startswith(printed) or printed.startswith(mine)


def near(a: str, b: str) -> bool:
    """One or two letters apart (`нюйтер`/`нюитер`, `гершел`/`гертел`)."""
    if abs(len(a) - len(b)) > 1 or min(len(a), len(b)) < 4 or a[:2] != b[:2]:
        return False
    limit = 1 if min(len(a), len(b)) < 6 else 2
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] <= limit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--genre", default="Ballet")
    a = ap.parse_args()
    con = duckdb.connect(str(a.db))

    pages = {r[0]: {"season": r[1], "city": r[2], "genre": r[3], "folio": r[4]} for r in con.execute(
        "SELECT page_id, season, city, genre, printed_folio FROM raw.review_page").fetchall()}
    blocks = con.execute("""
        SELECT b.block_id, b.page_id, b.block_index, b.block_type, b.text, b.caption_text
        FROM raw.review_block b JOIN raw.review_page p USING (page_id)
        WHERE p.genre = ? ORDER BY b.page_id, b.block_index""", [a.genre]).fetchall()

    first_page: dict[tuple, str] = {}
    by_page: dict[str, list[tuple]] = collections.defaultdict(list)
    for row in blocks:
        pg = pages[row[1]]
        key = (pg["season"], pg["city"])
        if key not in first_page or row[1] < first_page[key]:
            first_page[key] = row[1]
        by_page[row[1]].append(row)
    skip_before = {pid: first_page_skip(by_page[pid]) for pid in set(first_page.values())}
    page_order = sorted(by_page)
    prev_page = {p: q for q, p in zip(page_order, page_order[1:])
                 if pages[p]["season"] == pages[q]["season"] and pages[p]["city"] == pages[q]["city"]}

    mentions: dict[str, list[tuple]] = collections.defaultdict(list)
    for r in con.execute("""
        SELECT block_id, mention_id, mention_type, char_start, char_end, surface, entity_id,
               candidates_n, candidate_ids, link_method
        FROM entities.review_mention WHERE mention_type IN ('person', 'work')
        ORDER BY block_id, char_start""").fetchall():
        mentions[r[0]].append(r)

    person = {str(r[0]): {"display": r[1], "family": r[2], "first": r[3]} for r in con.execute(
        "SELECT person_id, display_name, canonical_family_name, canonical_first_name FROM research.person").fetchall()}
    by_form: dict[str, set[str]] = collections.defaultdict(set)
    fam_key: dict[str, str] = {}
    for pid, p in person.items():
        fam = re.sub(r"\s*\(.*?\)\s*", "", p["family"] or "").strip()
        fam_key[pid] = key_of(fam)
        for f in surname_forms(fam) if fam else ():
            by_form[f].add(pid)
            by_form[f.replace("-", "")].add(pid)
    non_governing = {str(w) for (w,) in con.execute("""
        SELECT work_id FROM research.work
        WHERE coalesce(work_source, 'repertoire') = 'review'
          AND coalesce(canonical_genre, '') NOT ILIKE '%бал%'""").fetchall()}
    list_credit: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    list_roles_of: dict[str, set[str]] = collections.defaultdict(set)
    for wid, pid, role in con.execute("""
        SELECT pw.work_id, pc.person_id, pc.role_category
        FROM research.production_credit pc
        JOIN research.production_work pw USING (production_id)
        WHERE pc.person_id IS NOT NULL""").fetchall():
        list_credit[str(wid)].append((str(pid), role))
        list_roles_of[str(pid)].add(role)
    dept: dict[str, str] = collections.defaultdict(str)
    for pid, hp in con.execute("""
        SELECT person_id, string_agg(DISTINCT CAST(heading_path AS VARCHAR), ' || ')
        FROM research.person_appearance GROUP BY 1""").fetchall():
        dept[str(pid)] = (hp or "").lower()

    page_works: dict[str, list[tuple[int, int, str, str]]] = collections.defaultdict(list)
    for pid, bidx, cs, surface, eid in con.execute("""
        SELECT m.page_id, b.block_index, m.char_start, m.surface, m.entity_id
        FROM entities.review_mention m JOIN raw.review_block b ON b.block_id = m.block_id
        WHERE m.mention_type = 'work' AND m.entity_id IS NOT NULL
        ORDER BY m.page_id, b.block_index, m.char_start""").fetchall():
        if str(eid) not in non_governing:
            page_works[pid].append((bidx, cs, surface, str(eid)))

    out: list[dict] = []
    stats = collections.Counter()

    def resolve(name: str, initials: str, mention, role: str, work_id: str,
                city: str = "") -> tuple[str, int, str, str]:
        """(person_id, candidates_n, candidate_ids, link_method)."""
        last = name.split()[-1]
        keys = {key_of(name), key_of(last), key_of(name.replace(" ", "-")), key_of(name).replace("-", "").replace(" ", "")}
        if initials.endswith("С"):
            keys.add("сен-" + key_of(last))       # `балетъ С. Леона`: Сенъ-Леонъ
        cands: set[str] = set()
        for k in keys:
            cands |= by_form.get(k, set())
        if mention and mention[8]:
            cands |= set(mention[8].split("|"))
        if mention and mention[6]:
            cands.add(str(mention[6]))
        cand_ids = "|".join(sorted(cands))
        want = LIST_ROLE.get(role, set())

        def by_initials(ids):
            if not initials:
                return list(ids)
            kept = [p for p in ids if initials_compatible(initials, person[p]["display"]) is not False]
            return kept or list(ids)
        # 1. the productions lists credit someone of that surname on this work
        if work_id and role not in DESIGN:
            here = [(pid, r) for pid, r in list_credit.get(work_id, []) if pid in cands]
            how = "list-credit"
            if not here:
                # a printed spelling the forms do not reach: `Нюйтера`, `Гершелемъ`
                k = key_of(name.split()[-1])
                here = [(pid, r) for pid, r in list_credit.get(work_id, [])
                        if any(near(k, f) for f in surname_forms(fam_key[pid]) or {fam_key[pid]})]
                how = "list-credit-spelling"
            if here:
                same = by_initials(sorted({pid for pid, r in here if r in want}))
                pick = same if len(same) == 1 else by_initials(sorted({pid for pid, _ in here}))
                if len(pick) == 1:
                    return pick[0], len(cands), cand_ids, how
        pool = by_initials(cands)
        # a printed first name (`Маріусомъ Петипа`) chooses among the family
        toks = name.split()
        if len(toks) >= 2:
            g = key_of(toks[0])[:4]
            named = [p for p in pool if key_of(person.get(p, {}).get("first") or "")[:4] == g]
            if len(named) == 1:
                return named[0], len(cands), cand_ids, "first-name"
        # 2. the lists credit one of them in this role on another work
        if want:
            other = sorted({p for p in pool if list_roles_of.get(p, set()) & want})
            if len(other) == 1:
                return other[0], len(cands), cand_ids, "list-credit-other-work"
        # 3. design and craft: the one candidate on the staff of that department
        if role in DESIGN:
            rx = re.compile(DEPARTMENT[role])
            # the review's own city: a Petersburg wigmaker is not `парики— г. Аѳанасьева` in Moscow
            here_city = "москва" if city == "Moscow" else "петербург"
            staff = sorted({p for p in pool if any(rx.search(seg) and here_city in seg
                                                   for seg in dept.get(p, "").split(" || "))})
            if len(staff) == 1:
                return staff[0], len(cands), cand_ids, "department"
            # 1903-04 Moscow «Баядерка» had «декораціи работы художниковъ … С.-Петербургскихъ
            # театровъ»: staff of the other city do work across, so they are kept, flagged
            staff = sorted({p for p in pool if rx.search(dept.get(p, ""))})
            if len(staff) == 1:
                return staff[0], len(cands), cand_ids, "department-other-city"
        # 4. the matcher's own link
        if mention and mention[6] and str(mention[6]) in pool:
            return str(mention[6]), len(cands), cand_ids, "mention-link"
        if len(pool) == 1 and initials:
            return pool[0], len(cands), cand_ids, "initials"
        return "", len(cands), cand_ids, ("unresolved" if cands else "printed-only")

    for block_id, page_id, bidx, btype, text, caption in blocks:
        if bidx < skip_before.get(page_id, 0):
            continue
        pg = pages[page_id]
        body = reflow(caption or text or "")
        if not body:
            continue
        masked = mask(body)
        is_fig = btype == "figure"
        ms = mentions.get(block_id, [])
        pms = [m for m in ms if m[2] == "person"]
        # only works the matcher identified govern a credit
        wms = [m for m in ms if m[2] == "work" and m[6] and str(m[6]) not in non_governing]
        clauses = clause_bounds(masked)
        cues = find_cues(body)
        stops = [m.start() for m in STOP_RE.finditer(body)]
        quotes = [(m.start(), m.end()) for m in re.finditer(r"[«„\"][^»“\"]{0,200}[»“\"]", body)]
        dates = [(m.start(), int(m.group(1)), month_of(m.group(2))) for m in DATE_RE.finditer(body)]
        if is_fig and PLATE_ARTIST.search(body):
            stats["plate illustrator lines skipped"] += 1
        done_names: set[int] = set()

        def clause_of(at: int) -> tuple[int, int]:
            for c0, c1 in clauses:
                if c0 <= at < c1:
                    return c0, c1
            return 0, len(body)

        def in_quote(at: int) -> bool:
            return any(q0 <= at < q1 for q0, q1 in quotes)

        def names_in(lo: int, hi: int) -> list[tuple[int, int, str, str, object]]:
            """Name groups in body[lo:hi]; a list ends at plain lowercase prose."""
            found = []
            joined_by_i = False
            for nm in NAME_RE.finditer(masked, lo, hi):
                sa, sz = nm.start("sur"), nm.end("sur")
                sur = body[sa:sz]
                toks = sur.split()
                # a given name before the surname: keep both, read the surname
                if len(toks) >= 2 and not re.fullmatch(r"\d+-[йяе]", toks[-1]) and key_of(toks[0]) in CAP_STOP:
                    sa += len(toks[0]) + 1
                    sur = body[sa:sz]
                    toks = sur.split()
                if key_of(toks[0]) in CAP_STOP or in_quote(sa):
                    continue
                if any(rx.fullmatch(toks[0]) for rx, _ in CUE_RE):
                    continue
                nxt = body[sz:sz + 12]
                if ADJ_NOT_NAME.search(toks[-1]) and re.match(r"\s+[" + LC + r"]", nxt) \
                        and not re.match(r"\s+и\s", nxt):
                    continue
                if re.match(r"[ЪЬ]", sur):
                    continue
                if ADJ_FORM.search(toks[-1]) and PLACE_NOUN.match(nxt):
                    continue                     # `Невскаго проспекта`
                init = re.sub(r"[^" + UC + r"]", "", nm.group("init"))
                mm = next((m for m in pms if sa <= m[3] < sz), None)
                if mm:
                    surf = body[sa:max(sz, mm[4])] if len(toks) > 1 else mm[5]
                else:
                    surf = re.sub(r"\s+\d+-[йяе]$", "", sur)
                if found:
                    between = masked[found[-1][1]:nm.start()]
                    if not NAME_JOIN.fullmatch(between):
                        break
                    # `бал. М. Петипа и Л. Иванова, Аполлонъ и Флора`: a list
                    # closes with its `и`; a comma after that starts something else
                    if "," in between and joined_by_i:
                        break
                    if re.search(r"(?<![" + LC + r"])и(?![" + LC + r"])", between):
                        joined_by_i = True
                found.append((sa, sz, surf, init, mm))
            return found

        def governing(start: int, end_cue: int, names_end: int, c0: int, c1: int):
            if is_fig:
                after = [w for w in wms if w[3] >= start]
                before = [w for w in wms if w[3] < start]
                if after:
                    return [after[0]], "caption-after"
                return ([before[-1]], "block") if before else ([], "")
            inside = [w for w in wms if start <= w[3] < end_cue]
            if inside:
                return inside[:1], "cue"
            in_cl_after = [w for w in wms if names_end <= w[3] < c1]
            if in_cl_after and re.match(r"\s*:", body[names_end:names_end + 3]):
                return in_cl_after, "clause-after"
            right_after = [w for w in wms if names_end <= w[3] <= names_end + 6]
            if right_after:
                return right_after[:1], "after-names"
            in_cl_before = [w for w in wms if c0 <= w[3] < start]
            if in_cl_before:
                return [in_cl_before[-1]], "clause"
            in_cl_after = [w for w in wms if names_end <= w[3] < c1]
            if in_cl_after and re.match(r"\s*:", body[names_end:names_end + 3]):
                return in_cl_after, "clause-after"
            near_after = [w for w in in_cl_after if w[3] - names_end <= 120]
            if near_after:
                return near_after[:1], "clause-after"
            before = [w for w in wms if w[3] < start]
            if before:
                return [before[-1]], "block"
            if in_cl_after:
                return in_cl_after, "clause-after"
            return [], ""

        def page_fallback():
            pw = page_works.get(page_id, [])
            if len({w[3] for w in pw}) == 1:
                return [(pw[0][2], pw[0][3])], "page"
            earlier = [w for w in pw if w[0] < bidx]
            if earlier:
                return [(earlier[-1][2], earlier[-1][3])], "page-earlier"
            q = prev_page.get(page_id)
            if q and page_works.get(q) and not pw:
                w = page_works[q][-1]
                return [(w[2], w[3])], "previous-page"
            return [("", "")], ""

        def emit(names, anon, rs, start, end_cue, limit, c0, c1, part, how_extra="", plural=False):
            names_end = names[-1][1] if names else end_cue
            gov, wsrc = governing(start, end_cue, names_end, c0, c1)
            work_rows = [(w[5], str(w[6])) for w in gov]
            if plural and wsrc in ("block", "clause", "page", ""):
                work_rows, wsrc = [("", "")], "several works"
            elif not work_rows:
                work_rows, wsrc = page_fallback()
            prior = [d for d in dates if d[0] <= start and d[2]]
            date = resolve_date(prior[-1][1], prior[-1][2], pg["season"]) if prior else None
            sent = body[c0:c1]
            yy = season_years(pg["season"])
            flags = []
            if yy and any(int(y) < yy[0] for y in YEAR.findall(sent)):
                flags.append("historical?")
            if FOREIGN.search(sent):
                flags.append("foreign?")
            phrase = body[start:limit].strip(" ,;")
            base = {"page_id": page_id, "block_id": block_id, "block_type": btype,
                    "season": pg["season"], "city": pg["city"], "printed_folio": pg["folio"] or "",
                    "date_undate": date or "", "work_source": wsrc, "part_surface": part,
                    "role_text": body[start:end_cue], "printed_phrase": phrase,
                    "context_flag": " ".join(flags)}
            for role in sorted(rs):
                for wsurf, wid in work_rows:
                    for n in names:
                        pid, cn, cids, how = resolve(n[2], n[3], n[4], role, wid, pg["city"])
                        out.append({**base, "char_start": n[0], "work_surface": wsurf, "work_id": wid,
                                    "role_category": role, "name_surface": n[2], "initials": n[3],
                                    "person_id": pid, "person_candidates_n": cn,
                                    "person_candidate_ids": cids if (not pid or cn > 1) else "",
                                    "link_method": how + how_extra, "mention_id": n[4][1] if n[4] else "",
                                    "is_anonymous": False})
                    for an in anon:
                        out.append({**base, "char_start": an[0], "work_surface": wsurf, "work_id": wid,
                                    "role_category": role, "name_surface": an[1], "initials": "",
                                    "person_id": "", "person_candidates_n": 0, "person_candidate_ids": "",
                                    "link_method": "anonymous", "mention_id": "", "is_anonymous": True})
            for n in names:
                done_names.add(n[0])

        # merge cues joined only by `и`, commas or two short words into one phrase
        phrases: list[list[tuple[int, int, str]]] = []
        for cu in cues:
            if in_quote(cu[0]):
                continue
            # `Костюмъ г. Іогансона въ этой роли`: the costume a dancer wore
            if cu[2] == "costumes" and re.fullmatch(r"костюм(?:ъ|а|ѣ|омъ)", body[cu[0]:cu[1]], re.I) \
                    and not re.match(r"\s+(?:работы|по\s+рисунк|по\s+эскиз)", body[cu[1]:cu[1] + 16], re.I):
                continue
            # dancers `въ женскихъ костюмахъ`
            if cu[2] == "costumes" and re.search(r"(?<![а-яѣ])въ\s+[" + LC + r"]+\s+$", body[:cu[0]]):
                continue
            if phrases:
                prev = phrases[-1][-1]
                gap = body[prev[1]:cu[0]]
                if len(gap) < 40 and re.fullmatch(r"[\s,]*(?:[а-яѣіѳ]+\.?\s*,?\s*){0,4}", gap):
                    phrases[-1].append(cu)
                    continue
            phrases.append([cu])

        last_design_role, last_costume_at, split_role = "", -999, "costume_making"
        for pi, ph in enumerate(phrases):
            start, end_cue = ph[0][0], ph[-1][1]
            c0, c1 = clause_of(start)
            nxt = phrases[pi + 1][0][0] if pi + 1 < len(phrases) else len(body)
            limit = min(c1, nxt)
            for s0 in stops:
                if end_cue <= s0 < limit:
                    limit = s0
                    break
            text_ph = body[start:limit]
            rs = {r for _, _, r in ph}
            single = len(ph) == 1
            if "costumes" in rs:
                last_costume_at = end_cue
                if re.search(r"рисунк|эскиз", text_ph, re.I):
                    rs = (rs - {"costumes"}) | {"costume_design"}
            if "headwear" in rs:
                last_costume_at, split_role = end_cue, "headwear"
            elif "costumes" in rs or "costume_design" in rs:
                split_role = "costume_making"
            # `Костюмы по оригинальнымъ рисункамъ изготовлены мастерами Каффи и Офицеровой`
            if rs & {"costume_design", "costumes"} and re.search(
                    r"(?:изготовлен|сшит|сдѣлан)\w*\s+(?:въ\s+мастерск\w*\s+|мастер\w*\s+|костюмер\w*\s+)",
                    text_ph, re.I):
                rs = (rs - {"costume_design", "costumes"}) | {"costume_making"}
            if "costume-split" in rs:
                rs.discard("costume-split")
                if start - last_costume_at < 160:
                    rs.add(split_role)
            if "choreography" in rs and re.search(
                    r"танц\w*(?:\s+[^\s]+){0,4}?\s+(?:поставлен|сочинен)|(?:сочинені\w*|сочинен\w*)\s+танц",
                    text_ph, re.I):
                rs.discard("author")
                if re.search(r"танц\w*(?:\s+[^\s]+){0,4}?\s+поставлен", text_ph, re.I) \
                        and not re.search(r"сочинен\w*\s+и\s+поставлен", text_ph, re.I):
                    rs.discard("staging")
            if "source" in rs and re.search(r"сюж\.\s*соч|сюжет\w*\s+(?:соч|составл)", text_ph, re.I):
                rs = (rs - {"source", "author"}) | {"libretto"}
            # `музыка соч. Минкуса`, `музыка балета соч. Цезаря Пуни`: `соч.` = composed
            if "music" in rs and "author" in rs and re.search(
                    r"муз(?:ык\w*|\.)\s+(?:\w+\s+){0,2}?(?:соч|сочин)", text_ph, re.I):
                rs.discard("author")
            # `программа его сочинена Тальони` is the libretto
            if "libretto" in rs and "author" in rs:
                rs.discard("author")
            # `балетъ поставленъ …`: `балетъ` there is the subject, not a credit
            if "ballet-by" in rs and ph[-1][2] != "ballet-by":
                rs.discard("ballet-by")
            # beside a design word, `при возобновленіи` / `постановки` frame the design credit
            if rs & DESIGN:
                rs -= {"staging", "staging-revival", "author", "ballet-by", "choreography"}
            # `Музыка … частью заимствована изъ сочиненій Мендельсона, Тома, Пуньо`
            # `по своему сюжету … переложеніемъ балета «Шехерезада» Л. С. Бакста`
            if "ballet-by" in rs and ph[-1][2] == "ballet-by":
                rs &= {"ballet-by"}
            if "music" in rs and "source" in rs:
                rs.discard("source")
            # `Волшебныя сказки: Котъ въ сапогахъ` heads a list of dances
            if rs == {"source"} and re.match(r"\s*:", body[end_cue:end_cue + 3]):
                continue
            # `данъ въ 45 разъ по возобновленіи`: a revived performance, not a credit
            if "staging-revival" in rs and re.match(r"(?:по\s+)?возобновлені[иея]", body[start:end_cue + 2], re.I) \
                    and re.search(r"по\s+$", body[max(0, start - 4):start]):
                rs.discard("staging-revival")
            if "staging-revival" in rs:
                rs.discard("staging")
            if "libretto" in rs and re.search(r"въ\s+программ|программ\w*\s+(?:спектакл|бенефис|вечер|концерт)",
                                              body[max(0, start - 4):limit], re.I):
                rs.discard("libretto")
            if "libretto" in rs and "source" in rs and ph[-1][2] == "source" and \
                    not re.search(r"[—–]", body[end_cue:limit]):
                rs.discard("libretto")      # `Темой для либретто послужила сказка Перро`
            if "work-of" in rs:
                rs.discard("work-of")
                if not rs and (last_design_role or is_fig):
                    rs = {last_design_role or "scenery"}
            if single and rs == {"choreography"} and not re.search(r"балетмейстер", body[end_cue:limit][:60], re.I):
                continue
            if rs & DESIGN:
                last_design_role = sorted(rs & DESIGN)[0]
            if not rs:
                continue

            # where the names stop: a quotation (the source cue may skip one --
            # `изъ сказки „Конекъ-Горбунокъ“ П. Ершова`), a bracket, a dash after a name
            lo = end_cue
            for m in re.finditer(r"[—–(«„)]", masked[end_cue:limit]):
                at = end_cue + m.start()
                before_names = names_in(lo, at)
                ch = m.group(0)
                if not before_names and ch in "—–()" and "ballet-by" not in rs:
                    continue
                if ch == "(" and re.match(r"\((?:мужск|женск)\w*\)", body[at:at + 12]):
                    continue
                if not before_names and ch in "«„" and "source" in rs:
                    q = next((q1 for q0, q1 in quotes if q0 == at), None)
                    if q:
                        lo = q
                        continue
                if ch in "—–" and "libretto" in rs and "source" in rs:
                    # `Либретто составлено по роману Виктора Гюго—А. А. Горскимъ`
                    src_names = before_names
                    lib_names = names_in(at + 1, min(c1, nxt))
                    emit(src_names, [], {"source"}, start, end_cue, at, c0, c1, "")
                    emit(lib_names, [], rs - {"source"}, start, end_cue, min(c1, nxt), c0, c1, "")
                    rs = set()
                    break
                limit = at
                break
            if not rs:
                continue
            # `композиторъ съ г-жами: Преображенской`: after a colon come performers
            # (a scenery or costume list is the exception: `написаны: для 1-й картины—г-мъ Кваппъ`)
            if not rs & DESIGN:
                colon = masked.find(":", end_cue, limit)
                if colon != -1:
                    limit = colon
            names = names_in(lo, limit)
            if names:
                gap_words = [w for w in re.findall(r"(?<![" + UC + LC + r"])[" + LC + r"]{2,}", masked[end_cue:names[0][0]])
                             if not GAP_FREE.fullmatch(w)]
                if len(gap_words) > (6 if rs & DESIGN else 4):
                    names = []                   # prose, not a credit
            strict = bool(rs & (DESIGN | {"staging", "staging-revival", "choreography"}))
            kept_n = []
            for n in names:
                tail = body[n[1]:n[1] + 3]
                if strict and re.match(r"\s*[«„]", tail):
                    continue                     # `танцы въ операхъ: Глинки «Жизнь за Царя»`
                if strict and not n[4] and not n[3]:
                    before = body[max(0, n[0] - 25):n[0]]
                    if not re.search(r"(?:гг?\.|г-мъ|г-ну|г-жи|г-жей|художник\w*|академик\w*|худ\.|"
                                     r"скульптор\w*|балетмейстер\w*|профессор\w*|машинист\w*|рисункамъ|эскизамъ|"
                                     r"работы|(?:мужскі[ея]|женскі[ея])\)?)\s*$", before):
                        continue                 # `костюмы Пьеро`: a bare unknown word
                kept_n.append(n)
            names = kept_n
            plural = bool(re.search(r"(?:новыхъ|этихъ|всѣхъ|обоихъ|трехъ|двухъ)\s+балет", body[c0:start], re.I))
            anon = [(end_cue + m.start(), m.group(0)) for m in ANON.finditer(body[end_cue:limit])]
            if not names and not anon:
                continue

            # part: the scene or dance number printed just before the cue
            seps = [m.end() for m in re.finditer(r"[;:]|\d+\)\s|,\s*(?=\d)|[—–]\s*(?=[" + UC + r"])", masked[:start])]
            seg0 = max([c0] + [s for s in seps if s >= c0])
            pre = body[seg0:start].strip(" ,—–:(")
            part = ""
            if rs & DESIGN and PART_WORDS.search(pre) and len(pre) <= 160:
                part = pre
            elif rs & {"music", "instrumentation", "staging", "choreography"} and pre and len(pre) <= 80 \
                    and not find_cues(pre) and not re.search(r"(?:^|\s)(?:и|г\.)$|сцен|сюжет", pre, re.I) \
                    and not any(seg0 <= w[3] < start for w in wms) and not re.search(r"балет|дѣйств", pre, re.I):
                part = pre
            emit(names, anon, rs, start, end_cue, limit, c0, c1, part, plural=plural)

        # scenery lists after a scenery cue: `«Облака» (…)—К. Ѳ. Вальцемъ`,
        # `г. Шангина—«Оазисъ въ пустынѣ» (1-я картина пролога)`
        scen = [cu for cu in cues if cu[2] == "scenery"]
        if scen:
            s_from = scen[0][1]
            pat_b = re.compile(r"(" + QUOTED + r"(?:\s*\([^)]{0,80}\))?)\s*[—–]\s*")
            pat_a = re.compile(r"[—–]\s*(" + QUOTED + r"(?:\s*\([^)]{0,80}\))?)")
            for m in pat_b.finditer(masked, s_from):
                ns = names_in(m.end(), min(len(body), m.end() + 60))
                ns = [n for n in ns if n[0] not in done_names][:3]
                if ns and ns[0][0] - m.end() < 8:
                    c0, c1 = clause_of(m.start())
                    emit(ns, [], {"scenery"}, m.start(), m.end(), ns[-1][1], c0, c1,
                         body[m.start(1):m.end(1)], "")
            for m in pat_a.finditer(masked, s_from):
                seg = masked[max(s_from, m.start() - 40):m.start()]
                ns = names_in(max(s_from, m.start() - 40), m.start())
                ns = [n for n in ns if n[0] not in done_names][-1:]
                if ns and m.start() - ns[-1][1] < 3:
                    c0, c1 = clause_of(m.start())
                    emit(ns, [], {"scenery"}, ns[0][0], ns[0][0], m.end(), c0, c1,
                         body[m.start(1):m.end(1)], "")

    # `ballet-by` is the print's `балетъ X` / `бал. X`: X may be the author or the
    # composer (`«Арлекинада», бал. Р. Дриго`); the lists decide where they can.
    for r in out:
        if r["role_category"] == "ballet-by":
            roles = {rl for pid, rl in list_credit.get(r["work_id"], []) if pid == r["person_id"]}
            r["role_category"] = ("music" if roles == {"music"} else
                                  "author" if roles else "ballet_by")
    # `на сюжетъ романа Сервантеса, М. Петипа`: a name the lists credit as author
    # or librettist of this work is not its literary source
    for r in out:
        if r["role_category"] == "source" and r["person_id"]:
            roles = {rl for pid, rl in list_credit.get(r["work_id"], []) if pid == r["person_id"]}
            if roles and "source" not in roles:
                r["role_category"] = "libretto" if "libretto" in roles else "author"
                r["link_method"] += "+role-from-list"
    # one row per (block, name position, role, work)
    seen, uniq = set(), []
    for r in out:
        k = (r["block_id"], r["char_start"], r["role_category"], r["work_id"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    out = sorted(uniq, key=lambda r: (r["page_id"], r["block_id"], int(r["char_start"]),
                                      r["role_category"], r["work_id"]))
    for i, r in enumerate(out, 1):
        r["credit_id"] = i
    cols = ["credit_id", "page_id", "block_id", "block_type", "char_start", "season", "city",
            "printed_folio", "date_undate", "work_surface", "work_id", "work_source", "part_surface",
            "role_category", "role_text", "printed_phrase", "name_surface", "initials", "person_id",
            "person_candidates_n", "person_candidate_ids", "link_method", "mention_id",
            "is_anonymous", "context_flag"]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)

    con.execute("DROP TABLE IF EXISTS research.review_credit")
    con.execute("""
        CREATE TABLE research.review_credit (
            credit_id              BIGINT PRIMARY KEY,
            page_id                VARCHAR NOT NULL,
            block_id               VARCHAR NOT NULL,
            block_type             VARCHAR,
            char_start             INTEGER,
            season                 VARCHAR NOT NULL,
            city                   VARCHAR NOT NULL,
            printed_folio          VARCHAR,
            date_undate            VARCHAR,
            work_surface           VARCHAR,
            work_id                VARCHAR,
            work_source            VARCHAR,
            part_surface           VARCHAR,
            role_category          VARCHAR NOT NULL,
            role_text              VARCHAR,
            printed_phrase         VARCHAR,
            name_surface           VARCHAR NOT NULL,
            initials               VARCHAR,
            person_id              VARCHAR,
            person_candidates_n    INTEGER,
            person_candidate_ids   VARCHAR,
            link_method            VARCHAR,
            mention_id             BIGINT,
            is_anonymous           BOOLEAN,
            context_flag           VARCHAR
        )""")
    con.execute(f"""
        INSERT INTO research.review_credit
        SELECT CAST(credit_id AS BIGINT), page_id, block_id, block_type, CAST(char_start AS INTEGER),
               season, city, nullif(printed_folio, ''), nullif(date_undate, ''),
               nullif(work_surface, ''), nullif(work_id, ''), nullif(work_source, ''),
               nullif(part_surface, ''), role_category, role_text, printed_phrase, name_surface,
               nullif(initials, ''), nullif(person_id, ''), CAST(person_candidates_n AS INTEGER),
               nullif(person_candidate_ids, ''), link_method,
               CAST(nullif(mention_id, '') AS BIGINT), CAST(is_anonymous AS BOOLEAN),
               nullif(context_flag, '')
        FROM read_csv('{a.out.as_posix()}', header=true, all_varchar=true)""")
    n, wp, ww = con.execute("""SELECT count(*), count(person_id), count(work_id)
                              FROM research.review_credit""").fetchone()
    print(f"{n:,} credits; {wp:,} with a person, {ww:,} with a work -> {a.out} and research.review_credit")
    for role, k in con.execute("""SELECT role_category, count(*) FROM research.review_credit
                                  GROUP BY 1 ORDER BY 2 DESC""").fetchall():
        print(f"  {role:16} {k:6,}")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
