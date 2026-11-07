import duckdb, re, csv, sys
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
rows=c.sql("""select m.mention_id, m.season, m.city, m.block_id, m.char_start, m.char_end, m.surface, e.evidence,
  coalesce(b.text,'') t, coalesce(b.caption_text,'') ct, b.block_type
  from research.review_mention m join entities.review_mention e on e.mention_id=m.mention_id join raw.review_block b on b.block_id=m.block_id
  where m.mention_type='person' and m.surface ilike 'Петипа%' and m.person_id is null""").fetchall()
def ctx(r):
    mid,s,city,bid,a,z,surf,ev,t,ct,bt=r
    best=None
    for src in (t, ct):
        for m in re.finditer(r"П\s*е", src):
            d=abs(m.start()-a)
            if d<=40 and (best is None or d<best[0]): best=(d,src,m.start())
    if best is None: return "","",""
    _,src,a2=best; z2=a2+(z-a)
    return src[max(0,a2-90):a2], src[a2:z2], src[z2:z2+40]
CREATOR=r"(балет[ъа]?|бал\.|постановк\w*|поставлен\w*|балетмейстер\w*|сочинен\w*|соч\.|танцами|компоновк\w*|возобновлен\w*|программ\w*|либретто|по\s+сюжету)\s+(\w+\s+){0,2}$"
out=[]
for r in rows:
    pre,hit,post=ctx(r); p=pre.replace('\n',' '); P=post.replace('\n',' ')
    ordm=re.match(r"\s*(\d)", P); ordn=ordm.group(1) if ordm else None
    rule=None
    if re.search(r"Маріус\w*\s*$|Маріус\w*\s+Пе-?\s*$", p): rule="A first name Маріус-"
    elif re.search(r"(г-ж\w*|Г-ж\w*|балерин\w*|артистк\w*)\s+М\.\s*$", p): rule="B honorific/fem + М. -> Марія"
    elif re.search(r"(г-ж\w*|Г-ж\w*)\s*$", p) and ordn: rule=f"C г-жа + ordinal {ordn}"
    elif re.search(r"М\.\s*$", p) and re.search(CREATOR, p.rstrip()[:-2].rstrip()+' ', re.I): rule="D creator word + М. -> Marius"
    elif re.search(r"М\.\s*$", p) and re.match(r"\s*\(", P): rule="E М. + (role) -> dancer Марія"
    elif re.search(r"М\.\s*$", p): rule="F М. other"
    elif re.search(r"(г-ж\w*|Г-ж\w*)\s*$", p): rule="G г-жа, no ordinal"
    elif re.search(r"\bг\.\s*$|\bгг\.", p): rule="H г./гг."
    else: rule="Z other"
    out.append((rule, r[0], r[1], r[2], ordn, p[-70:], hit, P[:30]))
out.sort()
w=csv.writer(open(sys.argv[1],'w',encoding='utf-8')); w.writerow(['rule','mention_id','season','city','ordinal','before','surface','after']); w.writerows(out)
from collections import Counter
for k,v in sorted(Counter(o[0] for o in out).items()): print(v, k)
