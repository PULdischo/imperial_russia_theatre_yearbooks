# Editorial timeline of the Ежегодник: design

Agreed with RG 2026-10-21. Goal: every дело added to the RGIA Reading Room adds
dated evidence of who was doing what in the Yearbook's редакція, and when, building
toward an editorial timeline. Current evidence: `docs/rgia/editor_tenure_evidence.md`.

## Ground rule
RG is the scholar; Claude is a Russian-reading research assistant who points her
to what is worth her time. Claude's scan checks are finding aids ("worth your time
to look here, and here is my reading"), never verification. Nothing is a finding
until RG has read the source herself.

## 1. Scope
The редакція: editors, assistant editors, anyone signing «за редактора», and paid
editorial staff (e.g. Шенкъ, Гельмерсенъ, secretaries). Officials the редакція
answered to (Directors, Контора managers, the Central Library head where it handled
the Yearbook) can be added later as needed. Contributors and artists are out.

## 2. Two tables: acts and spans
- **Acts**: one row per dated act on one page. Person (verbatim spelling), role as
  written, date (verbatim plus normalised), д., л., PDF page, what was done, and
  the certainty fields below. Acts are only ever added or corrected, never
  replaced by summaries.
- **Spans**: per person and role, earliest and latest act, optional "not before" /
  "not after" brackets, a sentence of reasoning, and the act ids each span rests
  on. "Last documented act" is never written as an end date.

## 3. Certainty, three separate fields per act
- **Source**: autograph / office copy / typed copy / another hand's note.
- **Claude's reading**: checked by Claude / summary only / uncertain, plus a note
  on what is uncertain (name, date, role).
- **RG-read**: empty until RG reads it; then her date and note. Only this counts
  as confirmation.
Inferences (from absences, from «за редактора», etc.) never go in acts; they live
in spans, with RG's rulings recorded there (e.g. 1904 signature = Гельмерсенъ,
unconfirmed). A span is established only when all its acts are RG-read and RG has
accepted the inference.

## 4. Where it lives
- Tracked files in the repo (acts and spans CSVs under `docs/rgia/`) are the record
  Claude maintains.
- The Reading Room shows them as a Timeline view, each act linked to its дело page
  and thumbnail. RG records RG-read status and notes there, in her own collection;
  Claude reads it and copies it into the repo, but never writes to it.

## 5. Growth with each new дело
A step added to the intake routine (`docs/rgia/README.md`) after the page summaries:
1. Search the new дело's summaries for editorial people and roles.
2. Read each candidate on the scan; add acts as "checked by Claude", RG-read empty.
3. Spans: earliest/latest dates update automatically (arithmetic on acts).
   Anything involving judgment, such as a new role reading, a bracket, a
   contradiction, or anything touching an RG ruling, is proposed to RG one question
   at a time, with evidence, and changes only on her yes.
4. End the intake with a short list for RG: new acts to read, with page links.

## Parked questions for RG
RG, 2026-10-21: hold these until more дела arrive, since new дела may bring
corroborating evidence and further questions. At each intake, check whether new
acts bear on any of them, add new questions here, and bring them to RG one at a
time, with evidence, only when she asks.

1. **Dating undated issue lists** (A001, A002, A004 Молчановъ; A010 Петровъ).
   Options: leave undated; date by the season in the heading; or date "about" the
   issue's distribution, from dated registers (2nd issue first sent to Moscow
   12 Mar 1893, д. 162 л. 4 об.; 4th issue handed out from Dec 1894, д. 159;
   5th issue acknowledged by Moscow 10 May 1896, д. 159 л. 17; all summary only).
   Claude's suggestion: distribution dates, each scan-checked first.
2. **Dating undated 1904 orders** (A037 editor; A034, A035 «П. Барт[…]»), filed
   among dated May-Oct 1904 orders in д. 163 лл. 29-37.
3. **Acts in no span**: the editor's endorsements of Oct-Dec 1900 (A022-A024,
   д. 165 лл. 36, 38, 41; summaries say Дягилевъ, not scan-checked), and П. Шенкъ
   as Завѣдывающій Центральною Библіотекою, 3 Oct 1901 (A026).
