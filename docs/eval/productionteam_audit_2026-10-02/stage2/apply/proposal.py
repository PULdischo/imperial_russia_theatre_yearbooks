import json,re,glob,itertools,sys,collections
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
import stage2_rules as R
log=[];fails=[]
R.run(log,fails)                       # spelling + leak stripping (in memory)
pages=sorted(f.split('/')[-1][:-9] for f in glob.glob(E.R+'productionteam_*.raw.json'))
def num(e):
    m=re.match(r'^(\d+)\.?$',(e.get('list_number') or '').strip()); return int(m.group(1)) if m else None
relabels=[]; prev_last=None
for p in pages:
    es=E.load(p)['entries']; season=p.split('_')[1]
    groups=[]
    for k,g in itertools.groupby(enumerate(es),key=lambda t:(t[1].get('institution'),t[1].get('heading_path'))):
        g=list(g); groups.append(dict(label=k,idx=[i for i,_ in g],nums=[num(e) for _,e in g]))
    for gi,g in enumerate(groups):
        nums=[n for n in g['nums'] if n is not None]
        if not nums: continue
        ref=None
        if gi>0:
            for gj in range(gi-1,-1,-1):
                pn=[n for n in groups[gj]['nums'] if n is not None]
                if pn: ref=groups[gj]; refnum=pn[-1]; break
        elif prev_last and prev_last[0]==season: ref=dict(label=prev_last[1]); refnum=prev_last[2]
        if ref is not None and nums[0]==refnum+1 and ref['label']!=g['label']:
            for i in g['idx']:
                es[i]['institution'],es[i]['heading_path']=ref['label']
            relabels.append((p,g['idx'][0]+1,g['idx'][-1]+1,g['label'],ref['label'])); g['label']=ref['label']
    for g in reversed(groups):
        nn=[n for n in g['nums'] if n is not None]
        if nn: prev_last=(season,g['label'],nn[-1]); break
print(len(log),'text changes;',len(relabels),'Rule-A relabels')
orig={}
for p in pages:
    orig[p]=json.load(open(E.R+p+'.raw.json'))['entries']
prop={}
ch=0
for p in pages:
    es=E.load(p)['entries']; rows=[]
    for i,e in enumerate(es):
        o=orig[p][i]
        d=(o.get('institution'),o.get('heading_path'))!=(e.get('institution'),e.get('heading_path'))
        ch+=d
        rows.append(dict(e='e%03d'%(i+1),list=e.get('list_number'),family=e.get('family_name'),first=e.get('first_name'),patronymic=e.get('patronymic'),inst=e.get('institution'),hp=e.get('heading_path'),old_inst=o.get('institution'),old_hp=o.get('heading_path'),changed=d,tenure=(e.get('tenure_note_text') or '')[:60]))
    prop[p]=rows
print(ch,'rows differ from stored')
json.dump(prop,open('/tmp/audit8/proposal.json','w'),ensure_ascii=False,indent=1)
json.dump(relabels,open('/tmp/audit8/relabels.json','w'),ensure_ascii=False,indent=1)
