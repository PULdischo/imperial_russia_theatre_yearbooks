import pandas as pd,random
v=pd.read_pickle('/private/tmp/claude-502/x/var.pkl'); d=pd.read_pickle('/private/tmp/claude-502/x/d2.pkl')
d=d.reset_index(drop=True)
idx={e:i for i,e in enumerate(d.entry_id)}
def near(i,col,val,k=3):
    pg=d.page_id[i]; me=d.person_id[i]
    for j in range(max(0,i-k),min(len(d),i+k+1)):
        if j!=i and d.page_id[j]==pg and d.person_id[j]!=me and d[col][j]==val and val!='': return True
    return False
def pagewide(i,col,val):
    pg=d.page_id[i]; me=d.person_id[i]
    g=d[(d.page_id==pg)&(d.person_id!=me)]
    return (g[col]==val).any() and val!=''
sub=v[v.grade.isin(['sub_letter','sub_whole'])].copy()
cm={'fam':'nf','fn':'nn','pat':'np'}
res=[]
for _,r in sub.iterrows():
    i=idx[r.entry_new]; hits=[]; pw=[]
    for f in ('fam','fn','pat'):
        if r[f] in('sub_letter','sub_whole'):
            hits.append(near(i,cm[f],d[cm[f]][i])); pw.append(pagewide(i,cm[f],d[cm[f]][i]))
    res.append((any(hits),any(pw)))
sub['near3']=[a for a,b in res]; sub['pagewide']=[b for a,b in res]
print(sub.near3.mean(),sub.pagewide.mean(),len(sub))
# baseline
random.seed(0); out={}
for f,col in (('fam','nf'),('fn','nn'),('pat','np')):
    sm=[i for i in random.sample(range(len(d)),3000) if d[col][i]!='']
    out[f]=(sum(near(i,col,d[col][i]) for i in sm)/len(sm), sum(pagewide(i,col,d[col][i]) for i in sm)/len(sm))
print(out)
# per-field observed
for f in ('fam','fn','pat'):
    m=sub[sub[f].isin(['sub_letter','sub_whole'])]
    rr=[(near(idx[e],cm[f],d[cm[f]][idx[e]]),pagewide(idx[e],cm[f],d[cm[f]][idx[e]])) for e in m.entry_new]
    print(f,len(m),sum(a for a,b in rr)/len(m),sum(b for a,b in rr)/len(m))
sub.to_pickle('/private/tmp/claude-502/x/sub.pkl')
