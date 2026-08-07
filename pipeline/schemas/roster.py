"""Pydantic models for the LLM-facing (nested) JSON contract for Spiski
(roster) pages, plus a flattener that produces rows matching the flat
person_entry / person_entry_service / person_entry_credit tables in
docs/schema.md (renamed from roster_entry / service_period /
roster_entry_credit per RG's schema.md revision).

The nested shape here is what we *ask the model for* -- easier for it to
produce one JSON object per person than to invent its own row-keying scheme.
Flattening to the relational shape (with our own generated IDs) happens
after parsing, same as docs/eval/gold/_build_roster.py did for the gold set.
"""
from typing import Optional, Literal
import re

from pydantic import BaseModel, Field

from .dates import parse_russian_date

EndType = Optional[Literal["died", "left service", "other"]]
CreditType = Literal["category_totals", "named_work"]

# Backfills category_production_count from credit_summary_text -- the
# production count ("11" in "Въ 11 балетахъ—33") was never asked of the
# model as a structured field (only the credit count after the dash was),
# but it's sitting right there in the verbatim summary sentence, present in
# ~79% of BalletArtists credit_summary_text values (checked directly against
# the full corpus). Deriving it here means no re-extraction is needed --
# every already-captured raw JSON file already has everything this needs.
_PRODUCTION_COUNT_RE = re.compile(r"[Вв]ъ\s+(\d+)\s+([^\s,;.]+)\s*[—-]\s*([\d.]+)")


def _parse_production_counts(credit_summary_text: Optional[str]) -> dict[str, int]:
    counts = {}
    for prod, label, _cnt in _PRODUCTION_COUNT_RE.findall(credit_summary_text or ""):
        counts[label] = int(prod)
    return counts


class ServicePeriodLLM(BaseModel):
    start_date_text: Optional[str] = None
    end_date_text: Optional[str] = None
    end_type: EndType = None


class CreditLLM(BaseModel):
    credit_type: CreditType
    label: str
    role_name: Optional[str] = None
    # float, not int: the printed ledger genuinely uses fractional credits
    # (e.g. "—.5") for a role split between two artists -- not an OCR error.
    count: Optional[float] = None


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
    """Returns {"person_entry": [...], "person_entry_service": [...], "person_entry_credit": [...]}
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
        production_counts = _parse_production_counts(e.credit_summary_text)
        for k, c in enumerate(e.credits, start=1):
            if c.count is None:
                count_out = ""
            elif c.count == int(c.count):
                count_out = str(int(c.count))
            else:
                count_out = str(c.count)
            production_count = production_counts.get(c.label)
            credits.append({
                "credit_id": f"{entry_id}__cr{k}", "entry_id": entry_id,
                "credit_type": c.credit_type, "label": c.label,
                "role_name": c.role_name or "",
                "category_production_count": "" if production_count is None else str(production_count),
                "category_credit_count": count_out,
            })
    return {"person_entry": entries, "person_entry_service": periods, "person_entry_credit": credits}
