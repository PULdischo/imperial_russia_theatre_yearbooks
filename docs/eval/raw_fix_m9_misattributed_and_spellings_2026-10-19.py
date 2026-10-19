"""M9 scan checks, 2026-10-19 (RG): two leaving notes copied onto the wrong person, and four extraction misreads, all
read on the full-resolution PDF images (zoomed) by Claude after the scan-read agents flagged them.

A. Misattributed notes -- the note is printed under the NEXT entry only, whose own row already carries it:
   productionteam_1902-03_p001 no. 1 Иванова, Евдокія Трофимовна: «Оставила службу 1 августа 1902 г.» belongs to no. 2 Офицерова.
   productionteam_1904-05_p001 no. 1 Неменскій, Исаакъ: «Оставилъ службу 1 апрѣля 1905 г.» belongs to no. 2 Каффи.
   -> the sentence is removed from the person's tenure_note_text and the service period's end date / end type are cleared.
B. Misreads -> the printed form:
   balletartists_1902-03_MSK_p002 no. 39: «Жвирблицъ» -> «Жвирблисъ» (as printed; 1900-01 and 1901-02 also «Жвирблисъ»).
   balletartists_1902-03_SP_p003 no. 60: «Молодова» -> «Мололова» (as printed: a print slip for Мосолова, the row is linked to
     Мосолова, Вѣра Владиміровна); «І декабря» -> «1 декабря»; «Московскімъ» -> «Московскимъ».
   balletartists_1903-04_MSK_p000 no. 5 Балдина: «Московскімъ» -> «Московскимъ».
   balletartists_1897-98_SP_p001 no. 20: «Гельцертъ» -> «Гельцеръ»; «0-Юши» -> «О-Іоши».
   NOT changed: Старженецкій-Лаппа 1896-97 «помошникомъ» -- the scan really prints «помош-никомъ».
Field edits only (entry positions unchanged, person_link unaffected).
usage: uv run python docs/eval/raw_fix_m9_misattributed_and_spellings_2026-10-19.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path

RAW = Path('outputs/full_run/raw')
WRITE = '--write' in sys.argv


def load(page):
    f = RAW / f'{page}.raw.json'
    return f, json.loads(f.read_text(encoding='utf-8'))


def entry(d, n, fam):
    e = d['entries'][n - 1]                      # entry_id numbers are 1-based
    assert e.get('family_name') == fam, (n, e.get('family_name'), fam)
    return e


def replace_all(obj, old, new):
    """Replace a substring in every string value of an entry; returns the number of replacements."""
    n = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and old in v:
                n += v.count(old); obj[k] = v.replace(old, new)
            elif isinstance(v, (dict, list)):
                n += replace_all(v, old, new)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str) and old in v:
                n += v.count(old); obj[i] = v.replace(old, new)
            elif isinstance(v, (dict, list)):
                n += replace_all(v, old, new)
    return n


done = {}
# A. misattributed notes
for page, n, fam, sentence, neighbour in [
        ('productionteam_1902-03_p001', 22, 'Иванова', 'Оставила службу 1 августа 1902 г.', (23, 'Офицерова')),
        ('productionteam_1904-05_p001', 20, 'Неменскій', 'Оставилъ службу 1 апрѣля 1905 г.', (21, 'Каффи'))]:
    f, d = done.get(page) or load(page)
    e = entry(d, n, fam)
    nb = entry(d, *neighbour)
    assert sentence in (nb.get('tenure_note_text') or ''), 'neighbour must keep the note'
    t = e['tenure_note_text']
    assert t.count(sentence) == 1, t
    e['tenure_note_text'] = t.replace(' ' + sentence, '').replace(sentence, '').rstrip()
    sp = e['service_periods']
    assert len(sp) == 1 and sp[0]['end_type'] == 'left service' and sp[0]['end_date_text'] == sentence.split('службу ')[1], sp
    sp[0]['end_date_text'] = None; sp[0]['end_type'] = None
    print(f'{page} no.{n} {fam}: removed «{sentence}» (printed under {neighbour[1]})')
    done[page] = (f, d)

# B. misreads
for page, n, fam, pairs in [
        ('balletartists_1902-03_MSK_p002', 5, 'Жвирблицъ', [('Жвирблицъ', 'Жвирблисъ')]),
        ('balletartists_1902-03_SP_p003', 7, 'Молодова', [('Молодова', 'Мололова'), ('І декабря', '1 декабря'), ('Московскімъ', 'Московскимъ')]),
        ('balletartists_1903-04_MSK_p000', 10, 'Балдина', [('Московскімъ', 'Московскимъ')]),
        ('balletartists_1897-98_SP_p001', 23, 'Гельцертъ', [('Гельцертъ', 'Гельцеръ'), ('0-Юши', 'О-Іоши')])]:
    f, d = done.get(page) or load(page)
    e = entry(d, n, fam)
    for old, new in pairs:
        k = replace_all(e, old, new)
        assert k >= 1, (page, n, old)
        print(f'{page} no.{n}: «{old}» -> «{new}» x{k}')
    done[page] = (f, d)

if WRITE:
    for f, d in done.values():
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{len(done)} pages', '| WRITTEN' if WRITE else '| dry run')
