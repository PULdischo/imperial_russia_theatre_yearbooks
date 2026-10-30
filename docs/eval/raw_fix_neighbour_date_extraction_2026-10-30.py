"""Start dates the extraction copied from the neighbouring entry (RG, 2026-10-30: "Fix the three clear").
Found by the neighbour-date check (docs/eval/person_audit_2026-10-19/neighbour_date_scan_results.csv); each read on the
full-resolution scan by a read-only agent and re-checked by Claude on the zoom:
  balletartists_1898-99_MSK_p007 no. 42 Лукьяновъ, Николай Ефимовичъ: print «(съ 1 сентября 1898 г.)», stored 1892 (Лѣсновскій's, below).
  balletartists_1909-10_SP_p005 no. 2 Алексѣевъ 2-й, Александръ Алексѣевичъ: print «(съ 1 іюня 1905 г.)», stored 1894 (Алексѣевъ 1-й's, above).
  balletartists_1907-08_SP_p004 no. 79 Пороховникова, Марія Викторовна: print «(съ 1 іюня 1898 г.)», stored 1890 (Постоленко's, below).
NOT changed: Орловъ 1902-03 (print «190:», last digit damaged; stored 1900, probably 1901) -- left as an open reading.
Field edits only (entry positions unchanged, person_link unaffected).
usage: uv run python docs/eval/raw_fix_neighbour_date_extraction_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
WRITE = '--write' in sys.argv
FIXES = [  # page, 1-based entry position, family name, wrong year, printed year
    ('balletartists_1898-99_MSK_p007', 8, 'Лукьяновъ', '1892', '1898'),
    ('balletartists_1909-10_SP_p005', 20, 'Алексѣевъ 2-й', '1894', '1905'),
    ('balletartists_1907-08_SP_p004', 1, 'Пороховникова', '1890', '1898'),
]
for page, n, fam, old, new in FIXES:
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    e = d['entries'][n - 1]                          # entry_id numbers are 1-based
    assert e.get('family_name') == fam, (page, n, e.get('family_name'))
    t = e['tenure_note_text']; sp = e['service_periods']
    assert t.count(old + ' г.') == 1 and len(sp) == 1 and sp[0]['start_date_text'].count(old) == 1, (t, sp)
    e['tenure_note_text'] = t.replace(old + ' г.', new + ' г.')
    sp[0]['start_date_text'] = sp[0]['start_date_text'].replace(old, new)
    print(f'{page} no.{n} {fam}: «{t}» -> «{e["tenure_note_text"]}»; start «{sp[0]["start_date_text"]}»')
    if WRITE:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('| WRITTEN' if WRITE else '| dry run')
