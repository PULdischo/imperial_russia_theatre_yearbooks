# Blind reading: printed headings on the ballet company pages

You are reading scanned pages of a pre-1918 Russian theatre yearbook (the "Ежегодникъ Императорскихъ театровъ"). Each page belongs to the list of one ballet company (St Petersburg = SP, Moscow = MSK) for one season. The list is printed in two columns of numbered entries (surname, first name, patronymic, a start date in brackets, then a note of roles and performance counts).

**This is a BLIND reading.** Look ONLY at the image files named below. Do NOT open any database, CSV, JSON (other than your batch file), or anything under the project's `outputs/full_run`, `docs/` or `pipeline/` folders. Read each page on its own evidence; never fill in a heading because another season has one.

## What I need

For every page: every HEADING that is printed on it, exactly where it stands, and the numbering of the entries. I do NOT need the entries themselves transcribed.

Kinds of heading (use these labels):
- `running_head`: the small line at the very top of the page, repeated from page to page (e.g. "СПИСОКЪ АРТИСТОВЪ." or "ПЕТЕРБУРГСКАЯ БАЛЕТНАЯ ТРУППА."). Record it, but it is not a section heading.
- `title`: a large display heading that opens a whole list (e.g. "Балетная труппа.").
- `section`: a centred or letter-spaced heading over a run of entries (e.g. "Артистки:", "Артисты:", or any other, such as pupils, guests, people who left).
- `post`: a staff-post label standing over one name or a short group at the start of the list (e.g. "Первый балетмейстеръ", "Режиссеръ", "Помощники режиссера:").
- `other_list`: a heading that belongs to a DIFFERENT list sharing the page (e.g. the end of the opera chorus above, or "Оркестры." below).

## How to work

1. Read `batch_<N>.json` in this folder (your N is given in your task). It has `pages` (in order) and `full_res` (the full-resolution image of each page).
2. For each page, Read the overview image `ov/<page_id>.png` (1500 px high; headings are legible at this size).
3. If a heading's exact letters or punctuation are not certain at that size, crop it from the full-resolution image with Python/PIL and enlarge it, then read the crop. Run Python like this:
   `cd "/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main" && uv run python -c "..."`
   Save any crops under `crops/` in this folder.
4. Keep the pre-reform spelling exactly as printed (ъ, ѣ, і, ѳ), including a final colon or period. Do not modernise, and do not "correct" what looks like a misprint; note it instead.

## What to record per page

Write one JSON object per page:

```
{"page_id": "...",
 "running_head": "..." or null,
 "headings": [
    {"kind": "title|section|post|other_list",
     "text": "<verbatim>",
     "column": "left|right|full",
     "before_entry": "<list number and surname of the FIRST entry under it, e.g. '1. Адамовичъ'; for a post over an unnumbered name, just the surname>",
     "certain": true|false}
 ],
 "first_entry": "<number and surname of the first ballet-list entry on the page>",
 "last_entry": "<number and surname of the last ballet-list entry on the page>",
 "numbering_restarts": ["<number and surname of each entry where the numbering starts again at 1>"],
 "entry_run_is": "women|men|mixed|staff|unclear",   // judged from the surnames on the page (-а/-ая = women)
 "foreign_matter": "<anything on the page that is not part of this ballet list: which list, and where on the page>" or null,
 "note": "<anything odd>" or null}
```

- List headings in reading order (left column top to bottom, then right column).
- If a page has NO heading other than the running head, `headings` is `[]`. That is the common case; do not invent one.
- `first_entry` / `last_entry` refer to ballet-list entries only (ignore foreign matter).
- If the page has no ballet-list entries at all, say so in `note`.

## Output

Write a JSON list of these objects, in page order, to `out/batch_<N>.json` in this folder. Write the file progressively (after every ~10 pages) so partial work is not lost. Your final message: one short paragraph saying how many pages you read, which pages had headings other than the running head, and anything odd. No transcription in the final message.
