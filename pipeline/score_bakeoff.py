"""Score the model bake-off against the hand-transcribed gold reviews.

Same metric as docs/eval/selector_2026-09-26.md: gold BODY words misread
(wrong or dropped), figure blocks excluded, dash spacing normalised on both
sides. Also reports ERROR OVERLAP with the incumbent qwen run, which is the
number that decides whether a second model is worth ensembling: resampling
the same view overlaps 95%, a chunked view 54%. Lower is better.
"""
from __future__ import annotations
import difflib, glob, io, os, re, sys

DASH = re.compile(r'\s*([—–-])\s*')
SPAN = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"')
TAG = re.compile(r'</?[a-z][^>]*>')
norm = lambda t: DASH.sub(r'\1', t)

def raw(p):
    return norm(TAG.sub('', " ".join(SPAN.findall(
        io.open(p, encoding='utf-8').read())).replace('\\n', ' ')))

def gold_body(p):
    t = "".join(l for l in io.open(p, encoding='utf-8')
                if not l.startswith('#')).split('[BLOCKS]')[-1]
    keep, drop = [], False
    for line in t.split('\n'):
        m = re.match(r'^\[([^\]]*)\]\s*$', line)
        if m:
            drop = m.group(1).startswith('figure'); continue
        if not drop: keep.append(line)
    return norm(TAG.sub('', re.sub(r'^caption:\s*', '', "\n".join(keep), flags=re.M)))

W = lambda t: re.findall(r'\S+', t)

def project(gold, run):
    out = [''] * len(gold)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            a=gold, b=run, autojunk=False).get_opcodes():
        if tag == 'equal':
            for k in range(i1, i2): out[k] = gold[k]
        elif tag == 'replace':
            blob = " ".join(run[j1:j2])
            for k in range(i1, i2): out[k] = blob
        elif tag == 'delete':
            for k in range(i1, i2): out[k] = ''
    return out

GOLDS = {os.path.basename(p)[3:].replace('.txt', ''): p
         for p in glob.glob('docs/eval/gold_reviews/*.txt')}
PIDS = [p for p in sorted(GOLDS) if '1891-92_SP_ballet_p002' not in p]
RUNS = [('qwen3-vl-plus (incumbent)', 'outputs/reviews/t0_lines_1')] + [
    (m, f'outputs/reviews/bakeoff_{m}')
    for m in ('claude-opus-5', 'claude-sonnet-5', 'claude-fable-5-1')]

errs, tot = {}, 0
for label, d in RUNS:
    if not all(os.path.exists(f'{d}/{p}.raw.json') for p in PIDS):
        print(f'  (skipping {label} — no run at {d})'); continue
    e = set(); n = 0
    for pid in PIDS:
        g = W(gold_body(GOLDS[pid])); n += len(g)
        pr = project(g, W(raw(f'{d}/{pid}.raw.json')))
        e |= {(pid, i) for i in range(len(g)) if pr[i] != g[i]}
    errs[label] = e; tot = n

if not errs:
    sys.exit('No runs found. Run pipeline/bakeoff_reviews.sh first.')

print(f'\n{len(PIDS)} gold pages, {tot} body words\n')
print(f'{"model":30s} {"misread":>8s} {"accuracy":>9s} {"overlap w/ qwen":>16s}')
base = errs.get('qwen3-vl-plus (incumbent)')
for label, e in errs.items():
    ov = (f'{100*len(e & base)/max(min(len(e), len(base)), 1):.0f}%'
          if base and label != 'qwen3-vl-plus (incumbent)' else '—')
    print(f'{label:30s} {len(e):8d} {100*(1-len(e)/tot):8.2f}% {ov:>16s}')

if base and len(errs) > 1:
    union = set().union(*errs.values())
    joint = set.intersection(*errs.values())
    print(f'\noracle over all models: {len(joint)} words no model reads correctly '
          f'({100*(1-len(joint)/tot):.2f}% ceiling)')
    print(f'errors somewhere in the set: {len(union)}')
