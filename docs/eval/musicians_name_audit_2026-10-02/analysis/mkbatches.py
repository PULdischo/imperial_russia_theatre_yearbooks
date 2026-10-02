import json,random,collections,re
random.seed(20261002)
allx=json.load(open('classified.json'))
full=[x for x in allx if x['cls'] not in('mixed_script','soft_hard','instr_i')]
sh=[x for x in allx if x['cls']=='soft_hard']; ii=[x for x in allx if x['cls']=='instr_i']
samp=random.sample(sh,18)+random.sample(ii,12)
for x in samp: x['sample']=True
json.dump([[x['page'],x['entry'],x['field']] for x in samp],open('/tmp/audit4/sample_ids.json','w'))
items=full+samp
byp=collections.defaultdict(list)
for x in items: byp[x['page']].append(x)
def bundle_line(p,e):
    for l in open(f'/tmp/audit4/{p}.txt',encoding='utf-8'):
        if l.startswith(e+' |'): return l.strip()
    return '?'
pages=sorted(byp)
batches=[];cur=[];n=0
for p in pages:
    k=len(byp[p])
    if cur and n+k>30: batches.append(cur);cur=[];n=0
    cur.append(p);n+=k
if cur: batches.append(cur)
key={}
for bi,ps in enumerate(batches,1):
    L=[f'# VERIFICATION batch {bi}  ({sum(len(byp[p]) for p in ps)} items on {len(ps)} pages)\n']
    for p in ps:
        L.append(f'\n## PAGE {p}   scan: outputs/roster_images_full/images/{p}.png   stored-row bundle: /tmp/audit4/{p}.txt')
        for x in sorted(byp[p],key=lambda x:(x['entry'],x['field'])):
            iid=f"{p}|{x['entry']}|{x['field']}"
            if x['stored'] is None:
                opts=None
            else:
                pair=[('S',x['stored']),('R',x['printed'])]; random.shuffle(pair)
                key[iid]={'A':pair[0][0],'B':pair[1][0]}
            L.append(f"\nITEM {iid}")
            L.append('  stored row: '+bundle_line(p,x['entry']))
            L.append(f"  field in question: {x['field']}")
            if x['stored'] is None:
                L.append('  (free-form item) first reviewer note: '+x['rest'][:300])
            else:
                L.append(f'  Option A: "{pair[0][1]}"')
                L.append(f'  Option B: "{pair[1][1]}"')
    open(f'/tmp/audit5/batch{bi}.txt','w',encoding='utf-8').write('\n'.join(L)+'\n')
json.dump(key,open('ab_key.json','w'),ensure_ascii=False)
print(len(batches),'batches',[sum(len(byp[p]) for p in ps) for ps in batches])
print(sum(1 for x in items if x['stored'] is None),'free-form items')
