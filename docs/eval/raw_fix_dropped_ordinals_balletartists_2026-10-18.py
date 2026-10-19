"""BalletArtists dropped ordinals (2026-10-18; issue #154 follow-up, after raw_fix_ordinal_shift_balletartists_2026-10-15.py).

The lists print same-surname artists as «Фамилія 1-я, Имя Отчество». Issue #154 fixed rows where extraction put the ordinal in the
wrong field; this fixes the 761 rows where it dropped the ordinal altogether («Хомякова 1-я» stored as «Хомякова»).
All 392 BalletArtists pages were read on the full-resolution scans (pdf/Spiski_BalletArtists, extract_image), every ordinal printed
on each page recorded and compared with raw; worklist docs/eval/dropped_ordinal_worklist_2026-10-18.tsv (RG: "apply all 761").
  drop                    746  ordinal printed, surname stored bare: append the ordinal exactly as printed
  drop_by_position          3  same, placed by entry index (1906-07 SP prints two «15.» Воронковъ; 1904-05 SP «1.» stored as «I.»)
  drop_surname_differs      9  same, and the stored surname is misread: corrected to the print (zoomed, RG 2026-10-18)
  shifted_letter_ordinal    3  ordinal misread as a letter and pushed into first_name («Э-й», «г-жа», «І-я»); names moved back
Where the print sets a comma before the ordinal («Голубева, 2-я», «Козловъ, 2-й») the comma is dropped, as in the Шелепина fix;
«Ѳедоровъ 1 й» (1903-04 SP no. 90) keeps its missing hyphen. A surname printed bare stays bare (e.g. 1909-10 SP no. 70 «Улановъ»
beside no. 71 «Улановъ 2-й»; 1899-00 MSK no. 65 «Некрасова» beside «Некрасова 2-я»).
Field edits only: no entries added or removed, so person_link entry_ids are unchanged (issue #131).
usage: uv run python docs/eval/raw_fix_dropped_ordinals_balletartists_2026-10-18.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

RAW = Path('outputs/full_run/raw')
WORKLIST = Path('docs/eval/dropped_ordinal_worklist_2026-10-18.tsv')
EXPECTED = {'drop': 746, 'drop_by_position': 3, 'drop_surname_differs': 9, 'shifted_letter_ordinal': 3}
SURNAME_MISREAD = {'Чередова': 'Черепова', 'Бакинь': 'Бакинъ', 'Климащевская': 'Климашевская', 'Оголейть': 'Оголейтъ',
                   'Кшесинскій': 'Кщесинскій',   # 1901-02 SP no. 30: «Кщесинскій 2-й» is printed (no. 29 «Кшесинскій 1-й»)
                   'Тихомировъ': 'Тихоміровъ'}
# ordinal misread as a letter and moved into first_name; the given name sits in patronymic, the patronymic in tenure or patronymic
SHIFTED = {('balletartists_1896-97_MSK_p006', 0): 'Э-й', ('balletartists_1901-02_MSK_p001', 2): 'г-жа',
           ('balletartists_1904-05_SP_p004', 7): 'І-я'}
PATRONYMIC = re.compile(r'^[А-ЯЁѲІѢ]\w*(вна|чна|ична|ичъ|вичъ)$')

work = defaultdict(list)
for w in csv.DictReader(WORKLIST.open(encoding='utf-8'), delimiter='\t'):
    work[w['page_id']].append(w)

rows, groups = [], Counter()
for page_id in sorted(work):
    f = RAW / f'{page_id}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    for w in work[page_id]:
        i = int(w['entry_index'])
        e = d['entries'][i]
        assert e['family_name'] == w['old_family_name'] and e.get('list_number') == (w['list_number'] or None), (page_id, i, e['family_name'])
        assert not re.search(r'[0-9]\s?-?\s?[яй]$', e['family_name'].strip()), (page_id, i)
        old = {k: e.get(k) for k in ('family_name', 'first_name', 'patronymic', 'tenure_note_text')}
        ordinal = re.search(r'([0-9]+\s?-?\s?[яй])$', w['new_family_name']).group(1)
        surname = e['family_name'].strip()
        if w['group'] == 'drop_surname_differs':
            surname = SURNAME_MISREAD[surname]
        new = {'family_name': f'{surname} {ordinal}'}
        if w['group'] == 'shifted_letter_ordinal':
            assert e['first_name'] == SHIFTED[(page_id, i)], (page_id, i, e['first_name'])
            if ' ' in e['patronymic']:                                   # «Евгеній Михайловичъ» in patronymic
                given, patr = e['patronymic'].split(' ')
                new.update(first_name=given, patronymic=patr)
            else:                                                        # patronymic opens tenure_note_text
                patr, _, rest = e['tenure_note_text'].partition(' ')
                new.update(first_name=e['patronymic'], patronymic=patr, tenure_note_text=rest.lstrip() or None)
            assert PATRONYMIC.match(new['patronymic']), (page_id, i, new)
        e.update(new)
        groups[w['group']] += 1
        rows.append((page_id, i, w['group'], old, {k: e.get(k) for k in old}))
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

for page_id, i, g, old, new in rows:
    if g != 'drop':
        print(f"{page_id[14:]:<17} {i:>3} {g:<22} {old['family_name']} / {old['first_name']} / {old['patronymic']}  ->  "
              f"{new['family_name']} / {new['first_name']} / {new['patronymic']} / {(new['tenure_note_text'] or '')[:24]!r}")
print(len(rows), 'rows on', len(work), 'pages', dict(groups))
assert dict(groups) == EXPECTED, groups
if '--write' in sys.argv:
    print('WRITTEN')
