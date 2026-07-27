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

_MONTHS = {
    "янв": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "іюн": 6,
    "июл": 7, "іюл": 7, "август": 8, "сентябр": 9, "октябр": 10,
    "ноябр": 11, "декабр": 12,
}

_DATE_RE = re.compile(
    r"(\d{1,2})\s+([а-яіѣ]+)\s+(\d{4})",
    re.IGNORECASE,
)


def _month_number(word: str) -> int | None:
    word = word.lower().replace("ѣ", "е").replace("і", "и")
    for stem, num in _MONTHS.items():
        if word.startswith(stem):
            return num
    return None


def parse_russian_date(text: str) -> str | None:
    """Extract the first day/month-name/year triple from free text like
    'съ 1 мая 1882 г.' or '† 4 іюня 1891 г.' and return 'YYYY-MM-DD'."""
    if not text:
        return None
    m = _DATE_RE.search(text)
    if not m:
        return None
    day, month_word, year = m.groups()
    month = _month_number(month_word)
    if month is None:
        return None
    try:
        return f"{int(year):04d}-{month:02d}-{int(day):02d}"
    except ValueError:
        return None
