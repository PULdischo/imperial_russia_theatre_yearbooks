"""Pydantic models for the LLM-facing JSON contract for season-review pages
(docs/season_reviews.md §3-§5), plus a flattener producing flat rows.

The central design decision: **a block's text is a list of spans, and
concatenating span.text reproduces the block byte for byte** -- including
newlines and leading indentation. That gives three things at once:

* plain text is always recoverable exactly (`block_plain_text`), so the
  annotation ablation in §11 compares like with like;
* styling is metadata sitting *on top of* the text, never expressed as
  literal spacing -- the failure mode that would otherwise poison every
  search over the corpus (§5);
* the annotations-off prompt variant is simply "one span per block", not a
  different schema.

Per CLAUDE.md's flatten-boundary convention, names here are the *LLM-facing*
contract and are deliberately plain. Any later renaming happens in the
flattener, so a naming change never requires re-running paid extraction.
"""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

Lang = Literal["ru", "fr", "de", "it", "la"]

BlockType = Literal[
    "heading",
    "paragraph",
    "verse",
    "cast_list",
    "personnel_news",   # provisional -- docs/season_reviews.md §4
    "enumerated_list",
    "figure",
    "footnote",
    "byline",
    "other",            # catch-all; NEVER discard text
]

FigureSubtype = Literal["plate", "photograph", "notated_music", "ornament", "other"]

# Catches literal letter-spacing leaking into span text ("Б а л е т ъ").
#
# Requires FOUR OR MORE consecutive single letters separated by single
# spaces. An earlier two-run version fired on ordinary Russian -- "г. Ершовъ
# и г. Морской" is full of one-letter words -- which made it useless. Four in
# a row does not occur naturally.
LETTER_SPACING_LEAK_RE = re.compile(r"(?:[^\W\d_] ){3,}[^\W\d_]")


def collapse_letter_spacing(text: str) -> str:
    """Close up runs of letter-spaced characters: "Б а л е т ъ" -> "Балетъ"."""
    return LETTER_SPACING_LEAK_RE.sub(lambda m: m.group(0).replace(" ", ""), text)


class SpanLLM(BaseModel):
    """One run of text sharing the same styling and language.

    `text` is verbatim: never normalised, never expanded, never corrected
    (docs/season_reviews.md §7). Styling flags describe how it is *printed*;
    they never alter the characters.
    """
    razryadka: bool = False
    text: str = ""
    bold: bool = False
    italic: bool = False
    lang: Optional[Lang] = None
    # Partially legible: a reading is offered but is not certain.
    uncertain: bool = False
    # Poorly printed but confidently read -- faint, smudged, or broken type.
    # A statement about the PRINTING, not about the reading: deliberately
    # separate from `uncertain`, which is a statement about our confidence.
    # Gold-only: the extraction prompt never asks the model for this, so it is
    # never scored (docs/season_reviews.md §11). Its purpose is diagnostic --
    # it lets us ask afterwards whether the model's errors cluster on badly
    # printed passages, which a raw error rate cannot reveal.
    damaged: bool = False
    # Wholly illegible: no reading offered. `text` MUST be empty.
    gap: bool = False
    gap_extent: Optional[str] = None  # free text, e.g. "about two words"

    def leaks_letter_spacing(self) -> bool:
        return bool(LETTER_SPACING_LEAK_RE.search(self.text))

    @field_validator("text", mode="after")
    @classmethod
    def _no_literal_letter_spacing(cls, v: str, info) -> str:
        """Repair, not reject.

        When a span is flagged `razryadka` AND its text is literally
        letter-spaced, the model has told us the spacing is typography rather
        than characters -- so closing it up is lossless. Unflagged spans are
        left alone and surface in quality checks instead, because there we
        cannot tell letter-spacing from genuinely spaced initials."""
        if info.data.get("razryadka") and LETTER_SPACING_LEAK_RE.search(v):
            return collapse_letter_spacing(v)
        return v


def _as_list(v):
    """Models routinely emit "" or null for an empty list. Re-parsing is free
    and re-extraction is not, so repair rather than reject (the approach
    known_issues.md #10-12 took for the tabular pipeline)."""
    if v in ("", None):
        return []
    return v


_FIGURE_SUBTYPE_ALIASES = {
    "ornamental": "ornament", "vignette": "ornament", "headpiece": "ornament",
    "tailpiece": "ornament", "engraving": "plate", "illustration": "plate",
    "music": "notated_music", "musical_example": "notated_music",
}


class BlockLLM(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # Models tend to write "type"; accept it and normalise.
    block_type: BlockType = Field(
        validation_alias=AliasChoices("block_type", "type"))
    spans: list[SpanLLM] = Field(default_factory=list)

    # enumerated_list: the enumerator exactly as printed -- "1)", "б)", or ""
    # when the printing has none. Storing it verbatim is what keeps the
    # numbered / lettered / bare distinction recoverable later (§4).
    enumerator: Optional[str] = None

    # figure
    figure_subtype: Optional[FigureSubtype] = None
    caption: list[SpanLLM] = Field(default_factory=list)
    # Plate captions are frequently set at 90 degrees (§10). Recorded because
    # a model that silently skips rotated text is the most likely cause of a
    # false `no_text` page.
    caption_vertical: bool = False

    # footnote: the marker as printed ("*", "1"), matching the anchor left in
    # the body text. Without it, which sentence the note belonged to is lost.
    footnote_marker: Optional[str] = None

    # Handwriting rather than type (§9). A diplomatic transcription should
    # not silently blur print and manuscript.
    manuscript: bool = False

    # Reading order is data, not array order (§8).
    column: Optional[int] = None

    _coerce_lists = field_validator("spans", "caption", mode="before")(_as_list)

    @field_validator("figure_subtype", mode="before")
    @classmethod
    def _normalise_subtype(cls, v):
        if v in ("", None):
            return None
        v = str(v).strip().lower()
        v = _FIGURE_SUBTYPE_ALIASES.get(v, v)
        # An unrecognised subtype must not fail the page -- the image is
        # recorded either way, and the label is the least important part.
        return v if v in ("plate", "photograph", "notated_music", "ornament",
                          "other") else "other"


class ReviewPageLLM(BaseModel):
    # The PRINTED folio, never a pencilled archival number (§9).
    printed_folio: Optional[str] = None
    tailpiece_present: bool = False
    # True only when there is genuinely nothing to transcribe. A plate WITH a
    # caption is not textless.
    no_text: bool = False
    # Library stamps, pencil foliation: noted, never transcribed into the
    # reading text (§9).
    copy_artifacts: list[str] = Field(default_factory=list)
    reading_order_uncertain: bool = False
    blocks: list[BlockLLM] = Field(default_factory=list)

    _coerce_lists = field_validator("copy_artifacts", "blocks",
                                    mode="before")(_as_list)

    @field_validator("copy_artifacts", mode="before")
    @classmethod
    def _artifacts_to_list(cls, v):
        if isinstance(v, str):
            return [v] if v.strip() else []
        return _as_list(v)


# --------------------------------------------------------------------------
# text reconstruction


def spans_plain_text(spans: list[SpanLLM]) -> str:
    """Concatenation of span text. Gaps contribute nothing -- their absence is
    recorded structurally rather than by inventing placeholder characters."""
    return "".join(s.text for s in spans if not s.gap)


def block_plain_text(block: BlockLLM) -> str:
    return spans_plain_text(block.spans)


def page_plain_text(page: ReviewPageLLM) -> str:
    """Blocks joined by a blank line, in reading order. This is the string the
    eval's character-error-rate is computed over (§11)."""
    parts = []
    for b in page.blocks:
        t = block_plain_text(b)
        if t:
            parts.append(t)
        cap = spans_plain_text(b.caption)
        if cap:
            parts.append(cap)
    return "\n\n".join(parts)


# --------------------------------------------------------------------------
# flatten


def flatten_review_page(page_id: str, season: str, city: str, genre: str,
                        page: ReviewPageLLM) -> dict:
    """Returns {"review_page": [...], "review_block": [...], "review_span": [...]}
    as lists of flat dicts, ID-linked."""
    blocks, spans = [], []

    def emit_spans(owner_id: str, role: str, items: list[SpanLLM]) -> None:
        for j, s in enumerate(items, start=1):
            spans.append({
                "span_id": f"{owner_id}__{role}{j:03d}",
                "block_id": owner_id,
                "span_role": role,          # "text" or "caption"
                "span_index": j,
                "text": s.text,
                "razryadka": s.razryadka,
                "bold": s.bold,
                "italic": s.italic,
                "lang": s.lang or "",
                "uncertain": s.uncertain,
                "damaged": s.damaged,
                "gap": s.gap,
                "gap_extent": s.gap_extent or "",
            })

    for i, b in enumerate(page.blocks, start=1):
        block_id = f"{page_id}__b{i:03d}"
        blocks.append({
            "block_id": block_id,
            "page_id": page_id,
            "block_index": i,            # reading order as transcribed
            "block_type": b.block_type,
            "enumerator": b.enumerator if b.enumerator is not None else "",
            "figure_subtype": b.figure_subtype or "",
            "caption_vertical": b.caption_vertical,
            "footnote_marker": b.footnote_marker or "",
            "manuscript": b.manuscript,
            "column": b.column if b.column is not None else "",
            "text": block_plain_text(b),
            "caption_text": spans_plain_text(b.caption),
        })
        emit_spans(block_id, "text", b.spans)
        emit_spans(block_id, "caption", b.caption)

    pages = [{
        "page_id": page_id,
        "season": season,
        "city": city,
        "genre": genre,
        "printed_folio": page.printed_folio or "",
        "tailpiece_present": page.tailpiece_present,
        "no_text": page.no_text,
        "copy_artifacts": "; ".join(page.copy_artifacts),
        "reading_order_uncertain": page.reading_order_uncertain,
        "n_blocks": len(page.blocks),
        "n_chars": len(page_plain_text(page)),
    }]

    return {"review_page": pages, "review_block": blocks, "review_span": spans}
