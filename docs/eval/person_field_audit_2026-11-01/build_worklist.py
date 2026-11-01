"""Collect the audit flags that need a scan read into scan_worklist.csv, one row per (page, item).
Drops signals shown to be checker noise or the print's own form (see README). Run after audit.py."""
import csv, re, collections
from pathlib import Path

D = Path(__file__).parent
rd = lambda n: list(csv.DictReader(open(D / n, encoding='utf-8')))
W = []


def add(check, signal, page, entry, no, stored, extra=''):
    W.append(dict(check=check, signal=signal, page_id=page, entry_id=entry, list_no=no, stored=stored, context=extra))


def roster_stored(r):
    return f"{r['family_name']} | {r['first_name']} | {r['patronymic']}"


SKIP_R1 = {'no patronymic (first name present)', 'surname starts lower-case'}  # print form: foreigners / «фонъ-», «де-»
SAMPLE_R1 = {'first name + patronymic both in first-name field': 8, 'first name inside surname field («Surname, Name.»)': 6,
             'punctuation left on the surname': 0}
seen = collections.Counter()
for r in rd('R1_name_field_shape.csv'):
    s = r['signal']
    if s in SKIP_R1: continue
    if s in SAMPLE_R1:
        seen[s] += 1
        if seen[s] > SAMPLE_R1[s]: continue
    if s == 'bracket or quote in a name field' and '(' in r['family_name'] and '(' not in r['first_name'] + r['patronymic']: continue
    add('R1', s, r['page_id'], r['entry_id'], r['no'], roster_stored(r), r['person'])
done_r2 = set()
for r in rd('R2_gender_conflict_in_row.csv'):
    k = (r['person'], r['genders'])
    if k in done_r2: continue
    done_r2.add(k)
    add('R2', 'gender conflict: ' + r['genders'], r['page_id'], r['entry_id'], r['no'], roster_stored(r), r['person'])
for r in rd('R3_one_off_spelling.csv'):
    add('R3', f"{r['field']}: «{r['value']}» vs usual «{r['common_neighbour']}» x{r['neighbour_count']}", r['page_id'], r['entry_id'], r['no'], roster_stored(r), r['person'])
for r in rd('R4_wrong_or_missing_column.csv'):
    s = r['signal']
    if s.startswith('instrument word in') and not re.match(r'(?i)(скрипк|альт\b|віолончел|контрабас|флейт|гобо|кларнет|фагот|валторн|вальдгорн|труб|тромбон|туба|литавр|арф|барабан)', r['value']): continue
    if s == 'Musicians row with no instrument' and re.search(r'(Репетитор|Капельмейстер|Концертмейстер|Библіотек|Инспектор|Настройщ|Пѣвч|хор)', r['value'], re.I): continue
    if s == 'credit text in rank_or_title' and 'онъ же' in r['value']: continue
    add('R4', s, r['page_id'], r['entry_id'], r['no'], roster_stored(r), r['value'])
for r in rd('R5_tenure_parse.csv'):
    add('R5', r['signal'], r['page_id'], r['entry_id'], r['no'], roster_stored(r), r['value'])
for r in rd('R6_numbering.csv'):
    add('R6', f"{r['signal']}: {r['detail']}", r['page_id'], r['entry_id'], r['no'], roster_stored(r), f"previous entry {r['entry_id_before']}")
for r in rd('R7_credit_summary.csv'):
    if r['signal'].startswith('credit summary text but no credit rows') and re.match(r'^\s*(Оставил|\d+ \w+ \d{4} г\. переведен)', r['value']): continue
    add('R7', r['signal'], r['page_id'], r['entry_id'], r['no'], roster_stored(r), r['value'])
for r in rd('C1_production_credits.csv'):
    if r['signal'].startswith('role_category') and re.search(r'(поста|состав|сюжет|обработ|сюит|сочин|соч\.)', r['role_text']): continue
    pid = r['credit_id'].rsplit('__c', 1)[0]
    add('C1', r['signal'], pid.split('__e')[0], r['credit_id'], '', f"{r['name_printed']} | {r['role_text']} | {r['role_category']}", r['person'])
for r in rd('V1_review_credits.csv'):
    add('V1', r['signal'], r['page_id'], r['credit_id'], '', f"{r['name_surface']} | initials {r['initials']} | {r['role']}", f"{r['printed_phrase']} || linked: {r['person']} {r['person_span']}")
for r in rd('J1_jubilee_obituary_links.csv'):
    if r['signal'] == 'surname differs' and r['basis'].startswith(('automatic: the only record agreeing on surname', 'automatic: the review-mention')): continue
    add('J1', r['signal'], '', r['entry_id'], '', r['name_verbatim'], f"{r['linked_or_candidate']} {r['person_span']} || {r['basis'][:160]}")
W.sort(key=lambda w: (w['page_id'] == '', w['page_id'], w['entry_id']))
for i, w in enumerate(W, 1): w['item'] = i
with open(D / 'scan_worklist.csv', 'w', newline='', encoding='utf-8') as f:
    cw = csv.DictWriter(f, fieldnames=['item', 'check', 'signal', 'page_id', 'entry_id', 'list_no', 'stored', 'context']); cw.writeheader(); cw.writerows(W)
c = collections.Counter(w['check'] for w in W)
print(len(W), 'items on', len({w['page_id'] for w in W}), 'pages;', dict(c))
