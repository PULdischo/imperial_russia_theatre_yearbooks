"""Latin-script genre left at the end of work_title with the genre field EMPTY -> moved into the genre field (RG, 2026-10-12: "yes").
Follow-up to raw_fix_mixed_script_names_2026-10-12.py, which removed exact duplicates only and left these apart from their twins.
Rule: genre empty; the title ends ", <token>"; the token is all Latin script and is a genre the corpus prints in a genre field
elsewhere (compared without the final period, case-insensitive). The token goes into genre exactly as printed. Cyrillic endings
(«весенняя сказка», «возможный случай», «принцѣ Датскомъ») and titles whose genre field holds something else are not touched.
Field edits only. Then rebuild (docs/eval/rebuild_after_raw_edit.sh) and diff the works.
usage: uv run python docs/eval/raw_fix_genre_in_title_latin_2026-10-12.py [--write]"""
import json, re, sys, collections
from pathlib import Path
RAW = Path('outputs/full_run/raw')
files = [f for f in sorted(RAW.glob('repertoire_*.raw.json')) if ' 2.' not in f.name]
docs = {f: json.loads(f.read_text(encoding='utf-8')) for f in files}
works = lambda d: (w for s in d.get('sessions', []) for w in (s.get('works') or []))
latin = lambda t: bool(re.fullmatch(r"[A-Za-zÀ-ÿ.\- ]+", t)) and re.search('[A-Za-z]', t)
VOCAB = {(w.get('genre') or '').strip().rstrip('.').lower() for d in docs.values() for w in works(d)}
VOCAB = {g for g in VOCAB if g and latin(g)}
n, touched, toks = 0, set(), collections.Counter()
for f, d in docs.items():
    for w in works(d):
        t = w.get('work_title') or ''
        if (w.get('genre') or '').strip():
            continue
        m = re.search(r',\s*([^,]{1,22})$', t)
        if not m:
            continue
        tok = m.group(1).strip()
        if latin(tok) and tok.rstrip('.').lower() in VOCAB and t[:m.start()].strip():
            w['work_title'], w['genre'] = t[:m.start()].strip(), tok
            n += 1; touched.add(f); toks[tok] += 1
            if '-v' in sys.argv:
                print(f.name[:-9], '|', t, '->', w['work_title'], '|', tok)
print(dict(toks.most_common()))
print(f'{n} titles on {len(touched)} pages', '(written)' if '--write' in sys.argv else '(dry run)')
if '--write' in sys.argv:
    for f in touched:
        f.write_text(json.dumps(docs[f], ensure_ascii=False, indent=2), encoding='utf-8')
else:
    print('\n'.join(sorted(f.name[:-9] for f in touched)), file=open('/dev/stderr', 'w')) if '--pages' in sys.argv else None
