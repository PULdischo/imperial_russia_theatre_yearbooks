"""Pydantic models for the LLM-facing (nested) JSON contract for Spiski
(roster) pages, plus a flattener that produces rows matching the flat
roster_entry / service_period / roster_entry_credit tables in docs/schema.md.

The nested shape here is what we *ask the model for* -- easier for it to
produce one JSON object per person than to invent its own row-keying scheme.
Flattening to the relational shape (with our own generated IDs) happens
after parsing, same as docs/eval/gold/_build_roster.py did for the gold set.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from .dates import parse_russian_date

EndType = Optional[Literal["died", "resigned", "other"]]
CreditType = Literal["category_total", "named_work"]


class ServicePeriodLLM(BaseModel):
    start_date_text: Optional[str] = None
    end_date_text: Optional[str] = None
    end_type: EndType = None


class CreditLLM(BaseModel):
    credit_type: CreditType
    label: str
    role_name: Optional[str] = None
    count: Optional[int] = None


class RosterEntryLLM(BaseModel):
    institution: str
    heading_path: Optional[str] = None
    list_number: Optional[str] = None
    family_name: str
    first_name: Optional[str] = None
    patronymic: Optional[str] = None
    rank_or_title: Optional[str] = None
    service_class: Optional[str] = None
    instrument: Optional[str] = None
    subject_taught: Optional[str] = None
    tenure_note_text: Optional[str] = None
    credit_summary_text: Optional[str] = None
    service_periods: list[ServicePeriodLLM] = Field(default_factory=list)
    credits: list[CreditLLM] = Field(default_factory=list)


class RosterPage(BaseModel):
    entries: list[RosterEntryLLM] = Field(default_factory=list)


def flatten_roster_page(page_id: str, entity_type: str, page: RosterPage) -> dict:
    """Returns {"roster_entry": [...], "service_period": [...], "roster_entry_credit": [...]}
    as lists of flat dicts, ID-linked, matching docs/schema.md exactly."""
    entries, periods, credits = [], [], []
    for i, e in enumerate(page.entries, start=1):
        entry_id = f"{page_id}__e{i:03d}"
        entries.append({
            "entry_id": entry_id, "page_id": page_id, "entity_type": entity_type,
            "institution": e.institution, "heading_path": e.heading_path or "",
            "list_number": e.list_number or "",
            "family_name": e.family_name, "first_name": e.first_name or "",
            "patronymic": e.patronymic or "", "rank_or_title": e.rank_or_title or "",
            "service_class": e.service_class or "", "instrument": e.instrument or "",
            "subject_taught": e.subject_taught or "",
            "tenure_note_text": e.tenure_note_text or "",
            "credit_summary_text": e.credit_summary_text or "",
        })
        for j, p in enumerate(e.service_periods, start=1):
            periods.append({
                "period_id": f"{entry_id}__sp{j}", "entry_id": entry_id, "period_order": j,
                "start_date_text": p.start_date_text or "",
                "start_date_undate": parse_russian_date(p.start_date_text) or "",
                "end_date_text": p.end_date_text or "",
                "end_date_undate": parse_russian_date(p.end_date_text) or "",
                "end_type": p.end_type or "",
            })
        for k, c in enumerate(e.credits, start=1):
            credits.append({
                "credit_id": f"{entry_id}__cr{k}", "entry_id": entry_id,
                "credit_type": c.credit_type, "label": c.label,
                "role_name": c.role_name or "", "count": c.count if c.count is not None else "",
            })
    return {"roster_entry": entries, "service_period": periods, "roster_entry_credit": credits}
