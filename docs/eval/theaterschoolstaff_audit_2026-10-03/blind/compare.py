import json,re,glob,collections
items=json.load(open('/tmp/tss/blind/items.json'))
prop={(pg,e,f):new for pg,e,f,old,new in items}
oldv={(pg,e,f):old for pg,e,f,old,new in items}
read={}
for f in sorted(glob.glob('/tmp/tss/blind/results_b*.txt')):
    for l in open(f,encoding='utf-8'):
        m=re.match(r'^(theaterschoolstaff_\S+)\s*\|\s*(e\d+)\s*\|\s*(\w+)\s*\|\s*PRINTED:\s*"([^"]*)"\s*\|\s*confidence\s*(\w+)',l)
        if m: read[(m.group(1),m.group(2),m.group(3))]=(m.group(4),m.group(5),l.strip())
agree=dis=unc=0; missing=[]; bad=[]
for k,new in prop.items():
    if k not in read: missing.append(k); continue
    pr,conf,line=read[k]
    if pr==new: agree+=1 if conf=='DIRECT' else 0; unc+= conf!='DIRECT'
    else: dis+=1; bad.append((k,oldv[k],new,pr,conf))
print('proposed',len(prop),'| read',len(read),'| agree',agree,'| UNCERTAIN-but-equal',unc,'| DISAGREE',dis,'| not yet read',len(missing))
for b in bad: print('DISAGREE',b)
