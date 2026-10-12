"""Two Moscow 1906-07 Repertoire pages: free-matinee banner restored, one benefit heading moved to the cell it is printed in
(each cell viewed 2026-10-12 on a 200-dpi render of the PDF page). Annotation field only; safe to re-run. Then rebuild.
usage: uv run python docs/eval/raw_fix_matinee_banners_2026-10-12.py [--write]"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
BANNER = 'Безплатные спектакли для воспитанниковъ и воспитанницъ столичныхъ учебныхъ заведеній.'
BENEFIT = 'Прощальный бенефисъ г. Власова.'
NOTE = 'scan-checked 2026-10-12: free-matinee banner restored / benefit heading moved to the evening cell it is printed in'
# page, date_text, session, theater starts with (None = all three theaters), annotation the print has
ROWS = [('repertoire_1906-07_p019', '6 Среда.', 'morning', None, BANNER),      # 6 Dec 1906, printed p. 103
        ('repertoire_1906-07_p035', '28 Среда', 'morning', None, BANNER),      # 28 Feb 1907, printed p. 119
        ('repertoire_1906-07_p035', '28 Среда', 'evening', 'Большой', BENEFIT)]
for page, date_text, session, theater, annotation in ROWS:
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    hits = [s for s in d['sessions'] if s['date_text'] == date_text and s['session'] == session
            and (theater is None or (s.get('theater') or '').startswith(theater))]
    assert len(hits) == (3 if theater is None else 1), (page, len(hits))
    for s in hits:
        print(page, date_text, session, s['theater'], ':', s.get('annotation'), '->', annotation)
        s['annotation'] = annotation
        s['_fix_note'] = NOTE
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
