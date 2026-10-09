"""Closed-vocabulary mention matching over the Season Review ballet text.

RG, 2026-10-07: *"there will be very few mentions of people who don't exist
elsewhere in the Yearbooks."* That is what makes this tractable without NER --
the population is closed, so matching against the project's own dictionaries
reaches nearly all mentions. Design and measurements: docs/season_reviews_fields.md
Part 2. Scope is the Ballet reviews; opera is deferred (RG, same day).

**Forms are GENERATED from the dictionary, not stemmed from the text.** Every
canonical surname is expanded into its plausible declined forms, folded, and
indexed; matching is then an exact lookup. Stemming arbitrary tokens was tried
in the exploratory pass and fails in both directions -- a 4-character floor
silently dropped `Дочь`->доч and `Донъ`->дон (losing the first words of
«Дочь фараона» and «Донъ-Кихотъ»), while a noun-only ending list missed every
adjectival surname (Чайковск**аго** 126x, Горск**имъ** 73x, Кшесинск**ой** 39x,
all present in `research.person`). Generation makes both classes explicit and
keeps the failure mode legible: a missed form is a missing rule, not a silent
threshold.

Two traps this corpus sets, both paid for already:

**Line breaks.** The stored text keeps the printed breaks, so a split word
arrives as `Кшесин- ской` or `Преобра- женской`. 7,173 words (3.7% of the
corpus) are split this way and ~3,000 of them are capitalised -- that is, they
are exactly the mentions this script exists to find. Reflow FIRST. A pattern
that fails across a break fails silently, indistinguishably from the name not
being there.

**Stem collisions.** Pre-reform orthography folds several letters together and
Russian surnames overlap common words. Matching is therefore restricted to
capitalised tokens, and a bare capitalised token at a sentence start is not
trusted on its own -- 36% of capitalised tokens are sentence-initial noise.
Honorific-anchored matches are reported at higher confidence than bare ones.

Honorifics govern LISTS, not single names: one `г-жи` followed by thirty
surnames. The scanner opens a list span at an honorific and keeps consuming
capitalised tokens across commas and `и`.

Roles are matched only inside `cast_list` blocks and the `Role—Performer`
em-dash construction. The role vocabulary mixes proper names (Лиза,
принцъ Шарманъ) with generic nouns (королева 53, офицеръ 55, цыганка 71), and
turned loose on running prose the generic half fires on ordinary words.

Usage:
    uv run python pipeline/match_review_mentions.py \
        --reviews-dir outputs/reviews/merged_full \
        --db outputs/full_run/imperial_theaters.duckdb \
        --out-dir outputs/reviews/mentions \
        [--seasons 1901-02,1904-05] [--limit-pages 60]
"""
from __future__ import annotations

import argparse
import collections
import csv
import re
import unicodedata
from pathlib import Path

csv.field_size_limit(10_000_000)

# ---------------------------------------------------------------- orthography

FOLD = str.maketrans({
    "ъ": "", "ѣ": "е", "і": "и", "ѳ": "ф", "ѵ": "и", "ё": "е",
    "Ъ": "", "Ѣ": "Е", "І": "И", "Ѳ": "Ф", "Ѵ": "И", "Ё": "Е",
})
CAP = re.compile(r"^[А-ЯЀ-ЏЪѢІѲѴ]")
# A hyphen after a digit or a Roman numeral is a COMPOUND hyphen, not a
# soft line-break one: the print reads `за XLV-` / `лѣтнюю службу`, and
# joining it manufactures `XLVлѣтнюю`, which looked like a mixed-script error
# and was not one. Latin I V X L C D M never end a Russian word, so the
# lookbehind is safe.
HYPHEN_BREAK = re.compile(r"(?<![\dIVXLCDM])([^\s-])-\s+")
WS = re.compile(r"\s+")


def fold(s: str) -> str:
    """Orthography-fold and lowercase, for dictionary lookup only."""
    return unicodedata.normalize("NFC", s).translate(FOLD).lower()


def key_of(s: str) -> str:
    """The lookup key: folded, with a word-final soft sign treated as a hard one.

    The corpus prints the same surname both ways and the smoke test found this
    costing real matches -- `Легать` 19x, `Сень-Леонъ` 7x, `Мендесь` 6x, all of
    which are the `-ъ` forms set with `ь`. Pre-reform orthography is unstable by
    nature, so this is a spelling variant to absorb, not an error to flag. Only
    the FINAL sign is touched; `ь` inside a word is meaningful (Васильевъ).
    Applied symmetrically to the dictionary and the text, so it can never
    introduce a match the other side would not also admit.
    """
    f = fold(s)
    # applied per hyphen component, because the sign also ends an inner one --
    # the corpus prints both `Сень-Леонъ` and `Сенъ-Леонъ` for the same man
    return "-".join(c[:-1] if c.endswith("ь") else c for c in f.split("-"))


def reflow(text: str) -> str:
    """Rejoin words the printed line break split, then collapse whitespace."""
    return WS.sub(" ", HYPHEN_BREAK.sub(r"\1", text)).strip()


# --------------------------------------------------------- form generation

# Pre-reform masculine adjectival genitive is -аго where modern Russian has
# -ого; both are generated because the corpus prints both.
ADJ_M = ["ий", "аго", "ого", "ому", "им", "ом", "ие", "их", "ими"]
ADJ_F = ["ая", "ой", "ую", "ою", "ыя", "ых"]
POSS_M = ["", "а", "у", "ым", "ом", "е", "ы", "ых"]
POSS_F = ["а", "ой", "у", "ою", "ы"]
CONS_M = ["", "а", "у", "ом", "е", "ы"]
VOWEL_A = ["а", "ы", "е", "у"]
# A stem that ended in ь is soft and takes -я/-ю/-емъ: Гертель -> Гертеля.
SOFT_M = ["", "я", "ю", "ем", "е", "и"]
# After ц ж ч ш щ the instrumental is -емъ, never -омъ: Вальцъ -> Вальцемъ.
SIB_M = ["", "а", "у", "ем", "е", "ы"]
SIBILANT = ("ц", "ж", "ч", "ш", "щ")
# Feminine -я nouns, which is how most fairy/spirit roles are named: Фея -> Феи.
VOWEL_YA = ["я", "и", "е", "ю", "ей"]
# genuinely indeclinable in standard Russian -- but see the -и note below
INDECL_TAIL = ("о", "у", "э", "ю")


def surname_forms(canonical: str, both_genders: bool = True) -> set[str]:
    """Plausible declined forms of a surname, folded.

    Deliberately slightly over-generative: a spurious form costs a candidate in
    `candidates_n`, which context then has to disambiguate, whereas a missing
    form costs the mention outright and silently.
    """
    base = key_of(canonical)
    if not base:
        return set()
    # softness is lost by key_of (which drops the final ь), so read it first
    soft = fold(canonical).split("-")[-1].endswith("ь")
    out = {base}

    def add(stem: str, endings: list[str]) -> None:
        out.update(stem + e for e in endings)

    if base.endswith(("ский", "цкий", "ской", "цкой", "ый", "ий")):
        stem = base[:-2] if base.endswith(("ий", "ый")) else base[:-2]
        add(stem, ADJ_M)
        # The same SURNAME occurs in both genders, so a person's forms span
        # both. A WORK title does not: the opera `Дубровскій` appears as
        # `Дубровскаго`, never as `Дубровская` -- and generating the feminine
        # made that title match the dancer Дубровская, who is simply absent
        # from research.person. Callers indexing titles pass both_genders=False.
        if both_genders:
            add(stem, ADJ_F)
    elif base.endswith(("ская", "цкая", "ая")):
        add(base[:-2], ADJ_F)
        if both_genders:
            add(base[:-2], ADJ_M)
    elif base.endswith(("ова", "ева", "ина", "ына")):
        add(base[:-1], POSS_F)
        if both_genders:
            add(base[:-1], POSS_M)
    elif base.endswith(("ов", "ев", "ин", "ын")):
        add(base, POSS_M)
        if both_genders:
            add(base, POSS_F)
    elif soft:
        add(base, SOFT_M)          # Гертель -> Гертеля, Гертелемъ
    elif base.endswith(INDECL_TAIL):
        pass                       # Дриго, Петренко -- indeclinable
    elif base.endswith("и"):
        # standard Russian leaves these alone, but this corpus declines them:
        # `Гримальди` is printed `Гримальды` in the genitive
        add(base, ["", "ы"])
        add(base[:-1], ["и", "ы"])
    elif base.endswith("я"):
        add(base[:-1], VOWEL_YA)
    elif base.endswith("а"):
        add(base[:-1], VOWEL_A)
    elif base.endswith(SIBILANT):
        add(base, SIB_M)
    else:
        add(base, CONS_M)
    return {f for f in out if len(f) >= 3}


# A title that opens with an act, scene or date specification is an excerpt
# record, whether or not `excerpt_of_work_id` was ever populated for it. Issue
# #88 linked most excerpts but left some unlinked, and those unflagged rows made
# their parent's bare title ambiguous: `6 и 7 март. бал. Конекъ-Горбунокъ` and
# `2-е х. бал. Лебединое озеро` both carry excerpt_of_work_id = NULL.
EXCERPT_SHAPE = re.compile(
    r"^\s*(\d+[\s-]*(и|,)?\s*\d*\s*-?[ехя]?\s*"
    r"(д|дѣйств|действ|карт|акт|сц|х|март|январ|феврал|апрѣл|ма[яй]|"
    r"іюн|іюл|август|сентябр|октябр|ноябр|декабр)\w*\.?|"
    r"изъ\s+(бал|оп)|отрывк|сюита\s+изъ|сцена\s+изъ|"
    r"\d+-[ея]\s+(карт|д))", re.I)


# The more robust test: an inline genre abbreviation with anything before it.
# A parent work is titled `Конекъ-горбунокъ`; an excerpt record is titled
# `3-е и4-е д. бал. Конекъ-горбунокъ`. Enumerating act patterns alone missed
# that one, because `и4-е` has no space after the conjunction.
INLINE_GENRE = re.compile(r"\S.*\b(бал|оп|ком|др|феер|траг)\.\s*\S", re.I)


def excerpt_shaped(title: str) -> bool:
    t = (title or "").strip()
    return bool(EXCERPT_SHAPE.match(t) or INLINE_GENRE.match(t))


SQUASH = re.compile(r"[\s\-–—'’.]+")


def squash(s: str) -> str:
    """A title key with hyphens, spaces and dots removed.

    The print is not consistent about them and neither is the transcription:
    `Конекъ-Горбунокъ` also appears as `Конекъ Горбунокъ` and `Конекъгорбунокъ`,
    `Донъ-Кихотъ` as `Донъ Кихотъ` and `ДонъКихотъ`. Consulted only after the
    exact key fails, and recorded as its own link_method so it stays auditable.
    """
    return SQUASH.sub("", key_of(s))


STEM_CHARS = 4


def stem_key(s: str) -> str:
    """Each word truncated to its first few letters, order preserved.

    Russian adjective+noun titles decline in BOTH words, which per-word form
    generation cannot reach: `Лебединое озеро` is printed `Лебединаго озера` and
    `Лебединомъ озерѣ`, `Тщетная предосторожность` as `Тщетной
    предосторожности`, `Евгеній Онѣгинъ` as `Евгенія Онѣгина`. Truncating each
    word collapses all of those onto one key. Four characters, not five: at five
    both `озера` and `озеро` survive intact and the inflection is never trimmed.
    Used only after the exact and squashed keys fail, requires at least two
    words so the key still carries ~8 characters of signal, and is reported as
    its own link_method.
    """
    parts = [w[:STEM_CHARS] for w in SQUASH.sub(" ", key_of(s)).split() if w]
    # Only multi-word titles. A single truncated word is far too lossy to match
    # on -- it linked «Хорошо» to `Хорошенькая` -- and single-word declension is
    # already covered by generating that word's forms.
    return " ".join(parts) if len(parts) >= 2 else ""


def title_forms(title: str) -> set[str]:
    """A work title, folded, plus its form without a leading genre abbreviation."""
    t = key_of(title).strip(" .,;:!?«»„“\"'")
    out = {t}
    # "бал. Щелкунчикъ", "2-я карт. бал. Конекъ-Горбунокъ" -> the title itself
    m = re.search(r"(?:бал|оп|ком|др|феер)\.\s*(.+)$", t)
    if m:
        out.add(m.group(1).strip())
    m = re.search(r"^\d+-[ея]\s+(?:карт|д|действ|акт)\w*\.?\s*(.*)$", t)
    if m and m.group(1):
        out.add(m.group(1).strip())
    # titles decline as readily as names -- «Пахиты», «Жизели», «Конька-горбунка»
    declined = set()
    for f in list(out):
        head, _, tail = f.rpartition(" ")
        if len(tail) >= 4:
            for d in surname_forms(tail, both_genders=False):
                declined.add((head + " " + d).strip() if head else d)
    return {f for f in out | declined if len(f) >= 3}


# ------------------------------------------------------------------ scanning

HONORIFIC = re.compile(
    r"(?<![А-Яа-яЀ-ЏёЁ])"
    r"(г-жи|г-жа|г-жъ|г-жею|г-же|гг\.|г-да|г-нъ|г\.|"
    r"восп-ца|восп-цы|восп-къ|уч-ца|уч-цы|уч-къ|в-ца|в-цы|в-къ|"
    r"арт\.|балерин\w*|танцовщиц\w*)\s*",
    re.I)
INITIALS = re.compile(r"(?:[А-ЯЀ-ЏІѲѴ]\.\s*){1,3}$")
TOKEN = re.compile(r"[А-Яа-яЀ-ЏЪѢІѲѴъѣіѳѵA-Za-zÀ-ÿ][\wА-Яа-яЀ-ЏЪѢІѲѴъѣіѳѵÀ-ÿ'’-]*")
SENT_END = re.compile(r"[.!?;:]\s*$")
QUOTED = re.compile(r"[«„\"]([^»“\"]{2,120})[»“\"]")
# Role—Performer, the cast-list grammar: em dash, en dash or hyphen-with-spaces
ROLE_PERF = re.compile(r"([А-ЯЀ-ЏІѲѴ][^—–\n;]{1,60}?)\s*[—–]\s*"
                       r"((?:г-жа|г-жи|г\.|гг\.|в-къ|восп-ца|уч-ца)?\s*"
                       r"[А-ЯЀ-ЏІѲѴ][\wА-Яа-яЀ-Џъѣіѳѵ'’-]+(?:\s+\d+-[яй])?)")
# a list keeps going across these
LIST_GLUE = re.compile(r"^\s*(,|и|и\s|;|\s)+$")


class Lexicon:
    """Folded form -> the entity ids that claim it."""

    def __init__(self) -> None:
        self.person: dict[str, list[str]] = collections.defaultdict(list)
        self.work: dict[str, list[str]] = collections.defaultdict(list)
        self.role: dict[str, list[str]] = collections.defaultdict(list)
        self.theater: dict[str, list[str]] = collections.defaultdict(list)
        self.work_squashed: dict[str, list[str]] = collections.defaultdict(list)
        self.work_stemmed: dict[str, list[str]] = collections.defaultdict(list)
        self.person_meta: dict[str, dict] = {}
        self.work_meta: dict[str, dict] = {}

    def add(self, index: dict, forms: set[str], eid) -> None:
        eid = str(eid)          # duckdb hands back UUID objects
        for f in forms:
            if eid not in index[f]:
                index[f].append(eid)


def build_lexicon(db: Path) -> Lexicon:
    import duckdb
    con = duckdb.connect(str(db), read_only=True)
    lex = Lexicon()

    for pid, fam, disp, ordn, first, last in con.execute("""
        select person_id, canonical_family_name, display_name, ordinal_suffix,
               first_attested_season, last_attested_season
        from research.person where canonical_family_name is not null""").fetchall():
        lex.person_meta[str(pid)] = {"family": fam, "display": disp, "ordinal": ordn,
                                "first_season": first, "last_season": last}
        lex.add(lex.person, surname_forms(fam), pid)

    # Every spelling the ROSTERS recorded for a person, not only the canonical
    # one. Entity resolution merges variants correctly -- `Балашева` and
    # `Балашова` are both Александра Балашова, printed both ways across the
    # years -- but research.person keeps one canonical form, so a review
    # printing the variant found nobody. Worse, the form generator then matched
    # `Балашева` to the MALE `Балашевъ` through its cross-gender forms, which is
    # exactly what the gender-contradiction check was catching: 20 of those 76
    # flags were this one ballerina. 949 spellings across 594 people were
    # invisible this way.
    #
    # An ordinal inside a variant (`Іогансонъ 1-й`) is stripped first, because
    # the ranker scores ordinals separately.
    n_variant = 0
    for pid, variant in con.execute("""
        select pl.person_id, pe.family_name
        from raw.person_entry pe
        join entities.person_link pl on pl.entry_id = pe.entry_id
        join research.person p on p.person_id = pl.person_id
        where pe.family_name is not null and pe.family_name <> ''
          and pe.family_name <> p.canonical_family_name
        group by 1, 2""").fetchall():
        bare = re.sub(r"\s*\d+-[яйе][яй]?\s*$", "", (variant or "").strip(" .,")).strip()
        if len(bare) < 3 or str(pid) not in lex.person_meta:
            continue
        lex.add(lex.person, surname_forms(bare), pid)
        n_variant += 1
    lex.n_variant_spellings = n_variant

    # Scan-verified spellings the ROSTERS never used, from
    # docs/eval/review_person_variants.csv. The rosters' own variants are
    # indexed above; this covers the other direction -- a review printing a
    # form no roster carries. Keyed on the canonical SURNAME, not a person_id,
    # because the review often gives no ordinal: `Соляниковъ` maps to
    # `Солянниковъ`, where the rosters hold two men, and the ranker chooses.
    #
    # Deliberately curated rather than inferred. Spreading variants across a
    # family automatically was tried and reverted: it fixed two cases and cost
    # 70 resolutions elsewhere, because it admits every family member as a
    # candidate for every mention.
    variants_path = Path("docs/eval/review_person_variants.csv")
    n_curated = 0
    if variants_path.exists():
        by_canon = collections.defaultdict(list)
        for q, meta in lex.person_meta.items():
            by_canon[(meta["family"] or "").strip()].append(q)
        with open(variants_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                printed = (row.get("printed_in_review") or "").strip()
                canon = (row.get("roster_canonical_family_name") or "").strip()
                if not printed or not canon:
                    continue
                for q in by_canon.get(canon, []):
                    lex.add(lex.person, surname_forms(printed), q)
                    n_curated += 1
    lex.n_curated_variants = n_curated



    for wid, title, genre, parent, is_excerpt in con.execute("""
        select work_id, canonical_title, canonical_genre, parent_genre,
               excerpt_of_work_id is not null
        from research.work where canonical_title is not null""").fetchall():
        lex.work_meta[str(wid)] = {
            "title": title, "genre": genre, "parent": parent,
            # the stored flag OR the title's own shape
            "is_excerpt": bool(is_excerpt) or excerpt_shaped(title),
        }
        # An excerpt row is indexed under its LITERAL title only. Its
        # genre/act-stripped reduction is by construction the parent's title --
        # `2-е д. бал. Коппелія` reduces to `коппелія` -- so generating that
        # form made every bare title ambiguous against its own excerpts:
        # «Коппелія» came back with 5 candidates, 4 of them its own act records.
        forms = ({key_of(title).strip(" .,;:!?«»„“\"'")}
                 if lex.work_meta[str(wid)]["is_excerpt"] else title_forms(title))
        lex.add(lex.work, forms, wid)
        for f in forms:
            sq = squash(f)
            if sq and str(wid) not in lex.work_squashed[sq]:
                lex.work_squashed[sq].append(str(wid))
            st = stem_key(f)
            if st and str(wid) not in lex.work_stemmed[st]:
                lex.work_stemmed[st].append(str(wid))

    for (role,) in con.execute("""
        select distinct role_name from raw.person_entry_credit
        where role_name is not null and role_name <> ''""").fetchall():
        base = key_of(role).strip(" .,;:")
        if len(base) < 3:
            continue
        # roles appear in oblique cases as often as not -- `въ роли Мирты`,
        # `Зюльме`, `Матильды` all surfaced as unknowns before this
        forms = {base}
        head, _, tail = base.rpartition(" ")
        target = tail if head else base
        for f in surname_forms(target):
            forms.add((head + " " + f).strip() if head else f)
        for f in forms:
            if len(f) >= 3 and str(role) not in lex.role[f]:
                lex.role[f].append(str(role))

    for tid, name in con.execute(
            "select theater_id, canonical_name from research.theater").fetchall():
        lex.add(lex.theater, surname_forms(name), tid)
    # institution vocabulary: adjectival, inflected, and absent from research.theater
    for name, tid in [("Императорскій", "INST:imperial"),
                      ("Маріинскій", "INST:mariinsky"),
                      ("Александринскій", "INST:alexandrinsky"),
                      ("Михайловскій", "INST:mikhailovsky"),
                      ("Эрмитажный", "INST:hermitage"),
                      ("Красносельскій", "INST:krasnoe_selo"),
                      ("Московскій", "INST:moscow"),
                      ("Петербургскій", "INST:petersburg")]:
        lex.add(lex.theater, surname_forms(name), tid)
    return lex


# ------------------------------------------------------------------- ranking

FEM_HON = {"г-жа", "г-жи", "г-жъ", "г-жею", "г-же", "восп-ца", "восп-цы",
           "уч-ца", "уч-цы", "в-ца", "в-цы", "балерина", "танцовщица"}
MASC_HON = {"г.", "гг.", "г-нъ", "г-да", "в-къ", "уч-къ", "восп-къ"}
FEM_CANON = ("ова", "ева", "ина", "ына", "ская", "цкая", "ая", "а")
MASC_CANON = ("овъ", "евъ", "инъ", "ынъ", "скій", "цкій", "ъ")
FEM_SURFACE = ("ая", "ой", "ую", "ою", "ой", "ы")
MASC_SURFACE = ("ій", "ый", "имъ", "аго", "ого", "ому", "омъ", "ъ", "ымъ")
SURFACE_ORDINAL = re.compile(r"(\d+)-([яй])")


def canon_gender(family: str) -> str | None:
    """Gender from the surname, ONLY where Russian actually marks it.

    The Slavic possessive and adjectival families inflect (-овъ/-ова,
    -скій/-ская) and are reliable. Nothing else is, and guessing from a final
    hard sign is actively harmful: `Ваземъ`, `Гейтенъ`, `Борхардтъ`, `Эрлеръ`,
    `Бастманъ`, `Мендесъ` are indeclinable and identical for both genders, and
    in this corpus they belong overwhelmingly to WOMEN -- Екатерина Ваземъ and
    Лидія Гейтенъ were among the period's leading ballerinas. An earlier
    version read the final `ъ` as masculine and penalised the correct candidate
    by 5 points; the smoke test surfaced 128 such mismatches, nearly all of
    them the rule's fault rather than the match's. `-а` is no safer: Петипа is
    a man.

    Returning None costs nothing -- the ranker simply scores no gender evidence
    and falls back to season and ordinal.
    """
    if family.endswith(("ская", "цкая")):
        return "f"
    if family.endswith(("скій", "цкій")):
        return "m"
    if family.endswith(("ова", "ева", "ина", "ына")):
        return "f"
    if family.endswith(("овъ", "евъ", "инъ", "ынъ")):
        return "m"
    return None


def surface_gender(surface: str, honorific: str) -> str | None:
    """Gender of the mention, from the honorific first and the ending second.

    The honorific is the reliable half -- `г-жа` vs `г.` is unambiguous, while
    an ending is not: `Павлова` is both the feminine nominative and the
    masculine genitive of `Павловъ`.
    """
    h = honorific.strip().lower()
    if h in FEM_HON:
        return "f"
    if h in MASC_HON:
        return "m"
    low = surface.strip()
    if low.endswith(("ая", "ую", "ою")):
        return "f"
    if low.endswith(("ій", "ый", "аго", "ого", "ому", "ымъ", "имъ")):
        return "m"
    return None


def season_covers(first: str | None, last: str | None, season: str) -> bool | None:
    """Whether a person was attested across this season. None when unknown."""
    if not first or not last or not season:
        return None
    return first <= season <= last


def rank_candidates(ids: list[str], surface: str, honorific: str, season: str,
                    lex: "Lexicon") -> tuple[str, int, str]:
    """Best candidate, its margin, and why. NEVER gates: a zero-scoring
    candidate set still returns the full list to the caller untouched.

    The design is explicit that season must rank rather than filter -- a hard
    season+ordinal gate left 15.5% of mentions with no candidate at all, since
    guest artists, roster gaps and ordinal mismatches are all common.
    """
    want_g = surface_gender(surface, honorific)
    # Compare the NUMBER only. `Павловой 2-й` is the oblique of the feminine
    # `Павлова 2-я`, so the literal suffix `2-й` looks masculine and an exact
    # string match penalised Anna Pavlova on her own mentions. Gender is scored
    # separately and separates `Легатъ 1-й` from `Легатъ 1-я` on its own.
    m = SURFACE_ORDINAL.search(surface)
    want_ord = m.group(1) if m else None

    # An ordinal is the roster's OWN disambiguator -- it exists precisely to
    # separate same-surname people -- so when the print gives one and exactly
    # one candidate carries it, that settles it. Scoring could not: Anna
    # Pavlova is attested in research.person for 1907-08 only, because that is
    # where the rosters place her, so on her mentions in every other season a
    # longer-serving Павлова drew level on the season bonus. 79 of her own
    # mentions were unresolved for that reason.
    if want_ord:
        exact = [pid for pid in ids
                 if re.sub(r"\D", "", (lex.person_meta.get(pid, {}).get("ordinal") or "")) == want_ord]
        if len(exact) == 1:
            g = canon_gender((lex.person_meta.get(exact[0], {}).get("family") or ""))
            if not (want_g and g and want_g != g):
                return exact[0], 99, "ordinal is unique among candidates"

    scored = []
    for pid in ids:
        meta = lex.person_meta.get(pid)
        if not meta:
            scored.append((0, pid, ""))
            continue
        score, why = 0, []
        meta_ord = re.sub(r"\D", "", meta.get("ordinal") or "") or None
        if want_ord and meta_ord:
            if meta_ord == want_ord:
                score += 6
                why.append("ordinal")
            else:
                score -= 4
        elif want_ord and not meta_ord:
            score -= 1
            why.append("ordinal-absent")
        elif not want_ord and meta_ord:
            score -= 2            # the print gives an ordinal when one is needed
        g = canon_gender(meta["family"] or "")
        if want_g and g:
            if want_g == g:
                score += 4
                why.append("gender")
            else:
                score -= 5
        cov = season_covers(meta.get("first_season"), meta.get("last_season"), season)
        if cov is True:
            score += 5
            why.append("season")
        elif cov is False:
            score -= 2            # ranked down, not excluded
        scored.append((score, pid, "+".join(why)))

    scored.sort(key=lambda x: -x[0])
    best = scored[0]
    margin = best[0] - (scored[1][0] if len(scored) > 1 else -99)
    return best[1], margin, best[2]


# ------------------------------------------------------------------- matching

ORDINAL = re.compile(r"\s*(\d+-[яйе][яй]?)")
# tokens that are grammatically capitalised but never a mention
STOP_CAPS = {"императорскихъ", "императорских", "его", "ея", "величества",
             "петербургъ", "петербург", "москва", "москвѣ", "москве",
             "россии", "россія", "росси", "театръ", "театр", "балет",
             "балетъ", "опера", "драма", "сезонъ", "сезон"}


def is_ballet_work(meta: dict) -> bool:
    if (meta.get("parent") or "") == "ballet":
        return True
    g = (meta.get("genre") or "").lower()
    return g.startswith(("бал", "ballet"))


def is_sentence_initial(text: str, start: int) -> bool:
    before = text[:start].rstrip()
    return not before or bool(SENT_END.search(before + " "))


def scan_block(text: str, block_type: str, lex: Lexicon,
               season: str = "", genre: str = "") -> tuple[list[dict], list[dict]]:
    """Mentions and unknown-name flags for one block of reflowed text."""
    mentions: list[dict] = []
    unknown: list[dict] = []
    claimed: set[tuple[int, int]] = set()

    def overlaps(a: int, b: int) -> bool:
        return any(not (b <= s or a >= e) for s, e in claimed)

    def emit(kind: str, a: int, b: int, ids: list[str], method: str,
             conf: str, evidence: str) -> None:
        claimed.add((a, b))
        eid = ids[0] if len(ids) == 1 else ""
        why = ""
        if kind == "work" and len(ids) > 1:
            # a printed title names the work, not one of its act records
            parents = [i for i in ids
                       if not lex.work_meta.get(i, {}).get("is_excerpt")]
            if len(parents) == 1:
                eid, method, why = parents[0], method + "+parent-work", "parent-work"
            elif len(parents) > 1 and genre == "Ballet":
                # Different art forms are deliberately different works here, so
                # `Донъ-Кихотъ [бал.]` and `Донъ-Кихотъ [героич. ком.]` are two
                # rows -- and inside a ballet review the ballet is the one meant.
                bal = [i for i in parents if is_ballet_work(lex.work_meta.get(i, {}))]
                if len(bal) == 1:
                    eid, method, why = bal[0], method + "+ballet-genre", "ballet-genre"
                else:
                    ids = parents
        if kind == "person" and len(ids) > 1:
            pick, margin, why = rank_candidates(ids, text[a:b], evidence, season, lex)
            # a decisive margin resolves; a tie leaves the candidate list standing
            if margin >= 4:
                eid, method = pick, method + "+ranked"
                # the print asked for an ordinal the chosen person does not
                # carry -- usually a roster gap, so do not present it as firm
                conf = "low" if "ordinal-absent" in why else "medium"
            else:
                why = f"tie(margin={margin})"
        if kind == "person" and eid:
            # A resolution whose gender CONTRADICTS the honorific is not a match
            # -- it is evidence that this family's other member is missing from
            # research.person. `Г-жа Галактіонова` resolving to `Галактіоновъ,
            # Павелъ Георгіевичъ` is a roster gap, not a link. Checked after
            # ranking as well as before it, because a family present only in one
            # gender can hold several same-gender candidates (Балашова x3) and
            # the ranker then penalises them all equally and still picks one.
            want_g = surface_gender(text[a:b], evidence)
            meta = lex.person_meta.get(eid)
            got_g = canon_gender((meta or {}).get("family") or "")
            if want_g and got_g and want_g != got_g:
                # Inside an honorific LIST, a contradiction means the list has
                # moved on to the other gender, not that someone is missing:
                # the print writes `г-жи A, B, Медалинскій` and lets the
                # honorific lapse. Медалинскій resolves correctly ~60 times
                # under `гг.`/`г.` and was flagged exactly once, here. So the
                # honorific is dropped as evidence and the match stands, rather
                # than being reported as an absent person.
                # ...but ONLY when the surface's own morphology agrees with
                # the entity, so that just the honorific is out of step.
                # `Медалинскій` is masculine by its ending and matches a
                # masculine entity -- only `г-жи` disagrees, so the honorific
                # lapsed. `Ефремова` is feminine by its ending AND by its
                # honorific, and matches a masculine entity: that is a real
                # contradiction and a genuinely absent woman, not a lapse.
                surf_morph = canon_gender(text[a:b].strip())
                if method.startswith("honorific-list") and surf_morph == got_g:
                    why, conf = "honorific lapsed in list", "medium"
                else:
                    unknown.append({
                        "surface": text[a:b], "normalised": fold(text[a:b]),
                        "evidence": f"{evidence} (db has {meta['family']})",
                        "rule": "gender-contradiction"})
                    eid, why, conf = "", "gender-contradiction", "low"
        mentions.append({
            "mention_type": kind, "char_start": a, "char_end": b,
            "surface": text[a:b], "normalised": fold(text[a:b]),
            "entity_id": eid,
            "candidates_n": len(ids),
            "candidate_ids": "|".join(ids[:8]),
            "link_method": method, "link_confidence": conf,
            "evidence": evidence, "rank_reason": why,
        })

    # 1. work titles -- explicitly marked by guillemets, so highest precision
    for m in QUOTED.finditer(text):
        inner = m.group(1).strip()
        a, b = m.start(1), m.end(1)
        key = key_of(inner).strip(" .,;:!?")
        ids = lex.work.get(key, [])
        if not ids:
            for alt in title_forms(inner):
                if alt in lex.work:
                    ids = lex.work[alt]
                    key = alt
                    break
        if not ids:
            sq = squash(inner)
            if sq and lex.work_squashed.get(sq):
                emit("work", a, b, lex.work_squashed[sq], "quoted-squashed",
                     "medium", "«…»")
                continue
            st = stem_key(inner)
            if st and lex.work_stemmed.get(st):
                emit("work", a, b, lex.work_stemmed[st], "quoted-stemmed",
                     "medium", "«…»")
                continue
        if ids:
            emit("work", a, b, ids, "quoted-exact" if len(ids) == 1 else "quoted-ambiguous",
                 "high", "«…»")
        elif DANCE_NUMBER.match(inner.strip()):
            emit("dance_number", a, b, [], "quoted-dance-number", "high", "«…»")
        else:
            emit("work", a, b, [], "quoted-unresolved", "medium", "«…»")

    # 2. roles -- only where the cast-list grammar supplies them
    if block_type in ("cast_list", "enumerated_list") or "—" in text or "–" in text:
        for m in ROLE_PERF.finditer(text):
            role_s, perf_s = m.group(1).strip(), m.group(2).strip()
            rk = key_of(role_s).strip(" .,;:")
            if rk in lex.role and not overlaps(m.start(1), m.end(1)):
                emit("role", m.start(1), m.end(1), lex.role[rk],
                     "cast-list", "high", "role—performer")

    # 3. people -- honorific-anchored list spans
    for h in HONORIFIC.finditer(text):
        pos = h.end()
        consumed = 0
        while pos < len(text) and consumed < 40:
            t = TOKEN.match(text, pos)
            if not t or not CAP.search(t.group()):
                break
            a, b = t.start(), t.end()
            o = ORDINAL.match(text, b)
            if o:
                b = o.end()
            key = key_of(t.group())
            if overlaps(a, b):
                # already matched by the quoted-title or cast-list pass; an
                # overlapping token is not evidence of an unknown name, and
                # falling through to the unknown branch here manufactured one
                # (Зюльме, Монна, Матильда are all IN the role dictionary)
                consumed += 1
                pos = b
                glue = re.match(r"\s*(?:,|и|;)\s*", text[pos:])
                if not glue:
                    break
                pos += glue.end()
                continue
            ids = lex.person.get(key, [])
            if ids:
                emit("person", a, b, ids, "honorific-list", "high",
                     h.group(1).strip())
            elif key in lex.theater:
                # `артистовъ Императорскихъ Московскихъ театровъ` sits inside an
                # honorific span but names an institution, not a person
                emit("theater", a, b, lex.theater[key], "honorific-span-institution",
                     "medium", h.group(1).strip())
            elif key in lex.role:
                emit("role", a, b, lex.role[key], "honorific-span-role",
                     "medium", h.group(1).strip())
            elif key not in STOP_CAPS and len(key) >= 3:
                unknown.append({"surface": text[a:b], "normalised": key,
                                "evidence": h.group(1).strip(),
                                "rule": "honorific-anchored"})
                claimed.add((a, b))
            consumed += 1
            pos = b
            glue = re.match(r"\s*(?:,|и|;)\s*", text[pos:])
            if not glue:
                break
            pos += glue.end()

    # 4. people, works and institutions -- bare capitalised tokens
    for t in TOKEN.finditer(text):
        a, b = t.start(), t.end()
        if overlaps(a, b) or not CAP.search(t.group()):
            continue
        key = key_of(t.group())
        if key in STOP_CAPS or len(key) < 3:
            continue
        initial_led = bool(INITIALS.search(text[max(0, a - 12):a]))
        if key in lex.theater:
            emit("theater", a, b, lex.theater[key], "bare", "medium", "")
        elif key in lex.person:
            if is_sentence_initial(text, a) and not initial_led:
                emit("person", a, b, lex.person[key], "bare-sentence-initial",
                     "low", "sentence start")
            else:
                emit("person", a, b, lex.person[key], "bare",
                     "high" if initial_led else "medium",
                     "preceded by initials" if initial_led else "")
        elif key in lex.work:
            emit("work", a, b, lex.work[key], "bare", "medium", "")
        elif initial_led:
            unknown.append({"surface": text[a:b], "normalised": key,
                            "evidence": text[max(0, a - 12):a].strip(),
                            "rule": "follows-initials"})
    return mentions, unknown


# RG's original statement of purpose named "musical numbers" alongside people,
# ballets and roles. These are those: individual dance numbers, named in French,
# which are not works in research.work and should not be reported as unresolved
# ones. They are a population with no table yet, like composers were.
DANCE_NUMBER = re.compile(
    r"^(pas\b|grand pas|scène|scene|valse|variation|coda|adagio|galop|"
    r"mazurka|czardas|csardas|tarantelle|divertissement|entrée|ballabile|"
    r"danse|polka|bolero|boléro|jota|saltarelle|pizzicato)", re.I)

BALLET_CONTEXT = re.compile(
    r"балет|танц|пляск|дивертисм|кордебалет|балерин|хореограф|pas\b|балетмейстер",
    re.I)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews-dir", required=True, type=Path)
    ap.add_argument("--db", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--genre", default="Ballet")
    ap.add_argument("--seasons", default="",
                    help="comma-separated, for a smoke test; default all")
    ap.add_argument("--limit-pages", type=int, default=0)
    a = ap.parse_args()

    lex = build_lexicon(a.db)
    n_forms = len(lex.person)
    print(f"  + {getattr(lex, 'n_variant_spellings', 0):,} roster variant spellings indexed")
    print(f"  + {getattr(lex, 'n_curated_variants', 0):,} scan-verified review variants "
          f"(docs/eval/review_person_variants.csv)")
    print(f"lexicon: {n_forms:,} person forms from {len(lex.person_meta):,} persons, "
          f"{len(lex.work):,} work forms from {len(lex.work_meta):,} works, "
          f"{len(lex.role):,} roles, {len(lex.theater):,} institution forms")

    with open(a.reviews_dir / "review_page.csv", encoding="utf-8") as f:
        pages = {r["page_id"]: r for r in csv.DictReader(f)}
    want = {s.strip() for s in a.seasons.split(",") if s.strip()}
    keep = {pid: p for pid, p in pages.items()
            if (not a.genre or p["genre"] == a.genre)
            and (not want or p["season"] in want)}
    if a.limit_pages:
        keep = dict(sorted(keep.items())[:a.limit_pages])

    rows: list[dict] = []
    unknowns: list[dict] = []
    n_blocks = 0
    with open(a.reviews_dir / "review_block.csv", encoding="utf-8") as f:
        for b in csv.DictReader(f):
            page = keep.get(b["page_id"])
            if not page:
                continue
            raw = b["text"] or b["caption_text"] or ""
            if not raw.strip():
                continue
            text = reflow(raw)
            n_blocks += 1
            ms, us = scan_block(text, b["block_type"], lex, page["season"],
                                page["genre"])
            ballet_ctx = bool(BALLET_CONTEXT.search(text))
            for m in ms:
                m.update(page_id=b["page_id"], block_id=b["block_id"],
                         season=page["season"], city=page["city"])
                rows.append(m)
            for u in us:
                u.update(page_id=b["page_id"], block_id=b["block_id"],
                         season=page["season"], city=page["city"],
                         ballet_context=ballet_ctx)
                unknowns.append(u)

    a.out_dir.mkdir(parents=True, exist_ok=True)
    mcols = ["mention_type", "season", "city", "page_id", "block_id",
             "char_start", "char_end", "surface", "normalised", "entity_id",
             "candidates_n", "candidate_ids", "link_method", "link_confidence",
             "evidence", "rank_reason"]
    with open(a.out_dir / "review_mention.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mcols)
        w.writeheader()
        w.writerows(rows)

    agg: dict[str, dict] = {}
    for u in unknowns:
        e = agg.setdefault(u["normalised"], {
            "normalised": u["normalised"], "surface_examples": set(),
            "n": 0, "seasons": set(), "rules": set(), "ballet_context_n": 0})
        e["surface_examples"].add(u["surface"])
        e["n"] += 1
        e["seasons"].add(u["season"])
        e["rules"].add(u["rule"])
        e["ballet_context_n"] += 1 if u["ballet_context"] else 0
    with open(a.out_dir / "review_mention_unknown.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["normalised", "occurrences", "ballet_context_occurrences",
                    "seasons", "rules", "surface_examples"])
        for e in sorted(agg.values(), key=lambda x: -x["n"]):
            w.writerow([e["normalised"], e["n"], e["ballet_context_n"],
                        " ".join(sorted(e["seasons"])), "|".join(sorted(e["rules"])),
                        " | ".join(sorted(e["surface_examples"])[:5])])

    # An unresolved title that is one or two letters away from a real work is a
    # candidate TRANSCRIPTION error, not a missing work. Reported, never
    # applied: a near-miss has to be checked against the scan, and this corpus
    # spells the same thing several ways on purpose.
    import difflib
    canon = {m["title"]: wid for wid, m in lex.work_meta.items()}
    folded_canon = {key_of(t): t for t in canon}
    near: list[tuple] = []
    seen_unres: dict[str, int] = collections.Counter(
        r["surface"] for r in rows if r["link_method"] == "quoted-unresolved")
    for surf, n in seen_unres.items():
        k = key_of(surf)
        if len(k) < 5:
            continue
        hit = difflib.get_close_matches(k, folded_canon.keys(), n=1, cutoff=0.82)
        if hit and hit[0] != k:
            near.append((n, surf, folded_canon[hit[0]],
                         round(difflib.SequenceMatcher(a=k, b=hit[0]).ratio(), 3)))
    near.sort(key=lambda x: (-x[0], -x[3]))
    side = a.out_dir / "review_title_candidate_misreads.csv"
    with open(side, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["occurrences", "printed_in_review", "closest_known_work",
                    "similarity"])
        w.writerows(near)

    # Work rows that a single printed title cannot choose between, and that
    # differ only in spelling -- `Привалъ кавалеріи` / `Привалъ кавалерія`
    # (59 appearances vs 1), `Фея куколъ` / `Фея куколь` (54 vs 3). These are
    # consolidation questions for the entity layer, not matching questions, so
    # they are reported rather than settled by a prominence guess.
    dup_rows: list[tuple] = []
    seen_sets: set[tuple] = set()
    for r in rows:
        if r["mention_type"] != "work" or r["entity_id"] or r["candidates_n"] < 2:
            continue
        ids = tuple(sorted(i for i in (r["candidate_ids"] or "").split("|") if i))
        if not ids or ids in seen_sets:
            continue
        seen_sets.add(ids)
        metas = [lex.work_meta.get(i, {}) for i in ids]
        genres = [(m.get("genre") or "-") for m in metas]
        # Candidates differing only in SPELLING are consolidation candidates;
        # candidates differing in GENRE are the deliberate "different art forms
        # are different works" policy (Карменъ is both оп. and бал.) and must
        # not be merged. Saying which is which keeps this list actionable.
        kind = ("spelling-variant?" if len(set(genres)) == 1
                else "art-form split (deliberate)")
        dup_rows.append((
            r["surface"], kind, len(ids),
            " | ".join(f"{m.get('title') or '?'} [{g}]"
                       for m, g in zip(metas, genres)),
            "|".join(ids)))
    dup_path = a.out_dir / "review_work_consolidation_candidates.csv"
    with open(dup_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["printed_in_review", "verdict", "n_candidates",
                    "colliding_rows", "work_ids"])
        w.writerows(sorted(dup_rows, key=lambda x: (x[1], -x[2])))

    by_type = collections.Counter(r["mention_type"] for r in rows)
    by_method = collections.Counter(r["link_method"] for r in rows)
    resolved = sum(1 for r in rows if r["entity_id"])
    ambiguous = sum(1 for r in rows if r["candidates_n"] > 1)
    unres = sum(1 for r in rows if r["candidates_n"] == 0)
    print(f"\n{len(keep):,} pages | {n_blocks:,} blocks -> {len(rows):,} mentions")
    print(f"  resolved to one entity : {resolved:,} ({100*resolved/max(len(rows),1):.1f}%)")
    print(f"  ambiguous (>1 candidate): {ambiguous:,}")
    print(f"  unresolved (0)         : {unres:,}")
    print("\n  by type:   " + "  ".join(f"{k} {v:,}" for k, v in by_type.most_common()))
    print("  by method: " + "  ".join(f"{k} {v:,}" for k, v in by_method.most_common()))
    print(f"\nunknown names: {len(agg):,} distinct forms, "
          f"{sum(e['n'] for e in agg.values()):,} occurrences "
          f"-> {a.out_dir / 'review_mention_unknown.csv'}")
    print(f"work-consolidation candidates: {len(dup_rows):,} collision sets "
          f"-> {dup_path}")
    print(f"candidate title misreads: {len(near):,} forms "
          f"({sum(n for n, *_ in near):,} occurrences) -> {side}")
    print("  NOT applied -- each needs checking against the scan")


if __name__ == "__main__":
    main()
