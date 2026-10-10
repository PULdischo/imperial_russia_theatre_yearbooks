"""Build jubilees_obituaries_all_entries.csv (every jubilee/obituary entry) and jubilees_obituaries_ballet_only.csv (core + mentions)
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
        d['source_file'] = re.sub(r'(_p\d+(-p\d+)?)?\.(png|pdf)( \.\. p\d+)?$', '', d['source_file']) + '.pdf'
        m = re.match(r'(\d{4})_Vol_([IVX-]+)__(.+)$', d['source_file'])     # render name -> real path under the season folder
        if m: d['source_file'] = f"{m.group(1)} Vol {m.group(2)}/{m.group(3)}"
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

# --- death marks printed in the rosters, for people with no obituary or review notice --------------------
# (roster_deaths_matched.csv, from build/match_roster_deaths.py). One row per person.
ORCH = {(x['season'], x['family_name']): x for x in csv.DictReader(open(HERE + '/roster_orchestra_lookup.csv', encoding='utf-8'))}
def roster_tier(r):
    o = ORCH.get((r['season'], r['family_name']))
    if o: return o['tier'], f"{o['orchestra']}: {o['basis']}" + (' (RG ruling 2026-10-10: opera-and-ballet orchestra)' if o['tier'] == 'core' else '')
    path = (r['heading_path'] or '').lower(); subj = (r['instrument_or_subject'] or '').lower(); ros = r['roster']
    if ros == 'BalletArtists': return 'core', 'roster: ballet troupe'
    if ros == 'Musicians':
        if 'балет' in path: return 'core', 'roster: ballet or opera-and-ballet orchestra (RG ruling 2026-10-10)'
        if 'александринск' in path or 'михайловск' in path or 'военной' in path: return 'none', ''
        return 'undecided', 'orchestra not stated in the roster data'
    if ros == 'TheaterSchoolStaff':
        if 'танц' in subj: return 'core', 'roster: dance teacher'
        if 'балетное' in path: return 'mentions', 'RG 2026-10-10: non-dance teacher in the ballet department'
        if 'классныя дамы' in path or 'почетные' in path: return 'mentions', 'RG 2026-10-10: theatre school staff'
        return 'none', ''
    if ros == 'ProductionTeam':
        if 'декоратор' in path or 'машинист' in path or 'художник' in path: return 'core', 'roster: designer or machinist (RG ruling 2026-10-10)'
        return 'mentions', 'RG 2026-10-10: wardrobe, lighting and other production staff'
    if 'художникъ' in path: return 'core', 'roster: artist of the production office (RG ruling 2026-10-10: designers)'
    return 'none', ''
ROSTER_NAME = {'BalletArtists': 'ballet troupe', 'Musicians': 'orchestras', 'TheaterSchoolStaff': 'theatre school staff',
               'ProductionTeam': 'production department', 'Administrators': 'administration'}
if os.path.exists(ROOT + '/roster_deaths_matched.csv'):
    seen = {}
    for r in csv.DictReader(open(ROOT + '/roster_deaths_matched.csv', encoding='utf-8')):
        if r['status'] != 'not in catalogue': continue
        k = (r['family_name'], r['first_name'], r['patronymic'])
        tier, basis = roster_tier(r)
        if k in seen:                                    # same person, another roster section or season
            d = seen[k]; d['notes'] += f" Also {r['season']} {ROSTER_NAME[r['roster']]} ({r['roster_page_id']}): {r['heading_path']}."
            if r['death_mark'] != d['dates']:
                if len(d['dates']) < 3: d['dates'] = r['death_mark']            # earlier row had a bare dagger
                elif len(r['death_mark']) >= 3:
                    d['notes'] += f" [SOURCE CONFLICT as stored: {r['roster_page_id']} has «{r['death_mark']}», {d['source_file']} has «{d['dates']}»." + (' Both read on the scans 2026-10-10 (pp. 15 and 29 of the 1906-07 lists): a print conflict within one volume.]' if r['family_name'] == 'Константиновъ' else ' Not checked on the scans.]')
            order = ['none', 'undecided', 'mentions', 'core']
            if order.index(tier) > order.index(d['relevance']): d['relevance'], d['tier_basis'] = tier, basis
            continue
        name = r['family_name'] + ', ' + ' '.join(x for x in (r['first_name'], r['patronymic']) if x)
        d = {'source_type': 'roster', 'season': r['season'], 'source_file': r['roster_page_id'], 'pdf_page': '', 'printed_page': '',
             'kind': 'death_mark', 'name_verbatim': name.strip(', '), 'name_latin': '', 'role': ' / '.join(x for x in (r['rank_or_title'], r['instrument_or_subject']) if x),
             'troupe_city': ROSTER_NAME[r['roster']], 'dates': r['death_mark'], 'length': 'death mark in roster', 'relevance': tier, 'tier_basis': basis,
             'evidence_verbatim': r['heading_path'], 'evidence_english': '', 'author': '', 'portrait': 'no',
             'notes': 'Name and date as stored in the database (raw.person_entry); not re-read for this catalogue.', 'see_also': ''}
        seen[k] = d; rows.append(d)

# Printed date conflicts between a roster death mark and the obituary; both sides zoomed on the scans 2026-10-10.
ROSTER_CONFLICT = {
    ('1890-91', 'Соловьевъ, Илья Епифановичъ'): 'Roster (musicians_1890-91_SP_p005, p. 80) prints «† 4 октября 1890 г.»; this obituary prints «9 октября 1890 г. скончался».',
    ('1892-93', 'Мейеръ, Іоганъ-Фридрихъ (Iohan Meyer)'): 'Roster (musicians_1892-93_SP_p002, p. 71) prints «† 28 марта 1893 г.»; this obituary prints 25-го марта 1893 twice (caption and text).',
    ('1908-09', 'Всеволожскій, Иванъ Александровичъ'): 'Roster (theaterschoolstaff_1909-10_p000, p. 145) prints «Всеволожской … † 28 октября 1909 г.»; this obituary prints «† 29 октября 1909 г.» in heading and text.',
}
for d in rows:
    c = ROSTER_CONFLICT.get((d['season'], d['name_verbatim']))
    if c and d['kind'] == 'obituary': d['notes'] = (d['notes'] + ' ' if d['notes'] else '') + '[SOURCE CONFLICT: ' + c + ']'

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
people = [d for d in rows if d['kind'] in ('obituary', 'jubilee', 'farewell', 'memorial_feature', 'death_notice', 'death_mark', 'biographical_feature') and d['name_verbatim']]
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
        DEATH = ('obituary', 'death_notice', 'death_mark')
        if d['kind'] in DEATH and e['kind'] in DEATH and abs(int(d['season'][:4]) - int(e['season'][:4])) > 1: continue   # two deaths years apart = two people
        if e['relevance'] == 'core' and e['source_type'] != 'roster': d['_core_link'] = True
        refs.append(f"{e['season']} {e['kind']} p. {e['printed_page']}" + (' (review)' if e['source_type'] == 'review' else ''))
    d['see_also'] = '; '.join(dict.fromkeys(refs))

for d in rows:                                           # a roster-only death of someone the catalogue already has as core
    linked = d.pop('_core_link', False)
    if d['source_type'] == 'roster' and d['relevance'] in ('undecided', 'mentions') and linked:
        d['relevance'], d['tier_basis'] = 'core', 'same person as a core entry (see_also)'

def key(d):
    m = re.search(r'\d+', d['printed_page']); return (d['season'], d['source_file'], int(m.group()) if m else 0)
rows.sort(key=key)
out_cols = ['source_type'] + COLS[:12] + ['tier_basis'] + COLS[12:] + ['see_also']
for name, keep in (('jubilees_obituaries_all_entries.csv', lambda d: True), ('jubilees_obituaries_ballet_only.csv', lambda d: d['relevance'] in ('core', 'mentions', 'undecided'))):
    with open(os.path.join(ROOT, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, out_cols, extrasaction='ignore'); w.writeheader(); w.writerows(d for d in rows if keep(d))

# mixed-script guard: no word may mix Cyrillic with Latin or Greek letters
bad = set()
for d in rows:
    for v in d.values():
        for wd in re.findall(r'\w+', v):
            if re.search('[Ѐ-ӿ]', wd) and re.search('[A-Za-zͰ-Ͽ]', wd): bad.add(wd)
import collections
people = [d for d in rows if d['kind'] in ('obituary', 'jubilee', 'farewell', 'memorial_feature', 'death_notice', 'death_mark', 'biographical_feature')]
print('rows', len(rows), '| person entries', len(people), collections.Counter(d['relevance'] for d in people))
print('by source:', collections.Counter((d['source_type'], d['relevance']) for d in people))
print('by kind (core+mentions):', collections.Counter((d['kind'], d['relevance']) for d in people if d['relevance'] != 'none'))
print('tier set by an RG ruling:', [(d['season'], d['name_verbatim']) for d in rows if d['tier_basis'].startswith('RG')])
print('mixed-script words:', bad or 'none')
