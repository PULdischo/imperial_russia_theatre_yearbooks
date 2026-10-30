"""1908-09 SP BalletArtists p006 (printed p. 94-95): tally copied into the tenure note; three tallies missing from the credits
(RG, 2026-10-30: "yes, go ahead with #1"). Found during the 1908-09 «Всего» read (known_issues.md, same date).

On this page extraction stored every tenure note without its parentheses («съ 1 іюня 1903 г.») and, on 16 entries, followed it
with the whole credit line. The 2026-10-19 duplicate-removal fix (raw_fix_duplicated_credit_in_tenure_2026-10-19.py) missed
them because the copies are not character-identical to credit_summary_text. Read by Claude on the scan (pdf/Spiski_BalletArtists/
ForUpload_1908-09_Spisok_BalletArtistsSP.pdf p. 7 and p. 8, zoomed): every entry prints «(съ … г.).», as on the neighbouring pages.
  T  tenure_note_text of all 22 entries set to the printed «(съ … г.).»; service_periods untouched (already parsed).
  C  Three people whose credit line was ONLY in the tenure note get it as credit_summary_text, as printed (Лопуховъ and
     Новиковъ already had their parsed credits, identical to the print; Обуховъ had none and gets them):
       no. 36 Лопуховъ: «Пробужденіе флоры (Аквилонъ—2). Всего — въ 2 балетахъ—2 раза.» (one ballet listed: print as is)
       no. 45 Новиковъ: «Эсмеральда (цыганка—1). Всего—въ 1 балетѣ—1 разъ.»
       no. 48 Обуховъ: his line runs from the foot of p. 94 to the top of p. 95 (SP p007, above no. 49 Огневъ, where nothing had
         stored it); the whole printed line is stored on his entry, joined at «Спя-|щая», like the column carry-overs whose owner
         holds the full tally. It ends «Всего—въ 7 операхъ—22 раза», «операхъ» for ballets (print slip, kept; genuine_print_typos.md).
  S  Same defect, MSK p003 no. 72 Станиславская: the tenure note also held the first half of her credit line; set to
     «(съ 1 сентября 1902 г.).» (her credit_summary_text already holds the whole line).
Field edits only; no entry added, removed or moved (person_link unaffected).
usage: uv run python docs/eval/raw_fix_1908-09_SP_p006_tenure_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, re, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
TENURE = re.compile(r'^\(?(съ \d+ [^\W\d_]+ \d{4} г\.)')


def credits(cat, n_prod, total, roles):
    return ([{'credit_type': 'category_totals', 'label': cat, 'count': n_prod},
             {'credit_type': 'category_totals', 'label': 'Всего', 'count': total}]
            + [{'credit_type': 'named_work', 'label': w, 'role_name': r, 'count': c} for w, r, c in roles])


ADD = {
    '36.': ('Лопуховъ', 'Пробужденіе флоры (Аквилонъ—2). Всего — въ 2 балетахъ—2 раза.',
            credits('балетахъ', 2, 2, [('Пробужденіе флоры', 'Аквилонъ', 2)])),
    '45.': ('Новиковъ', 'Эсмеральда (цыганка—1). Всего—въ 1 балетѣ—1 разъ.',
            credits('балетѣ', 1, 1, [('Эсмеральда', 'цыганка', 1)])),
    '48.': ('Обуховъ', 'Времена года (Зефиръ—2); Раймонда (Бернаръ-де-Вантадуръ — 3); Аленькій цвѣточекъ (Аленькій цвѣточекъ — 2, '
            'Люцентіо Фабіани—2); Спящая красавица (принцъ Фортюнэ—5); Пробужденіе флоры (Зефиръ — 3); Конекъ - горбунокъ (Мутча—2); '
            'Дочь фараона (рыбакъ—4). Всего—въ 7 операхъ—22 раза.',
            credits('операхъ', 7, 22, [('Времена года', 'Зефиръ', 2), ('Раймонда', 'Бернаръ-де-Вантадуръ', 3),
                                       ('Аленькій цвѣточекъ', 'Аленькій цвѣточекъ', 2), ('Аленькій цвѣточекъ', 'Люцентіо Фабіани', 2),
                                       ('Спящая красавица', 'принцъ Фортюнэ', 5), ('Пробужденіе флоры', 'Зефиръ', 3),
                                       ('Конекъ - горбунокъ', 'Мутча', 2), ('Дочь фараона', 'рыбакъ', 4)])),
}

write = '--write' in sys.argv
f = RAW / 'balletartists_1908-09_SP_p006.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
nt = 0
assert len(d['entries']) == 22
for e in d['entries']:
    old = e['tenure_note_text']; m = TENURE.match(old); assert m, old
    new = f'({m.group(1)}).'
    if new != old:
        e['tenure_note_text'] = new; nt += 1
        print(f"T {e['list_number']} {e['family_name']}: «{old[:70]}» -> «{new}»")
    if e['list_number'] in ADD:
        fam, text, cr = ADD[e['list_number']]
        assert e['family_name'] == fam and not e.get('credit_summary_text'), e['family_name']
        if e.get('credits'):  # Лопуховъ, Новиковъ: the parsed credits were already stored, only the text was missing
            assert e['credits'] == cr, (fam, e['credits'])
        e['credit_summary_text'] = text
        print(f"C {e['list_number']} {fam}: credit_summary_text set" + ('' if e.get('credits') else f' + {len(cr)} credits'))
        e['credits'] = cr
assert nt == 22, nt
if write: f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

f = RAW / 'balletartists_1908-09_MSK_p003.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
e = d['entries'][14]
assert e['family_name'] == 'Станиславская' and e['list_number'] == '72.' and e['tenure_note_text'].startswith('(съ 1 сентября 1902 г.). Донъ')
assert 'Всего—въ 5 балетахъ—23 раза' in e['credit_summary_text']
e['tenure_note_text'] = '(съ 1 сентября 1902 г.).'
print('S 72. Станиславская: tenure note -> «(съ 1 сентября 1902 г.).»')
if write: f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('WRITTEN' if write else 'dry run')
