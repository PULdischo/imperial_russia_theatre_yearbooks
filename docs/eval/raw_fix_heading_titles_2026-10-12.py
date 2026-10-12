"""Michel theatre (Михайловскій) Repertoire cells where a benefit or season heading («Bénéfice de M-r Guitry», «Clôture de la
saison.») is stored as the first work of the bill (RG, 2026-10-12: "fix this"). The heading moves from works[0].work_title to the
session's annotation, verbatim; the works that follow keep their order. Where the annotation already holds the same heading the
work is only removed; where it holds something else the heading is put in front of it. Field move only, no reading changed.
Removing works[0] renumbers the cell's later performance ids (w2 -> w1), so rebuild (docs/eval/rebuild_after_raw_edit.sh) and
diff the works afterwards.
usage: uv run python docs/eval/raw_fix_heading_titles_2026-10-12.py [--write] [-v]"""
import json, re, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
HEADING = re.compile(r'^(Bénéfice |Clôture de la saison|Réouverture)')
NOTE = 'heading moved from the first work title to the annotation (2026-10-12)'
norm = lambda t: re.sub(r'[\s.]+$', '', t or '').lower()
n, touched, kinds = 0, set(), {'set': 0, 'already there': 0, 'prefixed': 0}
for f in sorted(RAW.glob('repertoire_*.raw.json')):
    if ' 2.' in f.name:
        continue
    d = json.loads(f.read_text(encoding='utf-8'))
    for s in d.get('sessions', []):
        works = s.get('works') or []
        if not works or not HEADING.match(works[0].get('work_title') or ''):
            continue
        if (works[0].get('genre') or '').strip():   # a heading carrying a genre: a title is probably lost in it; needs the scan
            print('SKIPPED (has a genre):', f.name[:-9], s['date_text'], works)
            continue
        assert not any(HEADING.match(w.get('work_title') or '') for w in works[1:]), (f.name, works)
        head, old = works[0]['work_title'].strip(), (s.get('annotation') or '').strip()
        if not old:
            new, kind = head, 'set'
        elif norm(head) in norm(old) or norm(old) in norm(head):
            new, kind = (old if len(old) >= len(head) else head), 'already there'
        else:
            new, kind = head.rstrip('.') + '. ' + old, 'prefixed'
        if '-v' in sys.argv:
            print(f.name[:-9], s['date_text'], '|', head, '|', repr(old), '->', repr(new), '|', len(works) - 1, 'works left')
        s['works'], s['annotation'], s['_fix_note'] = works[1:], new, NOTE
        n += 1; kinds[kind] += 1; touched.add(f)
    if f in touched and '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{n} headings on {len(touched)} pages', kinds, '(written)' if '--write' in sys.argv else '(dry run)')
if '--pages' in sys.argv:
    print('\n'.join(sorted(f.name for f in touched)))
