"""Repertoire cells read on the scan 2026-10-12 while checking the bills that mix Russian and French drama (RG: "address these"):
- «Tête-à-tête, ком.» (Cyrillic genre in the print) stored with the Latin «com.»: 10 Dec 1890 (1890-91 p. 13) and 28 Dec 1890
  evening (p. 15), Михайловскій. Same misreading as 28/30 Oct 1892 (raw_fix_mikhailovsky_cells_2026-10-12.py).
- 11 Dec 1900, Михайловскій (1900-01 printed p. 18): the cell prints only «Злоба дня, др.», 499 р. 75 к.; the stored bill began
  with «Madame Lili» and «Le verre d'eau», which belong to the cells of 10 and 12 Dec (both already stored there).
- Free-matinee banner printed across the row but stored on one theater or none: 6 Dec 1900 morning, Александринскій and
  Михайловскій (the Маріинскій morning already had it); 28 Feb 1907 morning, all three SP theaters (1906-07 printed p. 118).
Then rebuild (docs/eval/rebuild_after_raw_edit.sh) and diff.
usage: uv run python docs/eval/raw_fix_mixed_bill_cells_2026-10-12.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
NOTE = 'scan-checked 2026-10-12 (raw_fix_mixed_bill_cells_2026-10-12.py)'
B1900 = 'Безплатные спектакли для воспитанниковъ столичныхъ учебныхъ заведеній.'
B1907 = 'Безплатные спектакли для воспитанниковъ и воспитанницъ столичныхъ учебныхъ заведеній.'
def tete(s):
    w = [x for x in s['works'] if x['work_title'] == 'Tête-à-tête']; assert len(w) == 1 and w[0]['genre'] == 'com.', s['works']
    w[0]['genre'] = 'ком.'
def zloba(s):
    assert [w['work_title'] for w in s['works']] == ['Madame Lili', "Le verre d'eau", 'Злоба дня'], s['works']
    s['works'] = s['works'][2:]
def banner(text):
    def f(s):
        assert not s.get('annotation') and not s.get('receipts_text'), s
        s['annotation'] = text
    return f
# page, day, session (None = any), theaters (prefixes), expected cells, fix
JOBS = [('repertoire_1890-91_pair012', '10', None, ['Михайловск'], 1, tete),
        ('repertoire_1890-91_p015', '28', 'evening', ['Михайловск'], 1, tete),
        ('repertoire_1900-01_p016', '11', None, ['Михайловск'], 1, zloba),
        ('repertoire_1900-01_p016', '6', 'morning', ['Александринск', 'Михайловск'], 2, banner(B1900)),
        ('repertoire_1906-07_p034', '28', 'morning', ['Маріинск', 'Александринск', 'Михайловск'], 3, banner(B1907))]
docs = {}
for page, day, session, theaters, n, fix in JOBS:
    f = RAW / f'{page}.raw.json'
    d = docs.setdefault(f, json.loads(f.read_text(encoding='utf-8')))
    hits = [s for s in d['sessions'] if s['date_text'].split()[0] == day and (session is None or s['session'] == session)
            and any((s.get('theater') or '').startswith(t) for t in theaters) and s.get('works')]
    assert len(hits) == n, (page, day, len(hits))
    for s in hits:
        before = json.dumps([s.get('annotation'), s['works']], ensure_ascii=False)
        fix(s); s['_fix_note'] = NOTE
        print(page, s['date_text'], s['session'], s['theater'], '\n   ', before, '\n ->', json.dumps([s.get('annotation'), s['works']], ensure_ascii=False))
if '--write' in sys.argv:
    for f, d in docs.items():
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
