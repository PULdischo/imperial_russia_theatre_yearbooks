"""Stage 5g (additive): validates raw.event_entry's date_undate
against the day-of-week printed alongside it in date_text, and corrects
the (surprisingly common) cases where it's wrong. See
docs/performance_normalization.md for the full investigation this
implements -- summary of what was actually found there, since the "why"
here depends on it:

- date_undate disagrees with its own printed weekday for 8.9% of rows
  (2,002/22,611), heavily concentrated in the 1891-92 through 1896-97
  seasons (13-45% mismatch there vs 0-4% elsewhere) -- a systematic
  extraction defect in those volumes, not scattered noise.
- Spot-checked directly against the source page image (repertoire_1890-91_
  p001): the PRINTED page is internally perfect: the defect is in
  extraction, not the original document. The specific failure mode is the
  day NUMBER drifting (under-counted) across a run of consecutive rows,
  while the weekday WORD stays reliably correct -- confirmed with a
  concrete example where a plausible-looking "shift the month back"
  fix would have silently replaced one wrong date with a different wrong
  one (1890-09-13 -> 1890-10-13, both land on a Saturday, but the real
  date was 1890-09-15).

That false-positive risk is why this only auto-corrects when >=2
consecutive mismatched rows agree on the same day-shift (a run) -- an
isolated single-row mismatch is exactly the case that produced a
confident wrong answer during the investigation, so it's never
auto-corrected here, only flagged.

Additive only: writes a new analysis.event_entry_date_check
table, does not touch raw.event_entry or the existing
analysis.event_entry (its completeness-reconciliation logic is a
separate, more complex piece of working code -- open question in the docs
about migrating it to corrected dates, not done here).

Usage:
    python pipeline/validate_performance_dates.py --db outputs/full_run/imperial_theaters.duckdb
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
from convertdate import julian

# Longest-prefix-first so e.g. "четверг" doesn't shadow-match before
# "четвергъ" gets a chance -- mirrors the same discipline as
# build_entities.py's ordinal-suffix regexes (don't guess from a partial
# match when a more specific one is available).
_DOW_PREFIXES = {
    'понедѣльник': 0, 'понед': 0, 'пон': 0,
    'вторник': 1, 'вторн': 1, 'втор': 1, 'вт': 1,
    'середа': 2, 'сред': 2, 'срѣд': 2,
    'четвергъ': 3, 'четверг': 3, 'четв': 3,
    'пятница': 4, 'пятниц': 4, 'пятн': 4,
    'суббота': 5, 'суббот': 5, 'субб': 5,
    'воскресенье': 6, 'воскресенiе': 6, 'воскрес': 6, 'воскр': 6,
    'недѣля': 6, 'недѣл': 6, 'вокрес': 6,
}
_DOW_ORDERED = sorted(_DOW_PREFIXES.items(), key=lambda kv: -len(kv[0]))

# Search width for an individual block's own candidate drifts. +/-7 spans
# a full week either side, wide enough to catch the two-week-adjacent
# coincidental match seen in the real data (Sept 13 -> Oct 13 both
# Saturday) -- deliberately wide so the majority-vote step below can see
# it and exclude it, not narrow enough to hide it.
_SEARCH_RADIUS = 7
# A drift is only ever auto-applied when this many blocks in a run
# independently agree on it -- the whole point of this module, per the
# false-positive found during the investigation (a single matching block
# is not enough evidence, confirmed the hard way).
_MIN_RUN_AGREEMENT = 2


def _parse_dow_word(word: str) -> int | None:
    t = word.lower().strip().rstrip('.').replace('ъ', '').replace('ь', '')
    for prefix, wd in _DOW_ORDERED:
        if t.startswith(prefix.replace('ъ', '').replace('ь', '')):
            return wd
    return None


def _parse_dow(date_text: str) -> int | None:
    m = re.match(r'^\d+\s*(.*)$', date_text.strip())
    if not m:
        return None
    return _parse_dow_word(m.group(1))


def _true_weekday(y: int, m: int, d: int) -> int:
    """Mon=0..Sun=6, verified against the well-documented October
    Revolution date (25 Oct 1917 Julian = 7 Nov 1917 Gregorian, a
    Wednesday) before trusting this library at all."""
    return julian.jwday(julian.to_jd(y, m, d))


def _shift_date(y: int, m: int, d: int, k: int) -> tuple[int, int, int]:
    """Shift a Julian-calendar date by k days via Julian Day Number
    arithmetic -- never constructs an intermediate calendar date directly
    (Python's datetime would reject e.g. a Julian-valid Feb 29 1900, which
    Gregorian doesn't have), and always returns a valid calendar date by
    construction, unlike incrementing a day field by hand."""
    return julian.from_jd(julian.to_jd(y, m, d) + k)


def validate_and_correct(con: duckdb.DuckDBPyConnection) -> dict:
    rows = con.execute("""
        SELECT event_id, page_id, date_text, date_undate
        FROM raw.event_entry
        ORDER BY page_id, event_id
    """).fetchall()

    # Group into date-blocks: the 5(-6) theaters sharing one printed date
    # label. First-seen order preserved per page, matching the printed
    # row order (event_id increments in printed order within a page).
    blocks: dict[tuple, list] = defaultdict(list)
    block_order: dict[str, list] = defaultdict(list)
    for event_id, page_id, date_text, date_undate in rows:
        if date_undate is None:
            continue
        key = (page_id, date_undate)
        if key not in blocks:
            block_order[page_id].append(key)
        blocks[key].append((event_id, date_text))

    results: dict[str, tuple] = {}

    for page_id, keys in block_order.items():
        block_infos = []
        for key in keys:
            _, date_undate = key
            members = blocks[key]
            distinct_texts = {dt for _, dt in members if dt is not None}
            y, m, d = map(int, date_undate.split('-'))
            info = {'key': key, 'y': y, 'm': m, 'd': d, 'members': members}
            if len(distinct_texts) != 1:
                info['status'] = 'intra_block_disagreement' if distinct_texts else 'unparseable'
                info['texts'] = distinct_texts
                block_infos.append(info)
                continue
            wd = _parse_dow(next(iter(distinct_texts)))
            if wd is None:
                info['status'] = 'unparseable'
                block_infos.append(info)
                continue
            try:
                true_wd = _true_weekday(y, m, d)
            except ValueError:
                # date_undate itself isn't a real calendar date (e.g.
                # 1902-11-31 -- November only has 30 days) -- a distinct,
                # smaller problem from a weekday mismatch, flagged
                # separately rather than crashing or silently mis-scoring.
                info['weekday'] = wd
                info['status'] = 'invalid_date'
                block_infos.append(info)
                continue
            info['weekday'] = wd
            info['status'] = 'verified' if true_wd == wd else 'mismatch'
            block_infos.append(info)

        # Find maximal runs of consecutive 'mismatch' blocks and resolve
        # each run as a unit -- not block by block -- since the whole
        # point of this design is that isolated single-block resolution
        # is unsafe (confirmed against a real example, see module
        # docstring).
        i, n = 0, len(block_infos)
        while i < n:
            if block_infos[i]['status'] != 'mismatch':
                i += 1
                continue
            j = i
            while j < n and block_infos[j]['status'] == 'mismatch':
                j += 1
            run = block_infos[i:j]

            for bi in run:
                cands = set()
                for k in range(-_SEARCH_RADIUS, _SEARCH_RADIUS + 1):
                    if k == 0:
                        continue
                    ny, nm, nd = _shift_date(bi['y'], bi['m'], bi['d'], k)
                    if _true_weekday(ny, nm, nd) == bi['weekday']:
                        cands.add(k)
                bi['candidates'] = cands

            vote = Counter(k for bi in run for k in bi['candidates'])
            best_k, best_count = (vote.most_common(1)[0] if vote else (None, 0))

            for bi in run:
                if best_count >= _MIN_RUN_AGREEMENT and best_k in bi['candidates']:
                    ny, nm, nd = _shift_date(bi['y'], bi['m'], bi['d'], best_k)
                    bi['status'] = 'corrected'
                    bi['corrected'] = (ny, nm, nd)
                    bi['drift'] = best_k
                else:
                    bi['status'] = 'unresolved'
            i = j

        for bi in block_infos:
            for event_id, _ in bi['members']:
                if bi['status'] == 'corrected':
                    ny, nm, nd = bi['corrected']
                    results[event_id] = (
                        'corrected', f'{ny:04d}-{nm:02d}-{nd:02d}', bi['drift'], None,
                    )
                elif bi['status'] == 'intra_block_disagreement':
                    results[event_id] = (
                        'intra_block_disagreement', None, None, ' | '.join(sorted(bi['texts'])),
                    )
                else:
                    results[event_id] = (bi['status'], None, None, None)

    # Sessions with no date_undate at all weren't in `blocks` above.
    all_ids = con.execute("SELECT event_id, date_undate FROM raw.event_entry").fetchall()
    for event_id, date_undate in all_ids:
        if event_id not in results:
            results[event_id] = ('no_date', None, None, None)

    con.execute("""
        CREATE OR REPLACE TABLE analysis.event_entry_date_check (
            event_id VARCHAR PRIMARY KEY,
            date_confidence VARCHAR,
            corrected_date_undate VARCHAR,
            drift_days INTEGER,
            note VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO analysis.event_entry_date_check VALUES (?, ?, ?, ?, ?)",
        [(sid, *vals) for sid, vals in results.items()],
    )
    return Counter(v[0] for v in results.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, type=Path)
    args = ap.parse_args()

    con = duckdb.connect(str(args.db))
    con.execute("CREATE SCHEMA IF NOT EXISTS analysis")
    counts = validate_and_correct(con)

    total = sum(counts.values())
    print(f"analysis.event_entry_date_check: {total} rows")
    for status, n in counts.most_common():
        print(f"  {status}: {n} ({n/total:.1%})")
    con.close()


if __name__ == "__main__":
    main()
