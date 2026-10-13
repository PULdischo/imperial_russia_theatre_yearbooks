"""Free-matinee banner sweep (RG, 2026-10-13: "work on these"). The yearbook prints one banner across the whole row of a city on a
free-performance day; the transcription often attached it to some theaters' morning sessions and not to others, or to none.
Candidates: (A) a date and city where one session has the banner and another no-receipts session does not; (B) a date and city
where two or more theaters have a morning with no receipts and no annotation. Every row below was read on the scan (PDF pages;
1892-93 from the pair016 band). Each listed morning session gets the banner as printed on its row. One banner sat on the wrong
session: 14 Nov 1900, Михайловскій, on the paid evening (1214 р. 02½ к.) instead of the morning. Annotation field only.
Not banners, left alone: 26 Nov 1895 (Маріинскій, Михайловскій: receipts lost in the binding fold); the Moscow coronation
weeks of May 1896 (a note «Всѣ послѣдующіе спектакли до конца сезона—безплатные.» printed once per column: handled in the
research layer, free_period_notes.csv).
usage: uv run python docs/eval/raw_fix_free_matinee_banner_sweep_2026-10-13.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
NOTE = 'scan-checked 2026-10-13: free-performance banner printed across the row (banner sweep)'
B = 'Безплатные спектакли для воспитанниковъ столичныхъ учебныхъ заведеній.'
BW = 'Безплатные спектакли для воспитанниковъ и воспитанницъ столичныхъ учебныхъ заведеній.'
B93 = 'Безплатные утренніе спектакли для воспитанниковъ учебныхъ заведеній.'
A3 = ['Маріинск', 'Александринск', 'Михайловск']; M3 = ['Больш', 'Малый', 'Нов']
# page, day of month, theaters whose morning session gets the banner, banner text
JOBS = [('repertoire_1892-93_pair016', '4', A3 + ['Больш', 'Малый'], B93),
        ('repertoire_1898-99_p012', '14', A3, B),
        ('repertoire_1900-01_p012', '14', ['Михайловск'], B),
        ('repertoire_1900-01_p017', '6', M3, B),
        ('repertoire_1900-01_p026', '7', ['Михайловск'], B),
        ('repertoire_1902-03_p011', '14', ['Нов'], B),
        ('repertoire_1902-03_p014', '6', ['Михайловск'], B),
        ('repertoire_1902-03_p015', '6', ['Малый'], B),
        ('repertoire_1902-03_p027', '12', M3, B),
        ('repertoire_1903-04_p013', '14', ['Малый', 'Нов'], B),
        ('repertoire_1906-07_p018', '6', A3, BW),
        ('repertoire_1909-10_p015', '14', ['Маріинск', 'Михайловск'], BW),
        ('repertoire_1909-10_p016', '14', ['Больш', 'Малый'], BW),
        ('repertoire_1909-10_p021', '6', A3, BW),
        ('repertoire_1909-10_p022', '6', ['Больш', 'Малый'], BW)]
n = 0
for page, day, theaters, text in JOBS:
    f = RAW / f'{page}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
    for t in theaters:
        hits = [s for s in d['sessions'] if s['date_text'].split()[0] == day and s['session'] == 'morning'
                and (s.get('theater') or '').startswith(t) and s.get('works')]
        assert len(hits) == 1, (page, day, t, len(hits))
        s = hits[0]
        assert not s.get('annotation') and not s.get('receipts_text'), (page, day, t, s.get('annotation'), s.get('receipts_text'))
        s['annotation'], s['_fix_note'] = text, NOTE; n += 1
    if page == 'repertoire_1900-01_p012':  # the banner stored on the paid evening
        ev = [s for s in d['sessions'] if s['date_text'].split()[0] == '14' and s['session'] == 'evening'
              and s['theater'].startswith('Михайловск')]
        assert len(ev) == 1 and (ev[0].get('annotation') or '').startswith('Безплатны') and ev[0].get('receipts_text'), ev
        print('removed from', page, '14 evening Михайловскій:', ev[0]['annotation'])
        ev[0]['annotation'] = None; ev[0]['_fix_note'] = NOTE + '; banner belongs to the morning session, removed from the paid evening'
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(n, 'morning sessions get the banner on', len(JOBS), 'pages', '(written)' if '--write' in sys.argv else '(dry run)')
