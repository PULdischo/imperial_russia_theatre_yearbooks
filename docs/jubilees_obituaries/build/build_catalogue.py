"""Build catalogue.csv (every jubilee/obituary entry) and ballet_entries.csv (core + mentions)
from first_read/A–H, applying the blind-second-read corrections and RG's tier rulings.

Run:  uv run python docs/jubilees_obituaries/build/build_catalogue.py
"""
import csv, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
COLS = ['season','source_file','pdf_page','printed_page','kind','name_verbatim','name_latin','role','troupe_city',
        'dates','length','relevance','evidence_verbatim','evidence_english','author','portrait','notes']

# Names where the two readings disagreed; settled on the scan 2026-10-10 (second read right each time).
NAME_FIXES = {
    'Борнштейнъ, Адольфъ Константиновичъ': 'Борншейнъ, Адольфъ Константиновичъ',
    'Платонова, Юлія Ѳеодоровна': 'Платонова, Юлія Ѳедоровна',
    'Пфейферъ, Ѳеодоръ Осиповичъ': 'Пфейферъ, Ѳедоръ Осиповичъ',
}
LATIN_FIXES = {'Bornshtein': 'Bornshein', 'Feodorovna': 'Fedorovna', 'Feodor ': 'Fedor '}

# RG 2026-10-10: designers/machinists, administrators over the ballet, the ballet critic, players in the
# combined opera-and-ballet orchestras, and drama actors who began in ballet all count as core.
CORE_BY_RULING = {
    ('1894-95', 'Бочаровъ'): 'designer',
    ('1893-94', 'Курбатовъ'): 'drama actor who began in ballet',
    ('1893-94', 'Большаковъ'): 'combined opera-and-ballet orchestra',
    ('1893-94', 'Гофманъ'): 'combined opera-and-ballet orchestra',
    ('1894-95', 'Морозовъ'): 'combined opera-and-ballet orchestra',
    ('1894-95', 'Гельвигъ'): 'combined opera-and-ballet orchestra',
    ('1908-09', 'Всеволожскій'): 'administrator over the ballet (Director of the Imperial Theatres)',
}

rows = []
for f in sorted(glob.glob(ROOT + '/first_read/[A-HJ]*.csv')):
    for r in csv.reader(open(f, encoding='utf-8')):
        if r[0] == 'season': continue
        if len(r) == 18: r = r[:11] + r[12:]            # G: section-title row has one stray cell
        assert len(r) == 17, (f, r)
        d = dict(zip(COLS, r))
        for k in d: d[k] = d[k].replace('Θ', 'Ѳ')    # Greek theta typed for Cyrillic fita
        if d['name_verbatim'] in NAME_FIXES:
            d['name_verbatim'] = NAME_FIXES[d['name_verbatim']]
            for a, b in LATIN_FIXES.items(): d['name_latin'] = d['name_latin'].replace(a, b)
            d['notes'] = (d['notes'] + ' ' if d['notes'] else '') + '[Name corrected from the blind second read, confirmed on the scan.]'
        d['tier_basis'] = 'reader' if d['relevance'] in ('core', 'mentions') else ''
        if '_Feature_' in d['source_file'] and 'Memories' not in d['source_file'] and 'Miscellaneous' not in d['source_file'] and d['name_verbatim'] and 'plate' not in d['printed_page'][:16]:
            # Single-person articles the Yearbook does not label as jubilees or obituaries (RG 2026-10-10).
            occasion = {'jubilee': 'a jubilee', 'other': 'no jubilee or death'}.get(d['kind'], d['kind'])
            d['notes'] = f"[Printed as a stand-alone article, not under a Юбилеи/Некрологи heading; occasion: {occasion}.] " + d['notes']
            d['kind'] = 'biographical_feature'
        for (season, surname), why in CORE_BY_RULING.items():
            if d['season'] == season and surname in d['name_verbatim'] and d['relevance'] == 'mentions':
                d['relevance'] = 'core'; d['tier_basis'] = 'RG ruling 2026-10-10: ' + why
        d['source_file'] = re.sub(r'(_p\d+)?\.(png|pdf)( \.\. p\d+)?$', '', d['source_file']) + '.pdf'
        rows.append(d)

for d in rows: d['source_type'] = 'section'; d['see_also'] = ''

# --- notices embedded in the Season Reviews (first_read/R_reviews.csv) ---------------------------------
FOLIO = {r['page_id']: r['printed_folio'] for r in csv.DictReader(open(HERE + '/review_page_folios.csv', encoding='utf-8'))}
MATCHED = {(r['review_page_id'], r['name_in_review']): r for r in csv.DictReader(open(ROOT + '/review_deaths_matched.csv', encoding='utf-8'))} \
    if os.path.exists(ROOT + '/review_deaths_matched.csv') else {}
KIND = {'jubilee': 'jubilee', 'farewell': 'farewell', 'memorial': 'memorial_feature', 'obituary': 'death_notice'}
for r in csv.DictReader(open(ROOT + '/first_read/R_reviews.csv', encoding='utf-8')):
    notes, rel, basis = r['notes'], r['relevance'], 'reader'
    if r['kind'] == 'obituary':
        m = MATCHED.get((r['page_id'], r['name_verbatim']))
        if m and m['basis'] == 'obituary': continue          # already in the catalogue as a full obituary
        if m:
            rel = m['relevance']; basis = 'roster' if m['basis'] == 'roster' else 'reader'
            notes = (m['notes'] + ' ' + notes).strip()
    city = 'Moscow' if '_MSK_' in r['page_id'] else 'SP'
    rows.append({'season': r['season'], 'source_file': r['page_id'], 'pdf_page': 'block ' + r['block_index'],
                 'printed_page': FOLIO.get(r['page_id'], ''), 'kind': KIND[r['kind']], 'name_verbatim': r['name_verbatim'],
                 'name_latin': r['name_latin'], 'role': r['role'], 'troupe_city': city, 'dates': r['dates'], 'length': 'notice in season review',
                 'relevance': rel, 'tier_basis': basis if rel != 'none' else '', 'evidence_verbatim': r['evidence_verbatim'],
                 'evidence_english': r['evidence_english'], 'author': '', 'portrait': 'no', 'notes': notes,
                 'source_type': 'review', 'see_also': ''})

# --- see_also: other entries that look like the same person (surname + first initial where both print one) ---
def _sur(d):
    n = d['name_verbatim']
    m = re.search(r'normalised name: ([^;]+)', d['notes'])
    if m: n = m.group(1)
    n = re.sub(r'\([^)]*\)', ' ', n)
    if ',' in n: s, rest = n.split(',', 1)
    else:
        w = [x for x in re.findall(r'[А-Яа-яѣіѳѵІѲѢ-]+', re.sub(r'\b[А-ЯІѲ][а-яѣіѳ]{0,3}\.', ' ', n)) if len(x) > 3 and not re.match(r'\d', x)]
        full = [x for x in w if x.endswith(('ъ', 'ая', 'ва', 'на', 'іи', 'ій', 'ти', 'го', 'па'))]
        s = w[-1] if w else n; rest = n
    s = re.sub(r'\s*\d-[йя].*$', '', s.strip()).split()[0] if s.strip() else ''
    ini = ''.join(w[0] for w in re.findall(r'[А-ЯІѲ][а-яѣіѳ]*', (rest.replace(s, ' ', 1) if s else rest).replace('г-жа', ' ')))[:2]
    return re.sub(r'(ъ|а|ой|ій|аго|ымъ)$', '', s.lower()).replace('сс', 'с'), ini
# Same surname and initials, different people.
NOT_SAME = {frozenset(p) for p in (
    ('Сампелевъ, Александръ Николаевичъ', 'Сампелевъ, Алексѣй Николаевичъ (Николаевъ, по театру Сампелевъ)'),
    ('М. И. Петипа', 'Маріи Петипа'),
)}
people = [d for d in rows if d['kind'] in ('obituary', 'jubilee', 'farewell', 'memorial_feature', 'death_notice', 'biographical_feature') and d['name_verbatim']]
keys = [_sur(d) for d in people]
for i, d in enumerate(people):
    refs = []
    for j, e in enumerate(people):
        if i == j or not keys[i][0] or keys[i][0] != keys[j][0]: continue
        x, y = keys[i][1], keys[j][1]
        if x and y and (x[0] != y[0] or (len(x) == 2 and len(y) == 2 and x != y)): continue
        if frozenset((d['name_verbatim'], e['name_verbatim'])) in NOT_SAME: continue
        o1, o2 = (re.search(r'(\d)-[йя]', z['name_verbatim']) for z in (d, e))
        if o1 and o2 and o1.group(1) != o2.group(1): continue
        if (e['source_file'], e['pdf_page']) == (d['source_file'], d['pdf_page']): continue
        refs.append(f"{e['season']} {e['kind']} p. {e['printed_page']}" + (' (review)' if e['source_type'] == 'review' else ''))
    d['see_also'] = '; '.join(dict.fromkeys(refs))

def key(d):
    m = re.search(r'\d+', d['printed_page']); return (d['season'], d['source_file'], int(m.group()) if m else 0)
rows.sort(key=key)
out_cols = ['source_type'] + COLS[:12] + ['tier_basis'] + COLS[12:] + ['see_also']
for name, keep in (('catalogue.csv', lambda d: True), ('ballet_entries.csv', lambda d: d['relevance'] in ('core', 'mentions'))):
    with open(os.path.join(ROOT, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, out_cols); w.writeheader(); w.writerows(d for d in rows if keep(d))

# mixed-script guard: no word may mix Cyrillic with Latin or Greek letters
bad = set()
for d in rows:
    for v in d.values():
        for wd in re.findall(r'\w+', v):
            if re.search('[Ѐ-ӿ]', wd) and re.search('[A-Za-zͰ-Ͽ]', wd): bad.add(wd)
import collections
people = [d for d in rows if d['kind'] in ('obituary', 'jubilee', 'farewell', 'memorial_feature', 'death_notice', 'biographical_feature')]
print('rows', len(rows), '| person entries', len(people), collections.Counter(d['relevance'] for d in people))
print('by source:', collections.Counter((d['source_type'], d['relevance']) for d in people))
print('by kind (core+mentions):', collections.Counter((d['kind'], d['relevance']) for d in people if d['relevance'] != 'none'))
print('ruled core:', [(d['season'], d['name_verbatim']) for d in rows if d['tier_basis'].startswith('RG')])
print('mixed-script words:', bad or 'none')
