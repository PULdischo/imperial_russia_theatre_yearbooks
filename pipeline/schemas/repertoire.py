"""Pydantic models for the LLM-facing (nested) JSON contract for Repertoire
pages, plus a flattener producing rows matching event_entry /
event_entry_performance in docs/schema.md (renamed from performance_session /
performance_work per RG's schema.md revision). Long/tidy per the structural
survey -- theater is a value on each session, not a fixed column."""
import re
from typing import Optional, Literal
from pydantic import BaseModel, Field

from .dates import parse_russian_date

SessionType = Literal["unspecified", "morning", "evening"]

# Pre-1898 RepertoireTables pages combine both cities' theaters on one page
# (see docs/structural_survey.md) -- city is derivable from the theater name
# itself and must NOT be taken as a single page-level constant, or every
# Moscow-house session on a combined-grid page gets mislabeled SP (or vice
# versa). Fall back to the page-level `city` arg only for a theater name this
# lookup doesn't recognize (e.g. a future season introduces a new venue).
#
# Matched by PREFIX, not exact string, because the model sometimes writes the
# generic word too ("Большой театръ") and sometimes just the proper name
# ("Большой") -- both verbatim-plausible depending on what's actually printed
# in that column header, so `theater` is left as the model wrote it and only
# the lookup is made tolerant of the variation.
THEATER_CITY = {
    "Маріинскій": "SP", "Александринскій": "SP", "Михайловскій": "SP",
    "Большой": "Moscow", "Малый": "Moscow", "Новый": "Moscow",
}


def _city_for_theater(theater: str, fallback: str) -> str:
    for name, city in THEATER_CITY.items():
        if theater.startswith(name):
            return city
    return fallback


def _day_number(date_text: str) -> str:
    m = re.match(r"\s*(\d{1,3})", date_text or "")
    return m.group(1) if m else ""


class WorkLLM(BaseModel):
    work_title: str
    genre: Optional[str] = None


class SessionLLM(BaseModel):
    date_text: str
    month_text: Optional[str] = None
    year_text: Optional[str] = None
    session: SessionType = "unspecified"
    theater: str
    is_dark: bool = False
    receipts_text: Optional[str] = None
    annotation: Optional[str] = None
    works: list[WorkLLM] = Field(default_factory=list)


class RepertoirePage(BaseModel):
    sessions: list[SessionLLM] = Field(default_factory=list)


def _parse_receipts(text: Optional[str]) -> tuple[str, str]:
    if not text:
        return "", ""
    try:
        rub_part, kop_part = text.replace("—", "-").split("р.")
        kop = kop_part.replace("к.", "").strip()
        return rub_part.strip(), ("" if kop == "-" else kop)
    except Exception:
        return "", ""


def flatten_repertoire_page(page_id: str, season: str, city: str, page: RepertoirePage) -> dict:
    events, performances = [], []
    for i, s in enumerate(page.sessions, start=1):
        event_id = f"{page_id}__s{i:03d}"
        rub, kop = _parse_receipts(s.receipts_text)
        theater = s.theater.strip().rstrip(".")  # strip table-header punctuation, keep the name
        event_city = _city_for_theater(theater, city)
        date_input = f"{_day_number(s.date_text)} {s.month_text or ''} {s.year_text or ''}".strip()
        events.append({
            "event_id": event_id, "page_id": page_id, "season": season, "city": event_city,
            "date_text": s.date_text, "month_text": s.month_text or "",
            "year_text": s.year_text or "",
            "date_undate": parse_russian_date(date_input) or "",
            "time_of_day": s.session, "theater": theater,
            "event_status": "no_performance" if s.is_dark else "performed",
            "receipts_text": s.receipts_text or "", "receipts_rubles": rub,
            "receipts_kopecks": kop, "annotation": s.annotation or "",
        })
        for j, w in enumerate(s.works, start=1):
            performances.append({
                "performance_id": f"{event_id}__w{j}", "event_id": event_id, "performance_order": j,
                "performance_title": w.work_title, "genre": w.genre or "",
            })
    return {"event_entry": events, "event_entry_performance": performances}
