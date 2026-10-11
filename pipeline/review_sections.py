#!/usr/bin/env python3
"""Which blocks on a review's first and last page belong to a NEIGHBOURING review.

An issue often packs two reviews onto one printed page, and the same printed
page is scanned into both PDFs, so a review can open with the tail of the
previous section (opera roster changes before a ballet review, drama
criticism before another) and run on into the next one. 17 of 46 reviews
open that way.

The rule was written for `build_bilingual.py` on 2026-10-06 and lived only
there, which meant the presentation layer dropped those paragraphs while the
mention layer went on attributing their names to the wrong review's season
and genre -- `Г. Петровскій въ роли судебнаго слѣдователя`, from the Tolstoy
/ Meyerhold drama notice, counted as a 1910-11 Moscow *ballet* person. Moved
here so there is one definition and both layers obey it.

**PARAGRAPHS ONLY, and the exceptions are the point.** A blanket "drop
everything before the section heading" is wrong in four reviews: three open
with a plate caption belonging to the review it INTRODUCES (1902-03 SP
Opera's first block is a «Сервилія» plate, above the ОПЕРА heading), and
1910-11 Moscow Ballet would lose its own parent title `ОБЗОРЪ СЕЗОНА
1910—1911 г.—МОСКВА`. Figures and headings before the section heading are
kept; only paragraphs are dropped.

Nothing is destroyed: `merged_full/review_block.csv` keeps every block, and
this is a read-time filter both consumers apply.
"""
from __future__ import annotations

#: blocks that belong to a photographic plate rather than the running review
PLATE = {"figure"}
#: a review's own section heading, as printed
SECTION_HEADING = {"балетъ", "опера", "драма"}
#: genre -> the heading word that is this review's OWN, for the run-on case.
#: Not applied to the combined "All" volumes, which legitimately hold both.
OWN_HEADING = {"Ballet": "балетъ", "Opera": "опера"}


def _heading_word(block: dict) -> str | None:
    if block.get("block_type") != "heading":
        return None
    return (block.get("text") or "").strip().strip(".").strip().lower()


def section_heading_index(blocks: list[dict]) -> int | None:
    """Index of the review's own section heading, if present."""
    for i, b in enumerate(blocks):
        if _heading_word(b) in SECTION_HEADING:
            return i
    return None


def foreign_heading_index(blocks: list[dict], own: str | None) -> int | None:
    """Index where a DIFFERENT section begins on this review's last page."""
    if not own:
        return None
    for i, b in enumerate(blocks):
        t = _heading_word(b)
        if t in SECTION_HEADING and t != own:
            return i
    return None


def foreign_block_indices(page_blocks: list[dict], *, is_first_page: bool,
                          is_last_page: bool, genre: str | None) -> set[int]:
    """Indices of blocks on this page that belong to a neighbouring review."""
    out: set[int] = set()
    if is_first_page:
        h = section_heading_index(page_blocks)
        if h:
            for bi, b in enumerate(page_blocks[:h]):
                if b.get("block_type") not in PLATE and b.get("block_type") != "heading":
                    out.add(bi)
    if is_last_page:
        f = foreign_heading_index(page_blocks, OWN_HEADING.get(genre or ""))
        if f is not None:
            out.update(range(f, len(page_blocks)))
    return out
