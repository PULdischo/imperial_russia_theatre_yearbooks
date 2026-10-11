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
for f in sorted(glob.glob(ROOT + '/first_read/[A-HJK]*.csv')):
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
KIND = {'jubilee': 'jubilee', 'farewell': 'farewell', 'memorial': 'memorial_feature', 'obituary': 'death_notice',
        'departure': 'departure', 'work_milestone': 'work_milestone'}
REVIEW_ROWS = [r for f in ('R_reviews.csv', 'R2_reviews_wider_search.csv') for r in csv.DictReader(open(ROOT + '/first_read/' + f, encoding='utf-8'))]
for r in REVIEW_ROWS:
    notes, rel, basis = r['notes'], r['relevance'], 'reader'
    if r['kind'] == 'obituary':
        m = MATCHED.get((r['page_id'], r['name_verbatim']))
        if m and m['basis'] == 'obituary': continue          # already in the catalogue as a full obituary
        if m:
            rel = m['relevance']; basis = 'roster' if m['basis'] == 'roster' else 'reader'
            notes = (m['notes'] + ' ' + notes).strip()
    city = 'Moscow' if '_MSK_' in r['page_id'] else 'SP'
    if r['page_id'] == 'review_1900-01_MSK_opera_p020' and 'Барцаль' in r['name_verbatim']:
        # full read 2026-10-11: the ceremony continues on p021 #1-#3, where the ballet presents a wreath
        rel, basis = 'mentions', 'full read of the reviews'
        r = dict(r, evidence_verbatim=r['evidence_verbatim'] + ' […] Императорскій балетъ, въ лицѣ г. Горскаго, поднесъ юбиляру вѣнокъ.',
                 evidence_english=r['evidence_english'] + ' The Imperial ballet, in the person of Gorskii, presented the jubilarian with a wreath (p021 #1 and #3; a figure caption sits between them).')
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

# --- occasions printed in the Repertoire's annotations and found nowhere else ------------------------------
# (repertoire_annotations_matched.csv, from build/match_repertoire_annotations.py). One row per season and annotation.
REP_CORE = {'Леньяни': 'ballerina', 'Трефилов': 'ballerina', 'Бергера': 'machinist-mechanic (RG ruling 2026-10-10: machinists)'}
REP_KIND = {'farewell': 'farewell', 'jubilee': 'jubilee', 'memorial': 'memorial_feature', 'for widow or family': 'memorial_feature',
            'anniversary (institution, work or event)': 'other'}
REP_NAME = {'Леньяни': 'г-жи Леньяни', 'Трефилов': 'балерины В. Трефиловой', 'Бергера': 'Н. А. Бергера', 'г. Власова': 'г. Власова',
            'Шаховского': 'князя А. А. Шаховского', 'кончины П. И. Чайковскаго': 'П. И. Чайковскаго'}
def rep_name(t):
    """the person where it is one of the ballet-relevant rows; otherwise the annotation itself, as printed"""
    return next((v for k, v in REP_NAME.items() if k in t), t.rstrip('.'))
if os.path.exists(ROOT + '/repertoire_annotations_matched.csv'):
    grp = {}
    for r in csv.DictReader(open(ROOT + '/repertoire_annotations_matched.csv', encoding='utf-8')):
        if not r['status'].startswith('NOT'): continue
        grp.setdefault((r['season'], r['kind'], re.sub(r'\W+', '', r['annotation'].lower())), []).append(r)
    for (season, kind, _), rs in grp.items():
        r = rs[0]; works = '; '.join(dict.fromkeys(x['works'] for x in rs if x['works']))
        core = next((why for k, why in REP_CORE.items() if k in r['annotation']), None)
        ballet_on_bill = bool(re.search(r'\(бал|бал\.|ком\.-бал', works))
        rel = 'core' if core else ('mentions' if ballet_on_bill else 'none')
        basis = ('Repertoire annotation: ' + core) if core else ('a ballet was on the bill' if ballet_on_bill else '')
        rows.append({'source_type': 'repertoire', 'season': season, 'source_file': '; '.join(dict.fromkeys(x['repertoire_page_id'] for x in rs)), 'pdf_page': '',
                     'printed_page': '; '.join(dict.fromkeys(x['printed_page'] for x in rs if x['printed_page'])), 'kind': REP_KIND[kind],
                     'name_verbatim': rep_name(r['annotation']), 'name_latin': '', 'role': '', 'troupe_city': f"{r['city']}, {r['theater']}",
                     'dates': '; '.join(dict.fromkeys(x['date'] for x in rs)) + ' (Repertoire date, old style)', 'length': 'annotation in the Repertoire table',
                     'relevance': rel, 'tier_basis': basis, 'evidence_verbatim': r['annotation'], 'evidence_english': '', 'author': '', 'portrait': 'no',
                     'notes': ('Kind of occasion: ' + kind + '. ' if REP_KIND[kind] in ('other', 'memorial_feature') else '') + 'On the bill: ' + (works or 'not stated') + '.', 'see_also': ''})

# What the Repertoire prints for each dated notice already in the catalogue (repertoire_date_check.csv).
REPCHK = {}
if os.path.exists(ROOT + '/repertoire_date_check.csv'):
    for r in csv.DictReader(open(ROOT + '/repertoire_date_check.csv', encoding='utf-8')):
        v = {'annotation names the person on that date': 'confirmed', 'person named on a DIFFERENT date': 'DATE DIFFERS',
             'event annotated that date, person not named': 'not named', 'no annotated Repertoire event for that date': ''}[r['status']]
        if v: REPCHK[(r['season'], r['name_in_catalogue'], r['dates_in_catalogue'])] = f"{v}: Repertoire {r['repertoire_date']}, {r['theater']}: «{r['annotation']}»"
DATE_FIX = {   # the review's date as the database stores it, against the review scan and the Repertoire
    ('1900-01', 'А. П. Крутикова'): ('23 Jan 1901', 'The database review text reads «25-го января»; the review page prints «23-го января» (scan read 2026-10-11; the typeface\'s 3 resembles a 5) and the Repertoire has the benefit on 23 January.'),
    ('1910-11', 'О. О. Палечека'): ('14 Feb 1911', 'The review text reads «14 февраля 1910 г.»; the Repertoire has the farewell benefit on 14 February 1911, inside the season under review. Review scan not checked.'),
}
for d in rows:
    d['repertoire_check'] = REPCHK.get((d['season'], d['name_verbatim'], d['dates']), '')
    if d['source_type'] == 'repertoire': d['repertoire_check'] = 'source'
    fx = DATE_FIX.get((d['season'], d['name_verbatim']))
    if fx and d['source_type'] == 'review':
        d['notes'] = (d['notes'] + ' ' if d['notes'] else '') + '[DATE CORRECTED from «' + d['dates'] + '»: ' + fx[1] + ']'; d['dates'] = fx[0]
        d['repertoire_check'] = d['repertoire_check'].replace('DATE DIFFERS', 'confirmed after correction')
    if d['repertoire_check'].startswith('DATE DIFFERS') and 'Верди' in d['name_verbatim']: d['repertoire_check'] = ''   # 1901 memorial concerts, not the 1911 remark
    if d['repertoire_check'].startswith('DATE DIFFERS') and 'Глазунов' in d['name_verbatim']:
        d['repertoire_check'] = d['repertoire_check'].replace('DATE DIFFERS', 'one day apart (the article prints «27-го января» for the celebration; the Repertoire and the ballet review have the performance on 28 January 1907)')

# Review dates the Repertoire could not confirm, re-read blind on the review scans (first_read/review_date_recheck/).
RECHK = {(r['page_id'], r['block'], r['name_in_catalogue']): r for r in csv.DictReader(open(ROOT + '/first_read/review_date_recheck/review_dates_blind_reread.csv', encoding='utf-8'))}
for d in rows:
    r = RECHK.get((d['source_file'], d['pdf_page'].replace('block ', ''), d['name_verbatim']))
    if r:
        what = 'no date is printed for the event itself' if re.match(r'NO ', r['date_as_read'], flags=re.I) else 'agrees'
        d['repertoire_check'] = ((d['repertoire_check'] + '; ') if d['repertoire_check'] else '') + f"re-read blind on the review scan 2026-10-11: {what}"

# Blind second read of the tiers of every section entry (first_read/tier_second_read/tier_comparison.csv).
TIER2 = {(r['season'], r['name']): r for r in csv.DictReader(open(ROOT + '/first_read/tier_second_read/tier_comparison.csv', encoding='utf-8'))}
# Both readers report the same fact; RG's rulings of 2026-10-10 make it core (designer on a ballet; ballet-orchestra player).
UPGRADE = {('1891-92', 'Васильевъ, Василій Васильевичъ'): 'designer: sets for the ballet «Царь Кандавлъ»',
           ('1891-92', 'Эзеръ, Карлъ Ѳедоровичъ'): 'solo cellist of the Moscow ballet orchestra',
           ('1892-93', 'Дровинъ (Тробинъ), Антонъ-Карлъ'): 'in the ballet orchestra 1886-88',
           ('1893-94', 'Помазанскій, Иванъ Александровичъ'): 'placed first in the ballet orchestra',
           ('1894-95', 'Вейкманъ Іеронимъ (Hieronymus Weickmann)'): 'first viola of the St Petersburg ballet orchestra 1855-59'}
# RG ruled on 2026-10-10 that theatre-school staff who did not teach dance, including honorary members of its
# conference, are "mentions"; that covers these six (two were already "mentions").
SCHOOL = {'Бостремъ': 'inspectress of the St Petersburg Theatre School', 'Маннъ': "honorary member of the St Petersburg Theatre School's conference",
          'Боборыкинъ': "honorary member of the Moscow Theatre School's conference", 'Спиро': 'temporarily inspector of externs at the Moscow Theatre School (1862)',
          'Ришардъ': 'chief supervisor at the St Petersburg Theatre School; daughter of a dancer', 'Орловъ, Иванъ': 'chief supervisor and acting assistant manager of the St Petersburg Theatre School'}
# RG, 2026-10-12, on posts that touched the ballet where the notice itself never names ballet or dance.
OFFICE_RULED = {('1893-94', 'Кистеръ'): ('core', 'head of the Imperial Theatres, 1875-81'),
                ('1891-92', 'Бегичевъ'): ('core', 'manager of the Moscow Imperial Theatres, 1881-82'),
                ('1893-94', 'Альбрехтъ, Евгеній'): ('mentions', 'Inspector of Music, in charge of all the St Petersburg orchestras'),
                ('1908-09', 'Юмашевъ'): ('mentions', 'assistant head of productions, Moscow office, from 1904'),
                ('1908-09', 'Правдинъ'): ('none', 'head of the drama classes at the theatre school')}
OFFICE = ()
for d in rows:
    t = TIER2.get((d['season'], d['name_verbatim'])) if d['source_type'] == 'section' else None
    d['tier_check'] = ''
    if not t: continue
    first = t['first_tier']
    if (d['season'], d['name_verbatim']) in UPGRADE:
        d['relevance'] = 'core'; d['tier_basis'] = 'RG ruling 2026-10-10 applied after the second read: ' + UPGRADE[(d['season'], d['name_verbatim'])]
        d['tier_check'] = f"second read: core (first read: {first}); both report the same fact"
    elif t['second_tier'] == first: d['tier_check'] = 'second read agrees'
    elif any(k in d['name_verbatim'] for k in SCHOOL):
        k = next(k for k in SCHOOL if k in d['name_verbatim'])
        d['tier_check'] = f"second read: {t['second_tier']} (first read: {first}); school post, no ballet or dance named in the text"
        d['relevance'] = 'mentions'; d['tier_basis'] = 'RG ruling 2026-10-10 (non-dance staff of the theatre school): ' + SCHOOL[k]
    elif any(k in d['name_verbatim'] for k in OFFICE):
        d['tier_check'] = f"second read: {t['second_tier']} — on office or school post alone, no ballet named in the text; tier left as first read pending RG"
    else: d['tier_check'] = f"second read: {t['second_tier']} — {t['second_remark'][:160]}"
    if not t['read_whole'].lower().startswith('yes'): d['tier_check'] += ' (entry cut off in the scan)'
    for (season, key), (tier, why) in OFFICE_RULED.items():
        if d['season'] == season and d['name_verbatim'].startswith(key):
            d['tier_check'] = f"second read: {t['second_tier']} (first read: {first}); post only, no ballet or dance named in the text"
            d['relevance'] = tier; d['tier_basis'] = (f'RG ruling 2026-10-12: {why}' if tier != 'none' else '')
            if tier == 'none': d['tier_check'] += f'; RG 2026-10-12: none ({why})'
for d in rows:   # the same man's jubilee notice names only the opera orchestra; his last appearance was in a ballet bill
    if d['season'] == '1908-09' and d['name_verbatim'].startswith('Ауэръ') and d['kind'] == 'jubilee' and d['relevance'] == 'none':
        d['relevance'] = 'core'; d['tier_basis'] = 'same person as a core entry (1906-07 farewell); this notice itself names only the Russian opera orchestra'

# Roster death marks re-read on the roster scans (first_read/roster_death_recheck/); ordinals the database row lacks.
ROSTER_ORDINAL = {'Ячменева, Марія Сергѣевна': 'Ячменева 1-я, Марія Сергѣевна', 'Брыкинъ, Николай Константиновичъ': 'Брыкинъ 1-й, Николай Константиновичъ',
                  'Александровъ, Михаилъ Михайловичъ': 'Александровъ 2-й, Михаилъ Михайловичъ'}
RR = collections.defaultdict(list) if 'collections' in globals() else None
import collections as _c
RR = _c.defaultdict(list)
for r in csv.DictReader(open(ROOT + '/first_read/roster_death_recheck/roster_deaths_blind_reread.csv', encoding='utf-8')): RR[r['name_in_catalogue']].append(r)
for d in rows:
    if d['source_type'] != 'roster' or d['name_verbatim'] not in RR: continue
    rr = RR[d['name_verbatim']]
    blind = not any('not blind' in r['confidence'] for r in rr)
    d['repertoire_check'] = ('re-read blind on the roster scan 2026-10-12: date agrees' if blind else 'read on the roster scan 2026-10-12 (not blind): date agrees') + (f' ({len(rr)} roster pages)' if len(rr) > 1 else '')
    if d['name_verbatim'] in ROSTER_ORDINAL:
        d['notes'] += f" The roster prints the ordinal, which the database row lacks: «{ROSTER_ORDINAL[d['name_verbatim']]}»."; d['name_verbatim'] = ROSTER_ORDINAL[d['name_verbatim']]
    d['notes'] = d['notes'].replace('Name and date as stored in the database (raw.person_entry); not re-read for this catalogue.', 'Name and date as stored in the database (raw.person_entry), confirmed on the roster scan.')

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
people = [d for d in rows if d['kind'] in ('obituary', 'jubilee', 'farewell', 'memorial_feature', 'death_notice', 'death_mark', 'biographical_feature', 'departure') and d['name_verbatim']]
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
out_cols = ['source_type'] + COLS[:12] + ['tier_basis'] + COLS[12:] + ['see_also', 'date_check', 'tier_check']
for name, keep in (('jubilees_obituaries_all_entries.csv', lambda d: True), ('jubilees_obituaries_ballet_only.csv', lambda d: d['relevance'] in ('core', 'mentions', 'undecided'))):
    with open(os.path.join(ROOT, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, out_cols, extrasaction='ignore'); w.writeheader(); w.writerows(dict(d, date_check=d.get('repertoire_check', '')) for d in rows if keep(d))

# mixed-script guard: no word may mix Cyrillic with Latin or Greek letters
bad = set()
for d in rows:
    for v in d.values():
        for wd in re.findall(r'\w+', v):
            if re.search('[Ѐ-ӿ]', wd) and re.search('[A-Za-zͰ-Ͽ]', wd): bad.add(wd)
import collections
people = [d for d in rows if d['kind'] in ('obituary', 'jubilee', 'farewell', 'memorial_feature', 'death_notice', 'death_mark', 'biographical_feature', 'departure')]
print('rows', len(rows), '| person entries', len(people), collections.Counter(d['relevance'] for d in people))
print('by source:', collections.Counter((d['source_type'], d['relevance']) for d in people))
print('by kind (core+mentions):', collections.Counter((d['kind'], d['relevance']) for d in people if d['relevance'] != 'none'))
print('tier set by an RG ruling:', [(d['season'], d['name_verbatim']) for d in rows if d['tier_basis'].startswith('RG')])
print('mixed-script words:', bad or 'none')
