"""Raw-tier corrections found during the ordinal-shift person review of 2026-10-12 (RG: fix these).
Every row was read on the scan at full zoom (docs/query_log.md, 2026-10-12). Field edits only: no entry is added,
removed or moved, so entry ids -- and entities.person_link -- are untouched (issue #131).
Each fix names the page, the entry's list number and its CURRENT values; the script refuses to run if any differ.
Dry run by default; --write saves the raw JSON (back the pages up first), then run docs/eval/rebuild_after_raw_edit.sh.
usage: uv run python docs/eval/raw_fix_ordinal_shift_rows_2026-10-12.py [--write]"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
MART = 'Мартьяновъ'
FED = {'patronymic': 'Никифоровна'}

# (page, list_number, {field: current}, {field: new})   -- service_periods edits are given separately below
FIXES = [
    # Мартьяновъ, Александръ Александровичъ (SP): the print has «Мартьяновъ» in every volume
    ('balletartists_1893-94_SP_p007', '38.', {'family_name': 'Мартяновъ'}, {'family_name': MART}),
    ('balletartists_1894-95_SP_p007', '40.', {'family_name': 'Мартыновъ'}, {'family_name': MART}),
    ('balletartists_1898-99_SP_p007', '40.', {'family_name': 'Мартъяновъ'}, {'family_name': MART}),
    ('balletartists_1900-01_SP_p007', '39.', {'family_name': 'Мартъяновъ'}, {'family_name': MART}),
    ('balletartists_1902-03_SP_p008', '43.', {'family_name': 'Мартъяновъ'}, {'family_name': MART}),
    ('balletartists_1903-04_SP_p008', '48.', {'family_name': 'Мартыновъ'}, {'family_name': MART}),
    ('balletartists_1904-05_SP_p000', '2.', {'family_name': 'Мартыновъ'}, {'family_name': MART}),
    ('balletartists_1904-05_SP_p008', '49.', {'family_name': 'Мартыновъ'}, {'family_name': MART}),
    ('balletartists_1905-06_SP_p000', '2.', {'family_name': 'Мартыновъ'}, {'family_name': MART}),
    ('balletartists_1906-07_SP_p000', '1.', {'family_name': 'Мартыновъ'}, {'family_name': MART}),
    ('balletartists_1907-08_SP_p000', '2.', {'family_name': 'Мартъяновъ'}, {'family_name': MART}),
    ('balletartists_1908-09_SP_p000', '2.', {'family_name': 'Мартыновъ 2-й'}, {'family_name': MART + ' 2-й'}),
    ('balletartists_1909-10_SP_p000', '2.', {'family_name': 'Мартъяновъ 2-й'}, {'family_name': MART + ' 2-й'}),
    # Ѳедорова, Екатерина Никифоровна (Moscow): patronymic misreads (some with Latin letters) and dropped ordinals
    ('balletartists_1898-99_MSK_p005', '124.', {'family_name': 'Ѳедорова', 'patronymic': 'Никіфоровна'}, {'family_name': 'Ѳедорова 2-я', **FED}),
    ('balletartists_1899-00_MSK_p005', '118.', {'family_name': 'Ѳедорова', 'patronymic': 'Никifoровна'}, {'family_name': 'Ѳедорова 1-я', **FED}),
    ('balletartists_1900-01_MSK_p005', '123.', {'family_name': 'Ѳедорова', 'patronymic': 'Никитфоровна'}, {'family_name': 'Ѳедорова 1-я', **FED}),
    ('balletartists_1901-02_MSK_p004', '119.', {'family_name': 'Ѳедорова', 'patronymic': 'Никifoровна'}, {'family_name': 'Ѳедорова 1-я', **FED}),
    ('balletartists_1903-04_MSK_p004', '105.', {'family_name': 'Ѳедорова 1-я', 'patronymic': 'Никifoровна'}, FED),
    ('balletartists_1904-05_MSK_p004', '94.', {'family_name': 'Федорова', 'patronymic': 'Никитовна'}, {'family_name': 'Федорова 1-я', **FED}),
    ('balletartists_1905-06_MSK_p004', '103.', {'family_name': 'Ѳедорова', 'patronymic': 'Никифоровна'}, {'family_name': 'Ѳедорова 1-я'}),
    ('balletartists_1906-07_MSK_p004', '98.', {'family_name': 'Ѳедорова 1-я', 'patronymic': 'Никіфоровна'}, FED),
    ('balletartists_1907-08_MSK_p005', '101.', {'family_name': 'Ѳедорова 1-я', 'patronymic': 'Никиторовна'}, FED),
    ('balletartists_1908-09_MSK_p003', '84.', {'family_name': 'Ѳедорова 1-я', 'first_name': 'Екатерина Никифоровна', 'patronymic': None}, {'first_name': 'Екатерина', **FED}),
    ('balletartists_1909-10_MSK_p005', '80.', {'family_name': 'Ѳедорова 1-я', 'patronymic': 'Никиторовна'}, FED),
    # Панова 4-я, Елизавета Евгеньевна (Moscow)
    ('balletartists_1896-97_MSK_p003', '83.', {'family_name': 'Панова 4-я', 'patronymic': 'Евгеніевна'}, {'patronymic': 'Евгеньевна'}),
    ('balletartists_1897-98_MSK_p003', '81.', {'family_name': 'Панова'}, {'family_name': 'Панова 4-я'}),
    ('balletartists_1898-99_MSK_p003', '77.', {'family_name': 'Панова', 'rank_or_title': '4-я'}, {'family_name': 'Панова 4-я', 'rank_or_title': None}),
    # Бакинъ (Moscow 1908-09): ordinals dropped; Александръ's leaving note not captured
    ('balletartists_1908-09_MSK_p004', '1.', {'family_name': 'Бакинъ', 'first_name': 'Сергѣй'}, {'family_name': 'Бакинъ 1-й'}),
    ('balletartists_1908-09_MSK_p004', '2.', {'family_name': 'Бакинъ', 'first_name': 'Александръ', 'tenure_note_text': 'съ 1895 г.'},
     {'family_name': 'Бакинъ 2-й', 'tenure_note_text': '(съ 1895 г.). Оставилъ службу 10 ноября 1908 г.'}),
    # ordinal in first_name, first name in patronymic, patronymic in the tenure note
    ('balletartists_1907-08_MSK_p003', '70.', {'family_name': 'Павлова', 'first_name': '1-я', 'patronymic': 'Евгенія', 'tenure_note_text': 'Ивановна (съ 1 сентября 1901 г.).'},
     {'family_name': 'Павлова 1-я', 'first_name': 'Евгенія', 'patronymic': 'Ивановна', 'tenure_note_text': '(съ 1 сентября 1901 г.).'}),
    ('balletartists_1907-08_MSK_p003', '71.', {'family_name': 'Павлова', 'first_name': '2-я', 'patronymic': 'Анна', 'tenure_note_text': 'Матвѣевна (съ 1 іюня 1899 г.).'},
     {'family_name': 'Павлова 2-я', 'first_name': 'Анна', 'patronymic': 'Матвѣевна', 'tenure_note_text': '(съ 1 іюня 1899 г.).'}),
    ('balletartists_1901-02_MSK_p001', '41.', {'family_name': 'Иванова', 'first_name': '4-я', 'patronymic': 'Надежда', 'tenure_note_text': 'Михайловна (съ 1 сентября 1900 г.).'},
     {'family_name': 'Иванова 4-я', 'first_name': 'Надежда', 'patronymic': 'Михайловна', 'tenure_note_text': '(съ 1 сентября 1900 г.).'}),
    # Тихоміровъ 1-й, Василій Ивановичъ (Moscow 1899-00): ordinal dropped; the patronymic Ивановичъ IS what is printed
    ('balletartists_1899-00_MSK_p008', '65.', {'family_name': 'Тихоміровъ', 'patronymic': 'Ивановичъ'}, {'family_name': 'Тихоміровъ 1-й'}),
]
# (page, list_number) -> service_periods[0] additions
PERIOD = {('balletartists_1908-09_MSK_p004', '2.'): {'end_date_text': '10 ноября 1908 г.', 'end_type': 'left service'}}

write = '--write' in sys.argv
docs, n = {}, 0
for page, num, cur, new in FIXES:
    d = docs.setdefault(page, json.loads((RAW / f'{page}.raw.json').read_text(encoding='utf-8')))
    hits = [e for e in d['entries'] if e.get('list_number') == num and all(e.get(k) == v for k, v in cur.items())]
    assert len(hits) == 1, (page, num, cur, [(e.get('family_name'), e.get('first_name'), e.get('patronymic')) for e in d['entries'] if e.get('list_number') == num])
    e = hits[0]
    before = {k: e.get(k) for k in new}
    e.update(new)
    if (page, num) in PERIOD:
        assert len(e['service_periods']) == 1 and e['service_periods'][0]['end_date_text'] is None
        e['service_periods'][0].update(PERIOD[(page, num)])
    n += 1
    print(f'{page} {num:5} {before} -> {new}')
print(f'{n} entries on {len(docs)} pages')
if write:
    for page, d in docs.items():
        (RAW / f'{page}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WRITTEN')
