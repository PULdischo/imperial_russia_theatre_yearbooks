import sys,re,collections,difflib,json
sys.argv=['x']
exec(open('/tmp/ss/compare_sections.py').read().split("if __name__=='__main__':")[0])
def rowres(prefix):
    P=load(prefix); pages=sorted(stored)
    order=sorted(pages,key=lambda p:(p.split('_')[1],int(p.rsplit('_p',1)[1])))
    C=carry(order,P); res={}; notin=collections.defaultdict(list); unused_all={}
    for pg in order:
        if pg not in C: continue
        m,unused=match(C[pg],stored[pg])
        for r,i in m:
            if i is None: notin[pg].append(r); continue
            e=stored[pg][i]; segs=[norm(x) for x in (e.get('heading_path') or '').split(' / ')[1:]]
            if r['sec']=='__UNKNOWN__': res[(pg,i)]=dict(sec=None,ok=None,fam=r['fam']); continue
            ps=norm(r['sec'])
            ok=any(ps==s or (len(s)>6 and (ps in s or s in ps)) or difflib.SequenceMatcher(None,ps,s).ratio()>=0.8 for s in segs)
            res[(pg,i)]=dict(sec=r['sec'],ok=ok,fam=r['fam'])
        unused_all[pg]=unused
    return res,notin,unused_all
RC,NC,UC=rowres('C'); RD,ND,UD=rowres('D')
print('rows compared: C',len(RC),'D',len(RD))
strong=[];single=[];agree=0
for k in sorted(set(RC)|set(RD)):
    c,d=RC.get(k),RD.get(k)
    if c and d and c['ok'] is not None and d['ok'] is not None:
        if c['ok'] and d['ok']: agree+=1
        elif (not c['ok']) and (not d['ok']): strong.append((k,c,d))
        else: single.append((k,c,d))
    elif (c and c['ok'] is False) or (d and d['ok'] is False): single.append((k,c,d))
print('both passes agree with stored section:',agree)
print('BOTH passes disagree with stored (strong candidates):',len(strong))
for (pg,i),c,d in strong[:60]:
    e=stored[pg][i]; print('  ',pg[-12:],'e%03d'%(i+1),e['family_name'],'| C:',c['sec'],'| D:',d['sec'],'| stored:',' / '.join((e.get('heading_path') or '').split(' / ')[1:]))
print('exactly one pass disagrees (single-reader, likely reader artefact):',len(single))
sp=collections.Counter((k[0][-12:]) for k,c,d in single); print('  by page:',dict(sp))
# rows missing in print / stored
def notfound(N,U,tag):
    n=sum(len(v) for v in N.values()); u=sum(len(v) for v in U.values()); print(tag,'printed rows not matched in stored:',n,'| stored rows not matched in print:',u)
notfound(NC,UC,'C'); notfound(ND,UD,'D')
json.dump({'strong':[(k[0],k[1]) for k,_,_ in strong]},open('/tmp/ss/strong.json','w'))
# rows that BOTH passes could not find in stored / stored rows both could not find
both_unused=collections.defaultdict(list)
for pg in UC:
    for i in UC[pg]:
        if i in UD.get(pg,[]): both_unused[pg].append(i)
print('stored rows that NEITHER pass found in the print:',sum(len(v) for v in both_unused.values()))
for pg,v in sorted(both_unused.items()):
    print('  ',pg[-12:],[('e%03d'%(i+1),stored[pg][i]['family_name'],stored[pg][i].get('list_number')) for i in v])

# ---- surnames: both passes read the same spelling and it differs from stored ----
def clean(x):
    x=re.split(r'\s{2,}|\(',x)[0].strip()
    x=x.replace('Θ','Ѳ').replace('θ','ѳ').replace('i','і').replace('I','І')
    return re.sub(r'\s+','',x)
def fam_reads(prefix):
    P=load(prefix); pages=sorted(stored)
    order=sorted(pages,key=lambda p:(p.split('_')[1],int(p.rsplit('_p',1)[1])))
    C=carry(order,P); out={}
    for pg in order:
        if pg not in C: continue
        m,_=match(C[pg],stored[pg])
        for r,i in m:
            if i is not None: out[(pg,i)]=clean(r['fam'])
    return out
FC,FD=fam_reads('C'),fam_reads('D')
both=[];one=[]
for k in sorted(set(FC)|set(FD)):
    e=stored[k[0]][k[1]]; sf=re.sub(r'\s*\d-?[йя]$','',(e.get('family_name') or '').strip()); sf=clean(sf)
    c=re.sub(r'\d-?[йя]$','',FC.get(k,'')) if k in FC else None; d=re.sub(r'\d-?[йя]$','',FD.get(k,'')) if k in FD else None
    ne=lambda a: a is not None and a.lower()!=sf.lower() and norm(a)[:4]==norm(sf)[:4]
    if ne(c) and ne(d) and c.lower()==d.lower(): both.append((k,sf,c))
    elif ne(c) or ne(d): one.append((k,sf,c,d))
print('\nSURNAMES: both passes read the same spelling, differing from stored:',len(both))
for (pg,i),sf,c in both: print('  ',pg[-12:],'e%03d'%(i+1),'stored:',sf,'| both read:',c)
print('SURNAMES: only one pass differs from stored:',len(one))
for (pg,i),sf,c,d in one[:80]: print('  ',pg[-12:],'e%03d'%(i+1),'stored:',sf,'| C:',c,'| D:',d)
