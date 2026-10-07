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
from match_review_mentions import (HONORIFIC, canon_gender, key_of, reflow,  # noqa: E402
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
HON_ONLY = re.compile(r"^\s*(г-жа|г-жи|г-жъ|гг?\.|г-да|г-нъ|в-къ|в-ца|восп-ца|"
                      r"восп-цы|уч-ца|уч-къ|арт\.)\s*", re.I)
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
        words = [w for w in re.split(r"\s+|\bи\b", segs[0]) if w
                 and not re.fullmatch(r"\d+-[яй]", w)]
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
    return not HONORIFIC.match(r)

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

    person_family = {str(r[0]): (r[1] or "") for r in con.execute(
        "SELECT person_id, canonical_family_name FROM research.person").fetchall()}
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
    n_pairs = resolved_by_credit = already = unresolved = 0
    inherited = 0
    for block_id, page_id, _bidx, _btype, text, caption in blocks:
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

        for pm in PAIR.finditer(body):
            left, right = pm.group(1), pm.group(2)
            left_p = performer_name(left, known_surnames)
            right_p = performer_name(right, known_surnames)
            # exactly one side must be a performer, or we cannot tell which is
            # the role -- `Гельцеръ — Манохинъ` is skipped rather than guessed
            if bool(left_p) == bool(right_p):
                continue
            if right_p:
                role_raw, perf_a, perf_b = left, pm.start(2), pm.end(2)
                grammar = "role-performer"
            else:
                role_raw, perf_a, perf_b = right, pm.start(1), pm.end(1)
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
                g = canon_gender(person_family.get(pid, ""))
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
                "performer_surface": body[perf_a:perf_b].strip(),
                "performer_person_id": entity,
                "performer_candidates_n": person[6],
                "performer_candidate_ids": person[7] or "",
                "link_method": method or "unresolved",
                "grammar": grammar,
                "work_surface": work_surface, "work_id": work_id,
                "work_source": work_source,
            })

    a.out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["page_id", "block_id", "season", "city", "printed_folio", "date_undate",
            "role_surface", "performer_surface", "performer_person_id",
            "performer_candidates_n", "performer_candidate_ids", "link_method",
            "grammar", "work_surface", "work_id", "work_source"]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
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
        SELECT row_number() OVER (ORDER BY page_id, block_id, role_surface),
               page_id, block_id, season, city, nullif(printed_folio, ''),
               nullif(date_undate, ''), role_surface,
               performer_surface, nullif(performer_person_id, ''),
               CAST(performer_candidates_n AS INTEGER),
               nullif(performer_candidate_ids, ''), link_method, grammar,
               nullif(work_surface, ''), nullif(work_id, ''),
               nullif(work_source, '')
        FROM read_csv('{a.out.as_posix()}', header=true, all_varchar=true)
    """)
    dated = con.execute("""SELECT count(*) FROM research.review_assertion
                           WHERE date_undate IS NOT NULL""").fetchone()[0]
    linked = con.execute("""SELECT count(*) FROM research.review_assertion
                            WHERE performer_person_id IS NOT NULL""").fetchone()[0]
    withwork = con.execute("""SELECT count(*) FROM research.review_assertion
                              WHERE work_id IS NOT NULL""").fetchone()[0]

    print(f"\n{n_pairs:,} role-performer pairs -> {len(out):,} assertions")
    print(f"  performer already linked by the matcher : {already:,}")
    print(f"  NEWLY resolved by the spiski credit     : {resolved_by_credit:,}")
    print(f"  still unresolved                        : {unresolved:,}")
    print(f"\n  with a performer entity : {linked:,}")
    print(f"  with a work entity      : {withwork:,}"
          f"  (of which {inherited:,} inherited from earlier on the page)")
    print(f"  with a resolved DATE    : {dated:,}")
    print(f"\n-> {a.out} and research.review_assertion")
    con.close()


if __name__ == "__main__":
    main()
