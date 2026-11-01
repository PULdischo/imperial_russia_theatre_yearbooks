"""BalletArtists name leads from the copied-tally sweep, read by Claude on the scans (RG, 2026-11-01: "yes, apply these").
  1901-02 SP p007 no. 29 Кшесинскій 1-й: the extraction shifted the name fields by one -- first_name «Гій» -> «Феликсъ», patronymic
     «Феликсъ» -> «Ивановичъ», and «Ивановичъ » removed from the start of the tenure note (printed «Кшесинскій 1-й, Феликсъ Ивано-
     вичъ (съ 15 января 1853 г.). Солистъ Его Императорскаго Величества.»). Role «Клоцъ Фроло» -> «Клодъ Фроло».
     The person this entry made on its own (a6bf4293) goes to docs/eval/person_merge_candidates_batch.md, not merged here.
  1901-02 SP p007 no. 30 Кщесинскій 2-й (printed with щ, kept): «Бирбантто» -> «Бирбанто», «Маркизантка» -> «Маркитантка»,
     «Инито» -> «Иниго» (text and credit rows).
  Surnames misread (each corrected to its own page; the yearbooks themselves vary between seasons):
     1892-93 MSK p002 no. 47 «Кольева» -> «Копьева»; 1900-01 SP p008 no. 58 «Плесскій» -> «Плессюкъ»;
     1903-04 SP p007 no. 39 and 1904-05 SP p007 no. 39 «Лазукко» -> «Лазуко».
Not changed (print, stored faithfully): 1895-96 SP «Тимомировъ 1-й»; 1901-02 SP «Кщесинскій 2-й»; identical printed tallies of
Гетцманъ and Бакинъ 1-й, MSK 1897-98 and 1899-00. Field edits only; no entry added, removed or moved.
usage: uv run python docs/eval/raw_fix_name_leads_2026-11-01.py [--write]; then rebuild_after_raw_edit.sh"""
import json, sys
from pathlib import Path
RAW = Path('outputs/full_run/raw')
pages = {}
def ent(page, i, fam):
    pid = f'balletartists_{page}'
    if pid not in pages: pages[pid] = json.loads((RAW / f'{pid}.raw.json').read_text(encoding='utf-8'))
    e = pages[pid]['entries'][i - 1]; assert e['family_name'] == fam, (page, i, e['family_name']); return e
def role(e, old, new, field):
    assert e['credit_summary_text'].count(old) == 1, (old, e['credit_summary_text']); e['credit_summary_text'] = e['credit_summary_text'].replace(old, new)
    r = [c for c in e['credits'] if c.get(field) == old]; assert len(r) == 1, (old, field); r[0][field] = new

e = ent('1901-02_SP_p007', 3, 'Кшесинскій 1-й')
assert (e['first_name'], e['patronymic']) == ('Гій', 'Феликсъ') and e['tenure_note_text'].startswith('Ивановичъ (съ 15 января 1853 г.).')
e['first_name'], e['patronymic'] = 'Феликсъ', 'Ивановичъ'
e['tenure_note_text'] = e['tenure_note_text'][len('Ивановичъ '):]
role(e, 'Клоцъ Фроло', 'Клодъ Фроло', 'role_name')
e = ent('1901-02_SP_p007', 4, 'Кщесинскій 2-й')
role(e, 'Бирбантто', 'Бирбанто', 'role_name'); role(e, 'Маркизантка', 'Маркитантка', 'label'); role(e, 'Инито', 'Иниго', 'role_name')
for page, i, old, new in [('1892-93_MSK_p002', 3, 'Кольева', 'Копьева'), ('1900-01_SP_p008', 15, 'Плесскій', 'Плессюкъ'),
                          ('1903-04_SP_p007', 14, 'Лазукко', 'Лазуко'), ('1904-05_SP_p007', 19, 'Лазукко', 'Лазуко')]:
    ent(page, i, old)['family_name'] = new
if '--write' in sys.argv:
    for pid, d in pages.items(): (RAW / f'{pid}.raw.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(pages), 'pages', 'WRITTEN' if '--write' in sys.argv else 'dry run')
