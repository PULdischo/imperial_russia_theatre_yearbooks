# How AI was used in this project — a plain-language description

Drafted 2026-11-02/06 for lay readers. Edit freely; the "research
assistant" framing is RG's own wording from an earlier session.

## Short version

> This database was built from scans of the *Yearbook of the Imperial
> Theatres* (1890–1911). I used AI at two stages, and at both it served
> as an assistant, never as the authority. First, an AI program that can
> read images made a first-pass transcription of each scanned page into
> tables: names, dates, titles and box-office figures, all in the
> original pre-1918 spelling. Second, I worked with an AI research
> assistant (Claude) to write the software that organizes the data, to
> check the transcription for errors, and to point me to places in the
> scans that needed a closer look. Every correction and every scholarly
> judgment in the database is mine, and I read the original sources
> myself before making any claim.

## Longer version

**What the source is.** The Imperial Theatres printed a yearbook every
season. It lists who worked in the theatres and what was performed each
day, where, and how much money it brought in. I have about 1,300 scanned
pages of these tables, printed in pre-revolutionary Russian spelling.

**Step 1: A machine makes a first draft.** Typing 1,300 dense tables by
hand would take years. Instead, each page image went to an AI model that
can read images (Qwen, from Alibaba). It filled in a fixed form for every
row: name, rank, date, theatre, title, receipts. I treat this output the
way I'd treat a fast but sometimes careless typist. It is a useful first
draft that I don't trust on its own. The old spelling (ъ, ѣ, і, ѳ) is
kept exactly as printed and never modernized.

**Step 2: Checking the draft.**

- **Against an answer key.** I typed a set of the hardest pages myself
  and measured how closely the machine's version matched mine.
- **Against the source's own logic.** The software flags anything that
  doesn't add up: a list whose numbers don't total correctly, a date that
  falls on the wrong day of the week, a page where the theatre never
  seems to close.
- **Against the yearbook itself.** The yearbook prints its own season
  totals and lists of productions. Where these disagree with the
  day-by-day tables, I go back to the scan to find out why.
- **By reading the page again in different ways.** For the performance
  calendars, the hardest tables, each page was read three separate ways
  and the readings were compared. Where they disagreed, that cell got a
  human look.

Every problem found is written down in a running log, along with its
cause and how it was fixed.

**Step 3: An AI research assistant.** I worked with Claude, an AI
assistant, to write the code that turns the transcriptions into a
database, to run the checks above, and to search through hundreds of
scans for the places that most needed my attention. I think of it as a
Russian-reading research assistant that helps me decide where to spend
my time. Its readings of the scans are labelled as its readings. They
are leads, not confirmations.

**Step 4: Connecting the records.** The yearbook prints the same dancer
or ballet many times across many years, often with different spellings.
The software matches only exact cases on its own, after allowing for
the old spelling. Uncertain matches come to me, and nothing is merged
without my decision. Where the evidence is truly mixed, I record the
uncertainty and leave the records separate.

**What the AI did not do.** It did not decide who someone was, settle
any doubtful reading, or make any historical argument. Every change to
the data can be traced to a specific scanned page, and I read the
sources myself before making any claim.

## How Qwen "read" the pages

Not optical character recognition (OCR) in the traditional sense. Qwen
is a **vision-language model**: one AI system that takes in an image and
writes text about it.

- **Traditional OCR** finds letter shapes and matches each one to a
  character, producing plain text. Working out the table structure is a
  separate step.
- **Qwen** received each page image (rendered at 300 dpi) with written
  instructions, e.g. "This is a staff list. For every person, give me
  the surname, initials, rank and dates of service, in this exact
  format." It breaks the image into small tiles, converts them into
  numbers, and then *writes* its answer one piece at a time, guided by
  the image, the instructions and what it has already written. Reading
  the letters and understanding the table happen in one step.

**The catch.** Because the model writes rather than matches shapes, it
draws on what it learned in training about what text usually looks like.
When the print is unclear it can produce something plausible that isn't
on the page. This project caught genre labels invented for the 1909–10
calendar, entries from one date leaking into another date's row, and a
free-text field where one entry was made up entirely. OCR errors look
like garbled characters; these errors look like correct text, which is
why the checking stage mattered so much.

Suggested sentence:

> "The scans were read by a type of AI that looks at a picture of a page
> and writes out what it sees in a form I designed. Unlike older
> text-recognition software, it reads the layout of the table and the
> words together, which makes it good at complicated pages. But when the
> print is unclear it can fill in something that looks right but isn't,
> so every page's output was checked rather than trusted."

## What Qwen sent back

One **JSON** file per scanned page: plain, structured text in which each
person (or each date-theatre-session on the calendar pages) is a block
of labelled fields, with the text as printed and `null` where nothing
was printed. Example, Moscow ballet roster 1890–91, first page:

```json
{
  "entries": [
    {
      "institution": "Балетная труппа.",
      "heading_path": "Балетмейстеръ.",
      "family_name": "Мендесъ",
      "first_name": "Іосифъ",
      "tenure_note_text": "съ 10 ноября 1889 г.",
      "service_periods": [
        { "start_date_text": "съ 10 ноября 1889 г.",
          "end_date_text": null, "end_type": null }
      ]
    }
  ]
}
```

- The files have since been **corrected**: confirmed fixes were made
  directly in them, and some calendar pages merge several readings. They
  are Qwen's output plus RG's corrections, with the history in git and
  `docs/eval/known_issues.md`.
- Everything else (tables, database, spreadsheet, Obsidian notes) is
  built from these files.
- Some field names are older than the database's (e.g. `is_dark` becomes
  "no performance"), so columns can be renamed without paying for the
  pages to be read again.

Suggested sentence:

> "For each page, the AI returned a structured text file listing every
> entry and its details (name, rank, dates, title, receipts) in the
> original spelling. Those files, corrected by hand wherever checking
> found an error, are the foundation the database is built from."

## Before publishing this

- The public site has an AI chat helper (`qwen-plus`) for asking
  questions about the data. If lay readers will meet it, add a sentence
  that it can make mistakes and the tables are the record.
- No accuracy figure is given on purpose: the README's 86.7% is from an
  early run. Measure a current one before citing a number.
