"""Genre «др.» removed from 7 divertissement rows: the scan prints «Дивертиссементъ.» / «Большой дивертиссементъ.» with NO genre
in every one (each cell viewed 2026-10-12 on a 300-dpi render of the PDF page). Same class as issue #113 (a genre the print
does not have). Field edit only. Then rebuild.
usage: uv run python docs/eval/raw_fix_divertissement_genre_2026-10-12.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
# page, date_text, theater starts with, title
ROWS = [('repertoire_1900-01_p026', '4 Воскре с.', 'Маріин', 'Дивертиссементъ'),
        ('repertoire_1901-02_p009', '24 Среда.', 'Новый', 'Дивертиссементъ'),
        ('repertoire_1902-03_p009', '23 Среда.', 'Новый', 'Дивертиссементъ'),
        ('repertoire_1905-06_p020', '22 Четвергъ.', 'Александрин', 'Большой дивертиссементъ'),
        ('repertoire_1905-06_p031', '10 Пятница.', 'Большой', 'Дивертиссементъ'),
        ('repertoire_1905-06_p042', '8 Суббота.', 'Маріин', 'Дивертиссементъ'),
        ('repertoire_1907-08_p010', '29 Понед.', 'Михайлов', 'Дивертиссементъ.')]
for page, date_text, theater, title in ROWS:
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    hits = [w for s in d['sessions'] if s['date_text'] == date_text and (s.get('theater') or '').startswith(theater)
            for w in s.get('works') or [] if w.get('work_title') == title and w.get('genre') == 'др.']
    assert len(hits) == 1, (page, len(hits))
    hits[0]['genre'] = None
    print(page, date_text, title, ': genre «др.» -> none')
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
