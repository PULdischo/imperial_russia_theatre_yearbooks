"""Check hand-typed gold transcriptions while you are still typing them.

Run it as often as you like -- it reads files, changes nothing, costs
nothing. The point is to catch a mistyped convention on page 2 rather than
after page 12.

    uv run python pipeline/check_gold_reviews.py
    uv run python pipeline/check_gold_reviews.py --file 06   # just one

ERROR means the file will not parse and must be fixed. WARN means it parses
but something looks off -- read it and decide; some warnings are legitimately
fine (a plate page really can have no folio).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gold_reviews import BLOCK_TYPES, GoldParseError, parse_gold_file
from schemas.review import (LETTER_SPACING_LEAK_RE, block_plain_text,
                            page_plain_text, spans_plain_text)

HEADERISH_RE = re.compile(r"^\[([a-zA-Z_][a-zA-Z_ )0-9]*)\]\s*$")

# The marks docs/season_reviews.md §7 forbids normalising. In a monospace
# font these are visually near-identical, so the only reliable way to know
# what you typed is to count codepoints.
# Pre-reform orthography: a word ending in a hard consonant takes a final ъ.
# A modern Russian spellchecker strips exactly these ("балетъ" -> "балет"),
# which is silent, plausible-looking, and destroys the thing the corpus is
# for. Abbreviations (соч., карт.) legitimately end without one, so a token
# followed by a full stop is exempt.
HARD_CONSONANTS = "бвгджзклмнпрстфхцчшщ"

# Cyrillic and Latin share many identical-looking glyphs (о/o, е/e, а/a, р/p,
# с/c, х/x, у/y, В/B, Н/H, Т/T ...). A word mixing the two scripts is almost
# always a keyboard-layout slip -- and it is invisible on screen, so nothing
# but a codepoint check will find it. This page mixes French and Russian
# constantly, which makes the slip likely rather than rare.
CYR = set("абвгдежзийклмнопрстуфхцчшщъыьэюяѣіѳѵ"
          "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯѢІѲѴЁё")
LAT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
          "àâçéèêëîïôùûüÿœæÀÂÇÉÈÊËÎÏÔÙÛÜŸŒÆ")
MIXED_WORD_RE = __import__("re").compile(r"[^\W\d_]{2,}")
WORD_RE = re.compile(r"[А-Яа-яЁёѢѣІіѲѳѴѵЪъЬь]+")

WATCHED = [
    ("\u2014", "em dash  —"),
    ("\u2013", "en dash – <- WRONG: does not occur in these volumes"),
    ("\u002d", "hyphen   -"),
    ("\u00ab", "«"),
    ("\u00bb", "»"),
    ("\u201e", "„"),
    ("\u201c", "“"),
    ("\u201d", "”  <- curly, usually WRONG here"),
    ("\u2019", "’  <- curly apostrophe, usually WRONG"),
    ("\u0022", '"  <- straight, usually WRONG'),
]
TAGS = ("r", "b", "i", "d", "l")


def lint(path: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warns: list[str] = []
    stats: dict = {}

    body_lines = [l for l in path.read_text(encoding="utf-8").splitlines()
                  if not l.lstrip().startswith("#")]

    # a mistyped block header is silently swallowed as body text, so catch it
    in_blocks = False
    for n, line in enumerate(body_lines, 1):
        s = line.strip()
        if s == "[BLOCKS]":
            in_blocks = True
            continue
        if not in_blocks:
            continue
        m = HEADERISH_RE.match(s)
        if m:
            head = m.group(1).split()[0]
            if head not in BLOCK_TYPES and head not in ("FIELDS", "BLOCKS"):
                errors.append(
                    f"line {n}: '[{m.group(1)}]' is not a block type -- it will "
                    f"be swallowed as body text. Valid: {', '.join(sorted(BLOCK_TYPES))}")

    text = "\n".join(body_lines)
    for t in TAGS:
        opens = len(re.findall(rf"<{t}(?:\s+[a-z]{{2}})?>", text))
        closes = len(re.findall(rf"</{t}>", text))
        if opens != closes:
            errors.append(f"unbalanced <{t}> tags: {opens} opening, {closes} closing")
    if text.count("[?") != len(re.findall(r"\[\?[^\]]*\]", text)):
        errors.append("an unclosed [? ... ] -- every [? needs a closing ]")

    try:
        page = parse_gold_file(path)
    except GoldParseError as e:
        errors.append(str(e))
        return errors, warns, stats

    # Invisible whitespace. None of this is visible on screen, and every one
    # of them is a straight character mismatch against the model's output.
    for b in page.blocks:
        for txt, where in ((block_plain_text(b), "text"),
                           (spans_plain_text(b.caption), "caption")):
            for bad, name in (("\t", "TAB"), ("\u00a0", "non-breaking space"),
                              ("  ", "double space")):
                if bad in txt:
                    i = txt.index(bad)
                    warns.append(
                        f"{b.block_type} {where}: {name} at "
                        f"...{txt[max(0,i-22):i+12]!r}... — invisible on screen, "
                        f"but a character mismatch")
    for ln, line in enumerate(body_lines, 1):
        if line != line.rstrip():
            warns.append(f"line {ln}: trailing whitespace")

    # mixed-script words
    for b in page.blocks:
        for txt in (block_plain_text(b), spans_plain_text(b.caption)):
            for m in MIXED_WORD_RE.finditer(txt):
                word = m.group(0)
                cyr = [c for c in word if c in CYR]
                lat = [c for c in word if c in LAT]
                if cyr and lat:
                    # In this corpus Cyrillic is the base script and stray
                    # Latin lookalikes are the error, so name the Latin ones.
                    latin = "".join(sorted(set(lat)))
                    warns.append(
                        f"MIXED SCRIPT in {word!r}: the Latin letter(s) "
                        f"{latin!r} sit inside a Cyrillic word — identical on "
                        f"screen, almost always a keyboard-layout slip")

    plain = page_plain_text(page)
    stats["punct"] = [(label, plain.count(ch)) for ch, label in WATCHED
                      if plain.count(ch)]
    missing_hard_sign = []
    for b in page.blocks:
        # Check the block's CONCATENATED text, not span by span: inline markup
        # splits a word across spans ("Сенъ-Жорж<d>а</d>"), and checking spans
        # individually reports the truncated half as a missing-ъ error.
        for txt in (block_plain_text(b), spans_plain_text(b.caption)):
            for m in WORD_RE.finditer(txt):
                word = m.group(0)
                nxt = txt[m.end():m.end() + 1]
                # exempt abbreviations ("соч.") and the first half of a word
                # broken across a line ("Постав-" / "ленъ")
                if len(word) > 1 and word[-1].lower() in HARD_CONSONANTS \
                        and nxt not in (".", "-"):
                    missing_hard_sign.append(word)
    stats["missing_hard_sign"] = missing_hard_sign
    stats["blocks"] = len(page.blocks)
    stats["chars"] = len(page_plain_text(page))
    stats["folio"] = page.printed_folio
    from collections import Counter
    stats["types"] = Counter(b.block_type for b in page.blocks)

    if not page.blocks:
        return errors, warns, stats          # not started; nothing to warn about

    if not page.printed_folio and not page.no_text:
        warns.append("printed_folio is empty -- correct only if the page truly "
                     "shows no printed number")
    for i, b in enumerate(page.blocks, 1):
        t = block_plain_text(b)
        if not t and not b.caption:
            warns.append(f"block {i} ({b.block_type}) is empty")
        # literal letter-spacing that was typed out instead of tagged <r>
        for s in b.spans:
            if not s.razryadka and LETTER_SPACING_LEAK_RE.search(s.text):
                warns.append(
                    f"block {i}: looks letter-spaced but is not inside <r>...</r>: "
                    f"{s.text[:40]!r} -- type the word closed up and wrap it")
        if b.block_type == "figure" and not b.caption:
            warns.append(f"block {i} is a figure with no 'caption:' line")
        if b.caption and b.block_type != "figure":
            warns.append(f"block {i} ({b.block_type}) has a caption -- "
                         f"captions belong to [figure]")
    return errors, warns, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=Path("docs/eval/gold_reviews"))
    ap.add_argument("--file", default=None,
                    help="check one file by its number, e.g. 06")
    args = ap.parse_args()

    files = sorted(args.dir.glob("*.txt"))
    if args.file:
        files = [f for f in files if f.name.startswith(args.file)]
        if not files:
            raise SystemExit(f"no gold file starting {args.file!r}")

    done = 0
    total_chars = 0
    for f in files:
        errors, warns, stats = lint(f)
        blocks = stats.get("blocks", 0)
        if blocks:
            done += 1
            total_chars += stats.get("chars", 0)
        status = "not started" if not blocks else (
            "ERRORS" if errors else ("ok, with notes" if warns else "ok"))
        print(f"\n{f.name}")
        print(f"  {status}", end="")
        if blocks:
            types = ", ".join(f"{k}x{v}" for k, v in
                              sorted(stats['types'].items()))
            print(f"  |  {blocks} blocks ({types})  |  {stats['chars']} chars"
                  f"  |  folio {stats['folio'] or '-'}")
        else:
            print()
        if stats.get("punct"):
            marks = "   ".join(f"{lab.split()[0] if ' ' in lab else lab}"
                               f" x{n}" for lab, n in stats["punct"])
            print(f"    punctuation: {marks}")
            for lab, n in stats["punct"]:
                if "WRONG" in lab:
                    warns.append(f"found {n}x {lab} -- check this is really "
                                 f"what the page prints; editors insert these "
                                 f"automatically")
        mhs = stats.get("missing_hard_sign") or []
        if mhs:
            uniq = sorted(set(mhs))
            warns.append(
                f"{len(mhs)} word(s) end in a hard consonant with no final ъ — "
                f"check against the page; a Russian spellchecker strips these: "
                f"{', '.join(uniq[:8])}" + (" ..." if len(uniq) > 8 else ""))
        for e in errors:
            print(f"    ERROR  {e}")
        for w in warns:
            print(f"    WARN   {w}")

    print(f"\n{'='*66}")
    print(f"{done} of {len(files)} typed, {total_chars:,} characters so far")
    if done == len(files):
        print("All twelve done. Next: uv run python pipeline/eval_reviews.py "
              "--raw-dir outputs/reviews/raw --run-id <label>")


if __name__ == "__main__":
    main()
