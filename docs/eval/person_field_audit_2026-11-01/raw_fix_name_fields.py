"""Name-field moves (person field audit, RG 2026-11-02: "Apply all three"):
B3  first name + patronymic stored together in first_name -> split (B3_split_first_patronymic.csv, 160 rows)
B4  Graduates «Surname, Name.» in family_name -> family_name / first_name (B4_split_graduate_surname.csv, 79 rows)
A5  second given name stored as patronymic -> joined into first_name, patronymic empty (A5_double_given_names.csv, 23 rows)
Field moves only: no letters changed, no entries added/removed/reordered (entities.person_link stays aligned, issue #131).
Each edit asserts the current raw value equals the CSV's 'now' value before changing it.
usage: uv run python docs/eval/person_field_audit_2026-11-01/raw_fix_name_fields.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import csv, json, sys, collections
from pathlib import Path

RAW = Path('outputs/full_run/raw'); D = Path(__file__).parent
edits = collections.defaultdict(list)   # page -> (idx, {field: (now, new)})
for r in csv.DictReader(open(D / 'B3_split_first_patronymic.csv', encoding='utf-8')):
    edits[r['entry_id']].append({'first_name': (r['first_name_now'], r['first_name_new']), 'patronymic': (r['patronymic_now'], r['patronymic_new'])})
for r in csv.DictReader(open(D / 'B4_split_graduate_surname.csv', encoding='utf-8')):
    edits[r['entry_id']].append({'family_name': (r['family_name_now'], r['family_name_new']), 'first_name': (r['first_name_now'], r['first_name_new'])})
for r in csv.DictReader(open(D / 'A5_double_given_names.csv', encoding='utf-8')):
    edits[r['entry_id']].append({'first_name': (r['first_name_now'], r['first_name_new']), 'patronymic': (r['patronymic_now'], r['patronymic_new'])})
by_page = collections.defaultdict(list)
for eid, es in edits.items():
    assert len(es) == 1, (eid, 'in two lists')
    page, idx = eid.rsplit('__e', 1)
    by_page[page].append((int(idx), eid, es[0]))
n = 0
for page, items in sorted(by_page.items()):
    f = RAW / f'{page}.raw.json'
    d = json.loads(f.read_text(encoding='utf-8'))
    for idx, eid, ch in items:
        e = d['entries'][idx - 1]
        for field, (now, new) in ch.items():
            assert (e.get(field) or '') == now, (eid, field, e.get(field), now)
        for field, (now, new) in ch.items():
            e[field] = new or None
        n += 1
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(n, 'entries on', len(by_page), 'pages', '| WRITTEN' if '--write' in sys.argv else '| dry run')
