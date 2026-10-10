"""Compare the first read (first_read/A–H) with the blind second read (V1–V5), heading by heading.

Writes build/reading_comparison.csv: one row per entry with both name readings and a status
(same / differs / first_only / second_only). Names are compared after stripping punctuation,
case and spacing only -- never orthography.
"""
import csv, glob, os, re, difflib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

def section(s):
    s = os.path.basename(s)
    s = re.sub(r'\.(png|pdf)$', '', s); s = re.sub(r'_p\d+.*$', '', s)
    return re.sub(r'^\d{4}_Vol_[IVX-]+__', '', s)

def norm(n):
    n = re.sub(r'\[\?\]', '', n)
    return re.sub(r'[^\w]+', '', n, flags=re.U).lower()

def toks(n):
    n = re.sub(r'\[[^\]]*\]', ' ', n)
    return sorted(t.lower() for t in re.findall(r'\w+', n, flags=re.U))

first = {}
for f in sorted(glob.glob(ROOT + '/first_read/[A-H]*.csv')):
    for r in csv.reader(open(f, encoding='utf-8')):
        if r[0] == 'season': continue
        if len(r) == 18: r = r[:11] + r[12:]            # G: heading row has one stray cell
        d = dict(zip(['season','source_file','pdf_page','printed_page','kind','name','name_latin','role','troupe_city','dates','length','relevance'], r))
        if d['kind'] in ('section_heading_only', 'other') or 'Miscellaneous' in d['source_file'] or 'Feature' in d['source_file'] or 'Endpages' in d['source_file']: continue
        first.setdefault(section(d['source_file']), []).append(d)
second = {}
for f in sorted(glob.glob(ROOT + '/blind_second_read/V*.csv')):
    for d in csv.DictReader(open(f, encoding='utf-8')):
        second.setdefault(section(d['image_file']), []).append(d)

out = []
for sec in sorted(set(first) | set(second)):
    A = first.get(sec, []); B = list(second.get(sec, [])); used = set()
    for a in A:
        best, bi = 0, None
        for i, b in enumerate(B):
            if i in used: continue
            s = max(difflib.SequenceMatcher(None, norm(a['name']), norm(b['name_verbatim'])).ratio(),
                    difflib.SequenceMatcher(None, ''.join(toks(a['name'])), ''.join(toks(b['name_verbatim']))).ratio())
            if s > best: best, bi = s, i
        if bi is not None and best >= 0.6:
            used.add(bi); b = B[bi]
            st = 'same' if norm(a['name']) == norm(b['name_verbatim']) else ('same_reordered' if toks(a['name']) == toks(b['name_verbatim']) else 'differs')
            out.append([sec, a['printed_page'], b['printed_page'], st, a['relevance'], a['name'], b['name_verbatim'], a['dates'], b['date_verbatim']])
        else:
            out.append([sec, a['printed_page'], '', 'first_only', a['relevance'], a['name'], '', a['dates'], ''])
    for i, b in enumerate(B):
        if i not in used:
            out.append([sec, '', b['printed_page'], 'second_only', '', '', b['name_verbatim'], '', b['date_verbatim']])
with open(HERE + '/reading_comparison.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['section','page_first','page_second','status','relevance','name_first','name_second','dates_first','date_second']); w.writerows(out)
import collections
print(collections.Counter(r[3] for r in out))
for r in out:
    if r[3] not in ('same', 'same_reordered'): print(' | '.join(r[:7]))
