"""Pydantic models for the LLM-facing (nested) JSON contract for the
per-season productions lists ("списокъ пьесъ") -- ballet first (RG,
2026-09-28), opera to follow once those pages are scanned -- plus a
flattener producing the flat production_entry / production_entry_performance
tables.

Each printed entry looks like:

    *19. Эсклармонда. Романтическая опера въ 4 д. съ прологомъ и эпилогомъ,
    музыка Массенэ, переводъ Н. М. Спасскаго.
        Исполнена: 1892 г.—января 6, 8, 10, 15, 26, 31; февраля 6, 9.
        Всего—8 разъ.

"*" marks a premiere that season (RG confirmed). This layer is verbatim
only: the description is kept as printed, and splitting it into genre /
acts / choreographer / composer / librettist is deliberately left for the
research layer (RG, 2026-09-28 -- how to read "соч." as a role is an open
question for her). The only derived values here are mechanical: the
calendar date assembled from the carried-forward year + month + day, and
the integer read out of "Всего—N".
"""
from datetime import date as _date
from typing import Optional
import re

from pydantic import BaseModel, Field

from .dates import parse_russian_date

_TOTAL_RE = re.compile(r"(\d+)")


class ProductionDateLLM(BaseModel):
    year_text: str
    month_text: str
    day_text: str
    note: Optional[str] = None
    # True for a part-performance printed AFTER "Всего" (e.g. "Всего—7 разъ.
    # 2-е дѣйствіе исполнено: 1899 г.—апрѣля 25."), which the printed total
    # does not count -- still a real performance, so it is kept as a date.
    outside_total: bool = False


class ProductionEntryLLM(BaseModel):
    list_number: Optional[str] = None
    is_premiere: bool = False
    title: str
    description_text: Optional[str] = None
    performed_text: Optional[str] = None
    total_text: Optional[str] = None
    total_count: Optional[int] = None
    post_total_text: Optional[str] = None
    fragment: Optional[str] = None
    dates: list[ProductionDateLLM] = Field(default_factory=list)


class ProductionsPage(BaseModel):
    section_heading: Optional[str] = None
    printed_page_number: Optional[str] = None
    entries: list[ProductionEntryLLM] = Field(default_factory=list)


def _valid_iso(iso: Optional[str]) -> Optional[str]:
    """parse_russian_date doesn't check the day exists ("38 декабря" ->
    "1897-12-38"); an impossible printed date (a genuine print error, left
    verbatim in day_text) gets no calendar date rather than an invalid one."""
    if not iso:
        return None
    try:
        _date.fromisoformat(iso)
    except ValueError:
        return None
    return iso


def _season_date(season: str, day_text: str, month_text: str) -> Optional[str]:
    """Calendar date from the list's own SEASON, not the printed year (RG,
    2026-09-28): a list belongs to its season by provenance (volume/file),
    so a performance in it falls August-December of the season's first year
    or January-July of its second, whatever year is printed beside it.
    The printed year stays verbatim in year_text; a disagreement is flagged
    separately (year_printed_matches_season), never silently "corrected"."""
    first = int(season[:4])
    probe = parse_russian_date(f"{day_text} {month_text} {first}")
    if not probe:
        return None
    month = int(probe[5:7])
    year = first if month >= 8 else first + 1
    return _valid_iso(f"{year:04d}{probe[4:]}")


def _total_from_text(total_text: Optional[str]) -> Optional[int]:
    m = _TOTAL_RE.search(total_text or "")
    return int(m.group(1)) if m else None


def flatten_productions_page(page_id: str, season: str, city: str,
                             page: ProductionsPage) -> dict:
    """Returns {"production_entry": [...], "production_entry_performance": [...]}."""
    entries, perfs = [], []
    for i, e in enumerate(page.entries, start=1):
        entry_id = f"{page_id}__e{i:03d}"
        entries.append({
            "production_entry_id": entry_id,
            "page_id": page_id,
            "season": season,
            "city": city,
            "section_heading": page.section_heading,
            "printed_page_number": page.printed_page_number,
            "entry_order": i,
            "list_number": e.list_number,
            "is_premiere": e.is_premiere,
            "title": e.title,
            "description_text": e.description_text,
            "performed_text": e.performed_text,
            "total_text": e.total_text,
            # the printed text is authoritative; the model's own integer is
            # only a fallback when the text carries no digits
            "total_count": _total_from_text(e.total_text) if e.total_text else e.total_count,
            "post_total_text": e.post_total_text,
            # counted dates only, so n_dates is directly comparable to total_count
            "n_dates": sum(1 for d in e.dates if not d.outside_total),
            "fragment": e.fragment,
        })
        for j, d in enumerate(e.dates, start=1):
            perfs.append({
                "production_performance_id": f"{entry_id}__d{j:03d}",
                "production_entry_id": entry_id,
                "date_order": j,
                "year_text": d.year_text,
                "month_text": d.month_text,
                "day_text": d.day_text,
                "note": d.note,
                "outside_total": d.outside_total,
                "date": _season_date(season, d.day_text, d.month_text),
                # False when the printed year isn't the one the season implies
                # (e.g. "1897 г.—февраля 12" in the 1897-98 list); None when
                # the printed year can't be read as a number
                "year_printed_matches_season": (
                    None if not (d.year_text or "").strip().isdigit()
                    or not _season_date(season, d.day_text, d.month_text)
                    else _season_date(season, d.day_text, d.month_text)[:4] == d.year_text.strip()),
            })
    return {"production_entry": entries, "production_entry_performance": perfs}
