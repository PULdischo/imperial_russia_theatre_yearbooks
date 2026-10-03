import json,re,collections
P=json.load(open('/tmp/audit8/proposal.json'));F=json.load(open('/tmp/audit9/final_chain.json'))
MO=('Большой театръ','Малый театръ','Новый театръ');SP=('Маріинскій театръ','Александринскій театръ','Михайловскій театръ')
def mk(inst):
    if re.search('МОСКВА',inst or '',re.I): return 'M'
    if re.search(r'С\.-?ПЕТЕРБУРГЪ',inst or '',re.I): return 'S'
def th(ch):
    for x in ch.split(' / '):
        if x in MO: return 'M'
        if x in SP: return 'S'
city={};kind={}
for pg in sorted(P):
    rows=P[pg]; n=len(rows)
    ev=[mk(r['inst']) or th(F[pg][r['e']][1]) for r in rows]
    for i,r in enumerate(rows):
        k=(pg,r['e'])
        if ev[i]: city[k]=ev[i]; kind[k]='known'; continue
        prev=next((ev[j] for j in range(i-1,-1,-1) if ev[j]),None)
        nxt=next((ev[j] for j in range(i+1,n) if ev[j]),None)
        if prev and nxt and prev!=nxt: city[k]='S'; kind[k]='content-override'
        else: city[k]=prev or nxt or 'S'; kind[k]='carry'
        if kind[k]=='carry' and 'Парикмахеры /' in F[pg][r['e']][1] and 'Парикмахерскій' not in F[pg][r['e']][1] and not pg.endswith(('_p003','_p004','_p005')): city[k]='S'; kind[k]='content-override'
# consistency vs identical-chain known rows
by=collections.defaultdict(collections.Counter)
for k,c in city.items():
    if kind[k]=='known': by[F[k[0]][k[1]][1]][c]+=1
sus=[]
for k,c in city.items():
    if kind[k]!='known':
        cnt=by.get(F[k[0]][k[1]][1])
        if cnt and cnt[c]==0: sus.append((k[0][14:],k[1],c,dict(cnt),F[k[0]][k[1]][1][:60]))
print(collections.Counter(kind.values()))
for sn in sorted({p.split('_')[1] for p in P}):
    tr=[];pv=None
    for pg in sorted(P):
        if pg.split('_')[1]!=sn: continue
        for r in P[pg]:
            c=city[(pg,r['e'])]
            if c!=pv: tr.append(pg[-4:]+':'+r['e']+'>'+c); pv=c
    print(sn,' '.join(tr))
print(len(sus),'carry rows disagreeing with identical-chain known rows')
for s in sus: print(s)
json.dump({f'{k[0]}|{k[1]}':'МОСКВА' if v=='M' else 'С.-ПЕТЕРБУРГЪ' for k,v in city.items()},open('/tmp/audit9/city.json','w'),ensure_ascii=False)
