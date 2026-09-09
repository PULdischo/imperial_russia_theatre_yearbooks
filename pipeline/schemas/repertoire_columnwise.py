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


class MergeResult:
    """Outcome of aligning one theater column against the date column.

    Replaces the old `list | None` return (2026-09-08). `None` discarded a
    whole theater-page -- up to 20 reconciled days thrown away because one
    was ambiguous -- and measured at 79% loss on columns carrying any
    compound day (docs/eval/known_issues.md #69). Now the reconciled days
    are kept and only the ambiguous ones are reported in `unresolved`."""

    __slots__ = ("sessions", "unresolved", "n_date_days", "n_theater_rows", "reason")

    def __init__(self, sessions, unresolved, n_date_days, n_theater_rows, reason=""):
        self.sessions = sessions
        self.unresolved = unresolved
        self.n_date_days = n_date_days
        self.n_theater_rows = n_theater_rows
        self.reason = reason

    @property
    def ok(self) -> bool:
        return not self.unresolved and bool(self.sessions)


def _date_groups(dates: list[dict]) -> list[tuple[str, list[dict]]]:
    """Consecutive date-column rows sharing a date_text are one calendar day
    that the DATE column itself marked as split."""
    out: list[tuple[str, list[dict]]] = []
    for d in dates:
        if out and out[-1][0] == d["date_text"]:
            out[-1][1].append(d)
        else:
            out.append((d["date_text"], [d]))
    return out


def _theater_days(theater_rows: list[dict]) -> list[list[dict]]:
    """Groups one theater's rows into calendar days using the THEATER's own
    УТРО/ВЕЧ labels.

    This is the 2026-09-08 correction, and it reverses an assumption this
    module was built on. Session subdivision is NOT a property of the day --
    it is printed inside each theater's own cell, and one theater can split
    a day its neighbours print whole. Verified directly on
    repertoire_1898-99_p009's "25 Воскрес.": Большой and Малый each print
    one cell, while Новый prints two, with УТРО/ВЕЧ markers in a narrow
    strip inside NOVY's column. The date column carries no marker at all
    there -- correctly, since it reports DAYS.

    Asking the date column how many sessions a day has was therefore asking
    a question the page does not answer, and it is why theaters that split
    were refused: measured across 1898-99, the date column reported 42
    compound days while the theater columns' own labels reported 61.

    A `morning` row immediately followed by an `evening` row is one day
    printed as two sessions. Anything else is one row, one day.
    """
    rows = sorted(theater_rows, key=lambda r: r["index"])
    days: list[list[dict]] = []
    i = 0
    while i < len(rows):
        if (rows[i].get("session") == "morning"
                and i + 1 < len(rows)
                and rows[i + 1].get("session") == "evening"):
            days.append([rows[i], rows[i + 1]])
            i += 2
        else:
            days.append([rows[i]])
            i += 1
    return days


def merge_columnwise_page(date_rows: list[dict], theater: str,
                           theater_rows: list[dict],
                           month_text: str | None = None,
                           year_text: str | None = None) -> "MergeResult":
    """Aligns one theater's column against the date column's calendar.

    The date column supplies the DATE SEQUENCE and nothing else. How many
    sessions a given day holds is decided per theater, from that theater's
    own УТРО/ВЕЧ labels -- see `_theater_days` for the evidence that this,
    not the date column, is where the page marks it.

    Alignment is then one theater-day to one calendar date, in order. When
    the two counts agree, every date is filled. When they do not, the
    matching prefix and suffix are still emitted and only the region that
    cannot be placed is reported in `.unresolved` -- a mismatch means rows
    have shifted somewhere in the middle, so days on either side of it are
    still soundly anchored to the ends.

    Returns a `MergeResult`, never None: refusing a whole theater-page for
    one bad day discarded up to 20 good days and measured at 79% loss
    (docs/eval/known_issues.md #69).
    """
    dates = sorted(date_rows, key=lambda r: r["index"])
    calendar: list[tuple[str, str]] = []
    for d in dates:
        dt = d["date_text"]
        if calendar and calendar[-1][0] == dt:
            continue                      # date column occasionally repeats a day
        calendar.append((dt, d.get("session", "unspecified")))

    tdays = _theater_days(theater_rows)

    def emit(date_text, day_rows):
        if len(day_rows) == 2:
            return [_session_record(date_text, r.get("session", "unspecified"),
                                     theater, r, month_text, year_text)
                    for r in day_rows]
        return [_session_record(date_text, day_rows[0].get("session", "unspecified"),
                                 theater, day_rows[0], month_text, year_text)]

    n_cal, n_th = len(calendar), len(tdays)
    if n_cal == n_th:
        sessions = []
        for (dt, _), day in zip(calendar, tdays):
            sessions.extend(emit(dt, day))
        return MergeResult(sessions, [], n_cal, len(theater_rows))

    # Labels did not reconcile. They are not always emitted: measured over
    # 1898-99, Маріинскій returned 32/33 morning/evening pairs and Новый
    # 17/17, but Александринскій returned ONE label across 252 rows while
    # genuinely splitting days on 11 pages. So fall back to arithmetic,
    # using the date column's own compound days as the candidate split
    # positions -- the two sources are complementary rather than rival:
    # labels know which day split when present, the date column knows when
    # it marked one, and either alone leaves a different theater stranded.
    compound = [i for i, (_, g) in enumerate(_date_groups(dates)) if len(g) > 1]
    groups = _date_groups(dates)
    n_rows = len(theater_rows)
    needed = n_rows - len(groups)
    if 0 <= needed <= len(compound):
        plan = [1] * len(groups)
        if needed == len(compound):
            for idx in compound:
                plan[idx] = 2
        elif needed > 0:
            # Ambiguous which of the compound days split; do not guess.
            return MergeResult(
                [], [dt for dt, _ in groups], len(groups), n_rows,
                reason=(f"{needed} split(s) needed among {len(compound)} compound "
                        f"day(s), and no labels to say which"))
        rows_sorted = sorted(theater_rows, key=lambda r: r["index"])
        sessions, ti = [], 0
        for idx, (dt, grp) in enumerate(groups):
            take = plan[idx]
            chunk = rows_sorted[ti:ti + take]
            ti += take
            if take == 2 and len(grp) == 2:
                for k, dsub in enumerate(grp):
                    sessions.append(_session_record(
                        dt, dsub.get("session", "unspecified"), theater, chunk[k],
                        month_text, year_text))
            else:
                sessions.append(_session_record(
                    dt, grp[0].get("session", "unspecified") if len(grp) == 1 else "unspecified",
                    theater, chunk[0], month_text, year_text))
        return MergeResult(sessions, [], len(groups), n_rows)

    # Neither source explains the discrepancy, and it cannot be localised:
    # emitting a plausible-looking but wrongly-dated row is the failure this
    # whole date/theater split exists to prevent.
    return MergeResult(
        [], [dt for dt, _ in _date_groups(dates)], n_cal, len(theater_rows),
        reason=(f"{n_th} theater day(s) against {n_cal} calendar date(s); "
                f"{len(theater_rows)} row(s) -- cannot localise"))
