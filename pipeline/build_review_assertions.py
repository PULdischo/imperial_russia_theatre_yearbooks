"""Turn review cast lists into dated performer -> role -> work assertions.

This is the join the whole Season Review track exists to make. Stated plainly:

- the **spiski** record performer -> work -> role, season-scoped, with **no date**
  (`raw.person_entry_credit`, 10,718 rows carrying a `role_name`)
- the **Repertoire** records what played on a **date**, with **no role**
- the **reviews** carry both, in prose: `21-го ноября ... Пахита ...
  Пахиты—г-жа Замбелли`

So the reviews supply the missing edge. Two things come out of that, and they are
the same computation:

**1. Disambiguation by evidence rather than heuristic.** `Петипа` appears 605
times with 9 candidates, all genuine members of the Petipa family, and no amount
of gender/season/ordinal ranking separates them. But the spiski already say
*which* Petipa danced *which* role in *which* season -- `Петипа 1-я, Марія
Маріусовна` as Войслава in «Млада», 1896-97. A review printing
`Войслава—г-жа Петипа` in 1896-97 therefore resolves to her, on record, not on
a guess. This signal reaches the ~6,354 person mentions that sit in a block
alongside a role.

**2. The dated assertion itself**, which neither source has alone.

Ambiguity that survives is mostly irreducible: a prose mention like
`балетъ г. Петипа` carries no role, and `Иванова` admits 52 candidates. That is
a property of the printed source, not a gap in the method, so an unresolved
assertion keeps its full candidate list rather than guessing.

Assertions land in `research.review_assertion` -- the research layer, because an
assertion IS a research fact, unlike a mention (which is linkage state and lives
in `entities`). Date handling follows the rest of the project: a theatrical
season runs September to August, so months Sep-Dec take the season's first year
and Jan-Aug its second.

Usage:
    uv run python pipeline/build_review_assertions.py \
        --reviews-dir outputs/reviews/merged_full \
        --db outputs/reviews/db/imperial_theaters_reviews.duckdb \
        --out outputs/reviews/mentions/review_assertion.csv
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
from match_review_mentions import (HONORIFIC, key_of, person_gender, reflow,  # noqa: E402
                                   surname_forms, surface_gender)

# The cast-list grammar, `X—Y`, where ONE side is a role and the other a
# performer. Which is which is decided by surname membership rather than by
# position, because the corpus prints both orders:
#
#   роль—performer   `Клодъ Фроло—Гельцеръ`, `судья—Бондыревъ`
#   performer—роль   `Составъ исполнителей былъ слѣдующій: Бессонэ — Галатея`
#
# and because the role half is often LOWERCASE -- `бабушка—Матвѣева`,
# `нотаріусъ—г. Жуляевъ`, `его жена—г-жа Матвѣева`, `владѣлецъ деревни —
# Гельцеръ`. An earlier version required a capital on the left and so dropped
# every descriptive common-noun role, which is a large share of them.
#
# Periods, colons and semicolons stay excluded from both halves: that is what
# keeps a span from crossing a sentence boundary, which produced role values
# like `Яковлевъ. Партію Германа пѣлъ г. Клементьевъ, графа Томскаго`.
PAIR = re.compile(
    r"([^—–\n;.:()»«]{2,60}?)\s*[—–]\s*([^—–\n;.:()»«]{2,60}?)"
    r"(?=[;.,)]|\s+и\s|$)")

# An institutional genitive is not a role: `артистъ Императорскихъ Московскихъ
# театровъ—г. X` has the shape of the cast-list grammar but names an employer.
NOT_A_ROLE = re.compile(
    r"(театр\w*|балета|балетъ|труппы|труппа|училищ\w*|оркестр\w*|"
    r"сцены|сцена|конторы|дирекці\w*|общества)$", re.I)
ROLE_VERB = re.compile(r"\b(пѣл\w*|пел\w*|исполнял\w*|исполнил\w*|танцовал\w*|"
                       r"танцевал\w*|выступал\w*|участвовал\w*|поставил\w*|"
                       r"изображал\w*|приглашен\w*|распредѣлен\w*)\b", re.I)
ROLE_PROSE = re.compile(r"^(роль|роли|парті\w+|въ\s+роли|составъ)\b", re.I)
# a conjunction fragment or a bare number is a piece of a list, not a role
ROLE_FRAGMENT = re.compile(r"^(и|а|но|же|съ|также)\s|^\d+\s*$|^и\s*\d", re.I)
# a music or authorship attribution rides the same dash: `Кякштъ — музыка
# варьяціи соч. …` is a credit, not a cast entry
ROLE_ATTRIBUTION = re.compile(r"\b(муз\.|музыка|соч\.|сочин\w*|балетмейстер\w*|"
                              r"декорац\w*|костюм\w*|дириж\w*)", re.I)
# Instrument solos, RG 2026-10-22: "keep the instrument solos as their own kind
# of statement. that's neat data!" Reviews print who played the solos in a
# ballet: `Исполняли соло: на скрипкѣ — г. Крейнъ; на віолончели — г.
# Аспергеръ; на арфѣ — г. Омъ`. The cast-pair grammar caught only the 13 of
# these whose honorific has no period (`г-нъ`, `г-жа`) -- PAIR stops at the
# period of `г.` -- and filed them as roles. They now go to their own table,
# research.review_solo, read by SOLO below, which allows `г.`, titles
# (`солистъ Его Величества г. Ауэръ`) and two players (`гг. Гордонъ и Беме`).
INSTRUMENT = (r"(?:скрипк|альт|віолончел|виолончел|контрабас|арф|флейт|гобо|"
              r"кларнет|фагот|валторн|вальторн|волторн|корнет|труб|тромбон|литавр|"
              r"селест|челест|роял|фортепіан|фортепиан|фисгармоні|органѣ|цитр|"
              r"гитар|мандолин|балалайк|колокольчик|ксилофон|piccolo|picollo|cornet)")
# `на` may be left out after a comma inside a list: `на скрипкѣ—г. Крюгеръ,
# кларнетѣ—г. …`
SOLO = re.compile(r"(?:\bна\s+|(?<=, )|(?<=,)|(?<=; )|(?<=;))(" + INSTRUMENT + r"[\w\-à]*(?:\s+à\s+\w+)?(?:\s*\([^)]{1,20}\))?)"
                  r"\s*[—–]\s*", re.I)
# a solo the PAIR grammar reads as a role: `на арфѣ`, `Соло на челесто`, or a
# lone instrument in the case `на` governs (`віолончели`, `мандолинѣ`), or
# Latin `cornet-à-piston`. NOT a bare noun: `уланскій корнетъ`, `корнета`,
# `Селестина`, `трубадуръ` are roles.
SOLO_ROLE = re.compile(r"^(?:соло\s+)?на\s+" + INSTRUMENT + r"|^" + INSTRUMENT +
                       r"[\w\-à]*(?:ѣ|и|ахъ)$|^cornet", re.I)
# where the player half of a solo clause stops: `;`, `, на <next instrument>`,
# or a sentence-ending period -- not the period of `г.` / `гг.` or an initial
SOLO_STOP = re.compile(r";|,\s*(?=на\s|" + INSTRUMENT + r")|\.(?=\s+[А-ЯЀ-ЏІѲѴA-Z][а-яѣіѳa-z])|\.$|\n")
SOLO_NOT_END = re.compile(r"(?:^|\s)(?:гг?|г-нъ|г-жа|[А-ЯЀ-ЏІѲѴA-Z])$")


def solo_span_end(body: str, start: int) -> int:
    """End of the player half of a solo clause that starts at `start`."""
    pos = start
    limit = min(len(body), start + 90)
    while pos < limit:
        m = SOLO_STOP.search(body, pos, limit)
        if not m:
            return limit
        if m.group(0) == "." and SOLO_NOT_END.search(body[start:m.start()]):
            pos = m.end()          # `г. Крейнъ`, `А. Ѳ. Арендсъ`: keep going
            continue
        return m.start()
    return limit


HON_ONLY = re.compile(r"^\s*(г-жа|г-жи|г-жъ|гг?\.|г-да|г-нъ|в-къ|в-ца|восп-ца|"
                      r"восп-цы|уч-ца|уч-къ|арт\.)\s*", re.I)
# PAIR keeps periods out of both halves so a span cannot cross a sentence --
# but the commonest masculine honorific is `г.`, and until 2026-10-22 that
# rule silently dropped every pair printed `Мутчи—г. Легатъ 1-й`: not one
# assertion had a `г. …` performer (141 had `г-нъ`, 1,509 `г-жа`). These
# periods are not sentence ends, so they are hidden from PAIR -- swapped for a
# same-length placeholder, so every offset still points into the real text.
# Covered: `г.` / `гг.` before a name, and a single-capital initial before
# another capital (`г. Н. Легатъ`, `С. Легатъ`).
NON_SENTENCE_PERIOD = re.compile(
    r"(?:(?<=\bг)|(?<=\bгг)|(?<=\bГ)|(?<=\bГг)|(?<=\b[А-ЯЀ-ЏІѲѴ]))\.(?=\s*[А-ЯЀ-ЏІѲѴ])")
MASK = "\u2024"   # one dot leader: not `.`, so PAIR's classes let it through


def mask_periods(body: str) -> str:
    return NON_SENTENCE_PERIOD.sub(MASK, body)


# With those periods hidden, a performer half can run back over a title or the
# previous clause: `г. Сампелевъ исполнилъ роль короля, г. Хлюстинъ — принца
# Маріо`, `заслуженная артистка М. Кшесинская—Аспичія`. Before, the period of
# `г.` / `М.` cut it short by accident. So when a half is not a performer as a
# whole, its TAIL is tried -- but only a tail that opens with an honorific or an
# initial, or follows a comma, so plain prose does not start yielding names.
PERFORMER_TAIL = re.compile(
    r"(?:^|(?<=[\s,]))((?:гг?\u2024|Гг?\u2024|г-нъ|г-жа|г-жи|г-да|в-къ|в-ца|в-цы|"
    r"восп-ц\w*|восп-къ|воспитанниц\w*|воспитанник\w*|[А-ЯЀ-ЏІѲѴ]\u2024)\s*"
    r"(?:[А-ЯЀ-ЏІѲѴ]\u2024\s*)*[А-ЯЀ-ЏІѲѴ][^\s,]*(?:\s+\d+(?:-[йяе]\S*)?)?)\s*$")
COMMA_TAIL = re.compile(r",\s*([^,]+?)\s*$")


def performer_tail(masked_side: str, side: str, known: set[str]) -> tuple[str | None, int]:
    """(surname, offset of the performer within the side) for a side that is
    only a performer at its end; (None, 0) otherwise."""
    for pat in (PERFORMER_TAIL, COMMA_TAIL):
        m = pat.search(masked_side)
        if m and m.start(1) > 0:
            p = performer_name(side[m.start(1):], known)
            if p:
                return p, m.start(1)
    return None, 0


ORD_TAIL = re.compile(r"\s*\d+-[яйе][яй]?\s*$")


def performer_name(side: str, known: set[str]) -> str | None:
    """The surname if this half of the pair is a performer, else None.

    A performer half is an optional honorific plus one or two name tokens whose
    last token is a known surname form. Requiring surname membership is what
    lets the role half be lowercase and unconstrained without the pattern
    drifting into ordinary prose.
    """
    t = ORD_TAIL.sub("", HON_ONLY.sub("", side.strip(" .,")))
    had_hon = bool(HON_ONLY.match(side.strip()))
    toks = [x for x in re.split(r"\s+", t) if x]
    if not toks or len(toks) > 3:
        return None
    last = key_of(toks[-1].strip(".,"))
    if last in known:
        return last
    # an honorific alone is good evidence even for a surname we do not hold
    if had_hon and len(toks) == 1 and re.match(r"[А-ЯЀ-ЏІѲѴ]", toks[0]):
        return last
    return None


def trim_leading_performers(role: str, known: set[str]) -> str:
    """Drop leading comma-separated segments that are just a surname.

    Cast lists separate pairs with commas as well as semicolons, so the role
    half of one pair can start inside the performer half of the last one:
    `Гельцеръ, Коленъ, молодой крестьянинъ, влюбленный въ Лизу` is really the
    role `Коленъ, …` with the previous pair's performer `Гельцеръ` stuck on the
    front. A segment is a performer if every word in it is a known surname form
    (plus an optional ordinal), which keeps genuine descriptive roles --
    `дона Серафина, племянница Мендоза` -- intact.
    """
    segs = [x.strip() for x in role.split(",")]
    while len(segs) > 1:
        # `и г. Тихомировъ` -- the previous pair's second performer, honorific
        # and all -- counts too (2026-10-22, once `г.` stopped cutting it off)
        seg0 = re.sub(r"^(?:[иа]\s+)?", "", segs[0])
        seg0 = HON_ONLY.sub("", seg0)
        words = [w for w in re.split(r"\s+|\bи\b", seg0) if w
                 and not re.fullmatch(r"\d+-[яй]", w)
                 and not re.fullmatch(r"[А-ЯЀ-ЏІѲѴ]\.", w)]
        if words and all(key_of(w.strip(".")) in known for w in words):
            segs.pop(0)
        else:
            break
    return ", ".join(segs).strip()


def plausible_role(role: str) -> bool:
    r = role.strip()
    if len(r) < 2 or NOT_A_ROLE.search(r) or ROLE_VERB.search(r):
        return False
    if ROLE_PROSE.match(r) or ROLE_FRAGMENT.match(r) or ROLE_ATTRIBUTION.search(r):
        return False
    # a bare honorific+surname on the left is a performer, not a role
    if HONORIFIC.match(r):
        return False
    # nor is a role with a performer inside it (`Дугминта, г. Гердтъ, солистъ
    # Его Величества`): two pairs run together, the role cannot be trusted
    return not re.search(r"(?:^|[\s,])(?:гг?\.|г-жа|г-жи|г-нъ|г-жей|г-жою)\s*[А-ЯЀ-ЏІѲѴ]", r)

csv.field_size_limit(10_000_000)

MONTHS = {
    "январ": 1, "феврал": 2, "март": 3, "апрѣл": 4, "апрел": 4, "ма": 5,
    "іюн": 6, "июн": 6, "іюл": 7, "июл": 7, "август": 8, "сентябр": 9,
    "октябр": 10, "ноябр": 11, "декабр": 12,
}
DATE_RE = re.compile(
    r"(\d{1,2})-(?:го|ro)\s+("
    r"январ\w*|феврал\w*|март\w*|апрѣл\w*|апрел\w*|ма[яй]|мая|"
    r"іюн\w*|июн\w*|іюл\w*|июл\w*|август\w*|сентябр\w*|октябр\w*|"
    r"ноябр\w*|декабр\w*)", re.I)


def month_of(word: str) -> int | None:
    w = key_of(word)
    if w.startswith(("мая", "май")):
        return 5
    for stem, n in sorted(MONTHS.items(), key=lambda x: -len(x[0])):
        if w.startswith(stem):
            return n
    return None


def season_years(season: str) -> tuple[int, int] | None:
    """'1901-02' -> (1901, 1902). Also tolerates '1901-1902'."""
    m = re.match(r"^(\d{4})-(\d{2,4})$", season.strip())
    if not m:
        return None
    y1 = int(m.group(1))
    tail = m.group(2)
    y2 = int(tail) if len(tail) == 4 else (y1 // 100) * 100 + int(tail)
    if y2 < y1:
        y2 += 100
    return y1, y2


# Julian month lengths. Imperial Russia used the Julian calendar until 1918 and
# this project stores dates as printed, so February has 29 days in EVERY year
# divisible by 4 -- including 1900, which the Gregorian calendar skips.
# `research.event` already holds 6 real events on 1900-02-29, and that is also
# why `date_undate` is VARCHAR there rather than DATE.
_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def julian_days_in_month(year: int, month: int) -> int:
    if month == 2 and year % 4 == 0:
        return 29
    return _DAYS[month - 1]


def resolve_date(day: int, month: int, season: str) -> str | None:
    """A theatrical season runs Sept-Aug, so the month picks the year.

    Returns a plain string, never a `datetime.date`: `datetime` applies
    Gregorian rules and rejects 29 February 1900, a date this corpus genuinely
    contains. An earlier version used `datetime.date(...).isoformat()` inside a
    try/except and so dropped those silently.
    """
    yy = season_years(season)
    if not yy or not (1 <= month <= 12):
        return None
    year = yy[0] if month >= 9 else yy[1]
    if not (1 <= day <= julian_days_in_month(year, month)):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def load_credits(con) -> tuple[dict, dict]:
    """(person_id, folded role) and (person_id, folded work) -> seasons credited."""
    rows = con.execute("""
        SELECT pl.person_id, c.label, c.role_name, sp.season
        FROM raw.person_entry_credit c
        JOIN raw.person_entry pe ON pe.entry_id = c.entry_id
        JOIN entities.person_link pl ON pl.entry_id = pe.entry_id
        JOIN raw.source_pages sp ON sp.page_id = pe.page_id
        WHERE c.role_name IS NOT NULL AND c.role_name <> ''
    """).fetchall()
    by_role: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    by_work: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for pid, work, role, season in rows:
        pid = str(pid)
        if role:
            by_role[(pid, key_of(role))].add(season or "")
        if work:
            by_work[(pid, key_of(work))].add(season or "")
    return by_role, by_work


# A review's FIRST page often opens with the tail of the previous section,
# because an issue packs two reviews onto one printed page -- 1912-13 SP opens
# with the last paragraphs of the opera review. build_bilingual already drops
# those for reading; the assertion builder has to as well, or it mines them.
# It did: the only "assertion" the 1912-13 ballet review produced was
# `представленій, посвященныхъ отечественнымъ авторамъ, и 16 %` -- `Вагнеру`,
# parsed out of an opera statistics sentence.
SECTION_HEADING = {"балетъ", "опера", "драма"}


def first_page_skip(blocks: list[tuple]) -> int:
    """`block_index` of the review's own section heading on its first page.

    Returns the stored block_index, NOT the position in this list: block_index
    is 1-based in the CSV, so comparing a list position against it silently
    skips one block too few and let the 1912-13 opera tail through.
    """
    for b in blocks:
        if b[3] != "heading":
            continue
        if (b[4] or "").strip().strip(".").strip().lower() in SECTION_HEADING:
            return int(b[2])
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews-dir", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--genre", default="Ballet")
    a = ap.parse_args()

    con = duckdb.connect(str(a.db))
    by_role, by_work = load_credits(con)
    print(f"spiski credits indexed: {len(by_role):,} (person, role) pairs, "
          f"{len(by_work):,} (person, work) pairs")

    person_family, person_g = {}, {}
    for pid, fam, disp in con.execute(
            "SELECT person_id, canonical_family_name, display_name FROM research.person").fetchall():
        person_family[str(pid)] = fam or ""
        person_g[str(pid)] = person_gender(disp or "", fam or "")
    known_surnames: set[str] = set()
    for fam in set(person_family.values()):
        if fam:
            known_surnames |= surname_forms(fam)

    pages = {r[0]: {"season": r[1], "city": r[2], "genre": r[3], "folio": r[4]}
             for r in con.execute("""SELECT page_id, season, city, genre,
                                     printed_folio FROM raw.review_page""").fetchall()}
    blocks = con.execute("""
        SELECT block_id, page_id, block_index, block_type, text, caption_text
        FROM raw.review_block ORDER BY page_id, block_index""").fetchall()
    mentions = collections.defaultdict(list)
    for r in con.execute("""
            SELECT block_id, mention_type, char_start, char_end, surface,
                   entity_id, candidates_n, candidate_ids
            FROM entities.review_mention ORDER BY block_id, char_start""").fetchall():
        mentions[r[0]].append(r)

    # Work mentions earlier on the same page, in reading order. A cast list in a
    # paragraph often names no title because the title was given a block or two
    # above. Inheriting is only safe when the page has settled on ONE work so
    # far: measured over the gap, 255 assertions have exactly one resolved work
    # earlier on their page, 464 have none at all, and 111 have two or more --
    # so this recovers the first group and declines the rest rather than
    # attaching a cast to the wrong ballet. Provenance is recorded in
    # `work_source` either way.
    page_works: dict[str, list[tuple[int, str, str]]] = collections.defaultdict(list)
    for page_id, bidx, surface, eid in con.execute("""
            SELECT m.page_id, b.block_index, m.surface, m.entity_id
            FROM entities.review_mention m
            JOIN raw.review_block b ON b.block_id = m.block_id
            WHERE m.mention_type = 'work' AND m.entity_id IS NOT NULL
            ORDER BY m.page_id, b.block_index, m.char_start""").fetchall():
        page_works[page_id].append((bidx, surface, str(eid)))

    out: list[dict] = []
    solos: list[dict] = []
    n_pairs = resolved_by_credit = already = unresolved = 0
    # the first block index to trust on each review's opening page
    first_page: dict[tuple, str] = {}
    for bid, pid, bidx, bt, tx, cap in blocks:
        pg = pages.get(pid)
        if not pg:
            continue
        key = (pg["season"], pg["city"], pg["genre"])
        if key not in first_page or pid < first_page[key]:
            first_page[key] = pid
    skip_before: dict[str, int] = {}
    by_page: dict[str, list[tuple]] = collections.defaultdict(list)
    for row in blocks:
        by_page[row[1]].append(row)
    for pid in set(first_page.values()):
        skip_before[pid] = first_page_skip(by_page[pid])

    inherited = skipped_foreign = 0
    for block_id, page_id, _bidx, _btype, text, caption in blocks:
        if _bidx < skip_before.get(page_id, 0):
            skipped_foreign += 1
            continue
        page = pages.get(page_id)
        if not page or (a.genre and page["genre"] != a.genre):
            continue
        body = reflow(text or caption or "")
        if not body:
            continue
        ms = mentions.get(block_id, [])
        works_here = [m for m in ms if m[1] == "work"]
        # a date stated in this block governs the pairs that follow it
        dates = [(m.start(), int(m.group(1)), month_of(m.group(2)))
                 for m in DATE_RE.finditer(body)]

        def work_and_date(at: int) -> tuple[str, str, str, str, bool]:
            """Governing work and date for a statement at offset `at`.

            The same rules as the cast pairs below: nearest work mention before
            it in the block, else the one work the page has settled on so far;
            nearest date before it in the block. The last value says whether
            the work was inherited from an earlier block.
            """
            prior = [w for w in works_here if w[3] <= at]
            wm = prior[-1] if prior else (works_here[0] if works_here else None)
            w_surface = wm[4] if wm else ""
            w_id = (wm[5] or "") if wm else ""
            w_source = "block" if wm else ""
            inh = False
            if not w_id:
                earlier = [w for w in page_works.get(page_id, []) if w[0] < _bidx]
                distinct = {w[2] for w in earlier}
                if len(distinct) == 1:
                    w_id = earlier[-1][2]
                    w_source = "page-earlier-block"
                    if not w_surface:
                        w_surface = earlier[-1][1]
                    inh = True
                elif len(distinct) > 1:
                    w_source = w_source or "ambiguous-on-page"
            pd = [d for d in dates if d[0] <= at] or dates
            iso_d = (resolve_date(pd[-1][1], pd[-1][2], page["season"])
                     if pd and pd[-1][1] and pd[-1][2] else None)
            return w_surface, w_id, w_source, iso_d or "", inh

        last_solo_end = -1
        for sm in SOLO.finditer(body):
            # the comma form (no `на`) only continues a list already started:
            # it must follow a solo clause directly, or `, Колокольчикъ—г-жа
            # Рославлева` -- a role in «Папоротникъ» -- reads as a bell solo
            if not body[sm.start():sm.start(1)].strip():
                if body[last_solo_end:sm.start()].strip(" ") not in (",", ";"):
                    continue
            p_a = sm.end()
            p_b = solo_span_end(body, p_a)
            last_solo_end = p_b
            # one row per player: split `гг. Гордонъ и Беме` / `г. Кюне-Вальтеръ,
            # Вагнеръ и г. Инспрукеръ` on `,` and `и`, and take the name
            # mention inside each piece -- a piece with none (an unknown
            # surname, `г. Омъ`) still makes a row, unresolved. A piece that is
            # only a title (`солистъ Его Величества`) is not a player.
            pieces, pos = [], p_a
            for sep in list(re.finditer(r",\s*|\s+и\s+", body[p_a:p_b])) + [None]:
                end = p_a + sep.start() if sep else p_b
                if body[pos:end].strip(" ,.;"):
                    pieces.append((pos, end))
                pos = p_a + sep.end() if sep else p_b
            w_surface, w_id, w_source, iso_d, _ = work_and_date(sm.start())
            rows_here = []
            for c_a, c_b in pieces:
                hit = [m for m in ms if m[1] == "person" and c_a <= m[2] < c_b]
                if hit:
                    rows_here += [(m, "") for m in hit]
                elif not re.match(r"\s*(солистъ|артистъ)\b", body[c_a:c_b]):
                    rows_here.append((None, body[c_a:c_b].strip(" ,.;")))
            for m, txt in rows_here:
                solos.append({
                    "page_id": page_id, "block_id": block_id,
                    "season": page["season"], "city": page["city"],
                    "printed_folio": page["folio"] or "",
                    "date_undate": iso_d,
                    # verbatim, `на` included only where printed
                    "instrument_surface": body[sm.start():sm.end(1)].strip(),
                    "performer_surface": m[4] if m else txt,
                    "printed_text": body[sm.start():p_b].strip(" ,;"),
                    "performer_person_id": (m[5] or "") if m else "",
                    "performer_candidates_n": m[6] if m else "",
                    "performer_candidate_ids": (m[7] or "") if m else "",
                    "link_method": ("already-linked" if m and m[5]
                                    else "unresolved"),
                    "work_surface": w_surface, "work_id": w_id,
                    "work_source": w_source,
                })

        for pm in PAIR.finditer(mask_periods(body)):
            # spans come from the masked text, strings from the real one
            left, right = body[pm.start(1):pm.end(1)], body[pm.start(2):pm.end(2)]
            left_p = performer_name(left, known_surnames)
            right_p = performer_name(right, known_surnames)
            l_off = r_off = 0
            if not left_p and not right_p:
                left_p, l_off = performer_tail(pm.group(1), left, known_surnames)
                if not left_p:
                    right_p, r_off = performer_tail(pm.group(2), right, known_surnames)
            # exactly one side must be a performer, or we cannot tell which is
            # the role -- `Гельцеръ — Манохинъ` is skipped rather than guessed
            if bool(left_p) == bool(right_p):
                continue
            if right_p:
                role_raw, perf_a, perf_b = left, pm.start(2) + r_off, pm.end(2)
                grammar = "role-performer"
            else:
                role_raw, perf_a, perf_b = right, pm.start(1) + l_off, pm.end(1)
                grammar = "performer-role"
            role_s = trim_leading_performers(
                role_raw.strip(" .,;:«»„“"), known_surnames)
            if not plausible_role(role_s):
                continue
            # the person mention overlapping the performer half of the pair
            person = next((m for m in ms if m[1] == "person"
                           and not (m[3] <= perf_a or m[2] >= perf_b)), None)
            if not person:
                continue
            n_pairs += 1
            cands = [c for c in (person[7] or "").split("|") if c]
            entity = person[5] or ""
            method = "already-linked" if entity else ""

            # governing work: nearest work mention before this pair
            prior = [w for w in works_here if w[3] <= perf_a]
            work_m = prior[-1] if prior else (works_here[0] if works_here else None)
            work_surface = work_m[4] if work_m else ""
            work_id = (work_m[5] or "") if work_m else ""
            work_source = "block" if work_m else ""
            if not work_id:
                earlier = [w for w in page_works.get(page_id, []) if w[0] < _bidx]
                distinct = {w[2] for w in earlier}
                if len(distinct) == 1:
                    work_id = earlier[-1][2]
                    work_source = "page-earlier-block"
                    if not work_surface:
                        work_surface = earlier[-1][1]
                    inherited += 1
                elif len(distinct) > 1:
                    work_source = work_source or "ambiguous-on-page"

            # --- the credit join ---
            # Gender still constrains it. Without this the join resolved
            # `г-жа Смирнова` to `Смирновъ, Александръ Митрофановичъ`: the
            # credit table is keyed by person, so a same-surname relative of the
            # other gender is a perfectly good index hit and a wrong answer.
            hon = HONORIFIC.match(body[perf_a:perf_b])
            want_g = surface_gender(body[perf_a:perf_b],
                                    hon.group(1) if hon else "")

            def gender_ok(pid: str) -> bool:
                if not want_g:
                    return True
                g = person_g.get(pid)   # patronymic first (#159: 2835 Легатъ)
                return (g is None) or (g == want_g)

            rk = key_of(role_s)
            if not entity and cands:
                cands = [c for c in cands if gender_ok(c)]
                hits = [c for c in cands if (c, rk) in by_role]
                exact = [c for c in hits if page["season"] in by_role[(c, rk)]]
                pick = exact if len(exact) == 1 else (hits if len(hits) == 1 else [])
                if pick:
                    entity = pick[0]
                    method = ("spiski-credit-role-season" if len(exact) == 1
                              else "spiski-credit-role")
                    resolved_by_credit += 1
                elif work_surface:
                    wk = key_of(work_surface)
                    whits = [c for c in cands if (c, wk) in by_work]
                    if len(whits) == 1:
                        entity, method = whits[0], "spiski-credit-work"
                        resolved_by_credit += 1
            if entity and method == "already-linked":
                already += 1
            elif not entity:
                unresolved += 1

            prior_d = [d for d in dates if d[0] <= perf_a] or dates
            day = month = None
            if prior_d:
                _, day, month = prior_d[-1]
            iso = resolve_date(day, month, page["season"]) if day and month else None

            out.append({
                "page_id": page_id, "block_id": block_id,
                "season": page["season"], "city": page["city"],
                "printed_folio": page["folio"] or "",
                "date_undate": iso or "",
                "role_surface": role_s,
                # the separator a list leaves in front (`, г. Гердтъ`, `и г. …`)
                # is not part of the name
                "performer_surface": re.sub(r"^(?:[,;]\s*)?(?:[иа]\s+)?", "",
                                            body[perf_a:perf_b].strip()),
                "performer_person_id": entity,
                "performer_candidates_n": person[6],
                "performer_candidate_ids": person[7] or "",
                "link_method": method or "unresolved",
                "grammar": grammar,
                "work_surface": work_surface, "work_id": work_id,
                "work_source": work_source,
                # a solo the pair grammar happened to catch: numbered with the
                # cast rows (so no other assertion_id moves) but left out of
                # review_assertion -- SOLO reads it into review_solo instead
                "statement_kind": ("instrument solo" if SOLO_ROLE.match(role_s)
                                   else "cast"),
            })

    a.out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["page_id", "block_id", "season", "city", "printed_folio", "date_undate",
            "role_surface", "performer_surface", "performer_person_id",
            "performer_candidates_n", "performer_candidate_ids", "link_method",
            "grammar", "work_surface", "work_id", "work_source", "statement_kind"]

    # Ids are kept stable across rebuilds: a row that was already in the table
    # (same block, role, performer, grammar) keeps its assertion_id, and new
    # rows are numbered after the highest id ever used. Docs and worklists cite
    # assertion_ids (#159), and the `г.` fix of 2026-10-22 added rows that a
    # plain row_number() would have interleaved, renumbering everything after.
    def perf_key(ps: str) -> str:
        # the surname, so `Кузнецова` (cut short by the old `г.` bug) and
        # `г. Кузнецова` are the same row
        t = re.sub(r"^(?:[,;]\s*)?(?:[иа]\s+)?", "", ps or "").strip()
        return performer_name(t, known_surnames) or key_of(t)

    prev: dict[tuple, list[int]] = collections.defaultdict(list)
    prev_max = 0
    if con.execute("""SELECT 1 FROM information_schema.tables WHERE
            table_schema = 'research' AND table_name = 'review_assertion'""").fetchone():
        for aid, bid, rs, ps, gr in con.execute("""SELECT assertion_id, block_id,
                role_surface, performer_surface, grammar
                FROM research.review_assertion ORDER BY assertion_id""").fetchall():
            prev[(bid, rs, perf_key(ps), gr)].append(int(aid))
            prev_max = max(prev_max, int(aid))
    # the 13 solo rows that left this table on 2026-10-22 held ids up to 1741;
    # never hand those out again
    prev_max = max(prev_max, 1952 if prev else 0)
    order = sorted(range(len(out)), key=lambda i: (out[i]["page_id"],
                   out[i]["block_id"], out[i]["role_surface"]))
    fresh = prev_max
    kept_ids = new_ids = 0
    for i in order:
        r = out[i]
        if r["statement_kind"] != "cast":
            r["assertion_id"] = ""
            continue
        k = (r["block_id"], r["role_surface"], perf_key(r["performer_surface"]),
             r["grammar"])
        if prev.get(k):
            r["assertion_id"] = prev[k].pop(0)
            kept_ids += 1
        elif prev:
            fresh += 1
            r["assertion_id"] = fresh
            new_ids += 1
        else:
            r["assertion_id"] = ""
    dropped_ids = sorted(x for v in prev.values() for x in v)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["assertion_id"] + cols)
        w.writeheader()
        w.writerows(out)

    con.execute("DROP TABLE IF EXISTS research.review_assertion")
    con.execute("""
        CREATE TABLE research.review_assertion (
            assertion_id            BIGINT PRIMARY KEY,
            page_id                 VARCHAR NOT NULL,
            block_id                VARCHAR NOT NULL,
            season                  VARCHAR NOT NULL,
            city                    VARCHAR NOT NULL,
            printed_folio           VARCHAR,
            date_undate             VARCHAR,
            role_surface            VARCHAR NOT NULL,
            performer_surface       VARCHAR NOT NULL,
            performer_person_id     VARCHAR,
            performer_candidates_n  INTEGER,
            performer_candidate_ids VARCHAR,
            link_method             VARCHAR,
            grammar                 VARCHAR,
            work_surface            VARCHAR,
            work_id                 VARCHAR,
            work_source             VARCHAR
        )
    """)
    con.execute(f"""
        INSERT INTO research.review_assertion
        SELECT * EXCLUDE (statement_kind) FROM (
          SELECT coalesce(CAST(nullif(assertion_id, '') AS BIGINT),
                          row_number() OVER (ORDER BY page_id, block_id, role_surface)),
                 page_id, block_id, season, city, nullif(printed_folio, ''),
                 nullif(date_undate, ''), role_surface,
                 performer_surface, nullif(performer_person_id, ''),
                 CAST(performer_candidates_n AS INTEGER),
                 nullif(performer_candidate_ids, ''), link_method, grammar,
                 nullif(work_surface, ''), nullif(work_id, ''),
                 nullif(work_source, ''), statement_kind
          FROM read_csv('{a.out.as_posix()}', header=true, all_varchar=true))
        WHERE statement_kind = 'cast'
    """)

    # --- instrument solos: their own table (RG 2026-10-22) ---
    solo_csv = a.out.with_name("review_solo.csv")
    solo_cols = ["page_id", "block_id", "season", "city", "printed_folio",
                 "date_undate", "instrument_surface", "performer_surface",
                 "printed_text", "performer_person_id", "performer_candidates_n",
                 "performer_candidate_ids", "link_method", "work_surface",
                 "work_id", "work_source"]
    with open(solo_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=solo_cols)
        w.writeheader()
        w.writerows(solos)
    con.execute("DROP TABLE IF EXISTS research.review_solo")
    con.execute("""
        CREATE TABLE research.review_solo (
            solo_id                 BIGINT PRIMARY KEY,
            page_id                 VARCHAR NOT NULL,
            block_id                VARCHAR NOT NULL,
            season                  VARCHAR NOT NULL,
            city                    VARCHAR NOT NULL,
            printed_folio           VARCHAR,
            date_undate             VARCHAR,
            instrument_surface      VARCHAR NOT NULL,
            performer_surface       VARCHAR NOT NULL,
            printed_text            VARCHAR NOT NULL,
            performer_person_id     VARCHAR,
            performer_candidates_n  INTEGER,
            performer_candidate_ids VARCHAR,
            link_method             VARCHAR,
            work_surface            VARCHAR,
            work_id                 VARCHAR,
            work_source             VARCHAR
        )
    """)
    con.execute(f"""
        INSERT INTO research.review_solo
        SELECT row_number() OVER (ORDER BY page_id, block_id, printed_text,
                                  performer_surface),
               page_id, block_id, season, city, nullif(printed_folio, ''),
               nullif(date_undate, ''), instrument_surface, performer_surface,
               printed_text, nullif(performer_person_id, ''),
               CAST(nullif(performer_candidates_n, '') AS INTEGER),
               nullif(performer_candidate_ids, ''), link_method,
               nullif(work_surface, ''), nullif(work_id, ''),
               nullif(work_source, '')
        FROM read_csv('{solo_csv.as_posix()}', header=true, all_varchar=true)
    """)
    n_solo, n_solo_linked = con.execute("""SELECT count(*),
        count(performer_person_id) FROM research.review_solo""").fetchone()
    dated = con.execute("""SELECT count(*) FROM research.review_assertion
                           WHERE date_undate IS NOT NULL""").fetchone()[0]
    linked = con.execute("""SELECT count(*) FROM research.review_assertion
                            WHERE performer_person_id IS NOT NULL""").fetchone()[0]
    withwork = con.execute("""SELECT count(*) FROM research.review_assertion
                              WHERE work_id IS NOT NULL""").fetchone()[0]

    print(f"\n{skipped_foreign:,} block(s) skipped as the previous review's tail")
    n_cast = sum(1 for r in out if r["statement_kind"] == "cast")
    print(f"{n_pairs:,} role-performer pairs -> {n_cast:,} assertions "
          f"(+{len(out) - n_cast:,} solo-shaped pairs left to review_solo)")
    print(f"  performer already linked by the matcher : {already:,}")
    print(f"  NEWLY resolved by the spiski credit     : {resolved_by_credit:,}")
    print(f"  still unresolved                        : {unresolved:,}")
    print(f"\n  with a performer entity : {linked:,}")
    print(f"  with a work entity      : {withwork:,}"
          f"  (of which {inherited:,} inherited from earlier on the page)")
    print(f"  with a resolved DATE    : {dated:,}")
    if prev or dropped_ids:
        print(f"\nassertion ids: {kept_ids:,} kept, {new_ids:,} new (from "
              f"{prev_max + 1:,}), {len(dropped_ids):,} earlier rows gone: "
              f"{dropped_ids[:40]}")
    print(f"\n{n_solo:,} instrument solos ({n_solo_linked:,} with a player "
          f"entity) -> {solo_csv} and research.review_solo")
    print(f"\n-> {a.out} and research.review_assertion")
    con.close()


if __name__ == "__main__":
    main()
