"""BalletArtists: performance tallies stored on the wrong person (RG, 2026-10-30: "yes, go ahead" -- read the pairs, then fix).

Found by the carry-over check (docs/query_log.md, 2026-10-30): 76 pairs of entries on the same page with identical stored credit
lines. All 76 pairs were read on the scans; every page where a copy turned up was then transcribed IN FULL by a reader who saw no
stored text (30 pages, 815 entries; 1900-01 SP p000 read in full by Claude), and the readings compared line by line with the
store. Every removal below rests on two independent readings, or on Claude's own reading where only one reader had it.
The extraction gave a person who has NO tally in print the tally of a neighbour (the next or previous entry, or the person level
with them in the next column); on two pages a whole run slipped:
  R  51 entries: nothing printed under the person -> credit_summary_text null, credits [] (their own service notes stay where they
     are stored, in tenure_note_text). Includes the 11 staff entries of 1900-01 SP p000 (ballet masters, régisseurs, assistants,
     the répétiteur, and Аистова, who prints only «Оставила службу 24 февраля 1901 г.»), which held the dancers' tallies from the
     right-hand column row by row.
  M  Run 1893-94 SP p003: Никитина (82) has no tally; Николаева (83), Ниманъ (84), Носкова (85) each held the NEXT person's.
     Moved back one entry; Носкова's «Въ 8 балетахъ—64» -> «Въ 12 балетахъ—64» (printed 12; Claude read the page).
     1900-01 SP p000 no. 2 Александрова 1-я gets her own «Въ 3 балетахъ—9. Всего—9 разъ.» (she held no. 13 Бурмистрова's).
  B  1905-06 MSK p004 no. 2 Бакинъ 2-й: role «свѣтлой» -> «слѣпой» (printed «Эсмеральда (слѣпой—3)»).
  P  Print slips that the extraction had silently corrected, restored as printed (genuine_print_typos.md):
     1907-08 SP p003 no. 68 Николаидисъ «Всего—18 разъ» (18+6=24); 1895-96 MSK p004 Артисты no. 7 Брыкинъ «Всего—56 разъ» (34+31+1=66).
  T  1900-01 SP p000: all 23 tenure notes get their printed parentheses, and the notes the page prints are restored: Петипа
     «Солистъ Его Императорскаго Величества.», Ивановъ «Заслуженный артистъ Императорскихъ театровъ.», Петровъ's secondment to the
     production department, Аистова's «Оставила службу 24 февраля 1901 г.» (+ end of her service period, 'left service').
Field edits only; no entry added, removed or moved (person_link unaffected).
usage: uv run python docs/eval/raw_fix_copied_tallies_2026-10-30.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from collections import Counter
from pathlib import Path

RAW = Path('outputs/full_run/raw')
REMOVE = """1890-91_MSK_p002 16 Доброва|1890-91_MSK_p003 12 Марковская 1-я|1890-91_MSK_p003 20 Нелидова|1890-91_MSK_p003 23 Николаева
|1890-91_MSK_p004 5 Петрова 1-я|1890-91_MSK_p004 8 Полякова 1-я|1890-91_SP_p004 14 Пишо 2-я|1890-91_SP_p006 7 Улина
|1891-92_SP_p002 2 Корсакъ|1891-92_SP_p002 21 Леонова|1891-92_SP_p002 31 Мокшева|1891-92_SP_p004 15 Цвѣткова
|1892-93_MSK_p001 20 Дмитріева 3-я|1892-93_MSK_p006 11 Степановъ|1892-93_SP_p003 9 Ольгина|1893-94_SP_p003 8 Никитина
|1894-95_MSK_p001 8 Берсъ|1894-95_MSK_p005 2 Ѳеоктистова 1-я|1894-95_SP_p005 7 Эрлеръ 2-я|1895-96_MSK_p001 18 Дантесъ 1-я
|1895-96_MSK_p003 11 Петрова 2-я|1895-96_MSK_p003 12 Подруцкая|1895-96_MSK_p003 18 Пѣшкова|1895-96_MSK_p004 5 Тихомирова
|1896-97_MSK_p004 3 Смирнова 2-я|1896-97_MSK_p004 6 Смирягина|1896-97_SP_p001 24 Ермолаева|1897-98_MSK_p002 6 Крылова 2-я
|1898-99_SP_p004 22 Цалисонъ|1899-00_SP_p000 11 Александрова 1-я|1902-03_MSK_p005 1 Бакинъ 1-й|1902-03_SP_p002 6 Исаева
|1903-04_MSK_p002 1 Дьякъ|1903-04_SP_p004 7 Садовская|1903-04_SP_p004 11 Ситникова|1905-06_MSK_p004 23 Бакинъ 1-й
|1906-07_SP_p003 10 Макарова 1-я|1907-08_SP_p003 15 Нижинская|1907-08_SP_p003 19 Ольхина|1907-08_SP_p005 12 Чернышева
|1900-01_SP_p000 1 Петипа|1900-01_SP_p000 2 Ивановъ|1900-01_SP_p000 3 Ширяевъ|1900-01_SP_p000 4 Аистовъ|1900-01_SP_p000 5 Ефимовъ
|1900-01_SP_p000 6 Камышевъ|1900-01_SP_p000 7 Петровъ|1900-01_SP_p000 8 Усачевъ|1900-01_SP_p000 9 Ѳомичевъ
|1900-01_SP_p000 10 Мозеръ|1900-01_SP_p000 11 Аистова"""
REMOVE = [tuple(x.strip().split(' ', 2)) for x in REMOVE.split('|')]
assert len(REMOVE) == 51

pages, done = {}, Counter()
def ent(page, i):
    pid = f'balletartists_{page}'
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    return pages[pid]['entries'][int(i) - 1]

# M: the 1893-94 run, read before anything is cleared
a, b, c, d = (ent('1893-94_SP_p003', i) for i in (8, 9, 10, 11))
assert [x['family_name'] for x in (a, b, c, d)] == ['Никитина', 'Николаева', 'Ниманъ', 'Носкова']
assert c['credit_summary_text'].startswith('Въ 8 балетахъ—64; въ 9 операхъ—30. Всего—94 раза.')
moved = [(b, a), (c, b), (d, c)]  # (receiver, current holder of the receiver's printed tally)
snap = {id(h): (h['credit_summary_text'], json.loads(json.dumps(h['credits']))) for _, h in moved}
for recv, holder in moved:
    recv['credit_summary_text'], recv['credits'] = snap[id(holder)]
    done['M'] += 1
d['credit_summary_text'] = d['credit_summary_text'].replace('Въ 8 балетахъ—64', 'Въ 12 балетахъ—64', 1)

alex = ent('1900-01_SP_p000', 12)
assert alex['family_name'] == 'Александрова 1-я' and 'Всего—72 раза' in alex['credit_summary_text']
alex['credit_summary_text'] = 'Въ 3 балетахъ—9. Всего—9 разъ.'
alex['credits'] = [{'credit_type': 'category_totals', 'label': 'балетахъ', 'count': 9},
                   {'credit_type': 'category_totals', 'label': 'Всего', 'count': 9}]
done['M'] += 1

for page, i, fam in REMOVE:
    e = ent(page, i)
    assert e['family_name'] == fam, (page, i, e['family_name'], fam)
    if (page, i) != ('1893-94_SP_p003', '8'):  # Никитина's stored tally was already handed to Николаева above
        assert e.get('credit_summary_text'), (page, i, fam)
    e['credit_summary_text'] = None; e['credits'] = []; done['R'] += 1

e = ent('1905-06_MSK_p004', 24); assert e['family_name'] == 'Бакинъ 2-й'
e['credit_summary_text'] = e['credit_summary_text'].replace('(свѣтлой—3)', '(слѣпой—3)')
for cr in e['credits']:
    if cr.get('role_name') == 'свѣтлой': cr['role_name'] = 'слѣпой'; done['B'] += 1

for page, i, fam, old, new, n_old, n_new in [('1907-08_SP_p003', 16, 'Николаидисъ', 'Всего—24 раза.', 'Всего—18 разъ.', 24, 18),
                                             ('1895-96_MSK_p004', 31, 'Брыкинъ', 'Всего—66 разъ.', 'Всего—56 разъ.', 66, 56)]:
    e = ent(page, i); assert e['family_name'] == fam and old in e['credit_summary_text'], (fam, e['credit_summary_text'])
    e['credit_summary_text'] = e['credit_summary_text'].replace(old, new)
    tot = [cr for cr in e['credits'] if cr['label'] == 'Всего']; assert len(tot) == 1 and tot[0]['count'] == n_old
    tot[0]['count'] = n_new; done['P'] += 1

NOTES = {1: 'Солистъ Его Императорскаго Величества.', 2: 'Заслуженный артистъ Императорскихъ театровъ.',
         7: 'Прикомандированъ къ монтировочной части для исполненія обязанностей помощника машиниста Маріинскаго театра.',
         11: 'Оставила службу 24 февраля 1901 г.'}
for i, e in enumerate(pages['balletartists_1900-01_SP_p000']['entries'], 1):
    t = e['tenure_note_text']; assert t.startswith('съ ') and '(' not in t, t
    e['tenure_note_text'] = f'({t.rstrip(".")}).' + (f' {NOTES[i]}' if i in NOTES else ''); done['T'] += 1
aist = pages['balletartists_1900-01_SP_p000']['entries'][10]
assert aist['family_name'] == 'Аистова' and aist['service_periods'][0]['end_date_text'] is None
aist['service_periods'][0].update(end_date_text='24 февраля 1901 г.', end_type='left service')

print(dict(done))
assert done == Counter({'R': 51, 'M': 4, 'B': 1, 'P': 2, 'T': 23}), done
if '--write' in sys.argv:
    for pid, dd in pages.items():
        (RAW / f'{pid}.raw.json').write_text(json.dumps(dd, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(pages), 'pages', 'WRITTEN' if '--write' in sys.argv else 'dry run')
