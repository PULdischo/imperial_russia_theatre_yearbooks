"""Pydantic models for the date-only and theater-only column-wise Repertoire
extraction (2026-09-01, docs/eval/known_issues.md #68). Two narrow, single-
column reads of the same page -- the date column alone establishes the row
sequence and session (morning/evening) labeling; each theater column alone
is read independently, with no date visible to it at all. A caller matches
the two by LIST POSITION rather than asking the model to re-attribute a
date to theater content, which is exactly the judgment call this approach
exists to avoid (see the module docstring precedent in row_detect.py and
the known_issues.md write-up for why: a composited date+theater crop with
an intervening theater column skipped over caused a real, reproducible
off-by-one date-boundary shift; separate crops matched by position fixed
it on both pages tested).

Deliberately NOT reusing SessionLLM/WorkLLM directly for either half --
neither model has a `theater` or `date_text` to give per row here (that's
the whole point), so `merge_columnwise_page` below is what actually builds
real SessionLLM-shaped dicts once date and theater sequences are matched up."""
from typing import Optional
from pydantic import BaseModel, Field

from .repertoire import SessionType, WorkLLM


class DateRowLLM(BaseModel):
    index: int
    date_text: str
    session: SessionType = "unspecified"


class DateOnlyPage(BaseModel):
    rows: list[DateRowLLM] = Field(default_factory=list)


class TheaterRowLLM(BaseModel):
    index: int
    works: list[WorkLLM] = Field(default_factory=list)
    receipts_text: Optional[str] = None
    annotation: Optional[str] = None
    is_dark: bool = False
    # Added 2026-09-01 (docs/eval/known_issues.md #68 addendum): confirmed
    # directly against the scan that compound УТРО/ВЕЧ subdivision is a
    # PER-THEATER property, not shared across the page -- on the same
    # date, one theater can print two separate performances while another
    # prints only one. Without this field, `merge_columnwise_page` had no
    # way to tell "this theater didn't split this compound day" (correct,
    # confirmed on repertoire_1898-99_p008's Михайловскій column) apart
    # from "the model merged two real sessions into one and lost the
    # first receipts figure" (a real bug, confirmed on the same page's
    # Александринскій column) -- both looked identical from outside: one
    # theater row where two were structurally possible.
    session: SessionType = "unspecified"


class TheaterOnlyPage(BaseModel):
    # The theater's own printed name, read from the header text visible at
    # the top of the crop -- NOT supplied by the caller. Manifest.csv has
    # no per-page theater-name list to fall back on, and the header is
    # already right there in the image the model is reading anyway.
    theater: str
    rows: list[TheaterRowLLM] = Field(default_factory=list)


def _session_record(date_text: str, session: str, theater: str, t: dict,
                     month_text: str | None, year_text: str | None) -> dict:
    return {
        "date_text": date_text,
        "month_text": month_text,
        "year_text": year_text,
        "session": session,
        "theater": theater,
        "is_dark": t.get("is_dark", False),
        "receipts_text": t.get("receipts_text"),
        "annotation": t.get("annotation"),
        "works": t.get("works", []),
    }


def merge_columnwise_page(date_rows: list[dict], theater: str,
                           theater_rows: list[dict],
                           month_text: str | None = None,
                           year_text: str | None = None) -> list[dict] | None:
    """Aligns one theater's rows against the date sequence by GROUPING the
    dates into calendar days first, then matching each day's theater
    row(s) by session label -- not by raw list position (2026-09-01
    redesign, docs/eval/known_issues.md #68 addendum; see `TheaterRowLLM`'s
    `session` field docstring for the confirmed evidence this replaces).

    A "compound" calendar day is 2 adjacent DateRowLLM entries sharing the
    same `date_text` (that's what session-splitting in the date column
    means). For each such day, three outcomes, checked in order:

    1. The next 2 theater rows' session labels are exactly {morning,
       evening} (a set, order-independent) -- this theater DOES split the
       day too. Match each date sub-row to the theater row with the same
       session label, consume both.
    2. The next 1 theater row is NOT itself a confident morning/evening
       match for a 2-way split (i.e. outcome 1 didn't apply) -- treat this
       as a theater that genuinely doesn't subdivide this particular day
       (confirmed real and correct on repertoire_1898-99_p008's
       Михайловскій column, which reads real content once where
       Маріинскій reads twice the same day). Emit ONE session record for
       the whole day rather than forcing a false split, consuming only 1
       theater row.
    3. Not enough theater rows remain to do either -- unresolved, same as
       any other real count mismatch.

    A simple (non-compound) day always consumes exactly 1 theater row.

    Returns None -- not a best-effort partial merge -- if theater rows run
    out early, or are left over at the end unconsumed: either means this
    theater's read still doesn't reconcile with the date column even
    session-aware, which is itself the signal the cross-check this feeds
    into is built to catch. This is deliberately conservative: outcome 1
    only fires on an EXACT, unambiguous session-label match -- anything
    murkier (e.g. both theater rows say "unspecified" when two real,
    distinct sessions plausibly exist) falls through to outcome 2 taking
    just one row, since guessing which of two ambiguous rows is which
    session is exactly the kind of silent misattribution this whole
    date/theater-split design exists to avoid."""
    dates = sorted(date_rows, key=lambda r: r["index"])
    theaters = sorted(theater_rows, key=lambda r: r["index"])

    date_groups: list[tuple[str, list[dict]]] = []
    for d in dates:
        if date_groups and date_groups[-1][0] == d["date_text"]:
            date_groups[-1][1].append(d)
        else:
            date_groups.append((d["date_text"], [d]))

    sessions = []
    ti = 0
    for date_text, group in date_groups:
        if len(group) == 1:
            if ti >= len(theaters):
                return None
            t = theaters[ti]; ti += 1
            sessions.append(_session_record(
                date_text, group[0].get("session", "unspecified"), theater, t,
                month_text, year_text))
            continue

        expected_sessions = {d.get("session", "unspecified") for d in group}
        if (ti + 1 < len(theaters)
                and {theaters[ti].get("session", "unspecified"),
                     theaters[ti + 1].get("session", "unspecified")} == expected_sessions
                and "unspecified" not in expected_sessions):
            by_session = {theaters[ti].get("session"): theaters[ti],
                          theaters[ti + 1].get("session"): theaters[ti + 1]}
            ti += 2
            for d in group:
                t = by_session[d.get("session", "unspecified")]
                sessions.append(_session_record(
                    date_text, d.get("session", "unspecified"), theater, t,
                    month_text, year_text))
        elif ti < len(theaters):
            t = theaters[ti]; ti += 1
            sessions.append(_session_record(
                date_text, "unspecified", theater, t, month_text, year_text))
        else:
            return None

    if ti != len(theaters):
        return None
    return sessions
