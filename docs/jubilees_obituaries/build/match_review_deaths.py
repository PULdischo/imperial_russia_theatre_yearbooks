"""Match the death lists printed in the Season Reviews (first_read/R_reviews.csv, kind=obituary)
to the obituary entries in jubilees_obituaries_all_entries.csv; names with no scanned obituary carry the roster finding
(queries logged in docs/query_log.md, 2026-10-10). Writes review_deaths_matched.csv.
"""
import csv, difflib, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = [r for r in csv.DictReader(open(ROOT + '/first_read/R_reviews.csv', encoding='utf-8')) if r['kind'] == 'obituary']
C = [r for r in csv.DictReader(open(ROOT + '/jubilees_obituaries_all_entries.csv', encoding='utf-8')) if r['kind'] == 'obituary']

def surname(n):
    n = re.sub(r'\b[А-ЯІѲ][а-яѣіѳ]{0,4}\.\s*', '', n)
    w = [x for x in re.findall(r'[А-Яа-яѣіѳѵІѲѢ-]+', n) if len(x) > 2]
    return w[-1] if w else n
def stem(s): return re.sub(r'(ъ|а|у|ой|ая|аго|ымъ|ѣ)$', '', s.lower())
def initials(n): return re.findall(r'\b([А-ЯІѲ])[а-яѣіѳ]{0,3}\.', n)

# No obituary section is scanned for these seasons; verdict from raw.person_entry (BalletArtists rosters).
ROSTER = {
    'Н. А. Разуевъ': 'Разуевъ, Николай Александровичъ — ballet roster 1890-91..1896-97',
    'Н. Н. Троицкая': 'Троицкая, Надежда Николаевна — ballet roster 1890-91..1896-97',
    'К. А. Ахмакова': 'Ахмакова, Клавдія Александровна — SP ballet roster to 1897-98, printed "† 16 августа 1897 г." (1890-91 roster row reads Калерія)',
    'С. С. Литавкинъ': 'Литавкинъ, Сергѣй Спиридоновичъ — SP ballet roster to 1897-98, printed "† 17 марта 1898 г."',
    'М. А. Дмитріевъ': 'Дмитріевъ, Михаилъ Андреевичъ — ballet roster 1897-98 (one season only)',
    'Гиллертъ': 'Гиллертъ, Станиславъ Феликсовичъ — SP ballet roster to 1907-08, printed "† 19 декабря 1907 г."',
    'К. А. Кондараки': 'not in any roster section in the database (rosters cover ballet, orchestra, school, administration, production team)',
    'А. В. Анненкова': 'not in any roster section in the database',
}
NOTES = {
    'Е. К. Смирнова': 'SOURCE CONFLICT: review and the 1893-95 ballet rosters print Е. К. / Евгенія Кирилловна; the obituary heading prints «Евгенія Дмитріевна» (checked on the scan). Same person: service date 19 декабря 1878 agrees. The obituary directly above is Сергѣева, Анна Дмитріевна.',
    'Н. П. Пуни': 'SOURCE CONFLICT: review prints «Н. П.»; obituary and the 1893-96 rosters print Николай Цезаревичъ.',
    'С. Г. Никитинъ': 'SOURCE CONFLICT: review prints 24-го іюля 1896; obituary prints † 23-го іюля 1896 (both obituary readings agree).',
    'М. Н. Казаковъ': 'SOURCE CONFLICT: review prints 16 сентября 1892; obituary prints 17-го сентября 1892 (both obituary readings agree).',
    'Ламберъ': 'Obituary heading is the double surname Ламберъ-Робине.',
}
out = []
for r in R:
    if 'Княг' in r['name_verbatim'] or 'Княз' in r['name_verbatim']:
        out.append([r['season'], r['page_id'], r['name_verbatim'], r['dates'], '', '', '', 'not theatre staff', r['relevance'], 'Imperial family death that closed the theatres; not an obituary subject.']); continue
    s = stem(surname(r['name_verbatim'])); ini = initials(r['name_verbatim'])
    cand = [c for c in C if c['season'] == r['season'] and
            difflib.SequenceMatcher(None, s, stem(re.split(r'[ ,(-]', c['name_verbatim'])[0])).ratio() > 0.84]
    if len(cand) > 1 and ini:        # several same-surname obituaries that season: use the given-name initial
        byini = [c for c in cand if re.search(r',\s*' + ini[0], c['name_verbatim'])]
        cand = byini or cand
    if len(cand) > 1:                # still several: prefer the troupe the review belongs to
        cand = [c for c in cand if ('ballet' in r['page_id']) == (c['relevance'] == 'core')] or cand
    c = cand[0] if len(cand) == 1 else None
    basis = 'obituary' if c else ('roster' if r['name_verbatim'] in ROSTER and 'not in any' not in ROSTER[r['name_verbatim']] else 'unmatched')
    tier = c['relevance'] if c else ('core' if basis == 'roster' else 'none')
    out.append([r['season'], r['page_id'], r['name_verbatim'], r['dates'],
                c['name_verbatim'] if c else '', c['printed_page'] if c else '', c['dates'] if c else '',
                basis, tier, ' '.join(x for x in (ROSTER.get(r['name_verbatim'], ''), NOTES.get(r['name_verbatim'], ''), '' if len(cand) <= 1 else 'AMBIGUOUS: ' + '; '.join(x['name_verbatim'] for x in cand)) if x)])
with open(ROOT + '/review_deaths_matched.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['season', 'review_page_id', 'name_in_review', 'date_in_review', 'obituary_name', 'obituary_printed_page', 'obituary_dates', 'basis', 'relevance', 'notes']); w.writerows(out)
import collections
print(len(out), collections.Counter((o[7], o[8]) for o in out))
for o in out:
    if o[7] != 'obituary' or 'CONFLICT' in o[9] or 'AMBIG' in o[9]: print(' | '.join(o[:3] + o[4:5] + o[7:9]), '|', o[9][:70])
