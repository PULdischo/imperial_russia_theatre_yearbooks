"""Stage 3: parse + validate raw model JSON (from run_pilot.py / extract.py)
into the flat, schema-conformant tables from docs/schema.md, merged across
every page in the manifest. Rows that fail validation are logged to
validation_errors.csv, never silently dropped -- and never crash the run for
every OTHER page.

Usage:
    python pipeline/parse_and_validate.py --manifest docs/eval/gold/source_pages.csv \
        --raw-dir outputs/pilot/raw --out-dir outputs/pilot/parsed
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schemas import RosterPage, RepertoirePage, flatten_roster_page, flatten_repertoire_page

ROSTER_KINDS = {"Administrators", "BalletArtists", "Musicians", "ProductionTeam",
                "TheaterSchoolStaff", "Graduates"}

# The model occasionally writes the printed Russian session label instead of
# the normalized English enum value the schema expects (rare: ~80/23000
# repertoire sessions). This is a categorical field, not verbatim text, so
# normalizing here is correct rather than a verbatim-preservation violation.
SESSION_LABEL_FIX = {"утро": "morning", "вечеръ": "evening", "день": "unspecified"}

# Matches pipeline/extract_page_headers.py's verbatim header_text, e.g.
# "16 февраля. 1908 г. 23 февраля." or a season-spanning "28 декабря.
# 1905—1906 гг. 5 января." -- see docs/eval/known_issues.md #69's
# "event-date field audit" addendum for why this exists (flatten_repertoire_
# page's per-session date_undate has no cross-row month/year inheritance,
# leaving ~80-87% of column-wise-extracted sessions with no date at all).
_PAGE_HEADER_RE = re.compile(
    r"^\s*(\d{1,2})\s+([а-яёіѣ]+)\.?\s*,?\s*"
    r"(\d{4}(?:\s*[—\-–]\s*\d{4})?\s*(?:г\.?г?\.?|гг\.?))\s+"
    r"(\d{1,2})\s+([а-яёіѣ]+)\.?\s*$",
    re.IGNORECASE,
)


# One page's own printed header genuinely has its two month names swapped
# from calendar order -- confirmed against the scan (repertoire_1902-03_p008:
# "22 ноября. 1902 г. 3 октября.", verbatim, both months clearly legible;
# the table's OWN internal "Ноябрь" divider row, printed between day 31 and
# day 1, proves the true order is October 22 - November 3, not the reverse).
# A genuine one-off (checked: no other page in the corpus has a header whose
# end-month falls chronologically before its start-month without a
# Dec->Jan year wrap) -- not worth generalizing into swap-detection logic
# that would risk misfiring on a page that genuinely needs the order it
# printed. page_header_dates.csv keeps the verbatim header text forever;
# this override only ever corrects the *derived* month assignment used to
# backfill date_undate, exactly the same verbatim-in/best-effort-derived-out
# split as _MANUAL_DATE_OVERRIDES in validate_performance_dates.py.
_PAGE_HEADER_MONTH_SWAP_FIX = {
    "repertoire_1902-03_p008": ("октября", "ноября"),
}


def load_page_headers(path: Path) -> dict[str, dict]:
    """Parses pipeline/extract_page_headers.py's output CSV into
    {page_id: {"start_month": ..., "end_month": ..., "year_text": ...,
    "start_day": ...}} for flatten_repertoire_page's page_header argument.
    A header_text that doesn't match the expected shape is skipped (not
    raised) -- the page just falls back to per-session month_text/year_text
    only, same as before this argument existed, rather than failing the
    whole run over one page's unusual header.

    start_day is kept (not just start_month/end_month/year_text) because
    _backfill_month_year assigns each session's month by comparing its own
    day number against start_day, not by walking session order -- see that
    function's docstring for why (docs/eval/known_issues.md's two-page-
    spread date_undate backfill: ~1/3 of pages have session lists that
    aren't stored in chronological order per theater, from cumulative
    manual out-of-order session fixes, which broke the original file-order
    rollover-detection approach)."""
    headers: dict[str, dict] = {}
    for row in csv.DictReader(open(path, encoding="utf-8")):
        page_id = row["page_id"]
        text = (row.get("header_text") or "").strip()
        m = _PAGE_HEADER_RE.match(text)
        if not m:
            continue
        start_day, start_month, year_text, _end_day, end_month = m.groups()
        if page_id in _PAGE_HEADER_MONTH_SWAP_FIX:
            start_month, end_month = _PAGE_HEADER_MONTH_SWAP_FIX[page_id]
        headers[page_id] = {
            "start_month": start_month, "end_month": end_month, "year_text": year_text,
            "start_day": int(start_day),
        }
    return headers

# Rare (~4/20000 roster entries) recurring model failure: when a row has no
# heading of its own to repeat, the model sometimes puts the person's full
# name ("Surname, First Patronymic") into heading_path and leaves
# family_name/first_name/patronymic empty, using the row's actual heading
# text as `institution` instead. Recoverable deterministically since the
# "Surname, First [Patronymic]" shape doesn't occur in real heading_path
# values (those are always institution/department/role segments).
NAME_IN_HEADING_RE = re.compile(
    r"^((?:(?:Графъ|Графиня|Князь|Княгиня|Баронъ|Баронесса)\s+)?"
    r"[А-ЯЁІѢѲѴ][а-яёіѣѳѵ\-]+(?:\s+\d+-(?:й|я|е))?),\s+"
    r"([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+)(?:\s+([А-ЯЁІѢѲѴ][а-яёіѣѳѵ]+))?"
    r"(?:,\s*(.+))?$"
)

# Graduates (theater-school report) pages print each graduating class as a
# plain name list followed by ONE trailing sentence giving the shared
# appointment date for the whole list ("Всѣ N человѣкъ... опредѣлены на
# службу... съ [date]..."). The per-entry extraction schema has nowhere to
# put a note covering N people at once, so the model either drops it, or --
# when the list spans a page break -- attaches it only to the half sharing
# its page. docs/ballet_graduates_tenure.csv (docs/ballet_graduates.md,
# docs/eval/known_issues.md #34 and its 7 addenda) is a hand-verified,
# page-by-page read of every one of the 399 ballet-department Graduates
# entries against the actual scans -- this loads its already-confirmed
# dates and backfills them here, so the fix lives in the pipeline instead
# of only in a reference CSV (docs/eval/known_issues.md #45).
_GRADUATES_TENURE_CSV = Path(__file__).parent.parent / "docs" / "ballet_graduates_tenure.csv"

_MONTH_GENITIVE = {
    1: "января", 2: "февраля", 3: "марта", 4: "апрѣля", 5: "мая", 6: "іюня",
    7: "іюля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def _load_graduates_tenure_corrections() -> dict[str, str]:
    """entry_id -> ISO start date, for every row in the CSV that has one
    (report_per_row / report_per_row_exception / report_hand_verified).
    not_stated_in_report rows are blank in the CSV and simply don't appear
    here -- nothing to backfill for those, by design."""
    if not _GRADUATES_TENURE_CSV.exists():
        return {}
    with open(_GRADUATES_TENURE_CSV, encoding="utf-8-sig") as f:
        return {row["entry_id"]: row["tenure_start_date"]
                for row in csv.DictReader(f) if row["tenure_start_date"]}


_GRADUATES_TENURE_CORRECTIONS = _load_graduates_tenure_corrections()


def _repair_graduates_tenure(parsed: dict, page_id: str) -> int:
    """Backfills a hand-verified start date from _GRADUATES_TENURE_CORRECTIONS
    onto whichever entries the model left undated. Only touches entries with
    no service_periods already -- never overwrites a date the model did
    capture (matches the 199/335 dated rows already correct in the CSV, e.g.
    entries whose only problem was a mislabeled `school`, not a missing
    date). The corrected date is rendered back into a printed-style Russian
    phrase (day + genitive month + year) rather than stored as raw ISO, so
    it still round-trips through parse_russian_date() like every other
    *_date_text field -- verified to reproduce the exact ISO date for all
    136 rows this touches. Returns the count backfilled."""
    n_filled = 0
    for i, e in enumerate(parsed.get("entries", []), start=1):
        if e.get("service_periods"):
            continue
        entry_id = f"{page_id}__e{i:03d}"
        iso_date = _GRADUATES_TENURE_CORRECTIONS.get(entry_id)
        if not iso_date:
            continue
        year, month, day = iso_date.split("-")
        date_text = f"{int(day)} {_MONTH_GENITIVE[int(month)]} {year} г."
        e["tenure_note_text"] = date_text
        e["service_periods"] = [{"start_date_text": date_text, "end_date_text": None, "end_type": None}]
        n_filled += 1
    return n_filled


# Two one-off extraction misattachments found during RG's 2026-08-24
# `institution`/`heading_path` accuracy audit -- both verified against the
# actual scans (docs/query_log.md, 2026-08-24), not guessed. Keyed by
# page_id -> list of (1-based entry index or None-for-"all entries on this
# page", field patches).
_MISATTACHMENT_FIXES: dict[str, list[tuple]] = {
    # balletartists_1903-04_MSK_p001, entry 25 (Другашева, Марія): her own
    # credit_summary_text is cut off mid-sentence ("...Жизель (Берта—3);")
    # by the page break. The rest of the same sentence ("Золотая рыбка
    # (постельница — 7); Донъ-Кихотъ Ламанчскій...") was captured on the
    # NEXT page (p002) but attached to `institution` there instead -- p.106
    # of the scan shows it's one continuous, complete credit list split
    # across the page boundary.
    "balletartists_1903-04_MSK_p001": [
        (25, "credit_summary_text_append",
         " Золотая рыбка (постельница — 7); Донъ-Кихотъ Ламанчскій (жена трактирщика — 4); "
         "Лебединое озеро (владѣтельная принцесса — 3); Эсмеральда (Гудула—1).")
    ],
    # balletartists_1903-04_MSK_p002: every entry on this page inherited the
    # orphaned text above as `institution` (the other half of Другашева's
    # credit line, wrongly read as a page header) -- there's no real
    # institution/running-header text visible anywhere on this page in the
    # scan, so the correct value is blank, not a guessed theater name.
    "balletartists_1903-04_MSK_p002": [(None, "institution", "")],
    # productionteam_1895-96_p001, entry 7 (Ковалевскій, Ѳедоръ Ѳедоровичъ):
    # institution/heading_path both duplicated his own name+date instead of
    # the real heading. p.108 of the scan shows he's listed directly under
    # "Михайловскій театръ. / Помощникъ машиниста." (the same theater as
    # Ашитковъ just above him, under a "Помощникъ машиниста" sub-role).
    "productionteam_1895-96_p001": [
        (7, "institution", "Михайловскій театръ."),
        (7, "heading_path", "Михайловскій театръ. / Помощникъ машиниста."),
    ],
}


def _repair_misattachments(parsed: dict, page_id: str) -> int:
    """Applies _MISATTACHMENT_FIXES for this page, if any. Returns the
    count of entries touched."""
    fixes = _MISATTACHMENT_FIXES.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for idx, field, value in fixes:
        targets = entries if idx is None else [entries[idx - 1]] if idx <= len(entries) else []
        for e in targets:
            if field == "credit_summary_text_append":
                e["credit_summary_text"] = (e.get("credit_summary_text") or "") + value
            else:
                e[field] = value
            n_touched += 1
    return n_touched


# Hand-transcribed from the scans, entry by entry -- found while scoping
# the "heading_path stuck holding a stale instrument name" bug (issue #56
# follow-up): 4 pages show an implausibly long run (13-39 rows) of the
# identical instrument-shaped heading_path value ("Ударные инструменты"
# every time), which a same-page/same-run entry either legitimately
# printed once (correctly, for that one person) or never happened
# at all -- confirmed by direct re-read of every affected page, not
# inferred from the run-length pattern alone. RG: "Do these now. No
# guess!" -- every value below was read directly off the cited scan,
# not derived from any heuristic. Two of the four affected pages
# (musicians_1893-94_MSK_p003, 25 of 27; musicians_1894-95_MSK_p003, all
# 31) already had their real instrument recovered separately via the
# issue #56 rank_or_title fix -- only the entries STILL missing an
# instrument after that fix are listed here.
_INSTRUMENT_TRANSCRIPTION_FIXES: dict[str, list[tuple]] = {
    # ForUpload_1893-94_Spisok_OrchestraMoscow.pdf p.102: entry 9
    # (Заальборнъ) is the genuine origin of this page's stuck run -- his
    # own instrument, correctly printed, just misplaced into heading_path
    # instead of the dedicated field. Entry 32 (Фарскій) prints "...
    # (онъ же и библіотекарь Музыкальной библіотеки) (съ 1 сентября
    # 1882 г.) Альтъ." -- his instrument was dropped from every field
    # entirely; only heading_path's stuck "Ударные инструменты" survived,
    # and that value was never his to begin with.
    "musicians_1893-94_MSK_p003": [
        (9, "instrument", "Ударные инструменты"),
        (32, "instrument", "Альтъ"),
    ],
    # ForUpload_1890-91_Spisok_OrchestraSP.pdf p.79, entries 54-66: a
    # cross-reference-stub run (most print "(см. оперный оркестръ)",
    # dropped entirely rather than captured -- see issue #27's "40% of
    # the time this phrase is lost outright" finding) where heading_path
    # got stuck at entry 57's own value ("Ударные инструменты",
    # Цимбергъ) instead of holding each person's own, genuinely
    # different instrument.
    "musicians_1890-91_SP_p004": [
        # Entries 1-2 (52-53, Фейтъ/Франкенштейнъ) are full entries with
        # heading_path stuck at "Капельмейстеръ" -- wrong for the same
        # reason as the rest of this run (a numbered "52."/"53." list
        # member can't be the section's own, separately-listed,
        # unnumbered Kapellmeister) -- and their own instrument was
        # never captured anywhere else either.
        (1, "instrument", "Арфа"),              # 52. Фейтъ
        (2, "instrument", "Литавры"),           # 53. Франкенштейнъ
        (3, "instrument", "Вторая скрипка"),    # 54. Харитоновъ
        (4, "instrument", "Первая скрипка"),    # 55. Хилле
        (5, "instrument", "Арфа"),              # 56. Цабель
        (6, "instrument", "Ударные инструменты"),  # 57. Цимбергъ (genuinely correct)
        (7, "instrument", "Контрабасъ"),        # 58. Циммерманъ
        (8, "instrument", "Віолончель"),        # 59. Шмидтъ
        (9, "instrument", "Первая скрипка"),    # 60. Штаакъ
        (10, "instrument", "Контрабасъ"),       # 61. Штаркъ
        (11, "instrument", "Первая скрипка"),   # 62. Штехертъ
        (12, "instrument", "Вальдгорнъ"),       # 63. Шуманъ, Отто Рейнгольдовичъ
        (13, "instrument", "Кларнетъ"),         # 64. Эллингеръ, Василій Адамовичъ
        (14, "instrument", "Первая скрипка"),   # 65. Энгель
        (15, "instrument", "Первая скрипка"),   # 66. Эрбъ
    ],
    # ForUpload_1901-02_Spisok_OrchestraMoscow.pdf p.121, entries 35-73:
    # same shape as the 1890-91 SP page above -- heading_path stuck at
    # entry 35's own value (Зюсъ, genuinely percussion) instead of each
    # person's real, individually varying instrument.
    "musicians_1901-02_MSK_p002": [
        (1, "instrument", "Ударные инструменты"),  # 35. Зюсъ (genuinely correct)
        (2, "instrument", "Первая скрипка"),    # 36. Ивановъ
        (3, "instrument", "Тромбонъ"),          # 37. Канисъ
        (4, "instrument", "Контрабасъ"),        # 38. Кведнау
        (5, "instrument", "Вторая скрипка"),    # 39. Кенигсбергъ
        (6, "instrument", "Флейта"),            # 40. Коробковъ
        (7, "instrument", "Фаготъ"),            # 41. Костлянъ
        (8, "instrument", "Вальдгорнъ"),        # 42. Котрба
        (9, "instrument", "Первая скрипка"),    # 43. Кратина
        (10, "instrument", "Первая скрипка"),   # 44. Крейнъ
        (11, "instrument", "Вторая скрипка"),   # 45. Кремеръ
        (12, "instrument", "Флейта"),           # 46. Кречманъ
        (13, "instrument", "Фаготъ"),           # 47. Кристель
        (14, "instrument", "Вальдгорнъ"),       # 48. Крутоголововъ
        (15, "instrument", "Труба"),            # 49. Кунстъ
        (16, "instrument", "Вальдгорнъ"),       # 50. Кудряшовъ
        (17, "instrument", "Контрабасъ"),       # 51. Кусевицкій
        (18, "instrument", "Віолончель"),       # 52. Лазаревъ
        (19, "instrument", "Литавры"),          # 53. Лидтке
        (20, "instrument", "Тромбонъ"),         # 54. Липаевъ
        (21, "instrument", "Первая скрипка"),   # 55. Литвиновъ
        (22, "instrument", "Вторая скрипка"),   # 56. Лясота
        (23, "instrument", "Корнетъ-а-пистонъ"),  # 57. Марквардтъ
        (24, "instrument", "Гобой"),            # 58. Миллеръ
        (25, "instrument", "Кларнетъ"),         # 59. Недбаль
        (26, "instrument", "Вторая скрипка"),   # 60. Фонъ-Нольте
        (27, "instrument", "Арфа"),             # 61. Омэ
        (28, "instrument", "Альтъ"),            # 62. Павловъ
        (29, "instrument", "Вторая скрипка"),   # 63. Палице
        (30, "instrument", "Первая скрипка"),   # 64. Пащеевъ
        (31, "instrument", "Первая скрипка"),   # 65. Пекарскій
        (32, "instrument", "Вторая скрипка"),   # 66. Плаксинъ
        (33, "instrument", "Віолончель"),       # 67. Плотниковъ
        (34, "instrument", "Вторая скрипка"),   # 68. Подруцкій
        (35, "instrument", "Фаготъ"),           # 69. Порубиновскій
        (36, "instrument", "Віолончель"),       # 70. Потаповъ
        (37, "instrument", "Труба"),            # 71. Путкамеръ
        (38, "instrument", "Первая скрипка"),   # 72. Рессеръ
        (39, "instrument", "Первая скрипка"),   # 73. Ривкиндъ
    ],
}


def _repair_instrument_transcriptions(parsed: dict, page_id: str) -> int:
    """Applies _INSTRUMENT_TRANSCRIPTION_FIXES for this page, if any --
    same idx-keyed pattern as _repair_misattachments, but only ever
    fills `instrument` when it's currently empty (never overwrites).
    Returns the count of entries touched."""
    fixes = _INSTRUMENT_TRANSCRIPTION_FIXES.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for idx, field, value in fixes:
        if idx is None or idx > len(entries):
            continue
        e = entries[idx - 1]
        if field == "instrument" and (e.get("instrument") or "").strip():
            continue
        e[field] = value
        n_touched += 1
    return n_touched


# Restores the real heading_path for the same 4 "stuck run" pages,
# closing out issue #56/#57. The correct value genuinely differs by
# page -- confirmed from adjacent same-page or preceding-page evidence
# for each, never assumed to be the same fix applied four times:
#   - musicians_1893-94_MSK_p003: entries 2-8 (immediately before the
#     run) read heading_path="Музыканты" -- a real, repeated section
#     label. Entry 1 (Александровъ) is a smaller instance of the same
#     bug (stuck at "Капельмейстеръ", the line above the numbered list --
#     confirmed via the analogous 1894-95_MSK_p002 page, where the same
#     numbered-list-starts-at-1 transition reads "Оркестръ Малаго театра
#     / Капельмейстеръ" for the unnumbered Kapellmeister entry, then
#     ".../ Музыканты" starting at entry "1.").
#   - musicians_1894-95_MSK_p003: continues musicians_1894-95_MSK_p002's
#     numbered list (item 6 follows item 5) -- that page's own entries
#     5/6-boundary read "Оркестръ Малаго театра / Музыканты", the exact
#     compound path to restore here.
#   - musicians_1890-91_SP_p004: the preceding page
#     (musicians_1890-91_SP_p003, entries 44-51) shows heading_path
#     genuinely holding each person's own individually-varying
#     instrument throughout, with no separate section-heading concept
#     anywhere on this stretch of pages -- so the correct restored value
#     here is each entry's own instrument (same value now correctly
#     sitting in `instrument` after the fix above), not some other label.
#   - musicians_1901-02_MSK_p002: the preceding page
#     (musicians_1901-02_MSK_p001, entries "1."-"34.") shows heading_path
#     legitimately NULL throughout its entire numbered list, with
#     `instrument` alone carrying every entry's real value -- so the
#     correct restored value here is NULL, not a fabricated section
#     label this list never actually used.
_HEADING_PATH_RESTORE_FIXES: dict[str, list[tuple]] = {
    "musicians_1893-94_MSK_p003": (
        [(1, "heading_path", "Музыканты")]
        + [(i, "heading_path", "Музыканты") for i in range(9, 36)]
    ),
    "musicians_1894-95_MSK_p003": [
        (i, "heading_path", "Оркестръ Малаго театра / Музыканты") for i in range(1, 32)
    ],
    "musicians_1890-91_SP_p004": [
        (1, "heading_path", "Арфа"), (2, "heading_path", "Литавры"),
        (3, "heading_path", "Вторая скрипка"), (4, "heading_path", "Первая скрипка"),
        (5, "heading_path", "Арфа"), (6, "heading_path", "Ударные инструменты"),
        (7, "heading_path", "Контрабасъ"), (8, "heading_path", "Віолончель"),
        (9, "heading_path", "Первая скрипка"), (10, "heading_path", "Контрабасъ"),
        (11, "heading_path", "Первая скрипка"), (12, "heading_path", "Вальдгорнъ"),
        (13, "heading_path", "Кларнетъ"), (14, "heading_path", "Первая скрипка"),
        (15, "heading_path", "Первая скрипка"),
    ],
    "musicians_1901-02_MSK_p002": [(i, "heading_path", None) for i in range(1, 40)],
}


def _repair_heading_path_restore(parsed: dict, page_id: str) -> int:
    """Applies _HEADING_PATH_RESTORE_FIXES for this page, if any.
    Unlike _repair_instrument_transcriptions, this always overwrites --
    every targeted row's current heading_path is the confirmed-wrong
    stuck value, not a real one that might already be correct. Returns
    the count of entries touched."""
    fixes = _HEADING_PATH_RESTORE_FIXES.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for idx, field, value in fixes:
        if idx is None or idx > len(entries):
            continue
        entries[idx - 1][field] = value
        n_touched += 1
    return n_touched


# The general "shape A" heading_path -> instrument migration, closing out
# the arc from issues #56-#58. Scoped by a fresh corpus-wide query
# (docs/query_log.md, 2026-08-27): 767 Musicians rows across exactly 19
# pages where `instrument` is empty and `heading_path` holds exactly a
# bare _KNOWN_INSTRUMENTS value -- the "safe" subset issue #57 explicitly
# separated out from the dangerous "stuck run" pages already fixed above.
# RG: "I don't want to generalize if it means we miss exceptional cases"
# -- rather than a blanket "trust heading_path" move, every one of the 19
# candidate pages was read against its scan by hand this session (not
# trusted from an earlier session's recollection -- "no guessing"),
# confirming heading_path is correct for the large majority (~741 of 767
# rows) but wrong or fabricated for a real minority, in four distinct
# shapes, each confirmed by direct comparison against the printed page:
#   - stuck/shifted from a neighboring row's real value (Браунштейнъ,
#     both Еременко instances, Плотниковъ, Ватерстрадъ/Вейкманъ's
#     shift-by-one, Кулле 1-й, Ластовскій, both Гуманъ instances)
#   - two adjacent rows' real instruments swapped with each other
#     (Фридрихъ/Царскій on musicians_1892-93_MSK_p001)
#   - a fabricated plural category word matching nothing printed
#     anywhere on the page (Розановъ "Кларнетисты", Ромашковъ 1-й/
#     Рѣзниковъ "Альты" -- confirmed no such subheading exists by
#     zooming the actual scan region)
#   - the person's own first name/patronymic duplicated into
#     heading_path because no instrument is printed at all for that
#     entry (Газенкампфъ, Лудольфи -- Лудольфи's real instrument was
#     still recoverable from context; see _SHAPE_A_CORRECTIONS)
# A fifth, distinct shape has no real instrument to recover at all --
# heading_path holds a stuck neighbor value same as the others, but the
# scan prints no instrument whatsoever for that person (a brand-new hire
# whose row ends at the tenure date): Голубевъ/Дворниковъ/Де-Буръ/
# Зайцевъ (musicians_1903-04_MSK_p001) and Яньшиновъ
# (musicians_1906-07_MSK_p004) -- `instrument` stays empty for these,
# only heading_path is cleared.
#
# NOTE on scope: three more confirmed-wrong cases found in this same scan
# pass -- Газенкампфъ, Лудольфи (both a duplicated own-name in
# heading_path, not an instrument), and Розановъ/Ромашковъ 1-й/Рѣзниковъ
# (a fabricated plural category word, "Кларнетисты"/"Альты", matching
# nothing printed on the page) -- are handled by _SHAPE_A_SPECIAL_CASES
# below instead of here, because their heading_path isn't a bare
# _KNOWN_INSTRUMENTS member at all, so the strict candidate filter this
# table feeds never reaches them.
_SHAPE_A_NO_INSTRUMENT: dict[str, set[int]] = {
    "musicians_1903-04_MSK_p001": {22, 27, 28, 33},  # Голубевъ/Дворниковъ/Де-Буръ/Зайцевъ
    "musicians_1906-07_MSK_p004": {125},             # Яньшиновъ
}

_SHAPE_A_CORRECTIONS: dict[str, dict[int, str]] = {
    "musicians_1890-91_MSK_p001": {16: "Альтъ"},                # Вейнаръ
    "musicians_1890-91_SP_p003": {8: "Фаготъ"},                 # Браунштейнъ
    "musicians_1891-92_MSK_p001": {34: "Ударные инструменты"},  # Еременко
    "musicians_1891-92_SP_p001": {
        12: "Флейта",  # Ватерстрадъ
        13: "Альтъ",   # Вейкманъ
        25: "Альтъ",   # Гуманъ
    },
    "musicians_1892-93_MSK_p001": {
        79: "Кларнетъ",  # Фридрихъ
        80: "Скрипка",   # Царскій
    },
    "musicians_1892-93_SP_p005": {
        19: "Тромбонъ",  # Кулле 1-й
        20: "Альтъ",     # Ластовскій
    },
    "musicians_1898-99_MSK_p002": {70: "Віолончель"},  # Плотниковъ
}


def _list_number_int(raw: str | None) -> int | None:
    """Extracts the leading integer from a printed list_number like
    "79." or "38.". Returns None if it doesn't start with digits.
    Continuation pages (a page's array starting mid-list, e.g. array
    position 1 = printed item "34.") mean raw array position can't be
    trusted to equal the printed number -- match on this instead."""
    if not raw:
        return None
    m = re.match(r"\s*(\d+)", raw)
    return int(m.group(1)) if m else None


def _repair_heading_path_shape_a(parsed: dict, page_id: str) -> tuple[int, int]:
    """The general migration for the 767-row "shape A" candidate set:
    Musicians entries where `instrument` is empty and `heading_path`
    holds exactly a bare known-instrument value. For the confirmed-safe
    majority, moves that value to `instrument` and clears `heading_path`
    (there's no other heading concept on these pages -- see issue #58's
    Ватерстрадъ-page precedent). For the confirmed-wrong minority (see
    _SHAPE_A_CORRECTIONS/_SHAPE_A_NO_INSTRUMENT above, every one scan-
    verified this session), uses the corrected value instead of trusting
    heading_path, or leaves `instrument` empty entirely rather than
    fabricate one. Keyed by the entry's own printed list_number, not raw
    array position -- a page whose list continues from the prior page
    doesn't start its array at list_number 1. Returns (n_migrated,
    n_corrected_or_blanked)."""
    entries = parsed.get("entries", [])
    no_instr = _SHAPE_A_NO_INSTRUMENT.get(page_id, set())
    corrections = _SHAPE_A_CORRECTIONS.get(page_id, {})
    n_migrated = 0
    n_special = 0
    for e in entries:
        if (e.get("instrument") or "").strip():
            continue
        hp = (e.get("heading_path") or "").strip()
        if hp not in _KNOWN_INSTRUMENTS:
            continue
        ln = _list_number_int(e.get("list_number"))
        if ln in no_instr:
            e["heading_path"] = None
            n_special += 1
        elif ln in corrections:
            e["instrument"] = corrections[ln]
            e["heading_path"] = None
            n_special += 1
        else:
            e["instrument"] = hp
            e["heading_path"] = None
            n_migrated += 1
    return n_migrated, n_special


# More Musicians heading_path bugs found during the same page-by-page
# scan pass, structurally different from the shape-A migration above --
# heading_path doesn't hold a *bare* instrument name for any of these, so
# none were in that candidate set -- but confirmed against the same
# scans:
#   - musicians_1899-00_SP_p001, entry 20 (Газенкампфъ): heading_path =
#     "Рудольфъ Владиміровичъ" -- his own first name + patronymic
#     duplicated into the field. Scan confirmed: no instrument printed
#     for him at all (entry ends at the tenure date). heading_path
#     cleared; instrument stays empty, not fabricated.
#   - musicians_1899-00_SP_p002, entry 63 (Лудольфи/Лудольфъ):
#     heading_path = "Валентинъ" -- same own-first-name-duplication bug,
#     but his real instrument (Контрабасъ) IS printed on the scan.
#   - musicians_1906-07_MSK_p003, entries 82/83/86 (Розановъ/Ромашковъ
#     1-й/Рѣзниковъ): heading_path = "Кларнетисты"/"Альты" -- a
#     fabricated plural category word matching nothing printed anywhere
#     on the page (confirmed by zooming the actual scan region: each
#     entry ends with its own plain singular instrument + period, no
#     subheading text anywhere nearby).
#   - musicians_1906-07_MSK_p003, entry 99 (Сиборъ): heading_path =
#     "Скрипка. Солистъ балета." -- genuinely both his instrument AND a
#     title bundled together (confirmed against the scan: printed
#     exactly that way, not a stuck value). Split rather than migrated
#     whole via _split_leading_instrument: instrument gets "Скрипка",
#     the "Солистъ балета" title moves to rank_or_title. RG flagged this
#     person (2026-08-27) for a later cross-corpus check -- likely a
#     guest artist for a specific ballet rather than a standing section
#     member.
#   - musicians_1906-07_MSK_p004, entry 122 (Эмме): heading_path =
#     "Дирижеръ" -- stuck on the very next section's own heading (the
#     "Оркестръ Малаго театра / Дирижеръ" line for Шульцъ, printed
#     immediately below on the same page), not anything belonging to
#     Эмме's own row. His real instrument (Альтъ) confirmed directly
#     from the scan; heading_path is cleared, not migrated, since
#     "Дирижеръ" was never his.
_SHAPE_A_SPECIAL_CASES: dict[str, list[tuple]] = {
    "musicians_1899-00_SP_p001": [(20, "clear_heading_path")],        # Газенкампфъ
    "musicians_1899-00_SP_p002": [(63, "instrument", "Контрабасъ")],  # Лудольфи
    "musicians_1906-07_MSK_p003": [
        (82, "instrument", "Кларнетъ"),  # Розановъ
        (83, "instrument", "Альтъ"),     # Ромашковъ 1-й
        (86, "instrument", "Альтъ"),     # Рѣзниковъ
        (99, "split_instrument_title"),  # Сиборъ
    ],
    "musicians_1906-07_MSK_p004": [(122, "instrument", "Альтъ")],     # Эмме
}


def _repair_shape_a_special_cases(parsed: dict, page_id: str) -> int:
    """Applies _SHAPE_A_SPECIAL_CASES for this page, if any. Keyed by
    printed list_number, not raw array position (see
    _repair_heading_path_shape_a). Returns the count of entries touched."""
    fixes = _SHAPE_A_SPECIAL_CASES.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    by_list_number = {_list_number_int(e.get("list_number")): e for e in entries}
    n_touched = 0
    for fix in fixes:
        ln = fix[0]
        e = by_list_number.get(ln)
        if e is None:
            continue
        if fix[1] == "split_instrument_title":
            hp = (e.get("heading_path") or "").strip()
            instr, rest = _split_leading_instrument(hp)
            if instr and not (e.get("instrument") or "").strip():
                e["instrument"] = instr
                e["heading_path"] = None
                if rest:
                    e["rank_or_title"] = (
                        (e.get("rank_or_title") or "").strip() + " " + rest
                    ).strip()
                n_touched += 1
        elif fix[1] == "clear_heading_path":
            if e.get("heading_path") is not None:
                e["heading_path"] = None
                n_touched += 1
        else:
            field, value = fix[1], fix[2]
            if field == "instrument" and (e.get("instrument") or "").strip():
                continue
            e[field] = value
            if field == "instrument":
                # heading_path never held a real heading for these rows
                # (a stuck neighbor value or a fabricated category word) --
                # clear it rather than leave a confirmed-wrong value sitting
                # next to the now-correct instrument.
                e["heading_path"] = None
            n_touched += 1
    return n_touched


# Follow-up to the shape-A arc, found while explaining to RG why so many
# Musicians `instrument` fields were still empty after issue #59: unlike
# `heading_path`, `tenure_note_text` behaves as a reliable verbatim capture
# regardless of whether `instrument` was separately parsed out -- confirmed
# by comparing already-`instrument`-filled rows (which still carry the same
# "(съ ... г.). <Instrument>." text in tenure_note_text) against empty
# ones. Running _split_leading_instrument() against every empty-`instrument`
# Musicians row's tenure_note_text (after stripping the leading tenure-date
# parenthetical) found 1854 of 2366 empty rows (78%) have a cleanly-
# recoverable instrument sitting there, unextracted -- corpus-wide, not
# confined to the 19 shape-A pages.
#
# Verified before writing this fix, same discipline as the shape-A arc:
# 10 rows sampled at random across 10 distinct pages (of 52 total) checked
# directly against scans -- all 10 correct. Then cross-checked all 1854
# rows against every OTHER Musicians row sharing the same (family_name,
# first_name, patronymic) with a known instrument elsewhere in the corpus:
# 1721 rows had such a cross-season match, 1715 (99.65%) agreed (exactly or
# via a known spelling/synonym variant -- Піанистъ/Фортепіано, Біолончель/
# Віолончель, etc.), leaving only 6 genuine conflicts. Scan-checked all 6
# directly:
#   - 4 (Шолларъ x2 seasons, Табаковъ, Грибенъ) matched their OWN page's
#     scan exactly -- the "conflict" was a genuine cross-season difference
#     (a real instrument change, or a same-named different person), not an
#     extraction error. Extracted as printed, no correction needed.
#   - 2 (Фишеръ/Франке 1-й on musicians_1892-93_SP_p002, adjacent rows 76
#     and 77) were a confirmed genuine swap -- the same failure class as
#     the Фридрихъ/Царскій swap in issue #59, just manifesting in
#     tenure_note_text instead of heading_path. Corrected via
#     _TENURE_NOTE_INSTRUMENT_CORRECTIONS below.
#
# Also confirmed the trailing "remainder" text after the instrument
# (e.g. Цабель's "Солистъ Двора Его Императорскаго Величества") is
# deliberately NOT touched by this fix -- one sampled row (Григоренко,
# musicians_1892-93_SP_p003) showed a remainder ("(см. оперный оркестръ)")
# that traced back to a genuinely wrong `rank_or_title` value already
# present in the raw JSON for that entry (a stuck-run fabrication matching
# the same bug class as the heading_path stuck runs, just in a different
# field) -- a distinct, not-yet-addressed bug, out of scope here. Moving
# remainder text into rank_or_title in this same pass would have risked
# propagating that kind of error; instrument extraction alone doesn't.
_TENURE_NOTE_INSTRUMENT_CORRECTIONS: dict[str, dict[int, str]] = {
    "musicians_1892-93_SP_p002": {
        76: "Віолончель",  # Фишеръ -- scan-confirmed; tenure_note_text said "Кларнетъ" (Франке 1-й's real value)
        77: "Кларнетъ",    # Франке 1-й -- scan-confirmed; tenure_note_text said "Віолончель" (Фишеръ's real value)
    },
}

_TENURE_NOTE_DATE_PREFIX_RE = re.compile(r"^\(?съ [^)]+г\.\)\.?\s*")

# Found in the same 2026-08-28 pass as the hand-fixes below: 18 more rows
# where tenure_note_text is prefixed with the cross-reference note itself
# ("(см. оперный оркестръ)."), not a tenure date, followed by the real
# instrument -- a shape the date-prefix regex above was never meant to
# match, so these were skipped entirely by the general extraction, not
# mis-extracted. Confirmed by scan on both affected pages, all 18 rows
# individually checked (musicians_1892-93_MSK_p003 p.99, entries 37-56;
# musicians_1891-92_SP_p002 p.63, entries 1-6) -- every one matches
# exactly, e.g. entry 56 (Юмерихъ) reads "(см. оперный оркестръ).
# Ударные инструменты." in print.
_TENURE_NOTE_CROSSREF_PREFIX_RE = re.compile(r"^\(с[мс]\.?[^)]*\)\.?\s*", re.IGNORECASE)

# Found triaging the ~512 rows still empty after issue #60 (RG: "Let's
# work on these") -- 5 more rows where the real instrument genuinely sits
# in tenure_note_text, but the general extraction above can't reach it,
# for three different reasons, each confirmed by scan or strong existing
# cross-season corroboration:
#   - a leading dual-role parenthetical before the date (Марквардтъ
#     "(онъ же и капельмейстеръ военной музыки) (съ ... г.). Труба.",
#     Фарскій "(онъ же и библіотекарь Музыкальной библіотеки) (съ ... г.).
#     Альтъ.") -- the date-prefix regex only matches at the very start of
#     the string, matching this project's established pattern for the
#     same dual-role-parenthetical shape elsewhere (rank_or_title,
#     patronymic).
#   - a malformed printed/captured punctuation variant that the date
#     regex doesn't match: a missing closing paren (Терентьевъ "(съ ...
#     г.. Скрипка.") or a comma instead of a period after the date
#     (Сольскій, 1896-97 season, "(съ ... г.), Вальдгорнъ.").
#   - _split_leading_instrument's own deliberate boundary-safety check
#     (only splits before a capitalized continuation) declining a
#     genuine split where the instrument is followed by a lowercase
#     descriptive continuation (Смирновъ "Піанистъ при драматическихъ
#     спектакляхъ." -- confirmed against the scan, ForUpload_1891-92_
#     Spisok_OrchestraSP.pdf p.65, item 34).
# Марквардтъ (Труба) and Фарскій (Альтъ) both have strong independent
# corroboration already established this session/in issue #57 across many
# other seasons; Терентьевъ (Скрипка) and Сольскій (Вальдгорнъ) each have
# the identical value confirmed on other pages earlier the same session.
_TENURE_NOTE_INSTRUMENT_HAND_FIXES: dict[str, dict[int, str]] = {
    "musicians_1891-92_SP_p004": {34: "Піанистъ"},   # Смирновъ
    "musicians_1895-96_MSK_p001": {63: "Труба"},     # Марквардтъ
    "musicians_1895-96_MSK_p003": {30: "Скрипка", 32: "Альтъ"},  # Терентьевъ, Фарскій
    "musicians_1896-97_SP_p003": {32: "Вальдгорнъ"},  # Сольскій
    # Found 2026-08-28 while answering RG's "why do only some
    # tenure_note_texts have an instrument" question -- cross-checking
    # every currently-empty-instrument row's tenure_note_text for ANY
    # instrument word at all (not just at a recognized prefix boundary)
    # surfaced these last 2 genuine misses, both scan-confirmed
    # (musicians_1902-03_MSK_p004 p.118, musicians_1905-06_MSK_p003
    # p.59): Фарскій "(онъ же и...) (съ 1 января 1894 г.). Альтъ.
    # † 31 августа 1903 г." -- a missing closing paren after the date
    # AND a dual-role parenthetical stacked on top, defeating both
    # existing carve-outs at once; Стрекаловъ "(съ 1 октября 1894 г.).
    # Переведенъ въ оркестръ Малаго театра 1 апрѣля 1901 г. Вторая
    # скрипка." -- the instrument sits AFTER a transfer note instead of
    # right after the date, a shape none of the extraction logic above
    # looks for (it only ever checks the very start of the string).
    "musicians_1902-03_MSK_p004": {26: "Альтъ"},        # Фарскій
    "musicians_1905-06_MSK_p003": {97: "Вторая скрипка"},  # Стрекаловъ
}


def _repair_tenure_note_instrument(parsed: dict, page_id: str) -> int:
    """Recovers `instrument` from `tenure_note_text` for Musicians entries
    where `instrument` is empty but the note holds a recognizable
    instrument name right after the tenure-date prefix (see the comment
    above for the verification behind this). Only ever fills `instrument`
    when empty; never touches tenure_note_text itself (a verbatim field)
    or any remainder text after the instrument. Uses
    _TENURE_NOTE_INSTRUMENT_CORRECTIONS for the two confirmed-wrong rows
    found during verification, and _TENURE_NOTE_INSTRUMENT_HAND_FIXES for
    5 more rows the general extraction can't reach (see that table's
    comment). Returns the count of entries touched."""
    entries = parsed.get("entries", [])
    corrections = _TENURE_NOTE_INSTRUMENT_CORRECTIONS.get(page_id, {})
    hand_fixes = _TENURE_NOTE_INSTRUMENT_HAND_FIXES.get(page_id, {})
    n_touched = 0
    for e in entries:
        if (e.get("instrument") or "").strip():
            continue
        ln = _list_number_int(e.get("list_number"))
        if ln in hand_fixes:
            e["instrument"] = hand_fixes[ln]
            n_touched += 1
            continue
        note = (e.get("tenure_note_text") or "").strip()
        if not note:
            continue
        m = _TENURE_NOTE_DATE_PREFIX_RE.match(note)
        if not m:
            m = _TENURE_NOTE_CROSSREF_PREFIX_RE.match(note)
        rest = note[m.end():].strip() if m else note
        instr, _rest = _split_leading_instrument(rest)
        if not instr:
            continue
        e["instrument"] = corrections.get(ln, instr)
        n_touched += 1
    return n_touched


# Крейнъ, Давидъ: 7 seasons (1897-98 through 1905-06) consistently read
# "Первая скрипка"; the last 2 (1906-07, 1907-08) switch to
# "Концертмейстеръ" -- a genuine promotion, but a rank/title, not an
# instrument name (this era's "concertmaster" = principal first violin,
# but the print itself doesn't repeat "Первая скрипка" for these 2 rows).
# Relocating it to rank_or_title rather than either leaving it stuck in
# tenure_note_text or inferring "Первая скрипка" without direct textual
# support for these specific rows -- matches this project's standing rule
# against fabricating values from a plausible-but-unstated inference.
_TENURE_NOTE_TITLE_RELOCATIONS: dict[str, dict[int, str]] = {
    "musicians_1906-07_MSK_p002": {52: "Концертмейстеръ"},
    "musicians_1907-08_MSK_p001": {52: "Концертмейстеръ"},
}


def _repair_tenure_note_title_relocation(parsed: dict, page_id: str) -> int:
    """Applies _TENURE_NOTE_TITLE_RELOCATIONS: moves a rank/title-shaped
    value that's sitting after the tenure date in tenure_note_text (not a
    bare instrument name, so _repair_tenure_note_instrument never reaches
    it) into rank_or_title instead. Does not touch `instrument` -- see the
    comment above. Returns the count of entries touched."""
    fixes = _TENURE_NOTE_TITLE_RELOCATIONS.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for e in entries:
        ln = _list_number_int(e.get("list_number"))
        if ln not in fixes:
            continue
        title = fixes[ln]
        note = (e.get("tenure_note_text") or "").strip()
        m = _TENURE_NOTE_DATE_PREFIX_RE.match(note)
        rest = note[m.end():].strip() if m else note
        if rest.rstrip(".") != title:
            continue  # tenure_note_text no longer matches what we verified; don't touch
        if not (e.get("rank_or_title") or "").strip():
            e["rank_or_title"] = title
            n_touched += 1
    return n_touched


# Found triaging known_issues.md's "Григоренко rank_or_title stuck-value"
# note (RG: "Let's fix this next"). `musicians_1892-93_SP_p003` genuinely
# mixes two kinds of row: musicians cross-listed from the Оперный оркестръ
# roster (printed as bare "(см. оперный оркестръ). <Instrument>." stubs,
# no date of their own -- 173 of these confirmed correct across 12 pages,
# left untouched) and musicians with their own complete record printed
# right there (full date + instrument, genuinely NOT cross-listed). On
# this one page, and only this one page, the model's own raw JSON
# extraction fabricated `rank_or_title="(см. оперный оркестръ)"` on 23 of
# the second kind too -- confirmed by direct scan reading for every one of
# the 23 (including a same-page cross-check: items 1-7 belong to a wholly
# separate "Оркестръ Александринскаго театра" list at the bottom of the
# same page, with no crossref concept at all, yet still got the same
# fabricated value). `_repair_musicians_rank_or_title()` (issue #56,
# validated correct for 3048+ other rows) faithfully relocated this
# fabricated value into tenure_note_text, same as it does for every
# genuine case -- the bug is upstream of that function, in the model's
# own extraction, not in the repair logic itself. Confirmed via the same
# page's prior season (`musicians_1891-92_SP_p003`) sharing the identical
# printed layout and genuinely alternating pattern, with zero fabricated
# rows -- this is a one-page artifact, not a recurring model bias.
_FABRICATED_CROSSREF_NOTE_FIXES: dict[str, set[int]] = {
    "musicians_1892-93_SP_p003": {
        1, 2, 3, 4, 5, 6, 7,  # Абрамовъ..Вагнеръ (separate Alexandrinsky list)
        19, 22, 23, 24, 25, 26, 27, 30, 31, 35, 36, 44, 51, 52, 62, 63,
    },
}
_FABRICATED_CROSSREF_SUFFIX_RE = re.compile(r"\s*\(с[мс]\.?[^)]*\)\s*$", re.IGNORECASE)


def _repair_fabricated_crossref_note(parsed: dict, page_id: str) -> int:
    """Strips a fabricated trailing "(см. ...)" cross-reference note from
    tenure_note_text for the 23 confirmed-wrong rows in
    _FABRICATED_CROSSREF_NOTE_FIXES -- see the comment above. Every other
    "(см. ...)" occurrence in the corpus is left untouched (confirmed
    genuine). Returns the count of entries touched."""
    targets = _FABRICATED_CROSSREF_NOTE_FIXES.get(page_id)
    if not targets:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for e in entries:
        ln = _list_number_int(e.get("list_number"))
        if ln not in targets:
            continue
        note = e.get("tenure_note_text") or ""
        new_note = _FABRICATED_CROSSREF_SUFFIX_RE.sub("", note).rstrip()
        if new_note != note:
            e["tenure_note_text"] = new_note
            n_touched += 1
    return n_touched


# Found while discussing tenure_note_text architecture with RG
# (2026-08-28), tracing build_duckdb.py's `instrument_clean`/
# `tenure_note_text_clean` CASE branches back to their source: a mirror
# image of the rank_or_title service-note relocation
# (_repair_musicians_rank_or_title step 4) -- here the resignation/
# transfer sentence lands in `instrument` instead, displacing (not just
# following) the real instrument value. Confirmed corpus-wide via
# `regexp_matches(instrument, '^(Оставилъ службу|Переведенъ)')`: exactly
# 2 rows, both on `musicians_1903-04_MSK_p000`, both scan-verified
# directly (p.113): entry 7 (Барсукъ-Самборскій) prints "... Вальдгорнъ.
# Оставилъ службу 1 октября 1903 г." as one continuous entry; entry 19
# (Гейслеръ) prints "... Контрабасъ. Переведенъ съ 1 октября 1902 г. въ
# Малый театръ." the same way. Both instruments also independently
# confirmed by unanimous cross-season corroboration (13 and 15 other
# seasons respectively, always the same value). Restores the real
# instrument and relocates the note to tenure_note_text, matching where
# it already correctly lands for these same two people in every other
# season (e.g. Гейслеръ's 1902-03 row already reads "...Контрабасъ.
# Переведенъ съ 1 октября 1902 г. въ Малый театръ." with `instrument`
# untouched).
_INSTRUMENT_SERVICE_NOTE_CORRECTIONS: dict[str, dict[int, str]] = {
    "musicians_1903-04_MSK_p000": {
        7: "Вальдгорнъ",   # Барсукъ-Самборскій
        19: "Контрабасъ",  # Гейслеръ
    },
}


def _repair_instrument_service_note(parsed: dict, page_id: str) -> int:
    """Applies _INSTRUMENT_SERVICE_NOTE_CORRECTIONS: restores the real
    instrument for a confirmed row where a resignation/transfer note
    displaced it, relocating the note into tenure_note_text. Returns the
    count of entries touched."""
    fixes = _INSTRUMENT_SERVICE_NOTE_CORRECTIONS.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for e in entries:
        ln = _list_number_int(e.get("list_number"))
        if ln not in fixes:
            continue
        note = (e.get("instrument") or "").strip()
        if not note:
            continue
        existing = (e.get("tenure_note_text") or "").strip()
        e["tenure_note_text"] = f"{existing} {note}".strip() if existing else note
        e["instrument"] = fixes[ln]
        n_touched += 1
    return n_touched


# Found answering RG's "why do some musicians have start dates and some
# don't" question (2026-08-28): every one of the 235 Musicians rows with
# no start date turned out to be a cross-reference stub whose real date
# is printed on a different ("home") page -- confirmed, not a data loss.
# Chasing the 48 rows that looked entirely blank (no date, no crossref
# text visible either) surfaced this one: 21 rows, all on
# `musicians_1891-92_MSK_p002`, where `instrument` literally holds "см.
# оперный оркестръ" (the crossref note itself) with nothing else --
# meaning the REAL instrument, genuinely printed right after the
# crossref note on this page, was dropped from every field entirely.
# Confirmed by direct scan reading (p.86): every affected row reads
# "<Surname> (см. оперный оркестръ). <Instrument>." as one continuous
# entry, e.g. entry 2 (Альбрехтъ): "Альбрехтъ (см. оперный оркестръ).
# Корнетъ." All 21 hand-transcribed directly from the scan, matched
# name-by-name against the page. Relocates the crossref note to
# tenure_note_text (matching the "(см. ...)" format already used
# corpus-wide for genuine crossref stubs) and restores the real
# instrument.
_INSTRUMENT_CROSSREF_CORRECTIONS: dict[str, dict[int, str]] = {
    "musicians_1891-92_MSK_p002": {
        2: "Корнетъ",       # Альбрехтъ
        3: "Віолончель",    # Аспергеръ
        5: "Скрипка",       # Большаковъ
        7: "Альтъ",         # Вихера
        8: "Скрипка",       # Гейнъ
        9: "Контрабасъ",    # Гейслеръ
        10: "Альтъ",        # Гильбертъ
        11: "Скрипка",      # Голласъ
        12: "Скрипка",      # Гофманъ
        13: "Віолончель",   # Грецкій
        17: "Тромбонъ",     # Зозель
        18: "Скрипка",      # Золотаренко
        21: "Скрипка",      # Кажданъ
        22: "Контрабасъ",   # Кведнау
        25: "Скрипка",      # Кремеръ
        29: "Скрипка",      # Кудике
        31: "Флейта",       # Лебедевъ
        35: "Альтъ",        # Павловъ
        36: "Віолончель",   # Пашъ
        37: "Скрипка",      # Пекарскій
        38: "Скрипка",      # Петровъ
    },
}


def _repair_instrument_crossref_note(parsed: dict, page_id: str) -> int:
    """Applies _INSTRUMENT_CROSSREF_CORRECTIONS: restores the real
    instrument for a confirmed row where a "(см. ...)" cross-reference
    note displaced it entirely, relocating the note into tenure_note_text
    (parenthesized, matching the corpus-wide convention for genuine
    crossref stubs). Returns the count of entries touched."""
    fixes = _INSTRUMENT_CROSSREF_CORRECTIONS.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for e in entries:
        ln = _list_number_int(e.get("list_number"))
        if ln not in fixes:
            continue
        note = (e.get("instrument") or "").strip()
        if not note:
            continue
        existing = (e.get("tenure_note_text") or "").strip()
        parenthesized = note if note.startswith("(") else f"({note})"
        e["tenure_note_text"] = f"{existing} {parenthesized}".strip() if existing else parenthesized
        e["instrument"] = fixes[ln]
        n_touched += 1
    return n_touched


# Found while checking the one unresolved rank_or_title/title-split residual
# ("по найму, Московскій пеховой", 2026-08-28) against the scan
# (ForUpload_1902-03_Spisok_Administration.pdf p.128, "Чиновники XII
# класса", entry 1): "пеховой" is an OCR misread of "цеховой" ("П" for
# "Ц") -- the page actually reads "Крыловъ, Сергѣй Онисимовичъ, по найму,
# Московскій цеховой (съ 1 марта 1889 г.)." "Цеховой" is a real word (a
# craft-guild/artisan social-estate designation), "пеховой" is not --
# confirmed a misread, not a print variant. Same person, same misread text,
# on both `administration_1902-03_p004` (idx 1) and
# `administration_1903-04_p004` (idx 2).
# list_number ALONE isn't a safe key here: both pages restart numbering
# per sub-list ("Канцелярскіе чиновники Конторы" / "Чиновники XII
# класса"), so idx 1 on administration_1902-03_p004 collides with a
# different real person (Балахнинъ) -- confirmed the hard way, a first
# draft of this fix silently overwrote his genuine rank_or_title.
# family_name is the actual disambiguator; list_number is kept too as a
# belt-and-suspenders check.
_OCR_MISREAD_CORRECTIONS: dict[str, dict[int, dict[str, tuple[str, str]]]] = {
    "administration_1902-03_p004": {
        1: {"family_name": ("Крыловъ", "Крыловъ"),
            "rank_or_title": ("по найму, Московскій пеховой", "по найму, Московскій цеховой")},
    },
    "administration_1903-04_p004": {
        2: {"family_name": ("Крыловъ", "Крыловъ"),
            "rank_or_title": ("по найму, Московскій пеховой", "по найму, Московскій цеховой")},
    },
}


def _repair_ocr_misreads(parsed: dict, page_id: str) -> int:
    """Applies _OCR_MISREAD_CORRECTIONS: single-field verbatim corrections
    for confirmed OCR misreads (scan-checked, not guessed). Each field's
    fix is a (expected_current_value, corrected_value) pair -- applied only
    if every field on the entry still holds its expected current value, so
    a list_number collision with an unrelated entry (confirmed to happen on
    both target pages here) can't silently overwrite the wrong row.
    Returns the count of entries touched."""
    fixes = _OCR_MISREAD_CORRECTIONS.get(page_id)
    if not fixes:
        return 0
    entries = parsed.get("entries", [])
    n_touched = 0
    for e in entries:
        ln = _list_number_int(e.get("list_number"))
        if ln not in fixes:
            continue
        field_fixes = fixes[ln]
        if any((e.get(field) or "").strip() != expected
               for field, (expected, _) in field_fixes.items()):
            continue
        for field, (_, corrected) in field_fixes.items():
            e[field] = corrected
        n_touched += 1
    return n_touched


# Found while triaging the ~512 rows still empty after the tenure_note_text
# fix (RG: "Let's work on these") -- a third, smaller instrument-recovery
# pattern, distinct from both prior ones: heading_path holds a genuine
# institutional/section heading with the person's own instrument tacked
# onto the END, as one compound value, instead of split across two fields.
# Unlike the shape-A migration (issue #59), the prefix here is real,
# information-bearing heading text (these pages also list non-orchestra
# roles -- répétiteurs, librarians -- under the same broader institution,
# so "the person belongs to the Orchestra" is worth keeping), not a stuck
# neighbor value -- so the prefix is preserved as the new heading_path,
# not blanked.
#
# Confirmed by scan on both affected pages (the only 2 in the corpus with
# this shape, 50 rows total): `musicians_1897-98_MSK_p000` (13 rows,
# "Оркестр оперы и балета. <Instrument>." -- the page's own top-of-page
# section heading, printed once, glued onto every row along with that
# row's real instrument) and `musicians_1902-03_SP_p001` (37 rows,
# "Оркестръ / <Instrument>"). Every single instrument value on both pages
# checked directly against the scan and matched exactly -- e.g. entry 8
# (Борхъ) reads "Ударные инструменты" in print, matching the extraction.
_PREFIXED_INSTRUMENT_HEADING_SEPARATORS = (" / ", ". ")
_PREFIXED_INSTRUMENT_HEADING_PREFIXES = (
    "Оркестръ", "Оркестр", "Оркестр оперы и балета", "Оркестръ оперы и балета",
)


def _repair_heading_path_prefixed_instrument(parsed: dict) -> int:
    """Splits a heading_path of the form "<real heading><sep><Instrument>"
    into heading_path="<real heading>" (sep/trailing period stripped) and
    instrument="<Instrument>", for Musicians entries where `instrument` is
    empty. Only matches when the text before the last separator is one of
    the confirmed real headings above (_PREFIXED_INSTRUMENT_HEADING_
    PREFIXES) and the text after it is exactly a known instrument -- see
    the comment above for the scan verification behind this. Returns the
    count of entries touched."""
    entries = parsed.get("entries", [])
    n_touched = 0
    for e in entries:
        if (e.get("instrument") or "").strip():
            continue
        hp = (e.get("heading_path") or "").strip()
        if not hp:
            continue
        for sep in _PREFIXED_INSTRUMENT_HEADING_SEPARATORS:
            if sep not in hp:
                continue
            prefix, _, tail = hp.rpartition(sep)
            tail = tail.strip().rstrip(".")
            if prefix in _PREFIXED_INSTRUMENT_HEADING_PREFIXES and tail in _KNOWN_INSTRUMENTS:
                e["heading_path"] = prefix
                e["instrument"] = tail
                n_touched += 1
                break
    return n_touched


# One-off year misreading found during RG's 2026-08-24 missing-pages audit
# (checking date continuity within each Repertoire season surfaced a
# phantom 596-day gap in 1895-96, which turned out to be this, not a
# missing page). Confirmed against the scan
# (ForUpload_1895-96_Repertoire_005.jpg): every row on this one page reads
# "1895 г." in the margin, but the model read it as "1893 г." on all 108
# sessions on the page (a genuine misreading, not a printed variant --
# checked corpus-wide first and confirmed no other Repertoire page has
# this shape of year/season mismatch, so this is scoped to just this page
# rather than a general rule).
_REPERTOIRE_YEAR_FIXES: dict[str, tuple[str, str]] = {
    "repertoire_1895-96_p005": ("1893 г.", "1895 г."),
}

# A confirmed damaged-type misread found during RG's 2026-08-25 check of the
# 4 remaining single-digit-misread candidates. `repertoire_1899-00_p037`
# sessions 19-21 (Большой/Малый/Новый) read date_text "23 Суббота", sitting
# chronologically between "28 Пятница" and "30 Воскрес." -- impossible as a
# real date (23 April 1900 was in fact a Sunday, already correctly used
# earlier on this same page for sessions 1-3, so this can't be a second,
# genuine "23"). A zoomed high-res crop of the actual scan
# (ForUpload_1899-00_Repertoire.pdf, page index 37) shows the printed glyph
# itself is worn/damaged -- not a clean "23" -- but visually and
# chronologically consistent with a mangled "29". Scoped to this exact
# page_id + exact wrong string so it can never touch the unrelated, correct
# "23 Воскрес." sessions elsewhere on the same page. The page's other
# out-of-sequence date on this page, "9 Четвергъ" (sessions 34-36), was
# checked separately and confirmed genuinely printed that way in the
# original book -- left untouched, not part of this fix.
_REPERTOIRE_DAY_FIXES: dict[str, tuple[str, str]] = {
    "repertoire_1899-00_p037": ("23 Суббота", "29 Суббота"),
}

# Two confirmed wrong-`month_text` bugs found during the same audit, each
# with a different underlying cause but the same fix shape (a page-keyed
# 1-based index range where the wrong month should read the right one):
#   - repertoire_1907-08_p000: the page genuinely spans Aug 30 - Sep 9
#     ("30 августа. ... 9 сентября." per the scan), but the model never
#     advanced month_text off "Августъ" after day 31 rolled over to 1 --
#     sessions 7-35 (days 1-9) need "Августъ" -> "Сентябрь".
#   - repertoire_1902-03_p008: the page spans Oct 22 - Nov 3, but the
#     model labeled every row "Ноябрь" from the start, including the
#     Oct 22-31 rows -- likely misled by this page's own running header
#     printing the two months in reverse order ("22 ноября. ... 3
#     октября.", the opposite of every other page's start-date-first
#     convention). Confirmed against the scan
#     (ForUpload_1902-03_Repertoire_008.jpg): the day sequence itself
#     (22...31, then a "Ноябрь" row-group label, then 1...3) is
#     internally consistent and unambiguous regardless of the header.
#     Sessions 1-29 (days 22-31) need "Ноябрь" -> "Октябрь"; sessions
#     30-40 (days 1-3) are already correctly "Ноябрь" and untouched.
#   - repertoire_1896-97_p000: a third variant of the same underlying
#     class of bug, causing all-September rows to collapse onto a single
#     bogus date (1896-09-01) instead of their real, distinct days.
#     Confirmed against the scan (ForUpload_1896-97_Repertoire_000.jpg):
#     the margin clearly reads "1 сентября." through "11 сентября." (a
#     normal one-page September 1-11 span), but `month_text` for every
#     one of those rows literally reads "1 сентября" (a full date
#     fragment bleeding in, not just the month name) -- `parse_russian_date`
#     picks up the stray "1" from inside month_text instead of the real,
#     varying day already sitting correctly in date_text, so every row
#     silently collapsed onto Sept 1. Sessions 21-70 (all of "1
#     сентября" onward, to the end of the page) need month_text ->
#     "Сентябрь".
# All three are page-specific fixes, not a general rule -- the
# corpus-wide scan that found the first two (a day-number decrease under
# an unchanged month_text) turned up several other candidate pages that
# do NOT share this same confirmed shape (see docs/eval/known_issues.md);
# those are left alone pending individual verification, not guessed at.
_REPERTOIRE_MONTH_FIXES: dict[str, list[tuple[int, int, str, str]]] = {
    "repertoire_1907-08_p000": [(7, 35, "Августъ", "Сентябрь")],
    "repertoire_1902-03_p008": [(1, 29, "Ноябрь", "Октябрь")],
    "repertoire_1896-97_p000": [(21, 70, "1 сентября", "Сентябрь")],
}

# A confirmed model fabrication, not a mislabeling like the fixes above --
# found chasing a 10-day gap on the season's last page. `ForUpload_1890-91_
# Repertoire.pdf` page index 12 (its final page, no page 13 exists) prints
# exactly 7 dates (May 7-15) and ends cleanly with a decorative closing
# flourish, confirmed by rendering the actual PDF page directly at high
# resolution -- nothing else is printed on it. But the raw JSON has 3 more
# sessions dated "26 -" (all `is_dark`, no works/receipts) that don't
# correspond to anything on the page or any other page in the file. Since
# they're already `is_dark` with no content, dropping them loses no real
# performance data -- there's no correct date to move them to, because
# they were never real to begin with.
_REPERTOIRE_FABRICATED_SESSIONS: dict[str, set[int]] = {
    "repertoire_1890-91_p012": {15, 16, 17},
}

# A confirmed content/date misalignment, structurally different from every
# fix above -- found checking `repertoire_1897-98_p010` as one of the 4
# single-digit-misread candidates. On real date 22 Марта the Маріинскій
# printed two sessions (a benefit matinee, then "A basso Porto" + Walküre
# 3rd act in the evening, 5785 р. 10 к.); the extraction treated the
# evening session as a new date "23 Понедѣльникъ" instead of recognizing
# it as day 22's second sitting, cascading a +1 date-label offset through
# every subsequent Маріинскій-column session (indices 51-76) while every
# other theater column on the same rows stayed correctly dated the whole
# time -- confirmed row-by-row, including exact receipts figures, against
# a 400dpi scan of the actual page (ForUpload_1897-98_Repertoire.pdf,
# page index 10). The chain resolves cleanly at index 76 (Маріинскій,
# "Romeo und Julie", 7983 р. 10 к.) -> real date 27 Марта -- there is no
# "28 Апрѣля" anywhere on this page. Indices 77-80 (Александринскій/
# Михайловскій/Большой/Малый) inherited that same fabricated "28 Апрѣля"
# for an unrelated reason: the page's own compositor split the 6 Апрѣля
# row across two printed sub-rows and used a bare "апр." (no day digit)
# as a purely visual month-transition aid for the top sub-row -- not a
# distinct calendar date, per RG's direct reading of the scan, confirmed
# against the pixel-measured grid lines (a full-width rule separates it
# from both 27 Пятница above and 6 Понедѣльникъ below, but its content --
# Михайловскій's "Bénéfice de M. Rousselle. Le Roman d'un jeune Homme
# pauvre" -- shares that same play title, at a different receipts figure,
# with the row explicitly labeled "6 Понедѣльникъ" just below, exactly
# the rehearsal-then-performance shape already established for 22 Марта).
# Index-keyed (not a uniform range shift or single find/replace like the
# fixes above) because the 10 affected sessions split into two different
# corrected targets depending on theater.
_REPERTOIRE_SESSION_DATE_FIXES: dict[str, dict[int, tuple[str, str]]] = {
    "repertoire_1897-98_p010": {
        51: ("22 Воскресенье", "Мартъ"),
        56: ("23 Понедѣльникъ", "Мартъ"),
        61: ("24 Вторникъ", "Мартъ"),
        66: ("25 Среда", "Мартъ"),
        71: ("26 Четвергъ", "Мартъ"),
        76: ("27 Пятница", "Мартъ"),
        77: ("6 Понедѣльникъ", "Апрѣль"),
        78: ("6 Понедѣльникъ", "Апрѣль"),
        79: ("6 Понедѣльникъ", "Апрѣль"),
        80: ("6 Понедѣльникъ", "Апрѣль"),
    },
}

# The "bare month name, no day digit" bug family -- found systematically by
# RG's 2026-08-25 corpus-wide search (prompted by the p010 "апр." row above)
# for every raw.event_entry.date_text that doesn't start with a digit: 34
# rows across 15 page/date_text combinations. 10 of those combinations are
# genuine blank divider rows (a real closure or simply an empty cell,
# already correctly captured as is_dark with zero content -- confirmed
# against scans, left alone, no entry needed here). The other 5 are real
# bugs, individually scan-verified with RG page by page, each a different
# shape -- too varied for the more specific tables above, so collected here
# as a generic per-index field-override mechanism (page_id -> {1-based
# session index: {field_name: new_value}}, applied via dict.update). Also
# updated pipeline/prompts/repertoire_system.txt so future extraction runs
# handle this convention correctly at the source; this table only fixes
# JSON already on disk.
#   - repertoire_1904-05_p021, index 40 (Новый театръ): the printed cell
#     genuinely splits УТРО/ВЕЧЕРЪ, but the model captured only the УТРО
#     half ("Женитьба, соверш. невѣр. событие, ком.", 330 р. 95 к.) and
#     mislabeled it with the bare month "Январь." instead of recognizing
#     it as 1 Января's morning session (RG confirmed against the scan: the
#     content sits on the row after the bare label, not before, and RG
#     corrected an initial guess that it was 31 Декабря). The matching
#     blank ВЕЧЕРЪ half is missing entirely from the JSON -- see
#     _REPERTOIRE_SESSION_INSERTIONS below for that half.
#   - repertoire_1903-04_p008, indices 32 and 35 (Михайловскій): a genuine
#     two-showing run of "Marthe, com. La carotte, com.-bouffe." at
#     different receipts each day -- RG confirmed both real dates carry
#     this same double-bill, just on 1 Суббота (1573 р. 70 к., currently
#     mislabeled "Ноябрь.") and 2 Воскрес. (772 р. 35 к., currently
#     mislabeled "1 Суббота").
#   - repertoire_1900-01_p009, indices 29-34 (all 3 Moscow theaters): a
#     phantom extra row inserted from misreading the "Ноябрь"/"Нодобрь"
#     month header as its own dated row, shifting content one label late
#     for exactly one boundary -- confirmed against the scan (Фея
#     куколъ+Парижскій рыночекъ+Привалъ кавалеріи/671 р. 71 к. genuinely
#     belongs on 1 Среда; Лакме/3026 р. 76 к. genuinely belongs on 2
#     Четвергъ). The now-redundant trailing "2 Четвергъ" placeholders
#     (indices 35-37, already empty) are dropped via
#     _REPERTOIRE_DUPLICATE_SESSIONS below.
#   - repertoire_1905-06_p005, index 34 (Новый театръ): same УТРО-half-only
#     capture-and-mislabel shape as p021 above ("Октябрь." -> 1 Суббота,
#     morning), plus a second, independent bug on the same session -- the
#     receipts (273 р. 41 к.) made it into the JSON but the work title
#     ("Каширская старина, др.", confirmed on the scan) was dropped
#     entirely, so it's restored here too.
_REPERTOIRE_FIELD_OVERRIDES: dict[str, dict[int, dict]] = {
    "repertoire_1904-05_p021": {
        40: {"date_text": "1 Суббота.", "session": "morning"},
    },
    "repertoire_1903-04_p008": {
        32: {"date_text": "1 Суббота."},
        35: {"date_text": "2 Воскрес."},
    },
    "repertoire_1900-01_p009": {
        29: {"date_text": "1 Среда", "month_text": "ноября"},
        30: {"date_text": "1 Среда", "month_text": "ноября"},
        31: {"date_text": "1 Среда", "month_text": "ноября"},
        32: {"date_text": "2 Четвергъ"},
        33: {"date_text": "2 Четвергъ"},
        34: {"date_text": "2 Четвергъ"},
    },
    "repertoire_1905-06_p005": {
        34: {"date_text": "1 Суббота.", "session": "morning",
             "works": [{"work_title": "Каширская старина", "genre": "др."}]},
    },
}

# New session records to insert that are missing from the raw JSON entirely
# -- part of the same 2026-08-25 bare-month-label investigation. Confirmed
# against the scan that repertoire_1904-05_p021's 1 Января cell for Новый
# театръ genuinely splits УТРО/ВЕЧЕРЪ (see _REPERTOIRE_FIELD_OVERRIDES
# above for the УТРО half, already present but mislabeled); the ВЕЧЕРЪ half
# is a plain dash with no content, and the model never emitted a row for it
# at all. page_id -> list of (insert immediately after this 1-based index
# in the pre-drop/pre-override session list, new session dict).
_REPERTOIRE_SESSION_INSERTIONS: dict[str, list[tuple[int, dict]]] = {
    "repertoire_1904-05_p021": [
        (40, {"date_text": "1 Суббота.", "month_text": "января.",
              "year_text": "1904—1905 гг.", "session": "evening",
              "theater": "Новый театръ", "is_dark": True}),
    ],
}

# Sessions confirmed as pure duplicates -- not fabrications like
# _REPERTOIRE_FABRICATED_SESSIONS (which have no corresponding page content
# anywhere), and not mislabeled content needing reattribution like
# _REPERTOIRE_FIELD_OVERRIDES above. In both cases below the exact same
# content (same works, same receipts) already exists correctly elsewhere on
# the same page under its real date, so dropping the extra copy loses no
# data. Found during the same 2026-08-25 bare-month-label sweep.
#   - repertoire_1900-01_p009, indices 35-37: the now-empty trailing "2
#     Четвергъ" placeholders left over once indices 32-34's real content is
#     relabeled to 2 Четвергъ (see _REPERTOIRE_FIELD_OVERRIDES above).
#   - repertoire_1905-06_p011, indices 26-28: byte-for-byte identical to
#     indices 29-31 (Аида/1686 р. 55 к., Красная мантія/210 р. 29 к., Въ
#     старомъ Гейдельбергѣ/120 р. 17 к.) -- the model captured 1 Вторника's
#     content twice, once correctly labeled and once under the bare
#     "Ноябрь" month header.
_REPERTOIRE_DUPLICATE_SESSIONS: dict[str, set[int]] = {
    "repertoire_1900-01_p009": {35, 36, 37},
    "repertoire_1905-06_p011": {26, 27, 28},
}

# Three confirmed cases (2026-09-10, docs/eval/known_issues.md #69,
# check_repertoire_unknown_theater's unrecognized_theater_field flags on
# the column-wise Gate 3 corpus) where a theater-only crop's own `theater`
# field came back wrong in a way no simple і/и normalization covers --
# each individually scan-verified by matching the session's OWN
# works/receipts against the real column that content belongs to, not
# guessed from the wrong string alone:
#   - repertoire_1903-04_p032: 'С.-Петербургский театр.' -- the model
#     substituted the page's own generic running header ("С.-
#     Петербургскіе театры.", printed above every column's specific
#     header) for the column-specific one. Confirmed genuinely
#     Маріинскій: the flagged rows' works ("Царя, оп." -> "Жизнь за
#     Царя", "Волшебная флейта") match Маріинскій's own crop
#     (repertoire_1903-04_p032__theateronly_0.png) row for row, including
#     receipts figures.
#   - repertoire_1907-08_p024: 'бургскіе театры. Александрийскій
#     театръ.' -- the tail of that same generic running header
#     concatenated with a slightly-misspelled real header ("Александрий-"
#     for "Александрин-"). Confirmed genuinely Александринскій: works
#     ("Холопы", "Смерть Іоанна Грознаго", "Урокъ танцевъ") are Russian
#     spoken-drama titles matching that theater's known repertoire.
#   - repertoire_1907-08_p008: 'Александровскій театръ.' -- NOT a
#     header-mixing or spelling-drift case at all: this string doesn't
#     resemble either the real per-column header or the running header.
#     Confirmed genuinely Михайловскій by direct crop comparison
#     (repertoire_1907-08_p008__theateronly_2.png) -- receipts figures
#     (1413 p. 88 к., 614 p. 88 к., ...) and French works ("commissaire
#     est bon enfant", "L'espionne") match that crop exactly, row for
#     row. A plain model error with no traceable relationship to what's
#     actually printed -- content-matched to the correct theater, not
#     pattern-matched to the wrong one.
# Matched by exact VALUE (not session index), so safe regardless of
# extraction source -- see _repair_repertoire's docstring on why that
# distinction matters here.
_REPERTOIRE_THEATER_FIELD_FIXES: dict[str, dict[str, str]] = {
    "repertoire_1903-04_p032": {"С.-Петербургский театр.": "Маріинскій театръ."},
    "repertoire_1907-08_p024": {"бургскіе театры. Александрийскій театръ.": "Александринскій театръ."},
    "repertoire_1907-08_p008": {"Александровскій театръ.": "Михайловскій театръ."},
}


_REPERTOIRE_MARIINSKY_TYPO_RE = re.compile(r"\bМариинскій\b")


def _repair_repertoire_theater_spelling(parsed: dict, page_id: str) -> tuple[int, int]:
    """Two theater-field fixes applied to EVERY Repertoire page, value-
    matched (not index-matched) so both are safe for any extraction
    source:

    1. The page-specific `_REPERTOIRE_THEATER_FIELD_FIXES` table above --
       an exact string match, so it only ever touches the confirmed wrong
       value on the confirmed page.
    2. The Мариинскій -> Маріинскій modernized-spelling drift (modern и
       for pre-reform і) -- measured at 337 flagged sessions across 27
       pages of the Gate 3 corpus, ALL of them this one theater (no other
       KNOWN_THEATERS name showed this drift in the theater field). Same
       fix shape as Roster's `_repair_mariinsky_spelling`
       (`_MARIINSKY_TYPO_RE` above), reimplemented here rather than
       shared because it applies to a session's `theater` field, not an
       entry's `heading_path`/`institution`.

    Returns (n_field_fixed, n_spelling_fixed)."""
    field_fixes = _REPERTOIRE_THEATER_FIELD_FIXES.get(page_id, {})
    n_field, n_spelling = 0, 0
    for s in parsed.get("sessions", []):
        theater = s.get("theater")
        if not theater:
            continue
        if theater in field_fixes:
            s["theater"] = field_fixes[theater]
            n_field += 1
            continue
        if _REPERTOIRE_MARIINSKY_TYPO_RE.search(theater):
            s["theater"] = _REPERTOIRE_MARIINSKY_TYPO_RE.sub("Маріинскій", theater)
            n_spelling += 1
    return n_field, n_spelling


def _repair_repertoire(parsed: dict, page_id: str, source: str = "baseline") -> tuple[dict, dict[str, int]]:
    """`source` distinguishes which extraction produced `parsed`, because
    the tables below are NOT all equally safe to apply regardless of that.

    `_REPERTOIRE_YEAR_FIXES` and `_REPERTOIRE_DAY_FIXES` match by VALUE
    (the session's own `year_text`/`date_text` equals the confirmed-wrong
    string) -- order-independent, so they only ever fire if that exact
    wrong string is actually present, regardless of extraction method.
    Applied unconditionally.

    Every other table here -- `_REPERTOIRE_MONTH_FIXES`,
    `_REPERTOIRE_SESSION_DATE_FIXES`, `_REPERTOIRE_FIELD_OVERRIDES`,
    `_REPERTOIRE_SESSION_INSERTIONS`, `_REPERTOIRE_FABRICATED_SESSIONS`,
    `_REPERTOIRE_DUPLICATE_SESSIONS` -- is keyed to a 1-based SEQUENTIAL
    INDEX into `parsed["sessions"]`, hand-verified against the single-call
    baseline extraction's own session ordering (interleaved by date across
    every theater on the page, one row per date/session). Column-wise
    extraction's merged output (`merge_columnwise_page`,
    `pipeline/schemas/repertoire_columnwise.py`) orders sessions GROUPED BY
    THEATER instead -- a completely different ordering -- so the same
    index `i` in column-wise output almost certainly lands on a different
    session's data entirely. Applying these unconditionally there would
    either silently misapply a hand-verified fix to the wrong row, or
    (for the range+value compound check in `_REPERTOIRE_MONTH_FIXES`)
    occasionally still match by coincidence on an unrelated session that
    happens to carry the same wrong value -- neither is acceptable for a
    fix that was specifically scan-verified against one exact row.

    Confirmed 2026-09-10 (docs/eval/known_issues.md #69) that several of
    these page_ids ARE part of the column-wise Gate 3 corpus
    (repertoire_1899-00_p037, repertoire_1907-08_p000,
    repertoire_1902-03_p008, repertoire_1904-05_p021,
    repertoire_1903-04_p008, repertoire_1900-01_p009,
    repertoire_1905-06_p005, repertoire_1905-06_p011) -- so this isn't a
    hypothetical risk, it's live for the very corpus about to be parsed.
    Until each of those 6 pages (`_REPERTOIRE_DAY_FIXES`/
    `_REPERTOIRE_YEAR_FIXES` don't apply to any of them) is individually
    re-verified against column-wise's own read and given its own
    content-keyed fix if the same defect recurs there, `source="columnwise"`
    skips all six index-keyed tables entirely rather than risk a silent
    misapplication -- an unfixed page that still needs review beats a
    wrongly "fixed" one that looks clean."""
    counts = {
        "year_fixed": 0, "month_fixed": 0, "day_fixed": 0, "session_fixed": 0,
        "field_overridden": 0, "inserted": 0,
        "fabricated_dropped": 0, "duplicate_dropped": 0,
        "theater_field_fixed": 0, "theater_spelling_fixed": 0,
    }
    index_keyed_safe = source == "baseline"
    year_fix = _REPERTOIRE_YEAR_FIXES.get(page_id)
    day_fix = _REPERTOIRE_DAY_FIXES.get(page_id)
    month_fixes = _REPERTOIRE_MONTH_FIXES.get(page_id, []) if index_keyed_safe else []
    session_fixes = _REPERTOIRE_SESSION_DATE_FIXES.get(page_id, {}) if index_keyed_safe else {}
    field_overrides = _REPERTOIRE_FIELD_OVERRIDES.get(page_id, {}) if index_keyed_safe else {}
    insertions = ({idx: new_s for idx, new_s in _REPERTOIRE_SESSION_INSERTIONS.get(page_id, [])}
                  if index_keyed_safe else {})
    drop_indices = _REPERTOIRE_FABRICATED_SESSIONS.get(page_id, set()) if index_keyed_safe else set()
    duplicate_indices = _REPERTOIRE_DUPLICATE_SESSIONS.get(page_id, set()) if index_keyed_safe else set()
    counts["fabricated_dropped"] = len(drop_indices)
    counts["duplicate_dropped"] = len(duplicate_indices)
    kept = []
    for i, s in enumerate(parsed.get("sessions", []), start=1):
        if i in drop_indices or i in duplicate_indices:
            continue
        val = s.get("session")
        if val in SESSION_LABEL_FIX:
            s["session"] = SESSION_LABEL_FIX[val]
        if year_fix and s.get("year_text") == year_fix[0]:
            s["year_text"] = year_fix[1]
            counts["year_fixed"] += 1
        for start_idx, end_idx, wrong, right in month_fixes:
            if start_idx <= i <= end_idx and s.get("month_text") == wrong:
                s["month_text"] = right
                counts["month_fixed"] += 1
        if day_fix and s.get("date_text") == day_fix[0]:
            s["date_text"] = day_fix[1]
            counts["day_fixed"] += 1
        if i in session_fixes:
            s["date_text"], s["month_text"] = session_fixes[i]
            counts["session_fixed"] += 1
        if i in field_overrides:
            s.update(field_overrides[i])
            counts["field_overridden"] += 1
        kept.append(s)
        if i in insertions:
            kept.append(insertions[i])
            counts["inserted"] += 1
    parsed["sessions"] = kept
    n_field, n_spelling = _repair_repertoire_theater_spelling(parsed, page_id)
    counts["theater_field_fixed"] = n_field
    counts["theater_spelling_fixed"] = n_spelling
    return parsed, counts


# One log message per _repair_repertoire() counts key -- (stage, message).
_REPERTOIRE_FIX_MESSAGES = {
    "year_fixed": ("repertoire_year_fixed",
        "session(s) had a scan-verified year_text fix applied (see "
        "_REPERTOIRE_YEAR_FIXES)"),
    "month_fixed": ("repertoire_month_fixed",
        "session(s) had a scan-verified month_text fix applied (see "
        "_REPERTOIRE_MONTH_FIXES)"),
    "day_fixed": ("repertoire_day_fixed",
        "session(s) had a scan-verified date_text fix applied for a "
        "damaged/worn printed digit (see _REPERTOIRE_DAY_FIXES)"),
    "session_fixed": ("repertoire_session_date_fixed",
        "session(s) had a scan-verified date_text/month_text "
        "reattribution applied (see _REPERTOIRE_SESSION_DATE_FIXES)"),
    "field_overridden": ("repertoire_field_overridden",
        "session(s) had a scan-verified field override applied (see "
        "_REPERTOIRE_FIELD_OVERRIDES)"),
    "inserted": ("repertoire_session_inserted",
        "session(s) inserted for a printed cell the model never "
        "emitted a row for (see _REPERTOIRE_SESSION_INSERTIONS)"),
    "fabricated_dropped": ("repertoire_fabricated_dropped",
        "session(s) confirmed fabricated (no corresponding page "
        "content, verified against the actual PDF page) and dropped "
        "-- see _REPERTOIRE_FABRICATED_SESSIONS"),
    "duplicate_dropped": ("repertoire_duplicate_dropped",
        "session(s) confirmed to duplicate content already correctly "
        "captured elsewhere on the same page and dropped -- see "
        "_REPERTOIRE_DUPLICATE_SESSIONS"),
    "theater_field_fixed": ("repertoire_theater_field_fixed",
        "session(s) had a scan-verified `theater` field correction "
        "applied for a wrong/header-mixed value (see "
        "_REPERTOIRE_THEATER_FIELD_FIXES)"),
    "theater_spelling_fixed": ("repertoire_theater_spelling_fixed",
        "session(s) had the Мариинскій->Маріинскій modernized-spelling "
        "typo fixed in `theater` (see _repair_repertoire_theater_spelling)"),
}


def _repair_roster(parsed: dict) -> tuple[dict, int]:
    """Returns (repaired parsed dict, count of entries dropped). An entry is
    dropped only when family_name is missing AND heading_path doesn't match
    a recoverable "Surname, First Patronymic[, rank]" shape -- e.g. a bare
    section heading like "Дежурные врачи" or "Парикмахеры" that the model
    emitted as its own entry with no person name anywhere in the JSON. There
    is no name to recover in that case, so the entry is dropped rather than
    fabricated -- and dropping only that one entry (not the whole page, as
    an uncaught pydantic error on this field would otherwise do) keeps every
    other, valid entry on the page."""
    kept = []
    n_dropped = 0
    for e in parsed.get("entries", []):
        if e.get("family_name"):
            kept.append(e)
            continue
        heading = e.get("heading_path") or ""
        m = NAME_IN_HEADING_RE.match(heading.strip())
        if not m:
            n_dropped += 1
            continue
        e["family_name"] = m.group(1)
        e["first_name"] = m.group(2)
        e["patronymic"] = m.group(3)
        e["heading_path"] = m.group(4)
        kept.append(e)
    parsed["entries"] = kept
    return parsed, n_dropped


# Found triaging RG's flagged "2 Оставилъ службу-as-family_name garbage
# rows" (carried over from issue #61) -- turned out to be issue #26's
# "non-person text captured as person_entry rows" pattern, in a specific,
# recurring shape: a trailing service-end or death note that belongs to
# the entry directly above gets split off into its own fake "person"
# entry instead. Corpus-wide search found 5 instances (not 2), spanning
# 3 entity types, not just Musicians -- confirmed by scan for every one:
#   - musicians_1891-92_MSK_p003 (x2), musicians_1897-98_SP_p001,
#     administration_1895-96_p001: family_name="Оставилъ службу",
#     tenure_note_text holds just the date -- e.g.
#     musicians_1897-98_SP_p001 entry 74 (Плацатка) prints "... Фаготъ.
#     Оставилъ службу 1 октября 1897 г." as one continuous entry.
#   - theaterschoolstaff_1902-03_p002: family_name="†", with the
#     trailing date text ("1902 г.") landing in first_name instead --
#     matches entry 11 (Шемаевъ)'s own printed "† 1902 г." death note.
# Every one of the 5 is the entry immediately preceding it, confirmed
# directly (not assumed from adjacency alone). Also spotted a distinct,
# unrelated bug on the same theaterschoolstaff page while checking this
# (a real person, Сперанскій, whose name landed in heading_path instead
# of family_name on the entry that follows) -- left unfixed, out of
# scope for this specific merge-and-drop repair.
_FRAGMENT_ENTRY_FAMILY_NAMES = {"Оставилъ службу", "†"}


def _repair_fragment_person_entries(parsed: dict) -> int:
    """Merges a mis-extracted trailing service-end/death note (family_name
    in _FRAGMENT_ENTRY_FAMILY_NAMES, no real name anywhere in the entry)
    into the tenure_note_text of the immediately preceding kept entry,
    where it genuinely belongs, then drops the fragment. A no-op if the
    fragment is the very first entry on the page (nothing to merge into --
    not observed in the corpus, but guarded rather than assumed away).
    Returns the count of entries merged and dropped."""
    entries = parsed.get("entries", [])
    kept = []
    n_merged = 0
    for e in entries:
        fam = (e.get("family_name") or "").strip()
        if fam in _FRAGMENT_ENTRY_FAMILY_NAMES and kept:
            fragment = " ".join(
                p.strip() for p in (fam, e.get("first_name"), e.get("tenure_note_text"))
                if p and str(p).strip()
            )
            prev = kept[-1]
            existing = (prev.get("tenure_note_text") or "").strip()
            prev["tenure_note_text"] = f"{existing} {fragment}".strip() if existing else fragment
            n_merged += 1
            continue
        kept.append(e)
    parsed["entries"] = kept
    return n_merged


# "Отдѣль" (soft sign) is never a real word in this context -- "отдѣлъ"
# (department, masc.) always ends in the hard sign in this pre-reform
# orthography. Confirmed via RG's 2026-08-24 institution/department
# accuracy audit: checked directly against the scan
# (ForUpload_1890-91_Spisok_ProductionTeam.pdf p.111, "Отдѣлъ
# декораціонный.") -- a genuine one-character extraction misreading
# (ъ -> ь), not a printed variant, confirmed corpus-wide to affect only
# heading_path, only "Отдѣль декораціонный" (130 ProductionTeam rows
# across 6 seasons), never any other "Отдѣль ..." phrase and never
# `institution`. Word-boundary matched so a genuine unrelated word ending
# the same way is never touched (none exist in this corpus, checked).
_SOFT_SIGN_TYPO_RE = re.compile(r"\bОтдѣль\b")


def _repair_department_spelling(parsed: dict) -> int:
    """Fixes the Отдѣль->Отдѣлъ typo in heading_path/institution. Returns
    the count of entries touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        for field in ("heading_path", "institution"):
            val = e.get(field)
            if val and _SOFT_SIGN_TYPO_RE.search(val):
                e[field] = _SOFT_SIGN_TYPO_RE.sub("Отдѣлъ", val)
                n_fixed += 1
    return n_fixed


_HARD_SIGN_TYPO_RE = re.compile(r"\b(Малый|Большой) театр\.")


def _repair_teatr_spelling(parsed: dict) -> int:
    """Fixes the театр.->театръ. typo (dropped pre-reform ъ) in
    heading_path/institution. Confirmed against the scan on
    productionteam_1894-95_p003 (ForUpload_1894-95_Spisok_ProductionTeam.pdf
    p.93): the same page extracts both "Малый театр." and "Малый театръ"
    for the identical printed subheader "Малый театръ." -- an extraction
    slip, not a genuine variant. Returns the count of entries touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        for field in ("heading_path", "institution"):
            val = e.get(field)
            if val and _HARD_SIGN_TYPO_RE.search(val):
                e[field] = _HARD_SIGN_TYPO_RE.sub(r"\1 театръ.", val)
                n_fixed += 1
    return n_fixed


_MOKEEV_TYPO_RE = re.compile(r"\bМокѳевъ\b")


def _repair_mokeev_spelling(parsed: dict) -> int:
    """Fixes a single homoglyph typo (ѳ/fita misread for ѣ/yat) in
    family_name: musicians_1890-91_SP_p004 entry #24 extracted as
    "Мокѳевъ" where the scan (p.79) clearly reads "Мокѣевъ", matching the
    spelling this same person (Николай Васильевичъ, trumpet, Оркестръ
    Александринскаго театра) uses in every other season 1891-92 through
    1902-03 -- confirmed by RG against the scan while reviewing
    entities.person_candidate. Returns the count of entries touched
    (always 0 or 1 -- this is a single confirmed one-off, not a pattern)."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        val = e.get("family_name")
        if val and _MOKEEV_TYPO_RE.search(val):
            e["family_name"] = _MOKEEV_TYPO_RE.sub("Мокѣевъ", val)
            n_fixed += 1
    return n_fixed


_ORDINAL_ONLY_RE = re.compile(r"^\d+-[йя]\.?$")
_SMOTRI_RE = re.compile(r"смотри|см\.")
_SMOTRI_TARGET_RE = re.compile(r"см\.?\s*(.+)", re.IGNORECASE)


def _repair_smotri_crossref(parsed: dict) -> int:
    """Fixes the "см. <оркестръ>" cross-reference-stub bug (issues #27/#29
    in known_issues.md): a musician who plays in more than one of this
    season's orchestras only gets their full biographical entry written
    out once, on one roster -- every other roster just cross-references
    it, e.g. "Бѣлкинъ (см. оперный оркестръ). Тромбонъ." (confirmed
    against musicians_1890-91_SP_p003, ForUpload_1890-91_Spisok_
    OrchestraSP.pdf p.78). The extraction step mis-splits this into
    first_name="см."/patronymic="<orchestra type>", or, when an homonym
    ordinal is also printed ("Вальтеръ 2-й"), into
    first_name="<ordinal>"/patronymic="см. <orchestra type>".

    This function does NOT attempt to resolve who the cross-reference
    points to -- that's a cross-page, cross-entity_type, sometimes-
    genuinely-ambiguous operation entities.py's Tier 1/2 matching (plus,
    where necessary, hand review) already owns, and raw/analysis is
    meant to stay a verbatim record of what's actually printed on THIS
    page, not a resolved identity. It only: (1) stops "см."/the
    cross-reference target from being stored as if they were real
    first_name/patronymic values, (2) preserves the ordinal onto
    family_name where one was about to be lost (matching the existing
    "<family_name> <ordinal>" convention used elsewhere), and (3) keeps
    the cross-reference itself, not just discards it, by folding it into
    tenure_note_text so a reader (or a future entity-resolution pass)
    still knows this entry points elsewhere. Returns the count of
    entries touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        first = (e.get("first_name") or "").strip()
        pat = (e.get("patronymic") or "").strip()
        ordinal = None
        target = None
        if _ORDINAL_ONLY_RE.match(first) and _SMOTRI_RE.search(pat):
            ordinal = first
            m = _SMOTRI_TARGET_RE.search(pat)
            target = m.group(1).strip() if m else pat
        elif first.rstrip(".").lower() == "см":
            target = pat or None
        else:
            continue

        if ordinal:
            fam = (e.get("family_name") or "").strip()
            if fam and not fam.endswith(ordinal):
                e["family_name"] = f"{fam} {ordinal}"
        e["first_name"] = None
        e["patronymic"] = None
        if target:
            note = f"(см. {target.rstrip('.')})"
            existing = (e.get("tenure_note_text") or "").strip()
            e["tenure_note_text"] = f"{existing} {note}".strip() if existing else note
        n_fixed += 1
    return n_fixed


_ROLE_NOTE_PATRONYMIC_RE = re.compile(r"^\(.*(?:же и|свящ|воспит|завѣд|состои).*\)$", re.IGNORECASE)


def _repair_role_note_patronymic(parsed: dict) -> int:
    """Fixes the case where a printed dual-role/appointment annotation is
    the *entire* patronymic field, with no real patronymic underneath --
    confirmed pattern, known_issues.md issue #30: "Марквардтъ, Августъ"
    (Musicians, 8 appearances 1894-1902) had patronymic exactly
    "(онъ же и капельмейстеръ военной музыки)" ("he is also the
    kapellmeister of the military band") every single time, i.e. this
    isn't a patronymic with a note appended (like the театр./Мариинскій
    fixes above) -- the whole field IS the note, and the real fact is
    this person genuinely has no patronymic recorded in the source.
    Deliberately narrow (whole-field match, not a substring strip) so it
    never touches a genuine patronymic that merely has a parenthetical
    appended to it (a separate, still-open question -- see issue #30's
    "13 people this is legitimately printed content" finding). Returns
    the count of entries touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        val = (e.get("patronymic") or "").strip()
        if val and _ROLE_NOTE_PATRONYMIC_RE.match(val):
            e["patronymic"] = None
            note = val if val.startswith("(") else f"({val})"
            existing = (e.get("tenure_note_text") or "").strip()
            e["tenure_note_text"] = f"{existing} {note}".strip() if existing else note
            n_fixed += 1
    return n_fixed


_LETTER_SPACED_RE = re.compile(
    r"^(?P<spaced>([А-ЯЁІѢѲѴа-яёіѣѳѵ\-] ){2,}[А-ЯЁІѢѲѴа-яёіѣѳѵ])(?P<ordinal> \d+-[йя])?$"
)


def _repair_letter_spacing(parsed: dict) -> int:
    """Fixes letter-spaced (tracked/разрядка) typography transcribed
    literally instead of being read as a normal word -- confirmed
    against the scan on musicians_1898-99_SP_p006 (page 94): every
    surname on this page is printed with letter-spacing for emphasis
    ("К у д е н г о л ь д т ъ"), which the model correctly collapses to
    a normal word in the great majority of cases but occasionally
    transcribes verbatim, spaces and all. Applied to family_name/
    first_name/patronymic alike (letter-spacing is a page-wide
    typographic choice, not specific to one field). Deliberately
    requires 3+ single-character tokens (never fires on a genuine short
    2-word value like a real "Иванъ Петровъ"-shaped name) and collapses
    by removing whitespace within the spaced run, which correctly
    handles a hyphenated surname spaced the same way
    ("М а й е р ъ - П и р к о" -> "Майеръ-Пирко") since the hyphen is
    itself one of the spaced tokens. Also handles a trailing homonym
    ordinal that ISN'T itself letter-spaced ("К у л л е 1-й" ->
    "Кулле 1-й", confirmed on the same page/scan, same convention as
    "<family_name> <ordinal>" used throughout the rest of the corpus) --
    the ordinal keeps its own separating space rather than being fused
    onto the collapsed name. Returns the count of entries touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        for field in ("family_name", "first_name", "patronymic"):
            val = e.get(field)
            if not val:
                continue
            m = _LETTER_SPACED_RE.match(val)
            if m:
                e[field] = m.group("spaced").replace(" ", "") + (m.group("ordinal") or "")
                n_fixed += 1
    return n_fixed


_DASH_CONTINUATION_RE = re.compile(r"^-\s*(.+)$")

_KNOWN_INSTRUMENTS = {
    "Ударные инструменты", "Первая скрипка", "Вторая скрипка", "Скрипка",
    "Альтъ", "Альть", "Віолончель", "Виолончель", "Віолончелъ", "Біолончель",
    "Контрабасъ", "Флейта", "Гобой",
    "Кларнетъ", "Басъ-кларнетъ", "Басскларнетъ",
    "Фаготъ", "Первый фаготъ", "Контръ-фаготъ",
    "Вальдгорнъ", "Вальдгорнь", "Вальдгорнт", "Вальтгорнъ", "Волторнъ",
    "Валторна", "Вальторнъ", "Валторнъ", "Волторна",
    "Труба", "Вторая труба", "2-я труба", "Тромбонъ", "Туба", "Арфа", "Литавры",
    "Корнетъ", "Корнетъ-а-пистонъ",
    "Фортепіано", "Органъ", "Піанистъ", "піанистъ", "Піанисть", "Органистъ", "Барабанъ",
}
# Longest-first so a multi-word instrument ("Первая скрипка") is tried
# before a substring of it ("Скрипка") would otherwise match first.
_INSTRUMENT_VARIANTS_BY_LEN = sorted(_KNOWN_INSTRUMENTS, key=len, reverse=True)


def _split_leading_instrument(text: str) -> tuple[str | None, str]:
    """If `text` starts with a known instrument name (bare, or followed
    by a period/space then more text), returns (instrument, remainder).
    Otherwise returns (None, text) unchanged. Used to peel an instrument
    off the front of a value without disturbing whatever comes after --
    e.g. "Скрипка. Солистъ Двора Его Императорскаго Величества" ->
    ("Скрипка", "Солистъ Двора Его Императорскаго Величества")."""
    for instr in _INSTRUMENT_VARIANTS_BY_LEN:
        if text == instr:
            return instr, ""
        if text.startswith(instr + "."):
            return instr, text[len(instr) + 1:].strip()
        if text.startswith(instr + " "):
            rest = text[len(instr):].strip()
            # Only a real boundary if what follows starts a new
            # sentence/clause (capitalized) -- guards against a false
            # split mid-phrase (no such case found in this corpus, but
            # cheap insurance for a future volume).
            if not rest or rest[0].isupper():
                return instr, rest
    return None, text


def _repair_compound_first_name(parsed: dict) -> int:
    """Fixes a two-word/hyphenated first name where the second half
    landed in patronymic instead of staying joined to first_name.
    Confirmed against the scan on musicians_1890-91_MSK_p004 (page 110):
    "Кнауеръ, Генрихъ - Эдуардъ" and "Падель, Іоганъ - Фридрихъ" both
    print as one hyphenated compound first name (common for this
    corpus's German-surnamed musicians -- see issue #30's "no real
    patronymic" note on the same pattern), extracted as
    first_name="Генрихъ"/patronymic="- Эдуардъ" instead of
    first_name="Генрихъ-Эдуардъ". A patronymic that starts with a bare
    dash is never a real patronymic (a genuine one never begins with
    punctuation), so this is a safe, general signal -- not scoped to
    these two people specifically. Also confirmed on
    musicians_1902-03_MSK_p002 (page 116): "Рессеръ, Мардохей Земинъ
    Шліомовичъ" -- no dash this time, a bare two-word first name printed
    with no comma before its own real patronymic -- extracted as
    first_name="Мардохей"/patronymic="Земинъ Шліомовичъ" instead of
    first_name="Мардохей Земинъ"/patronymic="Шліомовичъ". Detected the
    same way issue #32 detects instrument-shaped contamination: when
    patronymic is two words and the first of them is itself a known
    non-patronymic-shaped fragment already seen as part of a first name
    elsewhere ("Земинъ"), rather than a blanket "first word of any
    multi-word patronymic" rule, which would be too broad to trust
    without more than one example. Returns the count of entries
    touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        first = (e.get("first_name") or "").strip()
        pat = (e.get("patronymic") or "").strip()
        if not first or not pat:
            continue
        m = _DASH_CONTINUATION_RE.match(pat)
        if m:
            e["first_name"] = f"{first}-{m.group(1).strip()}"
            e["patronymic"] = None
            n_fixed += 1
        elif pat.startswith("Земинъ "):
            e["first_name"] = f"{first} Земинъ"
            e["patronymic"] = pat[len("Земинъ "):].strip() or None
            n_fixed += 1
    return n_fixed


def _repair_instrument_in_patronymic(parsed: dict) -> int:
    """Fixes an instrument name sitting in patronymic instead of the
    dedicated instrument field -- confirmed against the scan on
    musicians_1898-99_SP_p006 (page 94, entry 43): "Шредеръ, Карлъ (съ
    1 декабря 1884 г.). Ударные инструменты." prints no patronymic at
    all (matching this corpus's established German-surname-no-
    patronymic pattern, see issue #30), with "Ударные инструменты"
    genuinely being Шредеръ's own instrument -- extracted into
    patronymic while `instrument` was left NULL. Same underlying
    field-boundary confusion as issue #32's `instrument_clean` work, but
    that only cleaned the `instrument` field itself; this is the mirror
    case, where the value needs to move INTO instrument, not just out of
    it. Only fires when instrument is currently empty, so it can never
    clobber a real instrument value with a misplaced one.

    Strips a trailing period before matching -- found chasing the
    "Лудольфи, Валентинъ Контрабасъ." fused-name cluster RG flagged
    (carried over from issue #59): `patronymic="Контрабасъ."` (with the
    trailing period the printed sentence ends on) missed the original
    exact-match check by one character, on 2 rows each for Лудольфи and
    Котте (musicians_1893-94_SP_p001/musicians_1894-95_SP_p001, entries
    55 and 64) -- all 4 confirmed against the scan (e.g. "55. Котте,
    Фридрихъ-Эрнестъ (съ 1 сентября 1893 г.). Фаготъ." prints cleanly,
    matching the patronymic value exactly once the period is stripped).
    Returns the count of entries touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        pat = (e.get("patronymic") or "").strip()
        if pat.rstrip(".") in _KNOWN_INSTRUMENTS and not (e.get("instrument") or "").strip():
            e["instrument"] = pat.rstrip(".")
            e["patronymic"] = None
            n_fixed += 1
    return n_fixed


_TENURE_DATE_PREFIX_RE = re.compile(r"^\((съ [^)]+г\.)\)\.?\s*")
_SMOTRI_NOTE_PREFIX_RE = re.compile(r"^(\(с[мс]\.?[^)]*\))\.?\s*", re.IGNORECASE)
_SERVICE_NOTE_RE = re.compile(r"^(Переведенъ|Оставилъ службу|†)")


def _repair_musicians_rank_or_title(parsed: dict) -> tuple[int, int]:
    """Fixes `rank_or_title` for Musicians -- per docs/schema.md this
    field is "civil rank... or honorific," never an instrument, but a
    full-corpus audit found 97% of its non-blank Musicians values
    (3048 of 3157) are instrument-shaped contamination in one of several
    combined forms, confirmed against multiple scans
    (musicians_1890-91_MSK_p001 p.107, musicians_1893-94_MSK_p003 p.102,
    musicians_1892-93_MSK_p002 p.98). Deliberately a *split*, not a
    match-and-wipe: RG's explicit concern was that a blanket "contains
    an instrument word" rule would destroy real content sitting in the
    same field (confirmed real: "Скрипка. Солистъ Двора Его
    Императорскаго Величества" -- a genuine, verified honorific
    immediately following a misplaced instrument). Peels off, in order:

    1. A "(съ <date> г.)" tenure-start prefix -- confirmed by checking
       all 37 corpus occurrences directly against tenure_note_text: the
       same date text is present there in every single case, so this
       prefix is always fully redundant and safe to discard outright
       (not re-appended anywhere).
    2. A "(см. ...)" cross-reference note -- relocated to
       tenure_note_text verbatim, not discarded (unlike the tenure-date
       prefix, this doesn't duplicate anything else on the row).
    3. A leading known instrument name -- moved to `instrument` if that
       field is currently empty; always stripped from rank_or_title
       either way.
    4. Whatever remains, if it's a service note ("Переведенъ..."/
       "Оставилъ службу...") -- relocated to tenure_note_text.

    Anything left after all four steps stays in rank_or_title
    untouched -- this is deliberately the majority of genuine
    non-instrument values (honorifics like "Заслуженный артистъ
    Императорскихъ театровъ", roles like "Капельмейстеръ"), confirmed
    by manual review of every distinct value in the corpus, not
    inferred. Does NOT touch a value that doesn't match any of the
    four patterns, even partially -- e.g. "Пьянисть при драматическихъ
    спектакляхъ" (a genuine role sentence using a non-standard spelling
    of "pianist") is left exactly as printed rather than force-matched.

    Returns (entries with instrument recovered, entries with a note
    relocated to tenure_note_text)."""
    n_instr = n_note = 0
    for e in parsed.get("entries", []):
        val = (e.get("rank_or_title") or "").strip()
        if not val:
            continue
        original = val
        note_parts = []

        m = _TENURE_DATE_PREFIX_RE.match(val)
        if m:
            val = val[m.end():].strip()

        m2 = _SMOTRI_NOTE_PREFIX_RE.match(val)
        if m2:
            note_parts.append(m2.group(1))
            val = val[m2.end():].strip()

        instr, val = _split_leading_instrument(val)
        if instr:
            if not (e.get("instrument") or "").strip():
                e["instrument"] = instr
                n_instr += 1

        if val and _SERVICE_NOTE_RE.match(val):
            note_parts.append(val)
            val = ""

        if note_parts:
            existing = (e.get("tenure_note_text") or "").strip()
            addition = " ".join(note_parts)
            e["tenure_note_text"] = f"{existing} {addition}".strip() if existing else addition
            n_note += 1

        if val != original:
            e["rank_or_title"] = val or None
    return n_instr, n_note


def _repair_musicians_stray_heading(parsed: dict) -> int:
    """Fixes one confirmed one-off: `rank_or_title="Музыканты:"` on
    musicians_1892-93_MSK_p002 (page 98) -- confirmed against the scan
    this is a genuine printed section header ("Балетный оркестръ" ->
    "Музыканты:" -> "1. Альбрехтъ..."), not an instrument or a real
    personal title, that landed in the wrong field entirely. Deliberately
    scoped to this exact value rather than any general "looks like a
    heading" rule -- with only one confirmed instance, generalizing
    would risk false positives with no second example to validate
    against. Appends to heading_path (matching the "<parent> / Музыканты"
    compound-path convention already used 51 times elsewhere in this
    corpus) rather than replacing it. Returns the count of entries
    touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        if (e.get("rank_or_title") or "").strip() == "Музыканты:":
            heading = (e.get("heading_path") or "").strip()
            e["heading_path"] = f"{heading} / Музыканты" if heading else "Музыканты"
            e["rank_or_title"] = None
            n_fixed += 1
    return n_fixed


_MARIINSKY_TYPO_RE = re.compile(r"\bМариинскій\b")


def _repair_mariinsky_spelling(parsed: dict) -> int:
    """Fixes the Мариинскій->Маріинскій typo (modern и instead of
    pre-reform і) in heading_path/institution. Confirmed against the scan
    on productionteam_1903-04_p001 (page 119): every subheader on that
    page reads "Маріинскій театръ", but 8 of its entries' institution
    extracted as "Мариинскій" -- an extraction slip, not a genuine
    variant. Deliberately scoped to the nominative "Мариинскій театръ"
    form only -- does NOT touch the unrelated, still-open institution
    fabrication on administration_1903-04_p003 ("...Императорскомъ
    Мариинскомъ театрѣ", a different case form, see known_issues.md).
    Returns the count of entries touched."""
    n_fixed = 0
    for e in parsed.get("entries", []):
        for field in ("heading_path", "institution"):
            val = e.get(field)
            if val and _MARIINSKY_TYPO_RE.search(val):
                e[field] = _MARIINSKY_TYPO_RE.sub("Маріинскій", val)
                n_fixed += 1
    return n_fixed


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--raw-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--extraction-source", choices=["baseline", "columnwise", "rowlevel"],
                     default="baseline",
                     help="which extraction method produced --raw-dir's JSON. Controls "
                          "whether _repair_repertoire's index-keyed hand-fix tables apply "
                          "(they were verified against baseline's session ordering; see "
                          "_repair_repertoire's docstring). Default 'baseline' preserves "
                          "existing behavior for every run before 2026-09-10.")
    ap.add_argument("--page-headers", type=Path, default=None,
                     help="pipeline/extract_page_headers.py's output CSV (page_id, "
                          "header_text, ...). Optional -- when given, backfills "
                          "date_undate for Repertoire sessions that have no month_text/"
                          "year_text of their own, using the page's own printed date-"
                          "range header (see flatten_repertoire_page's page_header arg "
                          "and docs/eval/known_issues.md #69). Never touches the "
                          "verbatim month_text/year_text fields themselves.")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.manifest, encoding="utf-8")))
    page_headers = load_page_headers(args.page_headers) if args.page_headers else {}

    merged = {
        "person_entry": [], "person_entry_service": [], "person_entry_credit": [],
        "event_entry": [], "event_entry_performance": [],
    }
    errors = []

    for row in rows:
        page_id = row["page_id"]
        raw_path = args.raw_dir / f"{page_id}.raw.json"
        if not raw_path.exists():
            errors.append({"page_id": page_id, "stage": "missing_raw",
                            "error": f"no raw JSON at {raw_path}"})
            continue

        kind = "roster" if row["entity_type"] in ROSTER_KINDS else "repertoire"
        try:
            raw_text = raw_path.read_text(encoding="utf-8")
            parsed_json = json.loads(_strip_code_fence(raw_text))

            if kind == "roster":
                parsed_json, n_dropped = _repair_roster(parsed_json)
                if n_dropped:
                    errors.append({"page_id": page_id, "stage": "entry_dropped_no_name",
                                    "error": f"{n_dropped} entrie(s) had no family_name and no "
                                             f"recoverable name in heading_path (e.g. a bare "
                                             f"section heading captured as its own entry); "
                                             f"dropped, rest of page kept"})
                n_fragment_merged = _repair_fragment_person_entries(parsed_json)
                if n_fragment_merged:
                    errors.append({"page_id": page_id, "stage": "fragment_entry_merged",
                                    "error": f"{n_fragment_merged} entrie(s) were a trailing "
                                             f"service-end/death note mis-split into its own fake "
                                             f"person entry (see _FRAGMENT_ENTRY_FAMILY_NAMES); "
                                             f"merged into the preceding entry's tenure_note_text "
                                             f"and dropped"})
                if row["entity_type"] == "Graduates":
                    n_backfilled = _repair_graduates_tenure(parsed_json, page_id)
                    if n_backfilled:
                        errors.append({"page_id": page_id, "stage": "graduates_tenure_backfilled",
                                        "error": f"{n_backfilled} entrie(s) backfilled from "
                                                 f"docs/ballet_graduates_tenure.csv's hand-verified "
                                                 f"dates; not a validation failure, logged for visibility"})
                n_misattached = _repair_misattachments(parsed_json, page_id)
                if n_misattached:
                    errors.append({"page_id": page_id, "stage": "misattachment_fixed",
                                    "error": f"{n_misattached} entrie(s) had a scan-verified "
                                             f"institution/heading_path/credit_summary_text fix "
                                             f"applied (see _MISATTACHMENT_FIXES); not a validation "
                                             f"failure, logged for visibility"})
                n_spelling = _repair_department_spelling(parsed_json)
                if n_spelling:
                    errors.append({"page_id": page_id, "stage": "department_spelling_fixed",
                                    "error": f"{n_spelling} entrie(s) had the Отдѣль->Отдѣлъ "
                                             f"typo fixed; not a validation failure, logged for "
                                             f"visibility"})
                n_teatr = _repair_teatr_spelling(parsed_json)
                if n_teatr:
                    errors.append({"page_id": page_id, "stage": "teatr_spelling_fixed",
                                    "error": f"{n_teatr} entrie(s) had the Малый/Большой "
                                             f"театр.->театръ. typo fixed; not a validation "
                                             f"failure, logged for visibility"})
                n_mariinsky = _repair_mariinsky_spelling(parsed_json)
                if n_mariinsky:
                    errors.append({"page_id": page_id, "stage": "mariinsky_spelling_fixed",
                                    "error": f"{n_mariinsky} entrie(s) had the Мариинскій"
                                             f"->Маріинскій typo fixed; not a validation "
                                             f"failure, logged for visibility"})
                n_mokeev = _repair_mokeev_spelling(parsed_json)
                if n_mokeev:
                    errors.append({"page_id": page_id, "stage": "mokeev_spelling_fixed",
                                    "error": f"{n_mokeev} entrie(s) had the Мокѳевъ"
                                             f"->Мокѣевъ typo fixed; not a validation "
                                             f"failure, logged for visibility"})
                n_smotri = _repair_smotri_crossref(parsed_json)
                if n_smotri:
                    errors.append({"page_id": page_id, "stage": "smotri_crossref_cleaned",
                                    "error": f"{n_smotri} entrie(s) had a \"см. <orchestra>\" "
                                             f"cross-reference stub cleaned out of first_name/"
                                             f"patronymic (moved to tenure_note_text); not a "
                                             f"validation failure, logged for visibility"})
                n_role_note = _repair_role_note_patronymic(parsed_json)
                if n_role_note:
                    errors.append({"page_id": page_id, "stage": "role_note_patronymic_cleaned",
                                    "error": f"{n_role_note} entrie(s) had a dual-role/"
                                             f"appointment note occupying the entire "
                                             f"patronymic field, moved to tenure_note_text; "
                                             f"not a validation failure, logged for visibility"})
                n_letter_spaced = _repair_letter_spacing(parsed_json)
                if n_letter_spaced:
                    errors.append({"page_id": page_id, "stage": "letter_spacing_collapsed",
                                    "error": f"{n_letter_spaced} field(s) had letter-spaced "
                                             f"(tracked) typography collapsed back into a "
                                             f"normal word; not a validation failure, logged "
                                             f"for visibility"})
                n_compound_first = _repair_compound_first_name(parsed_json)
                if n_compound_first:
                    errors.append({"page_id": page_id, "stage": "compound_first_name_fixed",
                                    "error": f"{n_compound_first} entrie(s) had a two-word/"
                                             f"hyphenated first name's second half wrongly "
                                             f"split into patronymic, rejoined to first_name; "
                                             f"not a validation failure, logged for visibility"})
                n_instr_pat = _repair_instrument_in_patronymic(parsed_json)
                if n_instr_pat:
                    errors.append({"page_id": page_id, "stage": "instrument_in_patronymic_fixed",
                                    "error": f"{n_instr_pat} entrie(s) had an instrument name "
                                             f"sitting in patronymic, moved to the instrument "
                                             f"field; not a validation failure, logged for "
                                             f"visibility"})
                if row["entity_type"] == "Musicians":
                    n_rot_instr, n_rot_note = _repair_musicians_rank_or_title(parsed_json)
                    if n_rot_instr:
                        errors.append({"page_id": page_id, "stage": "rank_or_title_instrument_fixed",
                                        "error": f"{n_rot_instr} entrie(s) had an instrument "
                                                 f"name recovered from rank_or_title into the "
                                                 f"instrument field; not a validation failure, "
                                                 f"logged for visibility"})
                    if n_rot_note:
                        errors.append({"page_id": page_id, "stage": "rank_or_title_note_relocated",
                                        "error": f"{n_rot_note} entrie(s) had a cross-reference "
                                                 f"or service note relocated out of "
                                                 f"rank_or_title into tenure_note_text; not a "
                                                 f"validation failure, logged for visibility"})
                    n_stray_heading = _repair_musicians_stray_heading(parsed_json)
                    if n_stray_heading:
                        errors.append({"page_id": page_id, "stage": "stray_heading_in_rank_or_title_fixed",
                                        "error": f"{n_stray_heading} entrie(s) had a genuine "
                                                 f"section header (\"Музыканты:\") sitting in "
                                                 f"rank_or_title, moved to heading_path; not a "
                                                 f"validation failure, logged for visibility"})
                n_instr_transcribed = _repair_instrument_transcriptions(parsed_json, page_id)
                if n_instr_transcribed:
                    errors.append({"page_id": page_id, "stage": "instrument_hand_transcribed",
                                    "error": f"{n_instr_transcribed} entrie(s) had their "
                                             f"instrument hand-transcribed from the scan "
                                             f"(see _INSTRUMENT_TRANSCRIPTION_FIXES) after a "
                                             f"stuck heading_path run destroyed it in every "
                                             f"other field; not a validation failure, logged "
                                             f"for visibility"})
                n_heading_restored = _repair_heading_path_restore(parsed_json, page_id)
                if n_heading_restored:
                    errors.append({"page_id": page_id, "stage": "heading_path_restored",
                                    "error": f"{n_heading_restored} entrie(s) had heading_path "
                                             f"restored from a confirmed-stuck value (see "
                                             f"_HEADING_PATH_RESTORE_FIXES); not a validation "
                                             f"failure, logged for visibility"})
                n_shape_a_migrated, n_shape_a_special = _repair_heading_path_shape_a(parsed_json, page_id)
                if n_shape_a_migrated:
                    errors.append({"page_id": page_id, "stage": "heading_path_shape_a_migrated",
                                    "error": f"{n_shape_a_migrated} entrie(s) had a bare "
                                             f"instrument name moved from heading_path to "
                                             f"instrument (\"shape A\" migration); not a "
                                             f"validation failure, logged for visibility"})
                if n_shape_a_special:
                    errors.append({"page_id": page_id, "stage": "heading_path_shape_a_corrected",
                                    "error": f"{n_shape_a_special} entrie(s) had a confirmed-"
                                             f"wrong or confirmed-blank heading_path value "
                                             f"corrected/cleared rather than migrated as-is "
                                             f"(see _SHAPE_A_CORRECTIONS/_SHAPE_A_NO_INSTRUMENT); "
                                             f"not a validation failure, logged for visibility"})
                n_shape_a_special_cases = _repair_shape_a_special_cases(parsed_json, page_id)
                if n_shape_a_special_cases:
                    errors.append({"page_id": page_id, "stage": "heading_path_shape_a_special_case",
                                    "error": f"{n_shape_a_special_cases} entrie(s) had a one-off "
                                             f"heading_path bug fixed (see "
                                             f"_SHAPE_A_SPECIAL_CASES); not a validation failure, "
                                             f"logged for visibility"})
                n_tenure_note_instr = _repair_tenure_note_instrument(parsed_json, page_id)
                if n_tenure_note_instr:
                    errors.append({"page_id": page_id, "stage": "tenure_note_instrument_recovered",
                                    "error": f"{n_tenure_note_instr} entrie(s) had instrument "
                                             f"recovered from tenure_note_text (see "
                                             f"_repair_tenure_note_instrument); not a validation "
                                             f"failure, logged for visibility"})
                n_prefixed_instr = _repair_heading_path_prefixed_instrument(parsed_json)
                if n_prefixed_instr:
                    errors.append({"page_id": page_id, "stage": "heading_path_prefixed_instrument_split",
                                    "error": f"{n_prefixed_instr} entrie(s) had a compound "
                                             f"\"<heading><sep><Instrument>\" heading_path split "
                                             f"into the real heading plus instrument (see "
                                             f"_repair_heading_path_prefixed_instrument); not a "
                                             f"validation failure, logged for visibility"})
                n_title_relocated = _repair_tenure_note_title_relocation(parsed_json, page_id)
                if n_title_relocated:
                    errors.append({"page_id": page_id, "stage": "tenure_note_title_relocated",
                                    "error": f"{n_title_relocated} entrie(s) had a rank/title-"
                                             f"shaped value moved from tenure_note_text to "
                                             f"rank_or_title (see "
                                             f"_repair_tenure_note_title_relocation); not a "
                                             f"validation failure, logged for visibility"})
                n_fabricated_crossref = _repair_fabricated_crossref_note(parsed_json, page_id)
                if n_fabricated_crossref:
                    errors.append({"page_id": page_id, "stage": "fabricated_crossref_note_stripped",
                                    "error": f"{n_fabricated_crossref} entrie(s) had a fabricated "
                                             f"\"(см. ...)\" cross-reference note stripped from "
                                             f"tenure_note_text (see "
                                             f"_FABRICATED_CROSSREF_NOTE_FIXES); not a validation "
                                             f"failure, logged for visibility"})
                n_instr_service_note = _repair_instrument_service_note(parsed_json, page_id)
                if n_instr_service_note:
                    errors.append({"page_id": page_id, "stage": "instrument_service_note_restored",
                                    "error": f"{n_instr_service_note} entrie(s) had a resignation/"
                                             f"transfer note displacing the real instrument, "
                                             f"restored and relocated (see "
                                             f"_INSTRUMENT_SERVICE_NOTE_CORRECTIONS); not a "
                                             f"validation failure, logged for visibility"})
                n_instr_crossref = _repair_instrument_crossref_note(parsed_json, page_id)
                if n_instr_crossref:
                    errors.append({"page_id": page_id, "stage": "instrument_crossref_note_restored",
                                    "error": f"{n_instr_crossref} entrie(s) had a \"(см. ...)\" "
                                             f"cross-reference note displacing the real "
                                             f"instrument, restored and relocated (see "
                                             f"_INSTRUMENT_CROSSREF_CORRECTIONS); not a "
                                             f"validation failure, logged for visibility"})
                n_ocr_misread = _repair_ocr_misreads(parsed_json, page_id)
                if n_ocr_misread:
                    errors.append({"page_id": page_id, "stage": "ocr_misread_corrected",
                                    "error": f"{n_ocr_misread} entrie(s) had a scan-confirmed "
                                             f"OCR misread corrected (see "
                                             f"_OCR_MISREAD_CORRECTIONS); not a "
                                             f"validation failure, logged for visibility"})
                page = RosterPage.model_validate(parsed_json)
                tables = flatten_roster_page(page_id, row["entity_type"], page)
            else:
                parsed_json, repertoire_counts = _repair_repertoire(
                    parsed_json, page_id, source=args.extraction_source)
                for key, n in repertoire_counts.items():
                    if n:
                        stage, msg = _REPERTOIRE_FIX_MESSAGES[key]
                        errors.append({"page_id": page_id, "stage": stage,
                                        "error": f"{n} {msg}; not a validation failure, "
                                                 f"logged for visibility"})
                page = RepertoirePage.model_validate(parsed_json)
                tables = flatten_repertoire_page(page_id, row["season"], row["city"], page,
                                                  page_header=page_headers.get(page_id))

            for table_name, table_rows in tables.items():
                merged[table_name].extend(table_rows)

        except Exception as e:
            errors.append({"page_id": page_id, "stage": "parse_or_validate", "error": str(e)})

    for table_name, table_rows in merged.items():
        out_path = args.out_dir / f"{table_name}.csv"
        write_csv(table_rows, out_path)
        print(f"{table_name}: {len(table_rows)} rows -> {out_path}")

    errors_path = args.out_dir / "validation_errors.csv"
    if errors:
        write_csv(errors, errors_path)
        print(f"\n{len(errors)} pages FAILED validation -> {errors_path}")
    else:
        print("\nno validation errors")


if __name__ == "__main__":
    main()
