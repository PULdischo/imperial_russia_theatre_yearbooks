"""BalletArtists ordinal shift (2026-10-15; follow-up to raw_fix_mosolova_1907-08_2026-10-15.py).

The lists print sisters/brothers as «Фамилія 1-я, Имя Отчество» (once, 1909-10 MSK no. 76, «Шелепина, 1-я Вѣра Ивановна»).
Extraction put the ordinal in the wrong field on 216 rows, 1891-92..1909-10, in five shapes:
  A  first_name='1-я', patronymic=<first name>, tenure_note_text='<patronymic> (съ ...' (patronymic pushed into tenure)
  A0 the same, but the patronymic was dropped altogether (1909-10 MSK nos. 76-77, Шелепина: restored from the scan)
  B  first_name='1-й', patronymic='<first name> <patronymic>'
  C  first_name='1-я, <first name>', patronymic in place
  D  patronymic='1-я' (no patronymic printed: Мендесъ, Смирновъ, Алексѣевъ)
  E  names in place, tenure_note_text='1-я, съ ...' (ordinal pushed to the front of tenure)
  N  first_name='2-я' and nothing else printed («26. Грекова 2-я.», 1901-02 MSK)
Every row restored to the printed fields with the ordinal kept on the surname, as in the Мосолова fix («Мосолова 1-я»).
Tenure text is otherwise left exactly as extracted (pages whose neighbours read «съ ... г.)» keep that form).
Plus one surname misread on an edited row: 1907-08 MSK no. 30 prints «Костровской 1-й» (raw had «Костровскій»).
Field edits only: no entries added or removed, so person_link entry_ids are unchanged (issue #131).
All pages read on the full-resolution scans (pdf/Spiski_BalletArtists, extract_image), 2026-10-15.
usage: uv run python docs/eval/raw_fix_ordinal_shift_balletartists_2026-10-15.py [--write] [--tsv out.tsv]; then docs/eval/rebuild_after_raw_edit.sh"""
import csv, glob, json, re, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
ORD = r'([0-9]+\s?-?\s?[яй])'   # kept exactly as printed («Никитина 2 я», 1905-06 MSK no. 65, has no hyphen)
PATRONYMIC = re.compile(r'^[А-ЯЁѲІѢ]\w*(вна|чна|ична|ичъ|вичъ)$')
# A0: patronymic dropped by the extraction, read off the scan
DROPPED_PATRONYMIC = {('balletartists_1909-10_MSK_p004', '76.', 'Шелепина'): 'Ивановна',
                      ('balletartists_1909-10_MSK_p004', '77.', 'Шелепина'): 'Ивановна'}
SURNAME_MISREAD = {('balletartists_1907-08_MSK_p006', '30.', 'Костровскій'): 'Костровской'}
EXPECTED = {'A': 52, 'A0': 2, 'B': 19, 'C': 22, 'D': 9, 'E': 111, 'N': 1}


def ordinal(m):
    return m.group(1)


def fix(page_id, e):
    """Return (shape, new field values) for a shifted entry, or None."""
    fam, first, pat, ten = (e.get(k) for k in ('family_name', 'first_name', 'patronymic', 'tenure_note_text'))
    key = (page_id, e.get('list_number'), fam)
    if first and (m := re.match(ORD + r'$', first)):
        new = {'family_name': f'{fam} {ordinal(m)}'}
        if not pat and not ten:                                   # N
            return 'N', {**new, 'first_name': None}
        if ' ' in pat:                                            # B
            given, patr = pat.split(' ')
            assert PATRONYMIC.match(patr), (key, pat)
            return 'B', {**new, 'first_name': given, 'patronymic': patr}
        if key in DROPPED_PATRONYMIC:                             # A0
            assert not PATRONYMIC.match(ten.split(' ')[0]), (key, ten)
            return 'A0', {**new, 'first_name': pat, 'patronymic': DROPPED_PATRONYMIC[key]}
        patr, _, rest = ten.partition(' ')                        # A
        assert PATRONYMIC.match(patr), (key, ten)
        return 'A', {**new, 'first_name': pat, 'patronymic': patr, 'tenure_note_text': rest.lstrip() or None}
    if first and (m := re.match(ORD + r',\s*(\S+)$', first)):    # C
        assert PATRONYMIC.match(pat), (key, pat)
        return 'C', {'family_name': f'{fam} {ordinal(m)}', 'first_name': m.group(2)}
    if pat and (m := re.match(ORD + r'$', pat)):                 # D
        return 'D', {'family_name': f'{fam} {ordinal(m)}', 'patronymic': None}
    if ten and (m := re.match(ORD + r',\s*', ten)):              # E
        return 'E', {'family_name': f'{fam} {ordinal(m)}', 'tenure_note_text': ten[m.end():]}
    return None


rows, shapes = [], {k: 0 for k in EXPECTED}
for f in sorted(RAW.glob('balletartists_*.raw.json')):
    page_id = f.name[:-len('.raw.json')]
    d = json.loads(f.read_text(encoding='utf-8'))
    changed = False
    for i, e in enumerate(d['entries']):
        r = fix(page_id, e)
        if r is None:
            continue
        shape, new = r
        assert not re.search(r'\d-[яй]$', e['family_name']), (page_id, e['family_name'])
        key = (page_id, e.get('list_number'), e.get('family_name'))
        if key in SURNAME_MISREAD:
            new['family_name'] = new['family_name'].replace(key[2], SURNAME_MISREAD[key], 1)
        old = {k: e.get(k) for k in ('family_name', 'first_name', 'patronymic', 'tenure_note_text')}
        e.update(new)
        shapes[shape] += 1
        changed = True
        rows.append({'page_id': page_id, 'entry_index': i, 'list_number': e.get('list_number'), 'shape': shape,
                     **{f'old_{k}': v for k, v in old.items()},
                     **{f'new_{k}': e.get(k) for k in old}})
    if changed and '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

for r in rows:
    print(f"{r['page_id'][14:]:<17} {r['list_number']:<5} {r['shape']:<2} "
          f"{r['old_family_name']} / {r['old_first_name']} / {r['old_patronymic']} / {(r['old_tenure_note_text'] or '')[:28]!r}"
          f"  ->  {r['new_family_name']} / {r['new_first_name']} / {r['new_patronymic']} / {(r['new_tenure_note_text'] or '')[:28]!r}")
print(len(rows), 'rows', shapes)
assert shapes == EXPECTED, shapes
if '--tsv' in sys.argv:
    out = sys.argv[sys.argv.index('--tsv') + 1]
    with open(out, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter='\t'); w.writeheader(); w.writerows(rows)
    print('worklist ->', out)
if '--write' in sys.argv:
    print('WRITTEN')
