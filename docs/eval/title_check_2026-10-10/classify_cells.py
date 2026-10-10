"""Compare the blind cell readings (reader_reports/cells_*.csv) with the stored works/annotation (cell_worklist_private.csv)."""
import csv,glob,json,re,sys
D='docs/eval/title_check_2026-10-10/'
rd={}
for f in sorted(glob.glob(D+'reader_reports/cells_*.csv')):
    for r in csv.DictReader(open(f,encoding='utf-8')): rd[r['item']]=r
priv={r['item']:r for r in csv.DictReader(open(D+'cell_worklist_private.csv',encoding='utf-8'))}
def norm(s): return re.sub(r'[\s\.,;:\-—–!?«»"\']+','',(s or '').lower().replace('ѣ','е').replace('ь','ъ').replace('і','и').replace('ѳ','ф'))
LINE=re.compile(r'^\s*(?:\d+:\s*)?(.*?)\s*\[([^\]]*)\](?:.*)$',re.S)
def parse_lines(s):
    """-> list of halves; each half a list of (text, genre or None)"""
    halves=[]
    for h in re.split(r'\s*(?:;;|\|\|)\s*',s):
        h=re.sub(r'^(УТРО|ВЕЧЕРЪ|ВЕЧЕР|утро|веч\.?|вечеръ)\s*:\s*','',h.strip())
        items=[]
        for part in re.split(r'\s\|\s',h):
            m=LINE.match(part)
            if m: t,g=m.group(1).strip(),m.group(2).strip(); items.append((t, None if g in ('-','—','') else g))
            else: items.append((part.strip(),None))
        halves.append(items)
    return halves
def get(k):
    p=priv[k]; r=rd[k]
    return p,r,parse_lines(r['lines']),json.loads(p['stored_works'])
if __name__=='__main__':
    ok=[];flag=[]
    for k in priv:
        p,r,halves,works=get(k)
        if p['kind']!='banner_in_works': continue
        why=[]
        if len(halves)>1: why.append('split cell: '+str(len(halves))+' halves')
        lines=[x for h in halves for x in h]
        gl=[x for x in lines if x[1] is None]
        sw=works
        banner_w=[w for w in sw if not w[2]]   # genre-less stored works
        # each genre-less stored work should have a matching genre-less reader line
        for w in banner_w:
            if not any(norm(w[1])==norm(t) or norm(w[1]) in norm(t) or norm(t) in norm(w[1]) for t,g in gl):
                why.append('stored genre-less work %r has no reader line'%w[1][:40])
        # stored titled works should be found among reader lines
        for w in sw:
            if w[2] and not any(norm(w[1].split(',')[0])[:12]==norm(t)[:12] for t,g in lines): why.append('stored work %r not in reader lines'%w[1][:30])
        # reader titled lines not stored
        for t,g in lines:
            if g and not any(norm(w[1].split(',')[0])[:12]==norm(t)[:12] for w in sw): why.append('reader line %r not stored'%t[:30])
        (flag if why else ok).append((k,why))
    print('clean',len(ok),'flagged',len(flag))
    for k,why in flag:
        p,r,halves,works=get(k); print('\n',k,p['event_id'].replace('repertoire_',''),'|',why); print('   stored:',[(w[1][:40],w[2]) for w in works],'ann:',p['stored_annotation'][:60].replace('\n','/')); print('   reader:',r['lines'][:260])
