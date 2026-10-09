# Task: read the printed date headers of two-page spreads (blind read)

You are given header-band images of scanned pages from a pre-1918 Russian theatre yearbook (the repertoire tables, old orthography with ъ, ѣ, і). Each spread is a rotated two-page opening: the LEFT printed page and the RIGHT printed page each have their own date header line printed above the table, in the form `<day> <month>. <year> г. <day> <month>.` (e.g. `16 августа. 1892 г. 26 августа.`), and the table's top row lists one column per day (`16 Воскр.`, `17 Понед.` ...).

For every spread listed in your bundle file there are two images, `<id>_L.png` (the left part of the band) and `<id>_R.png` (the right part); they overlap in the middle around the seam between the two printed pages. Read BOTH images. The seam is where the first page's header/table ends and the second page's header begins. You are blind: you are not told what the dates should be.

For each spread report, for the LEFT printed page and the RIGHT printed page separately:
- the header as printed: start day+month, end day+month (months in Russian as printed);
- the first and the last day-column labels of that page's table, as printed (e.g. `16 Воскр.` ... `26 Среда`). A column cut off by the image edge may be partial; write what you can read and mark `(partial)`.
Do NOT infer, correct or fill in anything. If a day, month or label is not legible, write `?` for it. If a page's header is missing or the spread looks different (a single page, a rotated/odd layout) say so in NOTE. Zoom in (read the image carefully) before you write a digit; 1/4/7 and 3/8/9 are easily confused in this type.

Output: write ONE line per spread to the report file given in your task, exactly in this format, nothing else (no commentary lines, no blank lines):

`SPREAD <id> | L header: <d m> - <d m> | L cols: <first label> ... <last label> | R header: <d m> - <d m> | R cols: <first label> ... <last label> | NOTE: <anything unusual, or ->`

Example: `SPREAD repertoire_1892-93_pair002 | L header: 16 августа - 26 августа | L cols: 16 Воскр. ... 26 Среда (partial) | R header: 27 августа - 9 сентября | R cols: 27 Четвергъ (partial) ... 9 Среда | NOTE: -`
