import csv, re, sys, duckdb
from collections import Counter
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
rows=list(csv.DictReader(open(sys.argv[1],encoding='utf-8')))
hb={r['block_id'] for r in csv.DictReader(open('docs/eval/review_historical_passages.csv'))}
blk=dict(c.sql(f"select mention_id, block_id from research.review_mention where mention_id in ({','.join(x['mention_id'] for x in rows)})").fetchall())
MAR,MARIA,NAD,LUB,VER='Marius','Марія М.','Надежда М.','Любовь М.','Вѣра М.'
def third(season): return LUB if season<='1900-01' else (VER if season>='1902-03' else None)
CRE=r"(балет\w*|бал\.|постановк\w*|поставлен\w*|балетмейстер\w*|соч\.|сочин\w*|танц(ы|ами)\s+(и\s+постановка\s+)?|возобновлен\w*|либретто|программ\w*|сдѣланн\w*|на сюжетъ|автор\w*|акт\.)"
CRE_AFTER=r"^\s*(,\s*)?(муз|съ музык|и\s+(г\.\s*)?([А-ЯЁ]\.\s*){0,2}(Иванова|Горскаго|Корещенко|Минкуса|Глазунова|Чайковскаго|Дриго)|«|„|\(1-е дѣй|,\s*въ постановк|,\s*солист|\s*и\s+г\.\s*\*)"
HON=r"(г-ж\w*|Г-ж\w*)"
out=[]
for x in rows:
    b=x['before'].replace('-\n','').replace('\n',' '); a=x['after'].replace('\n',' '); a=re.sub(r'^-?\s*па','',a) if x['surface'].replace('\n','').endswith(('Пе-ти','Пети-','Пе-')) else a; s=x['season']
    bs=re.sub(r'(\s*[А-ЯЁIИ]\.)+\s*$','',b)
    m=re.search(r"((?:[А-ЯЁIИ]\.\s*){1,2})$", b); ini=re.sub(r"\s","",m.group(1)) if m else ''
    o=re.match(r"\s*(\d)", a); ordn=o.group(1) if o else ''
    clause=re.split(r"[;—]|\d\)", bs)[-1]
    hon_near = re.search(HON+r"[^;—]{0,50}$", bs) and not re.search(r"\bгг?\.\s*$", bs)
    coauthor = re.search(r"(Минкуса|Сенъ-?\s*Жоржа?|Сень-?\s*Жоржа?|Жоржъ|Пуни|Дриго|Глазунова|Чайковскаго|Иванова|Горскаго|Мазилье|Всеволожскаго)\s*,?\s*(и\s*)?$", bs)
    cre = (re.search(CRE+r"[^;—]{0,70}$", bs) or re.match(CRE_AFTER, a) or coauthor
           or re.search(r"(составлен\w*|фантазі\w*|солистомъ Его Величества)[^;—]{0,30}$", bs))
    fem_ctx = (re.search(HON+r"[^;—]{0,120}$", bs) or re.search(r"(заслуженн\w+ артистк\w*|балерин\w*)[^;—]{0,60}$", bs)
               or re.match(r"^\s*\((?!1-е)", a))
    male = re.search(r"(\bг\.|\bгг\.|г-нъ)\s*$", bs) or re.search(r"\bгг\.[^;—]{0,30}$", bs)
    if x['mention_id']=='9276': lab,who="X pupil «воспитанницы Петипа 1-я» 1897-98 (Любовь?)",None
    elif x['mention_id']=='15568': lab,who="R5 creator wording",MAR  # «pas de trois, М. Петипа … того же балетмейстера» (1901-02 p.205)
    elif blk[int(x['mention_id'])] in hb: lab,who="H0 historical block (ruled: stays unlinked)",None
    elif ini.startswith('М.С') or re.search(r'Сергѣевн\w*\s*$', b): lab,who="H1 «М. С.» = Суровщикова-Петипа, old cast (new)",None
    elif re.search(r"отц\w*\s+и\s+сын|были:\s*$|-\s*отца|отца,", b+a): lab,who="H2 historical wording (new)",None
    elif re.search(r"(18[0-8]\d)\s*(г|год)", b[-120:]): lab,who="Y past-year wording: RG to rule",None
    elif re.search(r"Маріус\w*\s*$", b): lab,who="R1 first name «Маріусъ»",MAR
    elif re.search(r"Марі[ия]\w*\s*$", b): lab,who="R1 first name «Марія»",MARIA
    elif ordn in ('1','2','3'):
        who={'1':MARIA,'2':NAD,'3':third(s)}[ordn]; lab=f"R2 ordinal «{ordn}» + season" if who else "X ordinal 3 in 1901-02 (no 3-я listed)"
    elif ordn: lab,who=f"X ordinal «{ordn}» (no such Петипа on the lists)",None
    elif ini in ('М.И.',): lab,who="R3 initials «М. И.»",MAR
    elif ini.startswith('И') or ini.startswith('I'): lab,who="X initial «И.» (scan check)",None
    elif ini=='М.' and (re.search(r'(балет\w*|бал\.|постановк\w*|соч\.)\s*(«[^»]{1,40}»\s*)?$', bs) or re.match(CRE_AFTER, a)) and not re.search(r'(г-ж\w*|Г-ж\w*)\s+$', bs): lab,who="R5 creator wording",MAR
    elif hon_near and ini=='М.': lab,who="R4 «г-жа/г-жи … М. Петипа»",MARIA
    elif cre and not hon_near: lab,who="R5 creator wording",MAR
    elif male: lab,who="X «г.»/«гг.» Петипа, not in a historical block",None
    elif ini=='М.' and (re.search(r"(исполн\w*|танцовал\w*|исп\.)[^;—]{0,25}$", bs) or re.match(r"^\s*,?\s*заслуженн", a)): lab,who="R6 «М.» + danced/«заслуженная артистка»",MARIA
    elif ini=='М.' and fem_ctx: lab,who="R6 «М.» in a ladies' list / «балерина» / role in brackets",MARIA
    elif hon_near and not ini:
        fem=[p for p,ss in [(MARIA,None),(NAD,('1892-93','1906-07')),(LUB,('1898-99','1900-01')),(VER,('1902-03','1905-06'))] if ss is None or ss[0]<=s<=ss[1]]
        lab,who=("R7 «г-жа Петипа», only Марія listed that season",MARIA) if len(fem)==1 else (f"X «г-жа Петипа», {len(fem)} daughters listed",None)
    else: lab,who="X no rule",None
    out.append((lab,who,x))
for k,v in sorted(Counter(l for l,_,_ in out).items()): print(f"{v:4} {k}")
w=csv.writer(open(sys.argv[2],'w',encoding='utf-8')); w.writerow(['label','proposed','mention_id','season','city','before','surface','after'])
for l,who,x in sorted(out,key=lambda t:(t[0],t[2]['season'])): w.writerow([l,who or '',x['mention_id'],x['season'],x['city'],x['before'][-90:].replace('\n',' '),x['surface'].replace('\n',''),x['after'][:40].replace('\n',' ')])
