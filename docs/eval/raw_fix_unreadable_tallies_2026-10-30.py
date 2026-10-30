"""BalletArtists: the 10 tally totals unreadable in the stored text and the 5 lines with an odd word for «въ» (RG, 2026-10-30:
"do the 15 scan reads first"). All 15 read by Claude on the scans (pdf/Spiski_BalletArtists, embedded images, zoomed).

Fixed to the print (7 entries):
  1893-94 MSK p004 no. 119 Шейндель  nothing printed under her; stored «Всего—?» -> null (no credit rows were stored)
  1902-03 SP  p001 no. 20  Головкина  nothing but «Оставила службу 1 ноября 1902 г.» (already in her tenure note); «Всего—?» -> null
  1893-94 SP  p003 no. 103 Поллини    «Всего—as 4 балетахъ» -> «Всего—въ 4 балетахъ» (italic въ)
  1894-95 SP  p003 no. 85  Оголейтъ 1-я «Всего—6. 3 балетахъ» -> «Всего—въ 3 балетахъ»
  1902-03 SP  p007 no. 30  Куницкій   «Всего 0—81» -> «Всего—81» (the print spaces «Всег о»; 57+20+4=81)
  1899-00 MSK p001 no. 24  Грачевская 2-я «дивертисементѣ» -> «дивертиссементѣ» (text and label; «дъ 1» IS printed, kept)
  1909-10 SP  p006 no. 17  Гончаровъ 1-й «герольдъ—3» -> «герольдъ—5», «Саракинскій» -> «Сарацинскій» (text and rows; «Съ 6
                                         балетахъ» IS printed, kept); tenure note given its printed opening parenthesis
Stored as printed, no change (8): the prepositions «съ» (1893-94 SP Пащенко 1-й), «дъ» (1899-00 MSK Грачевская 2-я), «Съ»
(1909-10 SP Гончаровъ 1-й), «Вь» (1910-11 MSK Иванова 1-я), «Вд» (1910-11 SP Прохоровъ) are all genuine misprints; Ваганова
(1901-02 SP), Михайлова (1902-03 MSK) and Тихоміровъ 2-й (1903-04 MSK) are the last entry on their page and the line breaks at the
foot after the number; 1910-11 MSK Никитина 1-я prints «Въ 1  балетахъ—34 … Всего— разъ» (digits missing in the print); 1910-11
SP Гончарова prints «Всего—4 | 66 разъ» (a stray 4). Logged in genuine_print_typos.md.
Field edits only; no entry added, removed or moved.
usage: uv run python docs/eval/raw_fix_unreadable_tallies_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
pages = {}
def ent(page, i, fam):
    pid = f'balletartists_{page}'
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    e = pages[pid]['entries'][i - 1]; assert e['family_name'] == fam, (page, i, e['family_name']); return e

def sub(e, old, new, n=1):
    t = e['credit_summary_text']; assert t.count(old) == n, (e['family_name'], old, t); e['credit_summary_text'] = t.replace(old, new)

for page, i, fam in [('1893-94_MSK_p004', 15, 'Шейндель'), ('1902-03_SP_p001', 19, 'Головкина')]:
    e = ent(page, i, fam); assert e['credit_summary_text'] == 'Всего—?' and not e.get('credits'); e['credit_summary_text'] = None

sub(ent('1893-94_SP_p003', 29, 'Поллини'), 'Всего—as 4 балетахъ', 'Всего—въ 4 балетахъ')
sub(ent('1894-95_SP_p003', 11, 'Оголейтъ 1-я'), 'Всего—6. 3 балетахъ', 'Всего—въ 3 балетахъ')
sub(ent('1902-03_SP_p007', 12, 'Куницкій'), 'Всего 0—81', 'Всего—81')

e = ent('1899-00_MSK_p001', 20, 'Грачевская 2-я'); sub(e, 'дивертисементѣ', 'дивертиссементѣ')
lab = [c for c in e['credits'] if c['label'] == 'дивертисементѣ']; assert len(lab) == 1; lab[0]['label'] = 'дивертиссементѣ'

e = ent('1909-10_SP_p006', 14, 'Гончаровъ 1-й')
sub(e, '(герольдъ—3)', '(герольдъ—5)'); sub(e, 'Саракинскій', 'Сарацинскій')
r = [c for c in e['credits'] if c.get('role_name') == 'герольдъ']; assert len(r) == 1 and r[0]['count'] == 3; r[0]['count'] = 5
r = [c for c in e['credits'] if 'Саракинскій' in (c.get('role_name') or '')]; assert len(r) == 1
r[0]['role_name'] = r[0]['role_name'].replace('Саракинскій', 'Сарацинскій')
assert e['tenure_note_text'] == 'съ 1 іюня 1904 г.).'; e['tenure_note_text'] = '(съ 1 іюня 1904 г.).'

if '--write' in sys.argv:
    for pid, d in pages.items(): (RAW / f'{pid}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(pages), 'pages', 'WRITTEN' if '--write' in sys.argv else 'dry run')
