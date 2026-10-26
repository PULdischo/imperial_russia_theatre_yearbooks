# Itemising the Ежегодникъ in/out registers (Д. 189, Д. 190)

Д. 189 and Д. 190 are not correspondence: they are the editorial office's own
ruled registers of papers in and out, one numbered line per item.

  Д. 189  «Журналъ входящихъ бумагъ по журналу "Ежегодникъ императорскихъ
          театровъ" 1898 г.»   (incoming, 74 PDF pages)
  Д. 190  «Журналъ исходящихъ бумагъ…  1899 г.»  (outgoing, 30 PDF pages)

Columns are `№ входящій` (or `№ исходящій`) | `Чис.` (day of month) | `СОДЕРЖАНІЕ`.
Month and year appear as headings in the number column or across the page; carry
the current month/year forward until a new heading changes it.

Every line is a separate, citable fact: what reached (or left) the editorial
office, on what date, from whom. **Transcribe line by line — do not summarise a
page.** This is the dated spine of the Yearbook's editorial operation: who sent
manuscripts and photographs, which articles and pictures were offered, which
printers billed, what the office sent out.

## Images

`outputs/rgia_dela/<DELO>/pages/` — for PDF page N, the original photo is
`oNNN.<ext>` and an enhanced greyscale copy `eNNN.jpg`, NNN = N-1 zero-padded
to 3 digits. Read the enhanced copy first; go to the ORIGINAL (and zoom) for
names, numbers and faint or coloured ink. Crop/zoom with python + cv2 into your
scratchpad when a line is hard.

## Write TWO files

**1. Items — `outputs/rgia_dela/<DELO>/items/part<K>.jsonl`, one line per register entry:**

- `delo` ("189"/"190"), `page` (int, PDF page)
- `entry_no` (string, as written: "1", "10", "" if none/illegible)
- `day` (string, the Чис. column as written, "" if blank)
- `month_year` (the heading in force, e.g. "Январь 1898 г."; "" if never stated)
- `content_ru` — the СОДЕРЖАНІЕ cell **verbatim**, pre-reform orthography kept
  (ъ, ѣ, і, ѳ). Mark any doubtful word with a trailing "?" and use "[нрзб]" for
  what you cannot read. Never silently normalise or complete a word.
- `content_en` — one short English rendering of that entry
- `key_names` — people, institutions, firms, works, periodicals read with
  reasonable confidence; doubtful readings get "?"
- `ballet` (bool), `ed_contributors`, `ed_illustrations`, `ed_print_finance`,
  `ed_editors` (bools; same meanings as docs/rgia/triage_instructions.md)
- `legibility` ("good"/"partial"/"poor"), `notes` ("" or e.g. "continues on p.12")

**2. Page triage — `outputs/rgia_dela/<DELO>/triage/part<K>.jsonl`, one line per PDF page**,
exactly the shape in `docs/rgia/triage_instructions.md` (page, folio, doc_type,
script, date, from_to, gist, key_names, legibility, relevance, why, ballet,
ed_* ×4). You have just read the page closely, so this costs little: `gist`
should say what the page's range of entries covers (e.g. "Incoming NN 1-14,
Январь 1898: Moscow office reports, a Petipa manuscript, photographs, printers'
bills"). Set `editorial` true via the sub-tags as usual.

## Rules

- Cover every page in your range, including blanks (write a page-triage line for
  a blank page and no item lines).
- Do not invent an entry number or a date. A blank Чис. means blank.
- An entry running over two lines is ONE entry. An entry continuing onto the next
  page is one entry on its first page, with `notes` saying so.
- Flag anything about ballet, a ballet work, dancer or ballet composer — that is
  the historian's first priority, and these registers are where a submitted
  ballet article or photograph first appears.
- Final reply: pages covered, entries written, and the two or three most notable
  items you saw.
