"""Propose minimal per-field edits for the STORED_WRONG items (verifier V == first read R1 != stored S), plus the manual rulings below.
Token alignment of the stored fields (family_name, first_name, patronymic, rank_or_title, tenure_note_text) against the verifier's printed entry; substitutions keep the stored
punctuation; trailing printed lines are appended to tenure_note_text. -> proposals.json (reviewed before apply_fixes.py)."""
import json, re, difflib, collections
D = 'docs/eval/administrators_audit_2026-10-07/'
A = json.load(open(D + 'adjudication.json'))
RAW = 'outputs/full_run/raw/'
import sys; sys.path.insert(0, D); from adm_common import kept
FIELDS = ['family_name', 'first_name', 'patronymic', 'rank_or_title', 'tenure_note_text']
TITLES = {'князь', 'княгиня', 'графъ', 'графиня', 'баронъ', 'баронесса', 'принцъ', 'свѣтлѣйшій'}
def core(t): return re.sub(r'[^\wѣіѳѵ]', '', t.lower())
def split_tokens(s): return [t for t in re.split(r'\s+', (s or '').strip()) if core(t)]
def clean_v(v): return re.sub(r'^\s*\d+[.)]\s*', '', v or '').strip()
# manual rulings (RG-rule: worn/damaged type keeps the intended letter; print variants noted): item -> 'SKIP' or explicit field edits
MANUAL = {
 'V1.39': {'family_name': ('Млюдзѣевскій', 'Млодзѣевскій'), 'patronymic': None, '_rank_remove': True},   # handled specially below
}
SKIP = {'V5.11', 'V5.12', 'V5.23', 'V5.22', 'V5.45', 'V7.23', 'V4.9', 'V7.9', 'V2.2', 'V3.40', 'V6.21', 'V7.33', 'V5.39'}   # worn/damaged print or non-person or duplicate (reviewed by hand)
props = {}; unhandled = []
for iid, r in A.items():
    if r['verdict'] not in ('STORED_WRONG',) and iid not in ('V1.39', 'V3.27', 'V3.39'): continue
    if iid in SKIP: continue
    it = r['item']; eid = it['entry_id']
    if not eid: unhandled.append((iid, 'no stored entry (READ_ONLY pair)')); continue
    pg, n = eid.rsplit('__e', 1); n = int(n)
    _ents = json.load(open(RAW + pg + '.raw.json'))['entries']; raw = _ents[dict(kept(_ents))[n]]
    vtxt = clean_v(r['verifier'])
    # stored token stream with field tags
    st = []
    for f in FIELDS:
        for t in split_tokens(raw.get(f)): 
            if core(t) in TITLES: continue
            st.append((f, t))
    vt = [t for t in split_tokens(vtxt) if core(t) not in TITLES]
    sm = difflib.SequenceMatcher(None, [core(t) for _, t in st], [core(t) for t in vt], autojunk=False)
    edits = collections.OrderedDict(); ok = True; append_text = None
    for tg, i1, i2, j1, j2 in sm.get_opcodes():
        if tg == 'equal': continue
        if tg == 'replace' and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1):
                f, old = st[i1 + k]; new_core = re.sub(r'^[^\wѣіѳѵ]*|[^\wѣіѳѵ]*$', '', vt[j1 + k])
                lead = re.match(r'^[^\wѣіѳѵ]*', old).group(0); trail = re.search(r'[^\wѣіѳѵ]*$', old).group(0)
                edits.setdefault(f, []).append(('sub', old, lead + new_core + trail))
        elif tg == 'insert' and i1 == len(st):                                  # trailing printed text
            # locate the char offset in the verifier text where the extra tokens start
            pos = 0; idx = 0
            for m in re.finditer(r'\S+', vtxt):
                if core(m.group(0)) and idx == j1 + (len([1 for t in re.split(r'\s+', vtxt) if core(t) in TITLES and False])): pos = m.start(); break
                if core(m.group(0)): idx += 1
            append_text = ' '.join(vt[j1:j2])
            edits.setdefault('tenure_note_text', []).append(('append', None, ' '.join(vt[j1:j2])))
        elif tg == 'delete':
            for k in range(i1, i2):
                f, old = st[k]; edits.setdefault(f, []).append(('del', old, None))
        else:
            ok = False
    props[iid] = dict(item=iid, entry_id=eid, page=pg, n=n, kinds=it['kinds'], stored={f: raw.get(f) for f in FIELDS}, verifier=vtxt, edits=edits, auto=ok, conf=r['conf'])
    if not ok: unhandled.append((iid, 'complex alignment'))
json.dump(props, open(D + 'proposals.json', 'w'), ensure_ascii=False, indent=1)
c = collections.Counter(); 
for p in props.values():
    for f, es in p['edits'].items():
        for e in es: c[(f, e[0])] += 1
print(len(props), 'proposals;', sum(1 for p in props.values() if p['auto']), 'auto;', 'unhandled', len(unhandled)); print(dict(c))
for u in unhandled[:40]: print('  UNHANDLED', u)
