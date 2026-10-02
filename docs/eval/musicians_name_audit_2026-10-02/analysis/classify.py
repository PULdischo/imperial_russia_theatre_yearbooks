import json,re,collections
r=json.load(open('all_discrepancies.json'))
irr={x[0] for x in json.load(open('map_irregular.json'))}
out=[]
for x in r:
    m=re.search(r'STORED:\s*"([^"]*)"(.*?)\|\s*PRINTED:\s*"([^"]*)"(.*)$',x['rest'])
    st,pr,tail=(m.group(1),m.group(3),m.group(2)+'|'+m.group(4)) if m else (None,None,x['rest'])
    x['stored'],x['printed'],x['tail']=st,pr,tail
    f=x['field']; unc='UNCERTAIN' in x['rest']; pt='PRINT-TYPO' in x['rest']
    cls='other'
    if st and pr:
        if any(ord(c)>0x4ff or (c.isascii() and c.isalpha()) for c in st) : cls='mixed_script'
        elif f=='instrument' and st.lower().replace('и','і').replace('б','в')==pr.lower().replace('и','і') or (f=='instrument' and st in('Виолончель','Біолончель') and pr=='Віолончель'): cls='instr_i'
        elif st[:-1]==pr[:-1] and st[-1] in 'ьъ' and pr[-1] in 'ьъ' : cls='soft_hard'
        elif f=='ordinal': cls='ordinal'
        elif f=='space': cls='space'
    elif f=='ordinal': cls='ordinal'
    if unc: cls='UNCERTAIN_'+cls
    if pt: cls='PRINTTYPO_'+cls
    x['cls']=cls; x['irregular']=x['page'] in irr
    out.append(x)
json.dump(out,open('classified.json','w'),ensure_ascii=False,indent=1)
c=collections.Counter(x['cls'] for x in out); print(c)
print('irregular pages items:',[(x['page'],x['entry']) for x in out if x['irregular']])
