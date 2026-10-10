# Consistency pass over a дело's page triage (text only, no images)

Different reading agents applied the tags and ratings unevenly. This pass reads the
finished rows in docs/rgia/dela/<DELO>.jsonl (do NOT edit that file) and proposes
field changes so every дело follows the same rules. Judge from the row's own text
(gist, doc_type, from_to, key_names, why) and its neighbours. Change nothing you are
not confident about; never alter gist, names, dates or any reading.

## Tag rules
- ballet: true only if the page concerns ballet in substance: a ballet work, ballet
  music, a ballet composer, dancer(s), the ballet troupe or its members (including
  troupe subscription tallies and lists naming ballet artists), an article about
  ballet. False for a mere figure of speech.
- ed_contributors: authors/contributors of the Yearbook: named authors, articles
  commissioned, offered, accepted or rejected, fees and offprints for authors.
- ed_illustrations: the Yearbook's pictures: photographs and photo sessions,
  photographers, artists and their drawings, clichés/plates, reproduction rights.
- ed_print_finance: print runs, printing/paper/binding costs and contracts, budgets,
  estimates, overspend, revenue totals, sale prices and price policy, stock of unsold
  copies. NOT a routine individual subscription payment or shipment with no such figures.
- ed_editors: the editorial office itself as the SUBJECT: who the editor is (named or
  signing as Редакторъ with a legible name), appointment, staff, salaries and premises
  of the редакція, its programme/policy, decisions about what the Yearbook contains,
  relations between editor and Directorate about how it is run. NOT set merely
  because the editor or the редакція wrote, signed or received the page, and NOT for
  К. А. Петровъ / Шенкъ of the Central Library handling routine sales and shipments.
  In a letter-book of the editor's own outgoing drafts, most pages should be false.

## Relevance rule (replaces "editorial means high")
- high: substantive ballet content (a work, ballet music, a composer, named dancers,
  an article or survey about ballet), OR substantive evidence for the Yearbook's
  editorial history (any ed_* tag where the page carries the real content: names,
  decisions, figures).
- medium: routine sales/subscription/shipment business, INCLUDING pages where the
  ballet troupe appears only as subscribers (troupe tallies, subscription circulars)
  with no work, composer or dancer named: keep ballet=true, rate medium unless the
  page is high on editorial grounds (RG, 2026-10-09); or a second/overlapping
  photo of a page whose content is already on its neighbour (unless this view is
  the more complete or legible one, in which case rate it like the content).
- low: covers, blanks, address slips, unreadable fragments.

## Output
Write outputs/rgia_dela/<DELO>/consistency_patch.jsonl, one line per page that needs
a change: {"page": N, "set": {"<field>": <value>, ...}, "reason": "<short>"}.
Allowed fields: ballet, ed_contributors, ed_illustrations, ed_print_finance,
ed_editors, relevance. Pages needing no change get no line. Then reply with, per
дело: number of pages changed, and before -> after counts for each tag and for
high/medium/low.
