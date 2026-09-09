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
from schemas.review import LETTER_SPACING_LEAK_RE, block_plain_text, page_plain_text

HEADERISH_RE = re.compile(r"^\[([a-zA-Z_][a-zA-Z_ )0-9]*)\]\s*$")
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
