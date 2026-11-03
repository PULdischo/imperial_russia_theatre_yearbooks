"""BalletArtists tally fixes, research-layer review 2026-11-03 (docs/research_layer_review_2026-11-03.md, "P1 follow-up").
Every reading was checked on the scan by Claude; RG approved group A ("yes to these") and asked for the «Своеправная» /
«Ватюшкина» / «Верта» lines to be chased. Edits only `credit_summary_text` and `credits` of the named entries; every old
value is asserted before it is changed, so a second run (or a run on a changed page) stops instead of guessing.
Entry index = position in the page's `entries` array (1-based, = the eNNN of entry_id); no entry is added or removed.

usage: uv run python docs/eval/tally_fixes_2026-11-03/raw_fix_tallies.py --raw-dir <dir> [--write]"""
import argparse, json
from pathlib import Path

BD_LABEL = 'ком. Батюшкина дочка—въ бал. Своенравная жена'   # the label the entries that parsed this line already use

# (page_id, entry index, family_name, [ops])
# ops: ('text', old, new)                       replace in credit_summary_text (old must occur once)
#      ('set_text', old_full, new_full)         replace the whole credit_summary_text
#      ('credit', match, changes)               the one credit whose fields equal `match` gets `changes`
#      ('drop', match)                          remove the one credit equal on `match`
#      ('join', match_a, match_b, new)          replace two adjacent credits (a then b) with one `new` credit
EDITS = [
    # A1: the line runs onto p.120 (1898-99 MSK idx 7), whose top was never stored. 53 + 59 + 3 = 115.
    ('balletartists_1898-99_MSK_p006', 25, 'Ивановъ 5-й', [
        ('set_text', 'Въ 7 балетахъ—53; въ 15 операхъ—59; въ 2 дра',
         'Въ 7 балетахъ—53; въ 15 операхъ—59; въ 2 драмахъ—3. Всего — 115 разъ. Въ томъ числѣ: Корсаръ (4-й корсаръ—4).'),
        ('credit', {'label': 'драмахъ', 'count': None}, {'count': 3}),
        ('credit', {'label': 'Всего', 'count': None}, {'count': 115}),
        ('append', {'credit_type': 'named_work', 'label': 'Корсаръ', 'role_name': '4-й корсаръ', 'count': 4}),
    ]),
    # A2: prints «Въ 2 операхъ—4; въ 1 драмѣ—8. Всего—12 разъ.» -- no ballets; the stored балетахъ item is invented.
    ('balletartists_1893-94_MSK_p007', 1, 'Смоликовъ', [
        ('drop', {'credit_type': 'category_totals', 'label': 'балетахъ', 'count': None}),
    ]),
    # A3 + A4: «ком. Батюшкина дочка—въ бал. Своенравная жена (part—N)» split into two items; joined under one label.
    ('balletartists_1893-94_SP_p001', 24, 'Засѣдателева', [
        ('join', {'label': 'Батюшкина дочка', 'count': None}, {'label': 'Своенравная жена', 'role_name': 'горничная'},
         {'credit_type': 'named_work', 'label': BD_LABEL, 'role_name': 'горничная', 'count': 3}),
    ]),
    ('balletartists_1893-94_SP_p007', 2, 'Маржецкій', [
        ('text', 'Своеправная', 'Своенравная'),
        ('join', {'label': 'ком. Батюшкина дочка', 'count': None}, {'label': 'Своеправная жена', 'role_name': 'поваръ'},
         {'credit_type': 'named_work', 'label': BD_LABEL, 'role_name': 'поваръ', 'count': 3}),
    ]),
    ('balletartists_1893-94_SP_p007', 22, 'Солянниковъ 1-й', [
        ('text', 'Своеправная', 'Своенравная'),
        ('join', {'label': 'ком. Батюшкина дочка', 'count': None}, {'label': 'Своеправная жена', 'role_name': 'графъ'},
         {'credit_type': 'named_work', 'label': BD_LABEL, 'role_name': 'графъ', 'count': 1}),
    ]),
    ('balletartists_1893-94_SP_p007', 27, 'Татариновъ', [
        ('text', 'Своеправная', 'Своенравная'),
        ('join', {'label': 'ком. Батюшкина дочка', 'count': None}, {'label': 'Своеправная жена', 'role_name': 'кастелянъ'},
         {'credit_type': 'named_work', 'label': BD_LABEL, 'role_name': 'кастелянъ', 'count': 3}),
    ]),
    # A4: Макарова 1901-02 SP p.74 no. 58: print «дивер-|тиссементѣ», «Сванильды».
    ('balletartists_1901-02_SP_p002', 19, 'Макарова', [
        ('text', 'дивертисементѣ', 'дивертиссементѣ'),
        ('text', 'Сваннильды', 'Сванильды'),
        ('credit', {'label': 'дивертисементѣ'}, {'label': 'дивертиссементѣ'}),
        ('credit', {'role_name': 'подруга Сваннильды'}, {'role_name': 'подруга Сванильды'}),
    ]),
    # Chased (RG "chase these"): 1893-94 SP p.63, the print reads «Своенравная» in all five; Горскій and Легатъ 1-й also print
    # «Тангейзеръ» and Горскій «скороходъ». Item labels keep their stored shape («Батюшкина дочка», «Тангейзер-»): only letters.
    ('balletartists_1893-94_SP_p006', 8, 'Гавликовскій', [('text', 'Своеправная', 'Своенравная')]),
    ('balletartists_1893-94_SP_p006', 11, 'Горскій', [
        ('text', 'Своеправная', 'Своенравная'), ('text', 'сворождъ', 'скороходъ'), ('text', 'Тангейзерь', 'Тангейзеръ'),
        ('credit', {'role_name': 'сворождъ'}, {'role_name': 'скороходъ'}),
        ('credit', {'label': 'Тангейзерь'}, {'label': 'Тангейзеръ'}),
    ]),
    ('balletartists_1893-94_SP_p006', 21, 'Левинсонъ', [('text', 'Своеправная', 'Своенравная')]),
    ('balletartists_1893-94_SP_p006', 22, 'Легатъ 1-й', [
        ('text', 'Своеправная', 'Своенравная'), ('text', 'Тангейзерь', 'Тангейзеръ'),
        ('credit', {'label': 'Тангейзерь'}, {'label': 'Тангейзеръ'}),
    ]),
    ('balletartists_1893-94_SP_p006', 24, 'Литавкинъ', [('text', 'Своеправная', 'Своенравная')]),
    # Chased: the print has Б in every case («Жизель (Берта—N)», «Батюшкина»), compared with В/Б in the same face on the same
    # page (scan check by a Claude helper, two crops re-read by Claude). Other slips in the same lines: «Уранія», «Жизель» for
    # «Яйзель», «Жертвы Амуру», «Флеръ-де-фаринъ» (lower-case ф as printed).
    *[(pg, i, fam, [('text', 'Верта', 'Берта'), ('credit', {'label': 'Жизель', 'role_name': 'Верта'}, {'role_name': 'Берта'})])
      for pg, i, fam in [('balletartists_1896-97_MSK_p001', 11, 'Горшкова'), ('balletartists_1899-00_SP_p005', 24, 'Чекетти'),
                         ('balletartists_1901-02_MSK_p003', 6, 'Подруцкая'), ('balletartists_1904-05_SP_p005', 19, 'Яковлева 1-я'),
                         ('balletartists_1905-06_SP_p005', 5, 'Яковлева 1-я'), ('balletartists_1907-08_MSK_p004', 22, 'Шаломытова')]],
    ('balletartists_1896-97_MSK_p004', 26, 'Ѳедорова', [
        ('text', 'Верта', 'Берта'), ('text', 'Урания', 'Уранія'),
        ('credit', {'label': 'Жизель', 'role_name': 'Верта'}, {'role_name': 'Берта'}),
        ('credit', {'role_name': 'Урания'}, {'role_name': 'Уранія'}),
    ]),
    ('balletartists_1898-99_MSK_p003', 24, 'Подруцкая', [
        ('text', 'Яйзель (Верта', 'Жизель (Берта'),
        ('credit', {'label': 'Яйзель', 'role_name': 'Верта'}, {'label': 'Жизель', 'role_name': 'Берта'}),
    ]),
    ('balletartists_1894-95_SP_p003', 28, 'Преображенская', [
        ('text', 'Ватюшкина', 'Батюшкина'), ('text', 'Верта', 'Берта'), ('text', 'Жертвамъ', 'Жертвы'),
        ('text', 'Флеръ-де-Фаринъ', 'Флеръ-де-фаринъ'),
        ('credit', {'label': 'ком. Ватюшкина дочка—въ бал. Своенравная жена'}, {'label': BD_LABEL, 'role_name': 'Берта'}),
        ('credit', {'label': 'Жертвамъ Амуру'}, {'label': 'Жертвы Амуру'}),
        ('credit', {'role_name': 'фея Флеръ-де-Фаринъ'}, {'role_name': 'фея Флеръ-де-фаринъ'}),
    ]),
    ('balletartists_1893-94_SP_p000', 19, 'Бастманъ', [('text', 'Ватюшкина', 'Батюшкина')]),
]


def _one(credits, match):
    hits = [i for i, c in enumerate(credits) if all(c.get(k) == v for k, v in match.items())]
    assert len(hits) == 1, (match, hits)
    return hits[0]


def apply(entry, ops):
    t = entry.get('credit_summary_text') or ''
    cr = entry.get('credits') or []
    for op in ops:
        kind = op[0]
        if kind == 'text':
            assert t.count(op[1]) == 1, (op, t)
            t = t.replace(op[1], op[2])
        elif kind == 'set_text':
            assert t == op[1], (op, t)
            t = op[2]
        elif kind == 'credit':
            i = _one(cr, op[1]); cr[i] = {**cr[i], **op[2]}
        elif kind == 'drop':
            i = _one(cr, op[1]); cr.pop(i)
        elif kind == 'join':
            a, b = _one(cr, op[1]), _one(cr, op[2])
            assert b == a + 1, (op, a, b)
            cr[a:b + 1] = [op[3]]
        elif kind == 'append':
            assert op[1] not in cr, op
            cr.append(op[1])
    entry['credit_summary_text'] = t
    entry['credits'] = cr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', required=True, type=Path)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    pages = {}
    for pg, idx, fam, ops in EDITS:
        f = a.raw_dir / f'{pg}.raw.json'
        d = pages.setdefault(f, json.loads(f.read_text(encoding='utf-8')))
        e = d['entries'][idx - 1]
        assert e['family_name'] == fam, (pg, idx, e['family_name'], fam)
        before = (e.get('credit_summary_text'), json.dumps(e.get('credits'), ensure_ascii=False))
        apply(e, ops)
        print(f'{pg}__e{idx:03d} {fam}')
        if before[0] != e['credit_summary_text']:
            print('   text:', e['credit_summary_text'])
        if before[1] != json.dumps(e['credits'], ensure_ascii=False):
            print('   credits:', e['credits'])
    if a.write:
        for f, d in pages.items():
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    print(len(EDITS), 'entries on', len(pages), 'pages', '| WRITTEN' if a.write else '| dry run')


if __name__ == '__main__':
    main()
