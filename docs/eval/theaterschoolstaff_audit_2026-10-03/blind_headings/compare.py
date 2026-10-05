import re, json, glob, os, collections, sys
ROOT='/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/'
def norm(s):
    s=(s or '').lower()
    s=re.sub(r'\(?uncertain\)?','',s)
    return re.sub(r'[^а-яѣіѳa-z]','',s)
def parse(path):
    out={}
    cur=None
    for line in open(path,encoding='utf-8'):
        line=line.rstrip('\n')
        m=re.match(r'\s*PAGE (\S+)',line)
        if m: cur=m.group(1); out[cur]=dict(title=None,heads=[],first=None,last=None,notes=[]); continue
        if not cur: continue
        s=line.strip()
        if s.startswith('TITLE_BLOCK:'):
            t=re.search(r'"(.*)"',s); out[cur]['title']=t.group(1) if t else None
        elif s.startswith('SCHOOL_HEADING:'):
            t=re.search(r'"(.*?)"',s)
            if t:
                b=re.search(r'BEFORE:\s*(.*?)\s*\|\s*AFTER:',s); a=re.search(r'AFTER:\s*(.*?)(?:\s*\|\s*COLUMN|$)',s)
                out[cur]['heads'].append(dict(text=t.group(1),before=b.group(1) if b else '',after=a.group(1) if a else ''))
        elif s.startswith('FIRST_ENTRY:'): out[cur]['first']=s
        elif s.startswith('LAST_ENTRY:'): out[cur]['last']=s
        elif s.startswith('NOTE:'): out[cur]['notes'].append(s)
    return out
def load_reader(prefix):
    d={}
    for f in sorted(glob.glob(f'/tmp/tt/results/{prefix}*.txt')):
        for pg,v in parse(f).items(): d[pg]=v
    return d
A=load_reader('A'); B=load_reader('B')
# stored
stored={}
for f in sorted(glob.glob(ROOT+'outputs/full_run/raw/theaterschoolstaff_*_p*.raw.json')):
    pg=os.path.basename(f)[:-9]; es=json.load(open(f))['entries']
    stored[pg]=dict(inst={e.get('institution') for e in es},schools=collections.Counter((e.get('heading_path') or '').split(' / ')[0] for e in es),es=es)
def school_key(s): return 'M' if 'московск' in norm(s) else ('S' if 'петербург' in norm(s) else '?')
def run():
    pages=sorted(stored)
    print('pages stored',len(pages),'| read by A',len(A),'| B',len(B))
    issues=[]
    for pg in pages:
        a,b=A.get(pg),B.get(pg)
        st=stored[pg]
        # A vs B agreement
        if a and b:
            if norm(a['title'] or '')!=norm(b['title'] or ''): issues.append((pg,'A/B TITLE DIFFER',a['title'],b['title']))
            ha=[norm(h['text']) for h in a['heads']]; hb=[norm(h['text']) for h in b['heads']]
            if ha!=hb: issues.append((pg,'A/B HEADINGS DIFFER',[h['text'] for h in a['heads']],[h['text'] for h in b['heads']]))
        for tag,r in (('A',a),('B',b)):
            if not r: continue
            # title vs stored institution (first page only)
            if r['title']:
                for inst in st['inst']:
                    if norm(inst)!=norm(r['title']): issues.append((pg,f'{tag} TITLE != STORED institution',r['title'],inst))
            # headings vs stored schools
            for h in r['heads']:
                k=school_key(h['text'])
                matches=[s for s in st['schools'] if norm(s)==norm(h['text'])]
                if not matches: issues.append((pg,f'{tag} HEADING not among stored school names',h['text'],list(st['schools'])))
            # school set implied by headings on page vs stored
            printed={school_key(h['text']) for h in r['heads']}
            stored_set={school_key(s) for s in st['schools']}
            if printed and not printed<=stored_set: issues.append((pg,f'{tag} printed school(s) absent from stored rows',printed,stored_set))
            if len(stored_set)>1 and not ('M' in printed): issues.append((pg,f'{tag} stored rows of BOTH schools but no Moscow heading printed on page',printed,dict(st['schools'])))
            if 'M' in printed and stored_set=={'S'}: issues.append((pg,f'{tag} Moscow heading printed but no stored Moscow rows',printed,stored_set))
    return issues
if __name__=='__main__':
    iss=run()
    print(len(iss),'issues')
    for i in iss: print(i)

# ---------- continuity check: carry the school forward page by page ----------
def continuity():
    seasons=collections.defaultdict(list)
    for pg in sorted(stored): seasons[pg.split('_')[1]].append(pg)
    out=[]
    for season,pgs in sorted(seasons.items()):
        state=None
        for pg in pgs:
            heads=[]
            for R in (A,B):
                r=R.get(pg)
                if r: heads.append([(school_key(h['text']),h['text']) for h in r['heads']])
            # use the union of what the readers saw (they should agree)
            seen={k for hs in heads for k,_ in hs}
            if 'S' in seen and state is None: state='S'
            exp=set()
            if 'M' in seen:
                if state=='S' or state is None:
                    # rows before the heading are S only if the page prints Petersburg content above it (BEFORE not 'none')
                    r=A.get(pg) or B.get(pg)
                    top=r['heads'][0]['before'].lower().startswith('none') if r and r['heads'] else True
                    exp={'M'} if top else {'S','M'}
                else: exp={'M'}
                state='M'
            elif 'S' in seen: exp={'S'}; state='S'
            else: exp={state} if state else set()
            got={school_key(s) for s in stored[pg]['schools']}
            out.append((season,pg[-4:],''.join(sorted(exp)) or '?',''.join(sorted(got)),dict(stored[pg]['schools']) if exp!=got else None, sorted(heads and heads[0] or [])[:1]))
    return out
if __name__=='__main__' and len(sys.argv)>1 and sys.argv[1]=='continuity':
    bad=[r for r in continuity() if r[4] is not None]
    print('pages where stored school set != expected by continuity:',len(bad))
    for r in bad: print(r[:5])
