"""TheaterSchoolStaff 1898-99 p003 + p004 (48 rows) are the CONTINUATION of the MOSCOW school's list (the Moscow heading is mid-page on p002;
p003/p004 print no school heading) but were stored under the Petersburg school -- found 2026-10-05 by the independent heading re-read
(blind_headings/README.md): the earlier blind sample could not see it because continuation pages print no school heading.
Evidence: every person on those pages appears only under the Moscow school in all other seasons; p003 prints the doctor as
"штатный врачъ при Московскихъ Императорскихъ театрахъ"; 4+ independent readers describe the pages as continuation. Only the first
heading_path segment changes. Dry run unless --write.  usage: uv run python <this> [--write]"""
import json, sys
SPB = 'Императорское С.-Петербургское Театральное Училище'
MOSCOW = 'Императорское Московское Театральное Училище'
R = 'outputs/full_run/raw/theaterschoolstaff_1898-99_p00%d.raw.json'
log, fails, data = [], [], {}
for n in (3, 4):
    d = json.load(open(R % n)); data[n] = d
    for i, e in enumerate(d['entries'], 1):
        hp = e.get('heading_path') or ''
        first, _, rest = hp.partition(' / ')
        if first != SPB: fails.append((n, i, hp)); continue
        e['heading_path'] = MOSCOW + (' / ' + rest if rest else ''); log.append((n, i, e['family_name'], hp, e['heading_path']))
print(len(log), 'rows to change;', len(fails), 'fails')
for f in fails: print('FAIL', f)
for l in log[:3] + log[-2:]: print(' ', l)
if '--write' in sys.argv and not fails:
    import os
    for n, d in data.items():
        json.dump(d, open((R % n) + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=2); os.replace((R % n) + '.tmp', R % n)
    json.dump(log, open(sys.argv[0].rsplit('/', 1)[0] + '/school_fix_1898_99_log.json', 'w'), ensure_ascii=False, indent=1); print('WRITTEN')
