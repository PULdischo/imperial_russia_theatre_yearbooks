"""Gold-free structural self-consistency checks.

The 12-page gold set catches real errors, but it's 12 pages out of ~1,300 --
most of a full run will have no ground truth to compare against. These
checks don't need any: they look for internally-inconsistent or
structurally-implausible patterns in a single page's own extracted output,
which is exactly where the known VLM failure modes from the pilot run show
up (see docs/eval/known_issues.md):

- non-deterministic recall (dark/blank cells silently dropped)
- heading_path re-including the institution name
- a rank-class token left inside heading_path instead of service_class
- arithmetic inconsistency between category-total credits and their stated sum
- duplicate rows (possible double-extraction)
- inconsistent verbatim spelling of the same theater within one page

None of these prove an error on their own -- a page can legitimately have no
dark cells, or credit categories can legitimately not sum to the total if the
source itself doesn't (e.g. mixed seasons). They're triage signals: flagged
pages are exactly the ones worth a human glance before trusting them, so the
review budget for a full run goes to the highest-risk pages instead of a
uniform random sample.

Usage:
    python pipeline/quality_checks.py --parsed-dir outputs/pilot/parsed \
        --out outputs/pilot/quality_flags.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

RANK_CLASS_RE = re.compile(r",?\s*[IVXLC]+\s*кл\.?:?\s*$", re.IGNORECASE)

#: The theater names Repertoire pages actually contain, this season and
#: every other one checked so far. Used three ways in this file: matching
#: verbatim spelling variants of the same theater (check_repertoire),
#: normalizing for cross-extraction cell comparison (_normalize_theater),
#: and -- 2026-09-01 -- flagging a `theater` field that matches NONE of
#: these, which is itself a signal (docs/eval/known_issues.md #68
#: addendum: repertoire_1898-99_p016 had a work title in the theater
#: field instead of a real theater name).
KNOWN_THEATERS = ["Маріинскій", "Александринскій", "Михайловскій", "Большой", "Малый", "Новый"]


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(open(path, encoding="utf-8")))


def by_page(rows: list[dict]) -> dict[str, list[dict]]:
    d = defaultdict(list)
    for r in rows:
        d[r["page_id"]].append(r)
    return d


def check_roster(parsed_dir: Path) -> list[dict]:
    flags = []
    entries = load(parsed_dir / "person_entry.csv")
    credits = load(parsed_dir / "person_entry_credit.csv")
    credits_by_entry = defaultdict(list)
    for c in credits:
        credits_by_entry[c["entry_id"]].append(c)

    seen_in_page = defaultdict(set)  # page_id -> {(family, first, patronymic)}
    for e in entries:
        page_id, entry_id = e["page_id"], e["entry_id"]
        heading_path, institution = e.get("heading_path", ""), e.get("institution", "")
        family, first, patr = e.get("family_name", ""), e.get("first_name", ""), e.get("patronymic", "")

        if institution and heading_path and institution.strip() in heading_path:
            flags.append(dict(page_id=page_id, table="person_entry", row_id=entry_id,
                               flag="institution_duplicated_in_heading_path",
                               detail=f"institution={institution!r} heading_path={heading_path!r}"))

        if RANK_CLASS_RE.search(heading_path or "") and not e.get("service_class", "").strip():
            flags.append(dict(page_id=page_id, table="person_entry", row_id=entry_id,
                               flag="rank_class_left_in_heading_path",
                               detail=f"heading_path={heading_path!r}"))

        key = (family.strip(), first.strip(), patr.strip())
        if family.strip() and key in seen_in_page[page_id]:
            flags.append(dict(page_id=page_id, table="person_entry", row_id=entry_id,
                               flag="duplicate_person_on_page", detail=str(key)))
        seen_in_page[page_id].add(key)

    for entry_id, rows in credits_by_entry.items():
        # Sequential block-scan, not a label->row dict (docs/eval/known_issues.md
        # #24): category_totals rows print in order, and a "Всего" row closes
        # out only the components seen since the *previous* "Всего" (or the
        # start of the entry) -- not the whole entry. An artist who performed
        # in more than one city prints more than one "Всего" in the same
        # credit_summary_text (e.g. a Moscow tally, then "Кромѣ того въ
        # С.-Петербургѣ: ..." with its own tally) -- collapsing same-labeled
        # rows across those blocks into a dict silently discards one block's
        # number entirely rather than checking each block against its own
        # total, which is what produced most of the originally-flagged
        # false-positive credit_sum_mismatch entries.
        block_components: list[dict] = []
        for r in rows:
            if r["credit_type"] != "category_totals":
                continue
            if r["label"] != "Всего":
                block_components.append(r)
                continue
            try:
                component_sum = sum(int(c["category_credit_count"]) for c in block_components
                                     if c["category_credit_count"])
                stated = int(r["category_credit_count"])
                if block_components and component_sum != stated:
                    page_id = rows[0]["entry_id"].split("__e")[0]
                    flags.append(dict(page_id=page_id, table="person_entry_credit", row_id=entry_id,
                                       flag="credit_sum_mismatch",
                                       detail=f"components sum to {component_sum}, stated Всего={stated}"))
            except (ValueError, KeyError):
                pass  # non-numeric count -- a different problem, not this check's job
            block_components = []

    return flags


def check_repertoire(parsed_dir: Path) -> list[dict]:
    flags = []
    events = by_page(load(parsed_dir / "event_entry.csv"))

    for page_id, rows in events.items():
        dark_count = sum(1 for r in rows if r.get("event_status", "").strip() == "no_performance")
        days = {r["date_text"].split()[0] for r in rows if r.get("date_text")}
        if dark_count == 0 and len(days) >= 6:
            flags.append(dict(page_id=page_id, table="event_entry", row_id="",
                               flag="zero_dark_cells_on_multiweek_page",
                               detail=f"{len(rows)} events across {len(days)} distinct days, none dark -- "
                                      f"real tables almost always have at least one dark day (e.g. Saturdays); "
                                      f"suspect the model silently dropped blank cells this run"))

        seen_keys = set()
        for r in rows:
            key = (r["date_text"].strip(), r["theater"].strip(), r["time_of_day"])
            if key in seen_keys:
                flags.append(dict(page_id=page_id, table="event_entry", row_id=r["event_id"],
                                   flag="duplicate_event_key", detail=str(key)))
            seen_keys.add(key)

            if r.get("receipts_text", "").strip() and not r.get("receipts_rubles", "").strip():
                flags.append(dict(page_id=page_id, table="event_entry", row_id=r["event_id"],
                                   flag="receipts_parse_failed",
                                   detail=f"receipts_text={r['receipts_text']!r} but receipts_rubles is empty"))

        theater_variants = defaultdict(set)
        for r in rows:
            t = r["theater"].strip()
            for name in KNOWN_THEATERS:
                if t.startswith(name):
                    theater_variants[name].add(t)
        for name, variants in theater_variants.items():
            if len(variants) > 1:
                flags.append(dict(page_id=page_id, table="event_entry", row_id="",
                                   flag="inconsistent_theater_spelling_on_page",
                                   detail=f"{name}: saw {sorted(variants)} within the same page"))

    return flags


def _normalize_theater(theater: str) -> str:
    """Matches by PREFIX against the same known-theater list check_repertoire
    uses, for the same reason: `театръ`/`театр` (pre-reform ъ present or
    dropped) and other verbatim punctuation/spelling variance would
    otherwise make two extractions' identical theater disagree as dict
    keys purely on spelling, confirmed a real issue testing this check
    (2026-09-01) -- column-wise extraction returned "Малый театр." (no ъ)
    against baseline/row-level's "Малый театръ." for the same page. This
    is about grouping cells for comparison, not correcting the verbatim
    value anywhere -- raw.person_entry-style verbatim preservation is a
    roster-layer concern; here it would just make every row for that
    theater falsely register as a disagreement between reads that
    actually agree."""
    for name in KNOWN_THEATERS:
        if theater.strip().startswith(name):
            return name
    return theater.strip()


def _load_sessions_by_cell(raw_json_path: Path) -> dict[tuple, str | None] | None:
    if not raw_json_path.exists():
        return None
    d = json.loads(raw_json_path.read_text(encoding="utf-8"))
    by_cell = {}
    for s in d.get("sessions", []):
        key = (
            (s.get("date_text") or "").strip().rstrip("."),
            _normalize_theater(s.get("theater") or ""),
            s.get("session", "unspecified"),
        )
        by_cell[key] = s.get("receipts_text")
    return by_cell


def check_repertoire_cross_extraction(page_raw_dir: Path | None, row_raw_dir: Path | None,
                                       column_raw_dir: Path | None) -> list[dict]:
    """Compares up to three independent Repertoire extractions of the same
    pages -- full-page baseline, row-isolated, column-wise (known_issues.md
    #68) -- and flags every (date, theater, session) cell where the reads
    that exist disagree. Each extraction method fails in a DIFFERENT way
    (page-level: attention-across-a-big-grid fabrication; row-level:
    cross-date contamination from a bad detected boundary; column-wise:
    its own isolated misreadings), confirmed directly rather than assumed
    -- so disagreement between them is a real, cheap signal, though not a
    complete one: two methods have been observed to independently make
    the *identical* wrong attribution on the same page (known_issues.md
    #68's "24 Среда" case), so agreement between exactly two reads is
    evidence, not proof. Every value is recorded in `detail`, not just a
    pass/fail flag, precisely so a 2-way and a 3-way disagreement both
    stay visible with what each read actually said, per RG's explicit
    request (2026-09-01) not to collapse that down to a single signal.

    Works from the raw *.raw.json files directly (before parse_and_
    validate.py's repair/cleanup passes), on purpose: the point is
    finding where the independent extractions themselves disagree, not
    where they land after downstream cleanup might paper over it.

    Any of the three directories may be None or simply not have a given
    page_id yet -- compares whatever's actually available for each page,
    skipping pages with fewer than 2 reads (nothing to compare)."""
    flags = []
    all_page_ids = set()
    dirs = {"page": page_raw_dir, "row": row_raw_dir, "column": column_raw_dir}
    for d in dirs.values():
        if d and d.exists():
            all_page_ids.update(p.stem.replace(".raw", "") for p in d.glob("*.raw.json"))

    for page_id in sorted(all_page_ids):
        sources = {}
        for name, d in dirs.items():
            if not d:
                continue
            by_cell = _load_sessions_by_cell(d / f"{page_id}.raw.json")
            if by_cell is not None:
                sources[name] = by_cell
        if len(sources) < 2:
            continue

        all_keys = set()
        for by_cell in sources.values():
            all_keys.update(by_cell.keys())

        for key in sorted(all_keys):
            values = {name: by_cell.get(key, "<missing>") for name, by_cell in sources.items()}
            if len(set(values.values())) > 1:
                date_text, theater, session = key
                flags.append(dict(
                    page_id=page_id, table="event_entry", row_id="",
                    flag="cross_extraction_disagreement",
                    detail=f"{date_text} / {theater} / {session}: {values}",
                ))
    return flags


def check_repertoire_rowlevel_duplicates(row_raw_dir: Path | None) -> list[dict]:
    """Flags a (date, theater, session) key that appears more than once
    within a SINGLE row-level page's own raw JSON -- catches the failure
    mode found 2026-09-01 (docs/eval/known_issues.md #68 addendum) on
    repertoire_1898-99_p014 without needing a second extraction to
    compare against: when `detect_rows` can't find a real boundary
    anywhere across a stretch of the page (confirmed there: literally no
    candidate line, not just a weak one, across ~430px covering 7 real
    dated rows), the resulting oversized, severely-compressed crop can
    still get its financial/title content read correctly by the model
    (verified against the scan) while every entry in the compressed
    region gets mislabeled with the ONE date still rendered at full,
    legible size elsewhere in the same crop -- producing several
    real-but-differently-dated rows that all claim the same
    (date, theater, session) key.

    Deliberately keyed on (date, theater, session), not just
    (date, theater): a genuine compound УТРО/ВЕЧ row legitimately
    produces two session dicts sharing the same date and theater, one
    `session="morning"` and one `"evening"` -- that's real content, not
    the bug, and including session in the key is what keeps it from
    being flagged. The confirmed bug instance repeated the same
    session value (`"unspecified"`) across every duplicate, which this
    key still catches.

    Works from row-level raw JSON directly (before parse_and_validate.py
    would even see it) on purpose, same rationale as
    `check_repertoire_cross_extraction`: this is a much cheaper, earlier
    signal than a second extraction pass or a full parse -- one page's
    own row-level output is enough to raise it."""
    flags = []
    if not row_raw_dir or not row_raw_dir.exists():
        return flags

    for raw_path in sorted(row_raw_dir.glob("*.raw.json")):
        page_id = raw_path.stem.replace(".raw", "")
        d = json.loads(raw_path.read_text(encoding="utf-8"))
        sessions = d.get("sessions", [])
        if not sessions:
            continue
        # Can't reuse _load_sessions_by_cell here -- it collapses to one
        # value per key, and the whole point of this check is the count
        # per key, not the (single, already-deduped) value.
        counts = defaultdict(list)
        for s in d.get("sessions", []):
            key = (
                (s.get("date_text") or "").strip().rstrip("."),
                _normalize_theater(s.get("theater") or ""),
                s.get("session", "unspecified"),
            )
            counts[key].append(s.get("receipts_text"))

        for key, receipts in counts.items():
            if len(receipts) > 1:
                date_text, theater, session = key
                flags.append(dict(
                    page_id=page_id, table="event_entry", row_id="",
                    flag="rowlevel_duplicate_date_theater_key",
                    detail=f"{date_text} / {theater} / {session} appears "
                           f"{len(receipts)}x in one row-level extraction "
                           f"-- receipts seen: {receipts}",
                ))
    return flags


def _modernize(s: str) -> str:
    """Normalizes pre-reform і to modern и for comparison only -- never
    to correct a verbatim value, just to detect when a theater field IS
    a real theater name that got partially or fully modernized. 2026-09-01:
    "Маріинскій" contains TWO і's (one mid-word, one right before the
    final й), and the model was found modernizing only ONE of them
    ("Мариинскій", not the fully-modernized "Мариинский") -- confirmed by
    checking the actual character codes, not assumed. A one-shot exact-
    match against a single fully-modernized spelling missed this partial
    case entirely; normalizing both sides before comparing catches any
    mix of modernized/preserved і's within the same word."""
    return s.replace("і", "и")


#: KNOWN_THEATERS pre-normalized once, so check_repertoire_unknown_theater
#: doesn't re-modernize the same 6 short strings on every session checked.
_MODERNIZED_THEATERS = {_modernize(name): name for name in KNOWN_THEATERS}


def check_repertoire_unknown_theater(raw_dir: Path | None) -> list[dict]:
    """Flags a session's `theater` field for one of two DISTINCT reasons,
    kept as separate flag types on purpose (see `_MODERNIZED_THEATERS`):

    `modernized_theater_spelling` -- the field matches a KNOWN_THEATERS
    name once і is normalized to и, meaning the model wrote the modern
    spelling instead of the pre-reform one this project requires
    preserved verbatim. Confirmed real 2026-09-01: 14 instances of
    "Мариинскій театръ" across 6 pages, each one a genuine theater
    (not a structural bug) just spelled wrong for this corpus.

    `unrecognized_theater_field` -- the field doesn't match ANY
    KNOWN_THEATERS name even after that normalization. Confirmed real
    2026-09-01 on repertoire_1898-99_p016 (docs/eval/known_issues.md #68
    addendum): row-level output had a WORK TITLE ("Евгеній Онѣгинъ,
    оп.") in the theater field for several sessions, with the real work
    title landing in `works` under a different entry instead -- a
    column-shift, not caught by the duplicate-key check (which only
    compares theater values against each other, not against what a
    theater name should look like).

    Works against any raw *.raw.json directory (baseline, row-level, or
    column-wise) -- this check isn't specific to one extraction method,
    unlike the duplicate-key check, which is a row-level-only artifact."""
    flags = []
    if not raw_dir or not raw_dir.exists():
        return flags

    for raw_path in sorted(raw_dir.glob("*.raw.json")):
        page_id = raw_path.stem.replace(".raw", "")
        d = json.loads(raw_path.read_text(encoding="utf-8"))
        for i, s in enumerate(d.get("sessions", []), start=1):
            theater = (s.get("theater") or "").strip()
            if not theater or any(theater.startswith(t) for t in KNOWN_THEATERS):
                continue
            row_id = f"{page_id}__s{i:03d}"
            theater_modernized = _modernize(theater)
            modernized_match = next(
                (canonical for modern, canonical in _MODERNIZED_THEATERS.items()
                 if theater_modernized.startswith(modern)), None)
            if modernized_match:
                flags.append(dict(
                    page_id=page_id, table="event_entry", row_id=row_id,
                    flag="modernized_theater_spelling",
                    detail=f"theater={theater!r} uses modern и where this corpus's "
                           f"pre-reform spelling is {modernized_match!r} (with і)",
                ))
            else:
                flags.append(dict(
                    page_id=page_id, table="event_entry", row_id=row_id,
                    flag="unrecognized_theater_field",
                    detail=f"theater={theater!r} matches none of {KNOWN_THEATERS} even "
                           f"modernized -- date={s.get('date_text')!r} "
                           f"receipts={s.get('receipts_text')!r} "
                           f"works={[w.get('work_title') for w in (s.get('works') or [])]}",
                ))
    return flags


#: A well-formed receipts figure always carries a rubles UNIT MARKER --
#: "р." (Cyrillic) or, per known_issues.md #15, occasionally "p." (Latin,
#: a confirmed OCR/model substitution this corpus already has to parse
#: around positionally rather than by unit letter). This is deliberately
#: permissive about everything else -- kopecks may be a number, the
#: dash-for-zero convention (e.g. "2710 р. — к."), or entirely blank; and,
#: confirmed against the scan 2026-09-10 (known_issues.md #69), the
#: RUBLES figure itself is sometimes printed with no digit at all -- a
#: dash ("— р. — к.", a Chaliapin benefit night with no box-office figure
#: printed) or plain blank space ("р.    к.", a УТРО session of a
#: compound day with nothing recorded) are both genuine, verbatim-correct
#: printed conventions, not truncation. Earlier this required a digit
#: immediately before the marker (`\d\s*[рp]\.?`), which flagged both of
#: those as malformed -- contradicting this check's own intent (stated
#: below) of only checking that a marker is present at all, not what
#: precedes it. Now checks for the marker alone -- and the trailing
#: period stays optional (re-confirmed 2026-09-10 fixing the digit
#: requirement above first made the period mandatory instead, which
#: immediately produced 60+ new false positives: this corpus's genuine
#: "р"/"p" marker is followed just as often by a comma, a dash, a colon,
#: or nothing at all as by a period -- a punctuation detail with no
#: bearing on whether the figure itself is malformed).
_RECEIPTS_UNIT_RE = re.compile(r"[рp]\.?", re.IGNORECASE)


def check_repertoire_malformed_receipts(raw_dir: Path | None) -> list[dict]:
    """Flags a `receipts_text` that's bare digits with no rubles unit
    marker at all -- e.g. `"2086"` instead of `"2086 р. — к."`. Confirmed
    real 2026-09-09 (docs/eval/known_issues.md #69 Gate 3 addendum) on a
    handful of pages per season (e.g. repertoire_1904-05_p000/p008,
    repertoire_1903-04_p030) -- concentrated on specific pages rather
    than scattered at random, so a real per-page signal worth routing to
    review rather than noise. Not a crop/divider issue (those produce
    truncated-from-the-EDGE figures like "611 р. 7", still carrying a
    unit marker) -- this is the model dropping the unit text entirely
    while keeping the number itself intact, a different failure mode.

    Works against any raw *.raw.json directory, matching
    check_repertoire_unknown_theater's scope -- this failure mode isn't
    specific to column-wise extraction and could recur on any method."""
    flags = []
    if not raw_dir or not raw_dir.exists():
        return flags

    for raw_path in sorted(raw_dir.glob("*.raw.json")):
        page_id = raw_path.stem.replace(".raw", "")
        d = json.loads(raw_path.read_text(encoding="utf-8"))
        for i, s in enumerate(d.get("sessions", []), start=1):
            rt = (s.get("receipts_text") or "").strip()
            if not rt or _RECEIPTS_UNIT_RE.search(rt):
                continue
            flags.append(dict(
                page_id=page_id, table="event_entry", row_id=f"{page_id}__s{i:03d}",
                flag="malformed_receipts_missing_unit",
                detail=f"receipts_text={rt!r} has no р./p. rubles marker -- "
                       f"date={s.get('date_text')!r} theater={s.get('theater')!r}",
            ))
    return flags


def check_repertoire_cross_theater_date_mismatch(raw_dir: Path | None) -> list[dict]:
    """Flags a page where theaters disagree on the DATE SEQUENCE the page
    covers -- the direct, single-page signal for the "date-only under-
    splits a compound day, shifting every subsequent date" failure mode
    confirmed 2026-09-10 on repertoire_1902-03_p024 (docs/eval/
    known_issues.md #69 addendum). On column-wise extraction specifically,
    `merge_columnwise_page` aligns each theater INDEPENDENTLY against the
    same date-only calendar (pipeline/schemas/repertoire_columnwise.py):
    when that calendar under- or over-counts a compound day, different
    theaters can land on different outcomes depending on whether their own
    row count happened to match the (wrong) calendar length or instead
    fell through to the compound-day reconciliation fallback -- producing
    exactly the disagreement this check looks for. The underlying
    invariant it checks -- one printed table, one shared calendar, every
    theater column reporting the same days -- holds regardless of
    extraction method, so this runs against any raw_dir, matching
    check_repertoire_unknown_theater's scope.

    Compares the DISTINCT date_text sequence per theater, with consecutive
    repeats of the same date_text collapsed to one -- a genuine compound
    морн./веч. day legitimately repeats one date_text twice in a row in
    the session list, and that repetition is not the signal here. Row
    COUNT is deliberately not compared: theaters legitimately differ in
    whether they split a given day into two sessions (confirmed
    per-theater, not per-page -- see `_theater_days`'s docstring in
    repertoire_columnwise.py), so a 13-row Маріинскій column and a 12-row
    Александринскій column on the same page are both correct provided the
    underlying dates they cover are identical and in the same order,
    which is what's actually checked.

    Calibrated against real data, not a guessed tolerance: 0 mismatches
    across 263 Gate 3 pages with 2+ theaters once the divider/crop fixes
    were in place (2026-09-10) -- full cross-theater date-sequence
    agreement is the observed norm on a correctly-extracted page, not an
    approximation worth padding with slack.

    ADDENDUM (2026-09-10, the repair pass in known_issues.md #69):
    comparing date_text VERBATIM stopped being safe once a page can mix
    an originally-successful theater's sessions with another theater's
    sessions recovered from an independent resample or a baseline
    fallback call -- two independent reads of the same calendar
    legitimately spell it differently ("13 Среда" vs "13 Среда.", "14
    Четвергъ" vs "14 Четвергь", ъ/ь being a common OCR-adjacent
    substitution) without the underlying day being wrong at all.
    Confirmed directly: 92 of a sample of 109 post-repair flags were this
    exact cosmetic variance, not a real shift. Now compares only each
    date_text's LEADING DIGIT RUN (the day number) -- the one substring
    that must be identical whether or not two calls agree on trailing
    weekday spelling/punctuation -- while still reporting the original,
    unmodified strings in `detail` for a human to read."""
    flags = []
    if not raw_dir or not raw_dir.exists():
        return flags

    day_number_re = re.compile(r"^\d+")

    for raw_path in sorted(raw_dir.glob("*.raw.json")):
        page_id = raw_path.stem.replace(".raw", "")
        d = json.loads(raw_path.read_text(encoding="utf-8"))
        by_theater = defaultdict(list)
        for s in d.get("sessions", []):
            theater = _normalize_theater(s.get("theater") or "")
            date_text = (s.get("date_text") or "").strip()
            if not theater or not date_text:
                continue
            by_theater[theater].append(date_text)

        if len(by_theater) < 2:
            continue

        def dedupe(seq: list[str]) -> list[str]:
            out: list[str] = []
            for x in seq:
                if not out or out[-1] != x:
                    out.append(x)
            return out

        def day_numbers(seq: list[str]) -> tuple:
            out = []
            for x in seq:
                m = day_number_re.match(x)
                out.append(m.group() if m else x)
            return tuple(out)

        sequences = {t: dedupe(v) for t, v in by_theater.items()}
        distinct = {day_numbers(v) for v in sequences.values()}
        if len(distinct) > 1:
            flags.append(dict(
                page_id=page_id, table="event_entry", row_id="",
                flag="cross_theater_date_mismatch",
                detail=f"{len(distinct)} distinct date sequences across theaters "
                       f"on this page (compared by day number): {sequences}",
            ))
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--page-raw-dir", type=Path, default=None,
                     help="full-page baseline *.raw.json directory, for "
                          "check_repertoire_cross_extraction")
    ap.add_argument("--row-raw-dir", type=Path, default=None,
                     help="row-isolated *.raw.json directory (run_pilot.py "
                          "--row-level's --out-dir), for "
                          "check_repertoire_cross_extraction and "
                          "check_repertoire_rowlevel_duplicates (the latter "
                          "needs only this one directory, no second "
                          "extraction to compare against)")
    ap.add_argument("--column-raw-dir", type=Path, default=None,
                     help="column-wise *.raw.json directory (run_pilot.py "
                          "--column-level's --out-dir), for the same check")
    args = ap.parse_args()

    flags = check_roster(args.parsed_dir) + check_repertoire(args.parsed_dir)
    if args.page_raw_dir or args.row_raw_dir or args.column_raw_dir:
        flags += check_repertoire_cross_extraction(
            args.page_raw_dir, args.row_raw_dir, args.column_raw_dir)
    if args.row_raw_dir:
        flags += check_repertoire_rowlevel_duplicates(args.row_raw_dir)
    for raw_dir in (args.page_raw_dir, args.row_raw_dir, args.column_raw_dir):
        flags += check_repertoire_unknown_theater(raw_dir)
        flags += check_repertoire_malformed_receipts(raw_dir)
        flags += check_repertoire_cross_theater_date_mismatch(raw_dir)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page_id", "table", "row_id", "flag", "detail"])
        w.writeheader()
        w.writerows(flags)

    by_flag = defaultdict(int)
    for fl in flags:
        by_flag[fl["flag"]] += 1
    print(f"{len(flags)} flags -> {args.out}")
    for flag_type, n in sorted(by_flag.items(), key=lambda x: -x[1]):
        print(f"  {flag_type}: {n}")


if __name__ == "__main__":
    main()
