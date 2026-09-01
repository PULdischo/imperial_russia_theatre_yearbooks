"""Stage 6 of the season-reviews pipeline: render the parsed JSON into the
human-facing formats (docs/season_reviews.md §2).

Three outputs per review document (season x city x genre):

  tei/*.xml    the source of truth for the edition -- citable, validatable,
               with page breaks carrying the printed folio
  md/*.md      the daily reading and grepping copy
  text/*.txt   line-rejoined searchable text

All three are RENDERERS over JSON already on disk. Changing a convention, or
adding a fourth format, is a re-run of this script -- never a re-extraction.

The searchable text is where the diplomatic line breaks are undone: an
end-of-line hyphen is closed up ("возобновле-\\nніемъ" -> "возобновленіемъ")
so that a word split across a line is findable. `verse` blocks are exempt --
there the line break is part of the text, not a typographic accident (§7).

Usage:
    python pipeline/build_review_outputs.py --parsed-dir outputs/reviews/parsed \
        --manifest outputs/reviews/manifest.csv --out-dir outputs/reviews/derived
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas.review import (BlockLLM, ReviewPageLLM, SpanLLM, block_plain_text,
                            spans_plain_text)
from parse_reviews import repair

# end-of-line hyphen followed by a lowercase letter -> the word continues
HYPHEN_BREAK_RE = re.compile(r"-\n(?=[a-zа-яѣіѳѵ])", re.IGNORECASE)


def rejoin(text: str) -> str:
    text = HYPHEN_BREAK_RE.sub("", text)
    return re.sub(r"(?<!\n)\n(?!\n)", " ", text)


# --------------------------------------------------------------------------
# TEI

TEI_HI = {"razryadka": "letterspaced", "bold": "bold", "italic": "italic"}


def tei_spans(spans: list[SpanLLM]) -> str:
    out = []
    for s in spans:
        if s.gap:
            ext = f' extent="{html.escape(s.gap_extent)}"' if s.gap_extent else ""
            out.append(f'<gap reason="illegible"{ext}/>')
            continue
        t = html.escape(s.text)
        for attr, rend in TEI_HI.items():
            if getattr(s, attr):
                t = f'<hi rend="{rend}">{t}</hi>'
        if s.lang and s.lang != "ru":
            t = f'<foreign xml:lang="{s.lang}">{t}</foreign>'
        if s.uncertain:
            t = f"<unclear>{t}</unclear>"
        out.append(t)
    return "".join(out)


def tei_block(b: BlockLLM) -> str:
    inner = tei_spans(b.spans)
    if b.block_type == "heading":
        return f"      <head>{inner}</head>"
    if b.block_type == "verse":
        lines = "\n".join(f"        <l>{html.escape(l)}</l>"
                          for l in block_plain_text(b).split("\n"))
        return f"      <lg>\n{lines}\n      </lg>"
    if b.block_type == "enumerated_list":
        n = f' n="{html.escape(b.enumerator)}"' if b.enumerator else ""
        return f"      <list><item{n}>{inner}</item></list>"
    if b.block_type == "figure":
        cap = tei_spans(b.caption)
        rend = ' rend="vertical"' if b.caption_vertical else ""
        sub = f' type="{b.figure_subtype}"' if b.figure_subtype else ""
        return f"      <figure{sub}><figDesc{rend}>{cap}</figDesc></figure>"
    if b.block_type == "footnote":
        n = f' n="{html.escape(b.footnote_marker)}"' if b.footnote_marker else ""
        return f'      <note place="foot"{n}>{inner}</note>'
    if b.block_type == "cast_list":
        return f'      <p type="castList">{inner}</p>'
    if b.block_type == "personnel_news":
        return f'      <p type="personnelNews">{inner}</p>'
    if b.block_type == "byline":
        return f"      <byline>{inner}</byline>"
    if b.block_type == "other":
        return f'      <p type="unclassified">{inner}</p>'
    return f"      <p>{inner}</p>"


def build_tei(doc_id: str, meta: dict, pages: list[tuple[str, ReviewPageLLM]]) -> str:
    title = (f"{meta['genre']} — {meta['city']}, сезонъ {meta['season']}")
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">',
        "  <teiHeader><fileDesc>",
        f"    <titleStmt><title>{html.escape(title)}</title></titleStmt>",
        "    <publicationStmt><p>Diplomatic transcription; see "
        "docs/season_reviews.md</p></publicationStmt>",
        "    <sourceDesc><bibl>Ежегодникъ Императорскихъ театровъ, "
        f"{html.escape(meta['season'])}</bibl></sourceDesc>",
        "  </fileDesc></teiHeader>",
        "  <text><body>",
        f'    <div type="seasonReview" xml:id="{doc_id}">',
    ]
    for page_id, page in pages:
        folio = f' n="{html.escape(page.printed_folio)}"' if page.printed_folio else ""
        parts.append(f'      <pb{folio} xml:id="{page_id}"/>')
        for b in page.blocks:
            parts.append(tei_block(b))
    parts += ["    </div>", "  </body></text>", "</TEI>"]
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------
# Markdown

def md_spans(spans: list[SpanLLM]) -> str:
    out = []
    for s in spans:
        if s.gap:
            out.append("[gap]")
            continue
        t = s.text
        if s.razryadka:
            t = f"<r>{t}</r>"
        if s.bold:
            t = f"**{t}**"
        if s.italic:
            t = f"*{t}*"
        if s.uncertain:
            t = f"[?{t}]"
        out.append(t)
    return "".join(out)


def build_md(doc_id: str, meta: dict, pages: list[tuple[str, ReviewPageLLM]]) -> str:
    lines = [f"# {meta['genre']} — {meta['city']}, сезонъ {meta['season']}", "",
             f"*Diplomatic transcription. {len(pages)} pages. "
             f"Conventions: `docs/season_reviews.md`.*", ""]
    for page_id, page in pages:
        folio = page.printed_folio or "?"
        lines += [f"---", "", f"`[[{page_id} | printed p. {folio}]]`", ""]
        for b in page.blocks:
            body = md_spans(b.spans)
            if b.block_type == "heading":
                lines += [f"## {body}", ""]
            elif b.block_type == "verse":
                lines += ["```", block_plain_text(b), "```", ""]
            elif b.block_type == "enumerated_list":
                lines += [f"{b.enumerator or '-'} {body}", ""]
            elif b.block_type == "figure":
                cap = md_spans(b.caption)
                vert = " *(caption set vertically)*" if b.caption_vertical else ""
                lines += [f"> **[{b.figure_subtype or 'figure'}]**{vert} {cap}", ""]
            elif b.block_type == "footnote":
                lines += [f"[^{b.footnote_marker or '*'}]: {body}", ""]
            else:
                lines += [body, ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------

def build_search_text(pages: list[tuple[str, ReviewPageLLM]]) -> str:
    out = []
    for page_id, page in pages:
        out.append(f"[[{page_id} | p. {page.printed_folio or '?'}]]")
        for b in page.blocks:
            t = block_plain_text(b)
            if not t:
                t = spans_plain_text(b.caption)
            if not t:
                continue
            out.append(t if b.block_type == "verse" else rejoin(t))
    return "\n\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--raw-dir", type=Path, default=None,
                    help="defaults to <parsed-dir>/../raw")
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    raw_dir = args.raw_dir or args.parsed_dir.parent / "raw"

    manifest = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in manifest:
        doc_id = f"review_{r['season']}_{r['city']}_{r['genre']}".replace(" ", "")
        groups[doc_id].append(r)

    for sub in ("tei", "md", "text"):
        (args.out_dir / sub).mkdir(parents=True, exist_ok=True)

    n_docs = n_pages = 0
    for doc_id, rows in sorted(groups.items()):
        rows.sort(key=lambda r: int(r["source_page_index"]))
        pages = []
        for r in rows:
            raw = raw_dir / f"{r['page_id']}.raw.json"
            if not raw.exists():
                continue
            page = ReviewPageLLM.model_validate(
                json.loads(raw.read_text(encoding="utf-8")))
            page, _ = repair(page)
            pages.append((r["page_id"], page))
        if not pages:
            continue
        meta = rows[0]
        (args.out_dir / "tei" / f"{doc_id}.xml").write_text(
            build_tei(doc_id, meta, pages), encoding="utf-8")
        (args.out_dir / "md" / f"{doc_id}.md").write_text(
            build_md(doc_id, meta, pages), encoding="utf-8")
        (args.out_dir / "text" / f"{doc_id}.txt").write_text(
            build_search_text(pages), encoding="utf-8")
        n_docs += 1
        n_pages += len(pages)

    print(f"{n_docs} documents, {n_pages} pages -> {args.out_dir}/(tei|md|text)")


if __name__ == "__main__":
    main()
