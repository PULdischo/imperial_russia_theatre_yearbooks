"""«перемоніймейстеръ» -> «церемоніймейстеръ» on the 10 BalletArtists entries that still carried the misread (RG, 2026-10-19:
"address this"). All 10 read on the full-resolution PDF images, zoomed (a read-only agent; 1891-92, 1899-00 and 1904-05 re-read
by Claude): the print has Ц (descender visible) every time, as on the 47 other entries already stored «церемоніймейстеръ»
(and Ширяевъ 1903-04, fixed earlier today). Also, Булгаковъ 1891-92: «начальникъ альгван-лӧвъ» -> «альгвазиловъ» (print
«альгвази-|ловъ», as stored for 1892-93).
1904-05 MSK p005 no. 8 Брыкинъ: the print is damaged («цер·мовій-мей-стеръ»: a broken second е and an н that looks like в);
only the certain п -> ц is corrected, the rest kept as stored.
Applies to every string field of the entry (tenure note, credit line, credits' role names). Field edit only.
Other misreads seen in the same tally lines (Шелякуничъ, пыгать, Копекъ, тью-хранитель ...) are NOT touched here.
usage: uv run python docs/eval/raw_fix_ceremoniymeyster_2026-10-19.py [--write]; then docs/eval/rebuild_after_raw_edit.sh"""
import collections, json, sys
from pathlib import Path
import duckdb

RAW = Path('outputs/full_run/raw')
con = duckdb.connect('outputs/full_run/imperial_theaters.duckdb', read_only=True)
eids = [r[0] for r in con.execute("""SELECT DISTINCT entry_id FROM raw.person_entry_credit
                                     WHERE role_name LIKE '%перемоні%' ORDER BY 1""").fetchall()]
con.close()
assert len(eids) == 10, eids


def fix(obj, old, new):
    n = 0
    for k, v in list(obj.items() if isinstance(obj, dict) else enumerate(obj)):
        if isinstance(v, str) and old in v:
            n += v.count(old); obj[k] = v.replace(old, new)
        elif isinstance(v, (dict, list)):
            n += fix(v, old, new)
    return n


pages = collections.defaultdict(list)
for e in eids:
    page, i = e.rsplit('__e', 1); pages[page].append((int(i), e))
total = 0
for page, items in sorted(pages.items()):
    f = RAW / f'{page}.raw.json'; d = json.loads(f.read_text(encoding='utf-8'))
    for i, e in items:
        ent = d['entries'][i - 1]                       # 1-based entry ids
        n = fix(ent, 'перемоні', 'церемоні')
        assert n >= 1, e
        if e == 'balletartists_1891-92_SP_p005__e002':
            m = fix(ent, 'альгван-лӧвъ', 'альгвазиловъ'); assert m >= 1, m; n += m
        print(f'{e:42} {ent.get("family_name")!s:18} {n} replacement(s)'); total += n
    if '--write' in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{total} replacements on {len(eids)} entries', '| WRITTEN' if '--write' in sys.argv else '| dry run')
