# Jubilee / obituary catalogue — reader brief

You are cataloguing jubilee notices (юбилеи) and obituaries (некрологи, "памяти ...")
in scanned pages of the *Ежегодникъ Императорскихъ театровъ* (1890–1913).
Page images (PNG, 250 dpi) are in: /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/jo/  — your assigned files are listed in your task.

## What to do
1. Look at EVERY assigned page. Each page may hold several separate entries
   (in the 1890s obituary sections, one per deceased person, often a single paragraph;
   in later volumes, longer signed articles). Catalogue EVERY entry, ballet or not.
2. For each entry, decide its ballet relevance:
   - `core`     — the person's career was in ballet: dancer/mime/corps de ballet, ballet master /
                  choreographer, ballet régisseur, ballet teacher (theatre school dance classes),
                  ballet composer (e.g. Pugni, Minkus, Drigo), conductor/accompanist/répétiteur or
                  orchestra player identified with the ballet, ballet designer/machinist, ballet pupil.
   - `mentions` — not mainly a ballet person, but the text says something about ballet
                  (wrote a ballet score, danced as a child, ballet décor, staged dances in an opera/drama,
                  taught dancing, married to a dancer, etc.). Say exactly what.
   - `none`     — no ballet content at all.
   Read the text — don't decide from the name alone. A drama actor whose obituary says he
   began in the ballet troupe or theatre-school dance class is `mentions` (or `core` if the
   ballet career was substantial).
3. Reading rules (strict): preserve pre-1918 orthography verbatim (ъ ѣ і ѳ ѵ) — never modernize.
   Names in this corpus are spelled inconsistently; read each one letter by letter. ZOOM: crop
   the region with Python (PIL is available via `uv run python` from the repo root
   /Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main)
   and Read the crop, for every name, date, and evidence snippet. If a letter is uncertain,
   write [?] after the word and say so in notes. Never guess silently. The PDF text layer is
   garbage — don't use it.
4. Find the printed page number (folio, e.g. "— 397 —") on each page.

## Output
Write a UTF-8 CSV to /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/catalogue/<your_label>.csv with exactly these columns:

season,source_file,pdf_page,printed_page,kind,name_verbatim,name_latin,role,troupe_city,dates,length,relevance,evidence_verbatim,evidence_english,author,portrait,notes

- kind: obituary | jubilee | memorial_feature | section_heading_only | other
- name_verbatim: as printed (surname, given names), pre-reform orthography
- name_latin: simple transliteration (e.g. Andreev, Konstantin Aleksandrovich)
- role: e.g. "ballet artist (corps)", "violinist, ballet orchestra", "drama actress"
- troupe_city: SP / Moscow / other, and troupe (ballet/opera/drama/orchestra/administration/...)
- dates: death date, or jubilee date + years of service, as printed
- length: "N lines" for short notices, "N pp" for longer ones; continuing entries across pages = one row, pdf_page like "3-4"
- evidence_verbatim: for core/mentions only — the shortest verbatim phrase showing the ballet connection
- evidence_english: one-line English gloss of the evidence
- author: signature/initials if printed
- portrait: yes/no
- notes: uncertainties, cross-references, anything odd (e.g. entry cut off at the file's start or end —
  say so, since the scan may not include the whole section)

Also note if a page begins mid-entry (the entry started on an unscanned page) or ends mid-entry.
Finally, reply with: number of entries, a list of the core + mentions ones (name, role, one line why),
and any readings you're not sure of. Don't edit anything outside /private/tmp/claude-502/-Users-rachelglodo-Documents-Princeton-2022-present-Dissertation-imperial-russia-theatre-yearbooks-main/83314e80-ecec-4197-9700-933427e98fad/scratchpad/catalogue/.
