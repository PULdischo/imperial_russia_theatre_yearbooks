"""Latin letters inside Cyrillic words in the Roster name/heading/note fields (known_issues.md #150 open item 5), plus two
misreads seen on the same scans, and the genre repeated at the end of 861 Repertoire titles on 74 pages (#112, widened).

Readings (2026-10-12):
- Read on the scan (outputs/roster_images_full, column crops): Тистрова, Гавликовскій, Спрышинская, Грекова 1-я / 2-я,
  Алексне, Никифо[ровна], Антиповна; «Ббліотеки» is the PRINT's own slip (musicians_1898-99_SP_p006), only the Latin i changes.
- Script-only (a Latin a / c / I standing for the identical Cyrillic letter, no reading changes; not viewed one by one):
  Милютина x5, Чернятина x7, Матятина x2, Кандина, Августина, Іосифъ.
- tenure_note_text: each word is taken from the same entry's credit_summary_text, which #150 read on the scan.
- Misreads seen on the same crops: Жуляевъ stored «Жуліевъ» (1897-98 MSK p005; «Жуляевъ» in his 7 other seasons);
  Гердтъ's start year stored 1866, printed 1860 (1903-04 SP p006; 1860 in every other season).
Field edits only, no entry added, removed or moved. Then run docs/eval/rebuild_after_raw_edit.sh and diff the persons.
usage: uv run python docs/eval/raw_fix_mixed_script_names_2026-10-12.py [--write]"""
import json, re, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
MIXED = re.compile('[А-Яа-яѣѢіІѳѲѵ][A-Za-z]|[A-Za-z][А-Яа-яѣѢіІѳѲѵ]')
WORD = re.compile(r'\S*(?:[А-Яа-яѣѢіІѳѲѵ][A-Za-z]|[A-Za-z][А-Яа-яѣѢіІѳѲѵ])\S*')

# (page, field, stored, corrected, expected number of entries)
NAMES = [
    ('balletartists_1893-94_SP_p005', 'family_name', 'Тиistroва', 'Тистрова', 1),
    ('balletartists_1894-95_MSK_p003', 'family_name', 'Милютинa', 'Милютина', 1),
    ('balletartists_1899-00_MSK_p003', 'family_name', 'Милютинa', 'Милютина', 1),
    ('balletartists_1901-02_MSK_p002', 'family_name', 'Милютинa', 'Милютина', 1),
    ('balletartists_1909-10_MSK_p003', 'family_name', 'Милютинa', 'Милютина', 1),
    ('balletartists_1899-00_SP_p003', 'family_name', 'Матятинa', 'Матятина', 1),
    ('balletartists_1903-04_SP_p002', 'family_name', 'Матятинa', 'Матятина', 1),
    ('balletartists_1902-03_SP_p005', 'family_name', 'Чернятинa', 'Чернятина', 1),
    ('balletartists_1903-04_SP_p005', 'family_name', 'Чернятинa', 'Чернятина', 1),
    ('balletartists_1905-06_SP_p004', 'family_name', 'Чернятинa', 'Чернятина', 1),
    ('balletartists_1906-07_SP_p005', 'family_name', 'Чернятинa', 'Чернятина', 1),
    ('balletartists_1907-08_SP_p005', 'family_name', 'Чернятинa', 'Чернятина', 1),
    ('balletartists_1909-10_SP_p005', 'family_name', 'Чернятинa', 'Чернятина', 1),
    ('balletartists_1903-04_SP_p006', 'family_name', 'Гавликowsкій', 'Гавликовскій', 1),
    ('balletartists_1904-05_SP_p004', 'family_name', 'Спрышиńskaя', 'Спрышинская', 1),
    ('balletartists_1905-06_MSK_p001', 'family_name', 'Гrekова', 'Грекова', 2),
    ('balletartists_1905-06_SP_p000', 'family_name', 'Алекcне', 'Алексне', 1),
    ('balletartists_1907-08_SP_p002', 'family_name', 'Кандинa', 'Кандина', 1),
    ('balletartists_1897-98_MSK_p005', 'family_name', 'Жуліевъ', 'Жуляевъ', 1),
    ('balletartists_1892-93_MSK_p000', 'first_name', 'Iосифъ', 'Іосифъ', 1),
    ('balletartists_1893-94_SP_p003', 'first_name', 'Августинa', 'Августина', 1),
    ('balletartists_1890-91_MSK_p005', 'patronymic', 'Никifoровна', 'Никифоровна', 1),
    ('balletartists_1892-93_MSK_p003', 'patronymic', 'Антипovна', 'Антиповна', 1),
]
NOTE_PAGES = ['balletartists_1890-91_MSK_p005', 'balletartists_1896-97_MSK_p003', 'balletartists_1897-98_MSK_p005',
              'balletartists_1900-01_MSK_p004', 'balletartists_1904-05_SP_p006', 'balletartists_1905-06_MSK_p005',
              'balletartists_1906-07_MSK_p005']
GENRE_TITLES, GENRE_PAGES = 861, 74

docs, n = {}, 0
def load(page):
    if page not in docs:
        docs[page] = json.loads((RAW / f'{page}.raw.json').read_text(encoding='utf-8'))
    return docs[page]

for page, field, old, new, expect in NAMES:
    hits = [e for e in load(page)['entries'] if old in (e.get(field) or '').split()]
    assert len(hits) == expect, (page, field, old, len(hits))
    for e in hits:
        e[field] = e[field].replace(old, new); n += 1
    print(page, field, old, '->', new, f'x{expect}')

# tenure_note_text: take each mixed-script word from the entry's own credit summary (matched on the 14 characters before it)
for page in NOTE_PAGES:
    for e in load(page)['entries']:
        t, c = e.get('tenure_note_text') or '', e.get('credit_summary_text') or ''
        if not MIXED.search(t):
            continue
        def repl(m):
            pre = t[max(0, m.start() - 14):m.start()]
            k = c.find(pre)
            assert pre and k >= 0, (page, m.group(0))
            ref = re.match(r'\S+', c[k + len(pre):]).group(0)
            assert not MIXED.search(ref) and len(ref) in (len(m.group(0)) - 1, len(m.group(0)), len(m.group(0)) + 1) \
                or m.group(0).startswith(('(nota', '(Кloyd')), (page, m.group(0), ref)
            print(page, 'tenure_note_text', m.group(0), '->', ref)
            return ref
        e['tenure_note_text'] = WORD.sub(repl, t); n += 1
        assert not MIXED.search(e['tenure_note_text']), (page, e['tenure_note_text'])

# heading: the print itself has «Ббліотеки» (no и); only the Latin i goes
hits = 0
for e in load('musicians_1898-99_SP_p006')['entries']:
    for f in ('heading_path', 'institution'):
        v = e.get(f)
        if isinstance(v, list) and any('Бблiотеки' in s for s in v):
            e[f] = [s.replace('Бблiотеки', 'Ббліотеки') for s in v]; hits += 1
        elif isinstance(v, str) and 'Бблiотеки' in v:
            e[f] = v.replace('Бблiотеки', 'Ббліотеки'); hits += 1
assert hits == 1, hits
print('musicians_1898-99_SP_p006 heading_path Бблiотеки -> Ббліотеки'); n += 1

# Гердтъ, 1903-04: printed «съ 22 ноября 1860 г.»
hits = [e for e in load('balletartists_1903-04_SP_p006')['entries'] if e.get('family_name') == 'Гердтъ']
assert len(hits) == 1 and '1866' in hits[0]['tenure_note_text'] and hits[0]['service_periods'][0]['start_date_text'] == '22 ноября 1866 г.'
hits[0]['tenure_note_text'] = hits[0]['tenure_note_text'].replace('1866', '1860')
hits[0]['service_periods'][0]['start_date_text'] = '22 ноября 1860 г.'
print('balletartists_1903-04_SP_p006 Гердтъ start 1866 -> 1860'); n += 1

# Repertoire, corpus-wide (RG, 2026-10-12: "let's do option 1"): the genre repeated at the end of work_title where the
# genre field already holds exactly that text. The print has it once; nothing printed is lost.
k, pages = 0, set()
for f in sorted(RAW.glob('repertoire_*.raw.json')):
    if ' 2.' in f.name:
        continue
    page = f.name[:-len('.raw.json')]
    d = json.loads(f.read_text(encoding='utf-8'))
    hit = False
    for s in d.get('sessions', []):
        for w in s.get('works') or []:
            t, g = w.get('work_title') or '', w.get('genre') or ''
            if len(g) > 1 and t.endswith(', ' + g) and t[:-len(', ' + g)].strip():
                w['work_title'] = t[:-len(', ' + g)]; k += 1; hit = True
    if hit:
        docs[page] = d; pages.add(page)
assert k == GENRE_TITLES and len(pages) == GENRE_PAGES, (k, len(pages))
print(f'genre suffix removed from {k} titles on {len(pages)} Repertoire pages')

print(f'\n{n} roster fields + {k} titles; {len(docs)} files', '(written)' if '--write' in sys.argv else '(dry run)')
if '--write' in sys.argv:
    for page, d in docs.items():
        (RAW / f'{page}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
