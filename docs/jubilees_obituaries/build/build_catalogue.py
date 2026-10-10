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
}

rows = []
for f in sorted(glob.glob(ROOT + '/first_read/[A-H]*.csv')):
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
        for (season, surname), why in CORE_BY_RULING.items():
            if d['season'] == season and surname in d['name_verbatim'] and d['relevance'] == 'mentions':
                d['relevance'] = 'core'; d['tier_basis'] = 'RG ruling 2026-10-10: ' + why
        d['source_file'] = re.sub(r'(_p\d+)?\.(png|pdf)( \.\. p\d+)?$', '', d['source_file']) + '.pdf'
        rows.append(d)

def key(d):
    m = re.search(r'\d+', d['printed_page']); return (d['season'], d['source_file'], int(m.group()) if m else 0)
rows.sort(key=key)
out_cols = COLS[:12] + ['tier_basis'] + COLS[12:]
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
people = [d for d in rows if d['kind'] in ('obituary', 'jubilee', 'memorial_feature')]
print('rows', len(rows), '| person entries', len(people), collections.Counter(d['relevance'] for d in people))
print('by kind (core+mentions):', collections.Counter((d['kind'], d['relevance']) for d in people if d['relevance'] != 'none'))
print('ruled core:', [(d['season'], d['name_verbatim']) for d in rows if d['tier_basis'].startswith('RG')])
print('mixed-script words:', bad or 'none')
