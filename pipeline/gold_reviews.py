"""Parser for the hand-typed gold transcription files in
docs/eval/gold_reviews/ (docs/season_reviews.md §11).

Produces the SAME ReviewPageLLM structure the model's output parses into, so
the eval compares like with like rather than comparing two different shapes.

File format
-----------
Lines beginning '#' are comments. Two sections:

    [FIELDS]
    printed_folio: 194
    tailpiece_present: yes
    no_text: no
    copy_artifacts:
    notes:

    [BLOCKS]
    [heading]
    <r>Балетъ.</r>

    [paragraph]
    ... text, line breaks kept exactly as printed ...

    [enumerated_list 1)]
    <i><l fr>Pas de deux</l></i>—г-жа Кшесинская 2-я.

    [figure plate vertical]
    caption: Станъ царя Кандавла—декорація художника В. В. Васильева
    («Царь Кандавлъ», балетъ Сенъ-Жоржа, дѣйствіе 1-е. картина 2-я).

    [footnote *]
    *) Смотри Ежегодникъ Императорскихъ театровъ, 1899 и 1900 г.

A block header is a line that is exactly '[type]', optionally followed by one
argument: the enumerator for enumerated_list, the subtype for figure, the
marker for footnote.

Inline markup:
    <r>...</r>     разрядка
    <b>...</b>     bold
    <i>...</i>     italic
    <d>...</d>     damaged printing -- faint, smudged or broken, but legible
    <l xx>...</l>  language (fr, de, it, la)
    [?text]        uncertain reading
    [gap]          illegible, no reading
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas.review import BlockLLM, ReviewPageLLM, SpanLLM

BLOCK_TYPES = {"heading", "paragraph", "verse", "cast_list", "personnel_news",
               "enumerated_list", "figure", "footnote", "byline", "other"}

HEADER_RE = re.compile(r"^\[([a-z_]+)(?:\s+(.*?))?\]\s*$")
TOKEN_RE = re.compile(
    r"(</?[rbid]>|<l\s+([a-z]{2})>|</l>|\[gap\]|\[\?)"
)
TRUTHY = {"yes", "true", "y", "1"}


class GoldParseError(Exception):
    pass


def parse_inline(text: str) -> list[SpanLLM]:
    """Turn marked-up text into spans whose concatenation is the plain text."""
    spans: list[SpanLLM] = []
    state = {"razryadka": False, "bold": False, "italic": False,
             "damaged": False}
    lang: str | None = None
    uncertain_depth = 0
    buf: list[str] = []

    def flush():
        if buf:
            spans.append(SpanLLM(text="".join(buf), lang=lang,
                                 uncertain=uncertain_depth > 0, **state))
            buf.clear()

    i = 0
    while i < len(text):
        m = TOKEN_RE.search(text, i)
        if not m:
            buf.append(text[i:])
            break
        buf.append(text[i:m.start()])
        tok = m.group(1)
        TAGMAP = {"r": "razryadka", "b": "bold", "i": "italic", "d": "damaged"}
        if tok in ("<r>", "<b>", "<i>", "<d>"):
            flush(); state[TAGMAP[tok[1]]] = True
        elif tok in ("</r>", "</b>", "</i>", "</d>"):
            flush(); state[TAGMAP[tok[2]]] = False
        elif tok.startswith("<l"):
            flush(); lang = m.group(2)
        elif tok == "</l>":
            flush(); lang = None
        elif tok == "[gap]":
            flush(); spans.append(SpanLLM(text="", gap=True))
        elif tok == "[?":
            flush(); uncertain_depth += 1
        i = m.end()
        # closing bracket for [?...]
        if tok == "[?":
            close = text.find("]", i)
            if close == -1:
                raise GoldParseError("unclosed [? ... ]")
            spans.append(SpanLLM(text=text[i:close], uncertain=True, lang=lang,
                                 **state))
            uncertain_depth -= 1
            i = close + 1
    flush()
    return [s for s in spans if s.text or s.gap]


def parse_gold_file(path: Path) -> ReviewPageLLM:
    fields: dict[str, str] = {}
    blocks: list[BlockLLM] = []
    section = None
    cur: BlockLLM | None = None
    cur_lines: list[str] = []
    cur_caption: list[str] = []
    in_caption = False

    def close_block():
        nonlocal cur, cur_lines, cur_caption, in_caption
        if cur is None:
            return
        body = "\n".join(cur_lines).strip("\n")
        cur.spans = parse_inline(body) if body else []
        cap = "\n".join(cur_caption).strip("\n")
        cur.caption = parse_inline(cap) if cap else []
        blocks.append(cur)
        cur, cur_lines, cur_caption = None, [], []
        in_caption = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.lstrip().startswith("#"):
            continue
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped == "[FIELDS]":
            close_block(); section = "fields"; continue
        if stripped == "[BLOCKS]":
            close_block(); section = "blocks"; continue

        if section == "fields":
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                fields[k.strip()] = v.strip()
            continue

        if section == "blocks":
            m = HEADER_RE.match(stripped)
            if m and m.group(1) in BLOCK_TYPES:
                close_block()
                btype, arg = m.group(1), (m.group(2) or "").strip()
                cur = BlockLLM(block_type=btype)
                if btype == "enumerated_list":
                    cur.enumerator = arg
                elif btype == "figure" and arg:
                    parts = arg.split()
                    if "vertical" in parts:
                        cur.caption_vertical = True
                        parts = [x for x in parts if x != "vertical"]
                    if parts:
                        cur.figure_subtype = parts[0]
                elif btype == "footnote" and arg:
                    cur.footnote_marker = arg
                continue
            if cur is None:
                if stripped:
                    raise GoldParseError(
                        f"{path.name}: text before any block header: {stripped[:60]!r}")
                continue
            if stripped.lower().startswith("caption:"):
                cur_caption.append(line.split(":", 1)[1].strip())
                in_caption = True
            elif in_caption:
                # A caption may run to several printed lines. It continues
                # until a blank line -- otherwise the continuation silently
                # lands in the figure's body instead.
                if not stripped:
                    in_caption = False
                else:
                    cur_caption.append(line)
            else:
                cur_lines.append(line)

    close_block()

    # "no" / "none" / "-" are natural things to type in a field that is
    # otherwise left blank; treat them as blank rather than as an artifact
    # literally named "no".
    artifacts = fields.get("copy_artifacts", "").strip()
    if artifacts.lower() in ("no", "none", "n/a", "-", "nothing"):
        artifacts = ""
    return ReviewPageLLM(
        printed_folio=fields.get("printed_folio", "").strip() or None,
        tailpiece_present=fields.get("tailpiece_present", "").strip().lower() in TRUTHY,
        no_text=fields.get("no_text", "").strip().lower() in TRUTHY,
        copy_artifacts=[artifacts] if artifacts else [],
        blocks=blocks,
    )


def is_filled_in(path: Path) -> bool:
    """A template with nothing typed into it yet has no blocks."""
    try:
        return bool(parse_gold_file(path).blocks)
    except GoldParseError:
        return False


if __name__ == "__main__":
    for p in sorted(Path(sys.argv[1] if len(sys.argv) > 1
                         else "docs/eval/gold_reviews").glob("*.txt")):
        page = parse_gold_file(p)
        print(f"{p.name:44} blocks={len(page.blocks):3} "
              f"folio={page.printed_folio!r} filled={bool(page.blocks)}")
