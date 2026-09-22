"""Best-effort parser for printed pre-reform Russian dates into an ISO-shaped
string. This is NOT a Gregorian conversion -- the source calendar is Julian
(Old Style) throughout, and per docs/schema.md we keep dates exactly as
printed. The ISO shape here is just a sortable/joinable stand-in for a real
Undate value; swap in undate-python's parser later without touching the
verbatim `*_date_text` fields this is derived from.

Returns None (not an exception) when the text doesn't match a recognized
day/month/year pattern -- callers should treat that as "needs a human or a
smarter parser," not a failure.
"""
import re
import unicodedata

_MONTHS = {
    "янв": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "іюн": 6,
    # docs/eval/known_issues.md #37: "іюня" (June) missing its leading "і"
    # ("юня") turned out to be a real, common extraction artifact, not a rare
    # typo -- confirmed 54 instances corpus-wide (mostly BalletArtists tenure
    # sentences), every one previously returning None here despite the rest
    # of the date being perfectly legible. "юн" can't collide with any other
    # month (none of the other 11 stems start with ю).
    "юн": 6,
    "июл": 7, "іюл": 7, "август": 8, "сентябр": 9, "октябр": 10,
    "ноябр": 11, "декабр": 12,
}

_DATE_RE = re.compile(
    # Repertoire year_text is often a season-spanning range, e.g.
    # "1896—1897 гг." (the printed table covers Aug of the first year
    # through summer of the second) rather than a single year -- the second
    # group is optional so single-year text (the common roster tenure-date
    # case, e.g. "1 мая 1882 г.") still matches exactly as before.
    # The day may carry a hyphenated ordinal suffix ("1-го сентября") --
    # confirmed in narrative-style tenure text (docs/eval/known_issues.md
    # #34) across 188 rows in 4 entity types (Graduates, BalletArtists,
    # Musicians, TheaterSchoolStaff), not just the Graduates report this was
    # found in -- every one of those was previously returning None here.
    # The month word may be followed by a comma instead of (or with no)
    # period -- confirmed on single-page-season Repertoire sessions whose
    # own printed month_text carries one ("1 января, 1906—1907 гг."); widen
    # the separator to [.,]? rather than just \.? so this comma case matches
    # too, without narrowing what already matched (this can only add
    # matches, never break an existing period-terminated or bare one).
    r"(\d{1,2})(?:-(?:го|й|е|я|му))?\s+([а-яіѣ]+)[.,]?\s+(\d{4})(?:\s*[—\-–]\s*(\d{4}))?",
    re.IGNORECASE,
)


def _month_number(word: str) -> int | None:
    # Check both directions: word.startswith(stem) handles the full form
    # ("Февраль" starts with stem "феврал"); stem.startswith(word) handles
    # abbreviated forms printed with a period ("Февр." is shorter than its
    # own stem). Abbreviations are consistently >=3 chars in the source, so
    # this doesn't collide across the 12 (mostly first-letter-distinct) stems.
    word = word.lower().replace("ѣ", "е").replace("і", "и").rstrip(".")
    for stem, num in _MONTHS.items():
        if word.startswith(stem) or (word and stem.startswith(word)):
            return num
    return None


def parse_russian_date(text: str) -> str | None:
    """Extract the first day/month-name/year triple from free text like
    'съ 1 мая 1882 г.' or '† 4 іюня 1891 г.' and return 'YYYY-MM-DD'.

    When the year is printed as a season-spanning range ("1896—1897 гг."),
    picks whichever of the two years the month actually falls in for a
    theater season running August-July: August-December is the first year,
    January-July is the second. A single printed year is used as-is."""
    if not text:
        return None
    # docs/eval/known_issues.md #37: a stray combining accent mark
    # ("дека́бря" for "декабря") occasionally lands mid-word and breaks the
    # month match even though every actual letter is present and correct --
    # NFD-decompose and drop Unicode combining marks (category Mn) before
    # matching. Pre-reform Russian never legitimately carries a combining
    # accent in running text, so this is always safe to strip, never a
    # meaningful character to preserve.
    text = "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")
    m = _DATE_RE.search(text)
    if not m:
        return None
    day, month_word, year, year2 = m.groups()
    month = _month_number(month_word)
    if month is None:
        return None
    if year2 and month <= 7:
        year = year2
    try:
        return f"{int(year):04d}-{month:02d}-{int(day):02d}"
    except ValueError:
        return None
