import re, json, glob, os, collections, sys, difflib
ROOT='/Users/rachelglodo/Documents/Princeton 2022-present/Dissertation/imperial_russia_theatre_yearbooks-main/'
def norm(s):
    s=(s or '').lower()
    for a,b in (('ѣ','е'),('і','и'),('ѳ','ф'),('θ','ф'),('ъ',''),('ь',''),('й','и'),('ё','е')): s=s.replace(a,b)
    return re.sub(r'[^а-яa-z0-9]','',s)
def parse(path):
    pages={}; cur=None; col=None; sec=None
    for line in open(path,encoding='utf-8'):
        line=line.rstrip('\n')
        m=re.match(r'\s*PAGE (\S+)',line)
        if m: cur=m.group(1); pages[cur]=dict(rows=[],notes=[],school=[]); col=None; sec=None; continue
        if not cur: continue
        s=line.strip()
        m=re.match(r'COLUMN\s+(\w+)',s)
        if m: col=m.group(1); sec='__CARRY__'; continue
        m=re.match(r'SECTION\s+CONTINUED',s)
        if m: sec='__CARRY__'; continue
        m=re.match(r'SECTION\s+"(.*)"',s)
        if m: sec=m.group(1); continue
        if s.startswith('SCHOOL_HEADING_ON_PAGE:'):
            if not re.match(r'SCHOOL_HEADING_ON_PAGE:\s*NONE',s): pages[cur]['school'].append(s)
            continue
        if s.startswith('NOTE:'): pages[cur]['notes'].append(s); continue
        if s.startswith(('CROPS','```')) or not s: continue
        m=re.match(r'(unnumbered|\d+[\.\)]?)\s+(.+)$',s)
        if m and sec is not None:
            pages[cur]['rows'].append(dict(col=col,sec=sec,no=m.group(1).strip('.)'),fam=m.group(2).strip()))
    return pages
def load(prefix):
    d={}
    for f in sorted(glob.glob(f'/tmp/ss/results/{prefix}[0-9].txt')):
        for pg,v in parse(f).items(): d[pg]=v
    return d
def carry(pages_order,P):
    """fill CONTINUED rows with the section in force. Two-column pages: the right column continues the end of the left column,
    EXCEPT on pages with a mid-page school heading: the top block (continuing the previous page, possibly through several sections) ends
    where the Moscow block starts in the left column (its 'Управляющій' heading); the right column's first rows then continue the section in
    force just before that heading."""
    last=None; out={}
    for pg in pages_order:
        if pg not in P: last=None; continue
        rows=P[pg]['rows']; has_school=any(re.search(r'\bafter\b',x) and 'top of page' not in x.lower() for x in P[pg]['school'])
        cur=last; frozen=None; filled=[]; prev_col=None
        for r in rows:
            if r['col']!=prev_col:
                if prev_col is not None and r['col']!='left' and has_school: cur=frozen if frozen is not None else cur
                prev_col=r['col']
            sec=r['sec']
            if sec=='__CARRY__': sec=cur if cur else '__UNKNOWN__'
            else:
                if r['col']=='left' and has_school and frozen is None and norm(sec).startswith('управляющ'): frozen=cur
                cur=sec
            filled.append(dict(r,sec=sec))
        out[pg]=filled; last=cur
    return out
stored={}
for f in sorted(glob.glob(ROOT+'outputs/full_run/raw/theaterschoolstaff_*_p*.raw.json')):
    pg=os.path.basename(f)[:-9]; stored[pg]=json.load(open(f))['entries']
def match(rows,es):
    """match printed rows to stored entries by (family prefix, list no); returns list of (printed, stored_index or None)"""
    used=set(); res=[]
    for r in rows:
        fam=norm(r['fam'])[:5]; cands=[]
        for i,e in enumerate(es):
            if i in used: continue
            if norm(e.get('family_name') or '')[:5]!=fam: continue
            ln=(e.get('list_number') or '').strip('.').strip()
            if r['no']=='unnumbered' and ln: continue
            if r['no']!='unnumbered' and ln and ln!=r['no']: continue
            cands.append(i)
        if cands: used.add(cands[0]); res.append((r,cands[0]))
        else: res.append((r,None))
    return res,[i for i in range(len(es)) if i not in used]
def run(prefix):
    P=load(prefix)
    pages=sorted(stored)
    order=sorted(pages,key=lambda p:(p.split('_')[1],int(p.rsplit('_p',1)[1])))
    C=carry(order,P)
    issues=[]; stats=collections.Counter(); names=[]
    for pg in order:
        if pg not in C: stats['page not read']+=1; continue
        res,unused=match(C[pg],stored[pg])
        for r,i in res:
            if i is None: stats['printed row not found in stored']+=1; issues.append((pg[-12:],'PRINTED ROW NOT IN STORED',r['no'],r['fam'],r['sec'])); continue
            e=stored[pg][i]; segs=[norm(x) for x in (e.get('heading_path') or '').split(' / ')[1:]]
            rf=re.split(r'\s{2,}|\(',r['fam'])[0].strip(); sf=(e.get('family_name') or '').strip()
            clean=lambda x: re.sub(r'\s+','',x.replace('Θ','Ѳ').replace('θ','ѳ').replace('i','і').replace('I','І'))
            if clean(rf).lower()!=clean(sf).lower() and norm(rf)[:4]==norm(sf)[:4]: names.append((pg[-12:],'e%03d'%(i+1),sf,rf))
            if r['sec']=='__UNKNOWN__': stats['no heading known']+=1; continue
            ps=norm(r['sec'])
            ok=any(ps==s or (len(s)>6 and (ps in s or s in ps)) or difflib.SequenceMatcher(None,ps,s).ratio()>=0.8 for s in segs)
            if ok: stats['row ok']+=1
            else: stats['SECTION MISMATCH']+=1; issues.append((pg[-12:],'SECTION MISMATCH','e%03d'%(i+1),r['fam'],'printed:'+r['sec'],'stored:'+' / '.join((e.get('heading_path') or '').split(' / ')[1:])))
        for i in unused:
            e=stored[pg][i]; stats['stored row not found in print']+=1; issues.append((pg[-12:],'STORED ROW NOT IN PRINT','e%03d'%(i+1),e.get('family_name'),e.get('list_number')))
    return stats,issues,P,names
if __name__=='__main__':
    for pref in sys.argv[1:] or ['C','D']:
        st,iss,P,names=run(pref); print('==',pref,'pages read',len(P),dict(st),len(iss),'issues |',len(names),'surname differences vs stored')
        for i in iss[:60]: print('  ',i)
        print('  surname diffs:',names[:40])
