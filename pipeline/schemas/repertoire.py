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


#: The rubles marker's trailing period is sometimes dropped by the model
#: ("2943 р 70" instead of "2943 р. 70 к.") -- confirmed 2026-09-17
#: (docs/eval/known_issues.md #70's receipts_parse_failed addendum) on
#: 6 sessions across the two-page-spread seasons, via quality_checks.py's
#: check_repertoire comparing this function's own output against
#: receipts_text. A literal `.split("р.")` silently drops the whole
#: figure (rub AND kop both come back "") whenever that period is
#: missing, even though the figure itself is perfectly legible -- this
#: was a parsing gap, not a data problem, so fixed here rather than by
#: touching any raw session. `maxsplit=1` matches the previous split's
#: behavior of splitting on the first occurrence only. `\b` is required
#: (not just bare `р`) -- caught live by re-running quality_checks.py
#: after this fix: a bare `р\.?` also matches the letter "р" wherever it
#: happens to occur INSIDE an ordinary Cyrillic word (e.g. "3-я каРт.",
#: "Я игРаю") -- two already-known receipts_text content-misplacement
#: cases (`known_issues.md` #70) that are not receipts figures at all.
#: Python's `re` treats Cyrillic as word characters under `\b` by
#: default, so this correctly requires "р" to stand alone as a marker
#: token rather than merely appear somewhere in the string.
#:
#: Also accepts a Latin "p"/"P" as the same marker -- confirmed
#: 2026-09-17 (known_issues.md #70's receipts-field addendum) on 42
#: sessions where the model wrote the rubles marker in Latin script
#: (visually near-identical to Cyrillic "р" in this typeface; 9 of
#: those even mix scripts within one figure, Latin "p." paired with
#: Cyrillic "к."). Unlike the genre field's Latin/Cyrillic script
#: variants (left alone there -- both are equally complete, final
#: values needing no further processing), this is a genuine parsing
#: gap: the old Cyrillic-only marker silently failed the whole split on
#: every one of these, even though the figure itself is perfectly
#: legible -- receipts_text itself is untouched either way (verbatim
#: model output, script and all), only the derived rubles/kopecks
#: parsing is widened to recognize both scripts as the same marker.
#:
#: Deliberately does NOT accept "q"/"Q", even though
#: `repertoire_1892-93_pair012`, 8 Вторн., Михайловскій genuinely prints
#: "1225 q. 27 к." (confirmed against the scan, RG, 2026-09-25) -- this
#: is a real compositor typo, understood as the rubles marker from
#: CONTEXT (its position in the figure, matching every other session's
#: "<rubles> р. <kopecks> к." shape corpus-wide) rather than any visual
#: resemblance to "р.", unlike the Latin-"p" case above. Same genuine-typo
#: class as the separately documented к./и./г. substitutions in
#: docs/eval/genuine_print_typos.md: RG's call is to leave it unparsed at
#: THIS layer, same as those (`receipts_text` verbatim, `receipts_rubles`/
#: `receipts_kopecks` empty, joining `receipts_parse_failed`) -- a
#: corrected numeric value for known genuine-typo cases like this belongs
#: in the `research` layer (derived via SQL only, per this project's
#: raw->analysis->entities->research layering), not baked into this
#: raw-tier parsing regex. Not yet built; when it is, this is the case
#: that motivated it.
_RUBLES_MARKER_RE = re.compile(r"\b[рp]\.?", re.IGNORECASE)

#: Same dropped-trailing-period gap as `_RUBLES_MARKER_RE`, just on the
#: kopecks side -- found 2026-09-17 doing the receipts-field audit
#: (docs/eval/known_issues.md #70): 7 sessions have receipts_text like
#: "2697 р. 70 к" (no period after "к"). The old literal `.replace("к.",
#: "")` silently left the marker in place ("70 к" instead of "70") since
#: it requires the exact "к." substring -- a real parsing gap, not
#: caught by the rubles-side fix since this is a different marker on the
#: other side of the same split. `\b` for the same reason as the rubles
#: marker (a bare `к` would also match inside an ordinary word). Also
#: accepts Latin "k"/"K", same reasoning and same 2026-09-17 finding as
#: the rubles marker above.
_KOPECKS_MARKER_RE = re.compile(r"\b[кk]\.?", re.IGNORECASE)

#: Genitive month name -> calendar length, for _backfill_month_year's
#: sanity check that a session's day number can't exceed its assigned
#: month's own length. Not a leap-year-aware calendar (February's 28 is
#: never actually hit as a start_month length check in this corpus, since
#: no page's own start_month is February with a day number that would
#: need this distinction) -- just enough precision for the one real case
#: this exists for.
_MONTH_LENGTH = {
    "января": 31, "февраля": 28, "марта": 31, "апрѣля": 30, "мая": 31,
    "іюня": 30, "іюля": 31, "августа": 31, "сентября": 30, "октября": 31,
    "ноября": 30, "декабря": 31,
}


def _parse_receipts(text: Optional[str]) -> tuple[str, str]:
    if not text:
        return "", ""
    try:
        rub_part, kop_part = _RUBLES_MARKER_RE.split(text.replace("—", "-"), maxsplit=1)
        kop = _KOPECKS_MARKER_RE.sub("", kop_part).strip()
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
    page.

    Assignment rule: a two-page-spread page's own day-number sequence
    resets from a high number back down near 1 exactly once, at the
    start/end-month boundary -- so any session whose own day number is
    >= the header's start_day belongs to start_month, and any session
    whose day number is < start_day (having wrapped around) belongs to
    end_month. This depends only on each session's own day number, not on
    where it sits in the sessions list -- deliberately NOT the file-order,
    walk-and-flip-on-decrease approach an earlier version of this function
    used, which assumed each theater's sessions are stored in chronological
    print order. That assumption turned out to be false for roughly a
    third of the two-page-spread corpus (confirmed by direct scan
    verification of all 88 pages, docs/eval/known_issues.md): cumulative
    manual out-of-order session fixes/insertions across this project left
    many theaters' session lists with day numbers that jump around rather
    than increasing monotonically, which made the old approach flip to
    end_month at the first stray out-of-order low day number and then
    mislabel every later, still-legitimately-start_month session for the
    rest of that theater's run.

    One more sanity check on top of the day>=start_day rule: a session day
    number that exceeds start_month's own calendar length (e.g. "31" on a
    page whose start_month is April, which only has 30 days) can't
    actually belong to start_month regardless of the threshold comparison
    -- it must be an end_month day instead (this surfaced on a real page,
    repertoire_1892-93_pair024, whose "мая"/May end_month legitimately has
    a 31st). _MONTH_LENGTH's February entry (28) is the common case only
    -- when start_month is "февраля" and the page's own start year is a
    Julian leap year (divisible by 4; no Gregorian century exception --
    this is the source calendar throughout, per dates.py), the length used
    here is bumped to 29, or a genuine "29 Суббота." row gets wrongly
    kicked into end_month by this same sanity check it exists to serve
    (confirmed on a real page, repertoire_1891-92_pair018, 1892 being a
    leap year: without this, Feb 29 gets reassigned to Mar 29, which
    lands on a different real weekday and fails validate_performance_
    dates.py's cross-check even though the original day>=start_day
    assignment was already correct).
    """
    if not page_header:
        return [(s.month_text or "", s.year_text or "") for s in sessions]

    start_month = page_header["start_month"]
    end_month = page_header["end_month"]
    year_text = page_header["year_text"]
    start_day = page_header.get("start_day")
    start_month_len = _MONTH_LENGTH.get(start_month)
    if start_month == "февраля" and start_month_len is not None:
        start_year_match = re.match(r"\d{4}", year_text or "")
        if start_year_match and int(start_year_match.group()) % 4 == 0:
            start_month_len = 29

    result: list[tuple[str, str]] = []
    for s in sessions:
        if s.month_text and s.year_text:
            result.append((s.month_text, s.year_text))
            continue
        if start_month == end_month or start_day is None:
            month = start_month
        else:
            day_str = _day_number(s.date_text)
            day_num = int(day_str) if day_str.isdigit() else None
            if day_num is not None and day_num < start_day:
                month = end_month
            elif (day_num is not None and start_month_len is not None
                  and day_num > start_month_len):
                month = end_month
            else:
                month = start_month
        result.append((s.month_text or month, s.year_text or year_text))

    return result


def _printed_page_for(page_id: str, date_undate: str,
                       printed_page_ranges: Optional[dict[str, list[tuple[str, str, str]]]]) -> str:
    """Looks up the verbatim printed page number for one session, from a
    small reference table built by scan-verifying every page (see
    docs/eval/known_issues.md's printed_page_number build-out). One CSV
    shape covers both season formats:

    - Single-page seasons (1898-99 onward): exactly one reference row per
      page_id, its [start_date, end_date] spanning the whole page -- always
      matches regardless of the session's own date.
    - Two-page-spread seasons (1890-91-1897-98): TWO reference rows share
      one page_id (one per physical printed half), each with a distinct,
      non-overlapping [start_date, end_date] sub-range and its own
      printed_page_number -- the session's own date_undate picks out which
      half it was actually printed on.

    A page_id missing from the reference table, or a date_undate that
    doesn't fall inside any of its ranges (an unparseable/missing date),
    returns "" rather than guessing -- same verbatim-in/best-effort-out
    contract as every other backfilled field here."""
    if not printed_page_ranges or page_id not in printed_page_ranges:
        return ""
    ranges = printed_page_ranges[page_id]
    if len(ranges) == 1:
        return ranges[0][2]
    if not date_undate:
        return ""
    for start_date, end_date, page_num in ranges:
        if start_date <= date_undate <= end_date:
            return page_num
    return ""


def flatten_repertoire_page(page_id: str, season: str, city: str, page: RepertoirePage,
                             page_header: Optional[dict] = None,
                             printed_page_ranges: Optional[dict[str, list[tuple[str, str, str]]]] = None
                             ) -> dict:
    events, performances = [], []
    backfilled = _backfill_month_year(page.sessions, page_header)
    for i, (s, (bf_month, bf_year)) in enumerate(zip(page.sessions, backfilled), start=1):
        event_id = f"{page_id}__s{i:03d}"
        rub, kop = _parse_receipts(s.receipts_text)
        theater = s.theater.strip().rstrip(".")  # strip table-header punctuation, keep the name
        event_city = _city_for_theater(theater, city)
        date_input = f"{_day_number(s.date_text)} {bf_month} {bf_year}".strip()
        date_undate = parse_russian_date(date_input) or ""
        events.append({
            "event_id": event_id, "page_id": page_id, "season": season, "city": event_city,
            "date_text": s.date_text, "month_text": s.month_text or "",
            "year_text": s.year_text or "",
            "date_undate": date_undate,
            "time_of_day": s.session, "theater": theater,
            "event_status": "no_performance" if s.is_dark else "performed",
            "receipts_text": s.receipts_text or "", "receipts_rubles": rub,
            "receipts_kopecks": kop, "annotation": s.annotation or "",
            "printed_page_number": _printed_page_for(page_id, date_undate, printed_page_ranges),
        })
        for j, w in enumerate(s.works, start=1):
            performances.append({
                "performance_id": f"{event_id}__w{j}", "event_id": event_id, "performance_order": j,
                "performance_title": w.work_title, "genre": w.genre or "",
            })
    return {"event_entry": events, "event_entry_performance": performances}
