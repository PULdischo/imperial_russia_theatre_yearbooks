"""Pydantic models for the LLM-facing (nested) JSON contract for Repertoire
pages, plus a flattener producing rows matching event_entry /
event_entry_performance in docs/schema.md (renamed from performance_session /
performance_work per RG's schema.md revision). Long/tidy per the structural
survey -- theater is a value on each session, not a fixed column."""
import json
import re
from collections import Counter
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


def _session_key(s: dict) -> tuple:
    return (s.get("date_text"), s.get("month_text"), s.get("theater"), s.get("session"))


def merge_repertoire_samples(sample_dicts: list[dict]) -> tuple[dict, dict]:
    """Union-merges N independent extraction samples of the SAME Repertoire
    page into one, to counter the model's non-deterministic dark-cell recall
    (known_issues.md #1 -- on repeat runs of the same page, the model
    sometimes emits every dark/blank cell and sometimes silently drops most
    of them; content accuracy on whatever IS emitted is fine, the gap is
    completeness). Confirmed via a live A/B test (2026-08-25, RG's request)
    that this really is run-to-run noise on at least one page with a known
    recall problem -- 3 baseline samples of the same page found 1, 8, and 2
    dark cells respectively -- so a union genuinely recovers more than any
    single sample does.

    A session (keyed by date_text+month_text+theater+session, i.e. one
    printed cell) is included in the merged output if ANY sample produced
    it at all. This can only ADD sessions a run silently dropped -- it can
    never invent a key that not one of the N samples ever produced, so a
    date genuinely absent from the printed table (and thus absent from
    every sample) stays absent from the merge too. This is the same
    guarantee the single-sample prompt already promises ("a day with no
    printed row at all ... should simply not appear in your output"); the
    merge just extends it across N tries instead of trusting one.

    Among samples that agree the key is dark, it stays dark. Among samples
    that captured real content for the same key, the version that the
    largest number of samples agree on (by receipts/annotation/works) wins,
    ties broken by first-seen order -- this does NOT try to reconcile
    disagreeing content field-by-field, only pick the most-corroborated
    whole session, so it never fabricates a hybrid that no sample actually
    produced.

    Returns (merged_dict, stats) -- stats is for visibility/logging, not
    used downstream.
    """
    if len(sample_dicts) == 1:
        return sample_dicts[0], {"samples": 1, "keys_recovered_by_union": 0,
                                  "keys_with_dark_vs_content_disagreement": 0}

    by_key: dict[tuple, list[dict]] = {}
    key_order: list[tuple] = []
    for sample in sample_dicts:
        for s in sample.get("sessions", []):
            k = _session_key(s)
            if k not in by_key:
                by_key[k] = []
                key_order.append(k)
            by_key[k].append(s)

    def content_signature(v: dict) -> str:
        return json.dumps({f: v.get(f) for f in ("receipts_text", "annotation", "works")},
                           sort_keys=True, ensure_ascii=False)

    merged_sessions = []
    n_recovered = 0
    n_dark_disagreement = 0
    for k in key_order:
        variants = by_key[k]
        if len(variants) < len(sample_dicts):
            n_recovered += 1  # at least one sample never produced this key at all
        dark_variants = [v for v in variants if v.get("is_dark")]
        content_variants = [v for v in variants if not v.get("is_dark")]
        if content_variants:
            if dark_variants:
                n_dark_disagreement += 1
            sig_counts = Counter(content_signature(v) for v in content_variants)
            best_sig = sig_counts.most_common(1)[0][0]
            merged_sessions.append(next(v for v in content_variants if content_signature(v) == best_sig))
        else:
            merged_sessions.append(dark_variants[0])

    merged = dict(sample_dicts[0])
    merged["sessions"] = merged_sessions
    stats = {"samples": len(sample_dicts), "keys_recovered_by_union": n_recovered,
              "keys_with_dark_vs_content_disagreement": n_dark_disagreement}
    return merged, stats


def _parse_receipts(text: Optional[str]) -> tuple[str, str]:
    if not text:
        return "", ""
    try:
        rub_part, kop_part = text.replace("—", "-").split("р.")
        kop = kop_part.replace("к.", "").strip()
        return rub_part.strip(), ("" if kop == "-" else kop)
    except Exception:
        return "", ""


def _backfill_month_year(sessions: list["SessionLLM"],
                          page_header: Optional[dict]) -> list[tuple[str, str]]:
    """Returns a (month_text, year_text) to use when COMPUTING date_undate
    for each session -- never the verbatim event_entry.month_text/year_text
    fields themselves, which stay exactly what the model read on that row
    (empty if empty). This is purely a derived-field input, the same
    "verbatim in, best-effort derived date out" contract dates.py's own
    docstring already documents for date_undate.

    Closes docs/eval/known_issues.md #69's "event-date field audit" gap:
    column-wise extraction populates month_text/year_text on only ~13-21%
    of sessions per season (a session only ever carries its OWN printed
    text, with no cross-row inheritance -- see the per-session date_input
    built below), vs ~100% for baseline extraction. `page_header` (from
    pipeline/extract_page_headers.py's small, separate, targeted read of
    just the page's own printed date-range line, e.g. "16 февраля. 1908 г.
    23 февраля.") gives an unambiguous start/end month+day for the whole
    page. Column-wise extraction emits one theater's entire run of
    sessions contiguously and in print order (confirmed against the raw
    JSON, not assumed), so walking each theater's own day-number sequence
    and switching from the header's start month to its end month at the
    one point (if any) where the day number decreases -- exactly where a
    real page's calendar rolls over a month boundary -- recovers the
    right month without guessing at any individual row's own content.
    """
    if not page_header:
        return [(s.month_text or "", s.year_text or "") for s in sessions]

    start_month = page_header["start_month"]
    end_month = page_header["end_month"]
    year_text = page_header["year_text"]

    result: list[Optional[tuple[str, str]]] = [None] * len(sessions)
    theater_runs: dict[str, list[int]] = {}
    for i, s in enumerate(sessions):
        theater_runs.setdefault(s.theater, []).append(i)

    for idxs in theater_runs.values():
        current_month = start_month
        prev_day: Optional[int] = None
        for i in idxs:
            s = sessions[i]
            if s.month_text and s.year_text:
                result[i] = (s.month_text, s.year_text)
                continue
            day_str = _day_number(s.date_text)
            day_num = int(day_str) if day_str.isdigit() else None
            if day_num is not None and prev_day is not None and day_num < prev_day:
                current_month = end_month
            if day_num is not None:
                prev_day = day_num
            result[i] = (s.month_text or current_month, s.year_text or year_text)

    return result  # type: ignore[return-value]


def flatten_repertoire_page(page_id: str, season: str, city: str, page: RepertoirePage,
                             page_header: Optional[dict] = None) -> dict:
    events, performances = [], []
    backfilled = _backfill_month_year(page.sessions, page_header)
    for i, (s, (bf_month, bf_year)) in enumerate(zip(page.sessions, backfilled), start=1):
        event_id = f"{page_id}__s{i:03d}"
        rub, kop = _parse_receipts(s.receipts_text)
        theater = s.theater.strip().rstrip(".")  # strip table-header punctuation, keep the name
        event_city = _city_for_theater(theater, city)
        date_input = f"{_day_number(s.date_text)} {bf_month} {bf_year}".strip()
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
