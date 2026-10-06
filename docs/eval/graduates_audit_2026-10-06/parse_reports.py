"""Parse the blind-reader reports into per-page structures and compare with the stored rows (stored_rows.json).
usage: uv run python parse_reports.py   (reads reader_reports/bundle_*.txt)"""
import re, json, glob, collections, sys
D = 'docs/eval/graduates_audit_2026-10-06/'
def clean(s):
    s = re.sub(r'\s{2,}\(.*$', '', s.strip())           # trailing "   (NOTE ...)" remarks
    s = re.sub(r'\s*\((?:NOTE|right|left)[^)]*\)\s*$', '', s)
    return s.strip()
def num(s): return re.sub(r'[^0-9]', '', s)
pages = collections.OrderedDict()
cur = None
for f in sorted(glob.glob(D + 'reader_reports/bundle_*.txt')):
    for line in open(f, encoding='utf-8'):
        line = line.rstrip('\n')
        m = re.match(r'^\s*(?:=== )?PAGE \| (graduates_[0-9-]+_p\d+)', line)
        if m: cur = m.group(1); pages[cur] = dict(rows=[], texts=[], heads=[], src=f.split('/')[-1]); continue
        if cur is None: continue
        t = line.strip()
        if t.startswith('ROW |'):
            parts = [clean(p) for p in t.split(' | ')]
            if len(parts) >= 4:
                pages[cur]['rows'].append(dict(n=num(parts[1]), fam=parts[2], first=parts[3].rstrip('.'), pat=parts[4] if len(parts) > 4 else '-', note=parts[5] if len(parts) > 5 else '-', raw=t))
        elif t.startswith('TEXT |'): pages[cur]['texts'].append(t)
        elif t.startswith('HEADING |'): pages[cur]['heads'].append(t)
json.dump(pages, open(D + 'parsed_reports.json', 'w'), ensure_ascii=False, indent=1)
print(len(pages), 'pages parsed;', sum(len(p['rows']) for p in pages.values()), 'ROW lines;', 'missing vs bundles:', end=' ')
want = [x for k in range(1, 7) for x in json.load(open(D + f'bundles/bundle_{k}.json'))]
print([w for w in want if w not in pages])
