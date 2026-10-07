"""Parse the blind-reader reports (reader_reports/bundle_NN.txt) into per-page structures (parsed_reports.json): rows with verbatim text + parsed fields,
and the heading stack in force for each row (H0..H3). uv run python parse_reports.py"""
import re, glob, json, collections
D = 'docs/eval/administrators_audit_2026-10-07/'
pages = collections.OrderedDict(); cur = None; stack = {}
def clean(s): return re.sub(r'\s+', ' ', s.strip())
for f in sorted(glob.glob(D + 'reader_reports/bundle_*.txt')):
    for line in open(f, encoding='utf-8'):
        t = line.rstrip('\n').strip()
        m = re.match(r'^PAGE \| (administration_[0-9-]+_p\d+) \|(.*)$', t)
        if m: cur = m.group(1); pages[cur] = dict(rows=[], heads=[], notes=[], texts=[], page_line=t, src=f.split('/')[-1]); stack = {}; continue
        if cur is None: continue
        m = re.match(r'^HEAD H(\d) \| (.*?)(?: \| (.*))?$', t)
        if m:
            lv = int(m.group(1)); stack = {k: v for k, v in stack.items() if k < lv}; stack[lv] = clean(m.group(2))
            pages[cur]['heads'].append((lv, clean(m.group(2)), clean(m.group(3) or ''))); continue
        if t.startswith('ROW |'):
            p = [clean(x) for x in t.split(' | ')]
            p += [''] * (9 - len(p))
            pages[cur]['rows'].append(dict(n=p[1], verbatim=p[2], fam=p[3], title=p[4], first=p[5], pat=p[6], rank=p[7], note=' | '.join(p[8:]), stack=dict(stack), raw=t))
        elif t.startswith('TEXT |'): pages[cur]['texts'].append(t)
        elif t.startswith('NOTE'): pages[cur]['notes'].append(t)
json.dump(pages, open(D + 'parsed_reports.json', 'w'), ensure_ascii=False, indent=1)
want = [x for f in sorted(glob.glob(D + 'bundles/bundle_*.json')) for x in json.load(open(f))]
print(len(pages), 'pages parsed;', sum(len(p['rows']) for p in pages.values()), 'ROW lines; missing:', [w[15:] for w in want if w not in pages])
