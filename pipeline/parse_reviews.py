"""Stage 3 of the season-reviews pipeline: parse the raw JSON responses,
validate against the pydantic contract, apply deterministic repairs, and
write flat CSVs.

Reads only files already on disk, so it is free to re-run. Every convention
change lands here rather than in the (paid, non-deterministic) extraction
step -- the flatten-boundary discipline from CLAUDE.md.

Deterministic repairs applied here, rather than by spending more prompt:

* Empty `figure` blocks are dropped. The model reliably sets
  `tailpiece_present` AND also emits a contentless figure block for a
  decorative ornament (known_issues_reviews.md #3). The block carries no
  text, but it inflates block counts, and block structure is compared
  separately in the eval (docs/season_reviews.md §11).

* Gap spans carrying text are contradictory -- a gap means no reading was
  offered. The text is kept and the gap flag cleared, since discarding a
  reading the model did produce would lose more than it gains.

Usage:
    python pipeline/parse_reviews.py --manifest outputs/reviews/manifest.csv \
        --raw-dir outputs/reviews/raw --out-dir outputs/reviews/parsed
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent))
from schemas.review import ReviewPageLLM, flatten_review_page, page_plain_text

TABLES = ("review_page", "review_block", "review_span")


def repair(page: ReviewPageLLM) -> tuple[ReviewPageLLM, list[str]]:
    notes = []
    kept = []
    for b in page.blocks:
        if b.block_type == "figure" and not b.spans and not b.caption:
            notes.append("dropped_empty_figure_block")
            continue
        for s in b.spans + b.caption:
            if s.gap and s.text:
                s.gap = False
                notes.append("gap_span_had_text_kept_text")
        kept.append(b)
    page.blocks = kept
    return page, notes


# A backslash that is not the start of a valid JSON escape. Seen once in
# 600 pilot calls (2026-09-25): the model wrote "съ\нимъ" where it meant
# "съ\nнимъ" -- CYRILLIC н in place of Latin n inside the escape sequence
# itself. A homoglyph error in the JSON syntax, not in the transcription.
# Left alone it costs the whole page: json.loads raises and the extraction
# is discarded. At ~1 in 600 that is roughly five pages of a 3,072-call
# full run, so it is worth repairing rather than re-paying for.
BAD_ESCAPE = re.compile(r'\\(?![\"\\/bfnrtu])')


def repair_json_escapes(text: str) -> tuple[str, int]:
    """Make an otherwise-valid response parseable. Returns (text, n_fixed).

    Cyrillic н (and Latin-lookalike т/р/с) directly after a backslash is
    read as a mangled \n and restored as a newline, keeping the character
    that follows. Any other invalid escape has the stray backslash dropped,
    which loses nothing but the backslash.

    Every repair is logged, and the page is flagged so it can be eyeballed
    -- this guesses at intent, and a guess belongs in front of a human."""
    n = 0

    def fix(m: re.Match) -> str:
        nonlocal n
        n += 1
        nxt = text[m.end():m.end() + 1]
        return "\\n" if nxt == "\u043d" else ""      # н -> newline, else drop

    return BAD_ESCAPE.sub(fix, text), n


# Latin letters the model substitutes for Cyrillic. Not lookalikes -- these
# are TRANSLITERATION slips: it writes the Latin letter for the same sound.
# Measured over the 600-response pilot: d->д 84x, g->г 16x, r->р 15x, v->в
# 10x, plus the true homoglyphs. Deliberately EXCLUDED as ambiguous: s
# (с/з/ш), h (н/х), b (в/ь), u (и/у) -- guessing those would invent readings.
# NOTE: "c" is deliberately ABSENT. It is not an unambiguous counterpart --
# it stands for с, ц or к depending on the word, and guessing one produced
# real errors: `tancovaли` became `тансовали` (should be `танцовали`) and
# `cапельмейстера` became `сапельмейстера` (should be `капельмейстера`, which
# is still in the corpus from an earlier run). A word containing a stray `c`
# now goes to the scan instead. Same reasoning as "s" (с/з/ш), "h" (н/х),
# "b" (в/ь) and "u" (и/у), which were never in this map.
LATIN_TO_CYRILLIC = {
    "a": "а", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
    "k": "к", "t": "т", "n": "н", "m": "м", "d": "д", "g": "г", "v": "в",
    "z": "з", "r": "р", "i": "і", "l": "л", "f": "ф",
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М",
    "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У", "G": "Г", "D": "Д",
}
# Greek lookalikes. The model reaches for these less often than Latin ones, but
# when it does they are invisible to a Latin-only test: `Тугоуховскій` came back
# as `Тугουховскій` (omicron + upsilon) and `Конекъ-Горбунокъ` as
# `Горбуноκъ` (kappa). Only unambiguous visual counterparts are listed; Greek
# nu is omitted because it looks like Latin v, not Cyrillic н.
GREEK_TO_CYRILLIC = {
    "\u03b1": "а", "\u03b5": "е", "\u03b9": "і", "\u03ba": "к", "\u03bc": "м",
    "\u03bf": "о", "\u03c1": "р", "\u03c4": "т", "\u03c5": "у", "\u03c7": "х",
    "\u0391": "А", "\u0392": "В", "\u0395": "Е", "\u0397": "Н", "\u0399": "І",
    "\u039a": "К", "\u039c": "М", "\u039f": "О", "\u03a1": "Р", "\u03a4": "Т",
    "\u03a5": "У", "\u03a7": "Х",
}

FOREIGN_TO_CYRILLIC = {**LATIN_TO_CYRILLIC, **GREEK_TO_CYRILLIC}

# Cyrillic letters with no Latin or Greek lookalike. One of these in a word is
# proof the word is Russian, which is what the ratio test below cannot
# establish on its own: `Чумаkova` is 4 Cyrillic against 4 Latin and fails any
# ratio, yet `ч` settles it -- no French, Italian, German or Latin word
# contains one. That matters because the romanisation is often a whole SUFFIX
# (-kova, -dova, -ketti), not a stray letter.
CYRILLIC_ONLY = set("бгджзийлпфцчшщъыьэюяѣѳѵБГДЖЗИЙЛПФЦЧШЩЪЫЬЭЮЯѢѲѴ")

# Latin `i` is NOT an unambiguous counterpart: pre-reform Russian writes both
# `і` and `и`, and the convention (і before a vowel or й) is a tendency this
# corpus does not keep consistently -- the standing rule here is that a
# pattern is a worklist, never a norm. Mapping it blindly to `і` produced
# `Чекетті` and `Гримальді` where the print has `и`. So `i` counts as certain
# only where the convention is unambiguous, and is referred to the scan
# otherwise.
I_BEFORE = set("аеиоуыэюяѣіaeiouy" + "й")


def _i_is_certain(word: str, idx: int) -> bool:
    nxt = word[idx + 1] if idx + 1 < len(word) else ""
    return nxt.lower() in I_BEFORE and nxt != ""

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
LATIN_RE = re.compile(r"[A-Za-z\u0391-\u03c9]")
# a word split by a printed line break: `Чума-\n kova`
HYPHEN_BREAK_RE = re.compile(r"([^\s\u2014\u2013-]+)-(\s*\n\s*)([^\s\u2014\u2013-]+)")
# two words run together across a script boundary, e.g. `HermitageЛ. Бакстъ`,
# `М. ПетипаLouis XV`. Not a letter error -- a missing space -- so it is
# reported and left alone rather than mangled into Cyrillic.
SCRIPT_BOUNDARY_RE = re.compile(
    r"(?:[a-z\u00e0-\u00ff]{3,}[\u0410-\u042F]|[\u0430-\u044F]{3,}[A-Z])")
WORD_RE = re.compile(r"[^\s\u2014\u2013,;:.!?()\u00ab\u00bb\u201e\u201c]+")

# RG's rule -- never mix the scripts inside one word -- has exactly ONE
# genuine exception in this corpus: a Roman numeral with a Cyrillic suffix
# ("III-е", "II-й"). Roman numerals are Latin here by RG's own gold ruling,
# because Cyrillic І is glyph-identical but makes the text unsearchable.
#
# I briefly added a second exception for a French particle hyphenated to a
# Russian surname ("de-Бріена", "de-Вантадуръ") and it was WRONG. Checking
# 1897-98_SP_ballet_p027 against the scan: the page prints Cyrillic
# "де-Бріена" in all five places, and Latin "de-" was the model's own
# substitution. The exception would have protected the very error it should
# repair. These are real French names -- Jean de Brienne and Bernart de
# Ventadorn, troubadours in Raymonda -- but the yearbook sets them in
# Cyrillic.
ROMAN_SUFFIXED = re.compile(r"^[IVXLCDM]+[-\u2013\u2014][\u0400-\u04FF]+$")


def repair_mixed_script(text: str) -> tuple[str, list[str]]:
    """Report EVERY word mixing Cyrillic and Latin; repair only the certain ones.

    RG, 2026-09-25: "definitely don't mix Cyrillic and latin letters in one
    word", and then: "I'd rather be suspicious of all mixed Cyrillic/latin
    words, then discard the false positives."

    So nothing is silently exempted. Every mixed word produces a line, tagged
    by what was done with it:

      repaired   -- one stray Latin letter in a word of 2+ Cyrillic, or
                    Cyrillic outnumbering Latin 3:1, and every stray letter
                    has an unambiguous counterpart. The text IS changed.
      unresolved -- mixed, but the fix is not obvious: a half-and-half word,
                    or a letter that could map several ways (s -> с/з/ш,
                    h -> н/х, b -> в/ь, u -> и/у). Text left alone.
      split-*    -- the same three verdicts for a word the printed line
                    break cut in half. Checked FIRST and separately, because
                    neither half is mixed on its own (`Чума-` is clean
                    Cyrillic, `kova` clean Latin) so the per-token pass is
                    blind to them. 56 of the 77 found later were this shape.
      boundary   -- two words run together across a script change
                    (`HermitageЛ. Бакстъ`, `М. ПетипаLouis XV`). A missing
                    space, not a letter error, so the text is left alone.
      roman      -- a Roman numeral with a Cyrillic suffix ("III-е", "II-й"),
                    which is correct: Roman numerals are Latin here by RG's
                    gold ruling, since Cyrillic І is glyph-identical but
                    makes the text unsearchable. Text left alone, still
                    reported so she can confirm rather than trust me.

    An earlier version exempted French particles hyphenated to Russian
    surnames ("de-Бріена") without reporting them. That was wrong twice
    over: the scan shows the page prints CYRILLIC "де-Бріена" throughout, so
    the exemption protected the very error it should fix -- and because it
    was silent, nothing would have surfaced the mistake."""
    fixes: list[str] = []

    def fix_word(m: re.Match) -> str:
        w = m.group(0)
        cyr = len(CYRILLIC_RE.findall(w))
        lat = LATIN_RE.findall(w)
        if not cyr or not lat:
            return w                                  # single script
        if ROMAN_SUFFIXED.match(w):
            fixes.append(f"roman {w!r} -- left as printed, confirm")
            return w
        if SCRIPT_BOUNDARY_RE.search(w):
            # two words run together, not one word with a stray letter
            fixes.append(f"boundary {w!r} -- missing space, CHECK THIS PAGE")
            return w
        russian = any(c in CYRILLIC_ONLY for c in w)
        amb_i = any(c in "iI" and not _i_is_certain(w, k)
                    for k, c in enumerate(w))
        certain = ((len(lat) == 1 and cyr >= 2) or cyr >= 3 * len(lat) or russian) \
                  and all(c in FOREIGN_TO_CYRILLIC for c in lat) and not amb_i
        if not certain:
            fixes.append(f"unresolved {w!r} -- CHECK THIS PAGE")
            return w
        out = "".join(FOREIGN_TO_CYRILLIC.get(c, c) for c in w)
        fixes.append(f"repaired {w!r} -> {out!r}")
        return out

    # PASS 1 -- words the printed line break split in two. Run first, because
    # neither half looks wrong on its own: `Чума-` is clean Cyrillic and `kova`
    # is clean Latin, so the per-token pass below cannot see the problem at all.
    # This was not a hypothetical: 56 of the 77 mixed-script words the review
    # quality check later found were of exactly this shape, invisible here.
    # The halves are repaired IN PLACE -- the hyphen and the line break stay,
    # because the raw layer keeps the printed lineation and only the reading
    # layer reflows.
    def fix_split(m: re.Match) -> str:
        head, gap, tail = m.group(1), m.group(2), m.group(3)
        joined = head + tail
        cyr = len(CYRILLIC_RE.findall(joined))
        lat = LATIN_RE.findall(joined)
        if not cyr or not lat:
            return m.group(0)
        if ROMAN_SUFFIXED.match(joined) or SCRIPT_BOUNDARY_RE.search(joined):
            fixes.append(f"split-boundary {joined!r} -- CHECK THIS PAGE")
            return m.group(0)
        russian = any(c in CYRILLIC_ONLY for c in joined)
        amb_i = any(c in "iI" and not _i_is_certain(joined, k)
                    for k, c in enumerate(joined))
        certain = ((len(lat) == 1 and cyr >= 2) or cyr >= 3 * len(lat) or russian) \
                  and all(c in FOREIGN_TO_CYRILLIC for c in lat) and not amb_i
        if not certain:
            fixes.append(f"split-unresolved {joined!r} -- CHECK THIS PAGE")
            return m.group(0)
        fix = lambda part: "".join(FOREIGN_TO_CYRILLIC.get(c, c) for c in part)
        out_h, out_t = fix(head), fix(tail)
        fixes.append(f"split-repaired {joined!r} -> {out_h + out_t!r}")
        return f"{out_h}-{gap}{out_t}"

    text = HYPHEN_BREAK_RE.sub(fix_split, text)
    return WORD_RE.sub(fix_word, text), fixes


def load_folio_corrections(path: Path) -> dict[str, str]:
    """Hand-verified printed_folio overrides, applied at PARSE time.

    raw/*.raw.json is the model's response and the reproducibility record --
    CLAUDE.md: "verbatim, never hand-edited". So corrections live in a CSV
    that is applied on the way out, exactly like the tabular pipeline puts
    fixes in `analysis` rather than `raw`. Re-parsing is free, so a
    correction costs nothing and can be withdrawn by deleting a row.

    An empty printed_folio column means "this page carries NO printed folio"
    -- which is a real and common answer: full-page plates are unpaginated,
    and the model sometimes invents a number from the caption instead.
    """
    if not path or not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["page_id"]: r["printed_folio"].strip()
                for r in csv.DictReader(f) if r.get("page_id")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--folio-corrections", type=Path,
                    default=Path("docs/review_folio_corrections.csv"),
                    help="hand-verified printed_folio overrides; applied at "
                         "parse time so raw/ is never edited. Pass a "
                         "nonexistent path to disable.")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    out = {t: [] for t in TABLES}
    folio_fixes = load_folio_corrections(args.folio_corrections)
    errors, repairs = [], []
    n_ok = n_missing = n_failed = n_folio_fixed = 0

    for r in rows:
        page_id = r["page_id"]
        raw_path = args.raw_dir / f"{page_id}.raw.json"
        if not raw_path.exists():
            n_missing += 1
            continue
        text = raw_path.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            fixed, n_esc = repair_json_escapes(text)
            try:
                data = json.loads(fixed)
            except json.JSONDecodeError as e:
                n_failed += 1
                errors.append({"page_id": page_id, "stage": "json",
                               "error": f"{type(e).__name__}: {e}"})
                continue
            repairs.append({"page_id": page_id,
                            "repair": f"json_escape_repair: {n_esc} invalid "
                                      f"escape(s) -- CHECK THIS PAGE"})
        try:
            page = ReviewPageLLM.model_validate(data)
        except ValidationError as e:
            n_failed += 1
            errors.append({"page_id": page_id, "stage": "schema",
                           "error": str(e).replace("\n", " | ")[:800]})
            continue

        page, notes = repair(page)
        for note in notes:
            repairs.append({"page_id": page_id, "repair": note})

        mixed: list[str] = []
        for blk in page.blocks:
            for sp in list(blk.spans) + list(blk.caption):
                if sp.text:
                    sp.text, f = repair_mixed_script(sp.text)
                    mixed += f
        for f in mixed:
            repairs.append({"page_id": page_id, "repair": f"mixed_script: {f}"})

        if page_id in folio_fixes:
            was = page.printed_folio
            page = page.model_copy(
                update={"printed_folio": folio_fixes[page_id] or None})
            repairs.append({"page_id": page_id,
                            "repair": f"folio_correction: {was!r} -> "
                                      f"{page.printed_folio!r}"})
            n_folio_fixed += 1

        flat = flatten_review_page(page_id, r["season"], r["city"], r["genre"], page)
        for t in TABLES:
            out[t].extend(flat[t])

        # the plain text, one file per page -- what the eval scores and what
        # the derived formats are built from
        text_dir = args.out_dir / "text"
        text_dir.mkdir(exist_ok=True)
        (text_dir / f"{page_id}.txt").write_text(page_plain_text(page),
                                                 encoding="utf-8")
        n_ok += 1

    for t in TABLES:
        path = args.out_dir / f"{t}.csv"
        if out[t]:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(out[t][0].keys()))
                w.writeheader()
                w.writerows(out[t])

    if errors:
        with open(args.out_dir / "validation_errors.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["page_id", "stage", "error"])
            w.writeheader()
            w.writerows(errors)
    if repairs:
        with open(args.out_dir / "repairs.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["page_id", "repair"])
            w.writeheader()
            w.writerows(repairs)

    print(f"parsed {n_ok} pages | not yet extracted {n_missing} | failed {n_failed}")
    if folio_fixes:
        print(f"  folio corrections applied: {n_folio_fixed} of {len(folio_fixes)} on file")
    for t in TABLES:
        print(f"  {t}: {len(out[t])} rows")
    if repairs:
        from collections import Counter
        for k, v in Counter(r["repair"] for r in repairs).items():
            print(f"  repair {k}: {v}")
    if errors:
        print(f"  -> {args.out_dir/'validation_errors.csv'}")


if __name__ == "__main__":
    main()
