"""BalletArtists: the performance tally stored twice (RG, 2026-10-19: "address this").
On 913 rows the extraction put the credit line («Въ 11 балетахъ—44; въ 14 операхъ—74. Всего—118 разъ. ...») in
credit_summary_text AND again inside tenure_note_text. The print has it once (scan-checked: Свѣтинская 1898-99 p.117,
Гулинъ 1-й 1897-98 p.97, Ширяевъ 1903-04 p.112, and the bare-surname rows of 1901-02 MSK p.114). schema.md defines
tenure_note_text as the tenure note and credit_summary_text as the tally, so the copy inside tenure_note_text is removed;
credit_summary_text and the parsed credits are untouched. A leaving or other note that follows the tally is kept
(«(съ 10 іюня 1878 г.). Оставилъ службу 10 іюля 1901 г.»). Five 1901-02 Moscow rows printed as a bare surname plus a tally
(Ленская, Николаева 3-я, Павлова, Рѣпина, Соколова) are left with no tenure note (null), as printed.
Field edit only: no entries added, removed or reordered (person_link unaffected).
usage: uv run python docs/eval/raw_fix_duplicated_credit_in_tenure_2026-10-19.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import collections, json, re, sys
from pathlib import Path
import duckdb

RAW = Path('outputs/full_run/raw')
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
rows = con.execute("""
    SELECT entry_id, page_id, tenure_note_text, credit_summary_text FROM raw.person_entry
    WHERE credit_summary_text IS NOT NULL AND length(credit_summary_text) > 10
      AND position(credit_summary_text IN tenure_note_text) > 0
    ORDER BY page_id, entry_id""").fetchall()
con.close()
assert len(rows) == 913, len(rows)

by_page = collections.defaultdict(list)
for eid, page, t, cr in rows:
    by_page[page].append((int(eid.rsplit('__e', 1)[1]), eid, t, cr))

n = emptied = with_tail = 0
for page, items in by_page.items():
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    for idx, eid, t, cr in items:
        e = d['entries'][idx - 1]                      # entry_id numbers are 1-based
        assert e.get('tenure_note_text') == t and e.get('credit_summary_text') == cr, eid
        i = t.index(cr)
        rest = re.sub(r'\s+', ' ', (t[:i].rstrip() + ' ' + t[i + len(cr):].lstrip())).strip()
        if t[i + len(cr):].strip():
            with_tail += 1
        if not rest:
            rest = None; emptied += 1
        e['tenure_note_text'] = rest
        n += 1
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{n} rows on {len(by_page)} pages; {with_tail} keep a note after the tally; {emptied} left with no tenure note',
      '| WRITTEN' if '--write' in sys.argv else '| dry run')
