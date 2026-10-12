"""Eight Михайловскій Repertoire cells, each read on the scan 2026-10-12 (RG: "fix"):
- two benefit headings stored as a work WITH a genre the print does not have (the heading stands alone, in the heading typeface,
  over the bill): heading -> annotation, as printed with its period (1898-99 printed p. 20; 1901-02 printed p. 18);
- «Pepa, com.» (Latin letters, French comedy) stored in Cyrillic homoglyphs as «Репа»: 10, 11, 13, 15 April 1893 (1892-93 pp. 22-23);
- «Tête-à-tête, ком.» (Cyrillic genre in the print, a Russian-language piece) stored with the Latin «com.»: 28 and 30 Oct 1892 (p. 8).
Then rebuild (docs/eval/rebuild_after_raw_edit.sh) and diff.
usage: uv run python docs/eval/raw_fix_mikhailovsky_cells_2026-10-12.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
NOTE = 'scan-checked 2026-10-12 (raw_fix_mikhailovsky_cells_2026-10-12.py)'
def cells(d, dates):
    return [s for s in d['sessions'] if s['date_text'].split()[0] in dates and (s.get('theater') or '').startswith('Михайловск')]
def heading(s):
    w = s['works'][0]; assert w['work_title'].startswith('Bénéfice de '), w
    s['annotation'] = ((w['work_title'].rstrip('.') + '. ') + (s.get('annotation') or '')).strip(); s['works'] = s['works'][1:]
def pepa(s):
    w = s['works'][0]; assert w['work_title'] == 'Репа' and w['genre'] == 'com.', w
    w['work_title'] = 'Pepa'
def tete(s):
    w = [x for x in s['works'] if x['work_title'] == 'Tête-à-tête']; assert len(w) == 1 and w[0]['genre'] == 'com.', s['works']
    w[0]['genre'] = 'ком.'
JOBS = [('repertoire_1898-99_p018', {'19'}, 1, heading), ('repertoire_1901-02_p016', {'8'}, 1, heading),
        ('repertoire_1892-93_pair022', {'10', '11', '13', '15'}, 4, pepa), ('repertoire_1892-93_pair008', {'28', '30'}, 2, tete)]
for page, dates, n, fix in JOBS:
    f = RAW / f'{page}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
    hits = [s for s in cells(d, dates) if s.get('works')]
    if fix is tete:
        hits = [s for s in hits if any(w['work_title'] == 'Tête-à-tête' for w in s['works'])]
    assert len(hits) == n, (page, len(hits), [(s['date_text'], s['works']) for s in hits])
    for s in hits:
        before = json.dumps([s.get('annotation'), s['works']], ensure_ascii=False)
        fix(s); s['_fix_note'] = NOTE
        print(page, s['date_text'], '\n   ', before, '\n ->', json.dumps([s.get('annotation'), s['works']], ensure_ascii=False))
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('(written)' if '--write' in sys.argv else '(dry run)')
