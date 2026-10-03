import json,re,glob,itertools,sys
sys.path.insert(0,'/tmp/audit8')
import engine_pt as E
PT='productionteam_'
SPELL=[(r'Отдѣль','Отдѣлъ'),(r'декорационн','декораціонн'),(r'Парижмахер','Парикмахер'),(r'Вутафор','Бутафор'),(r'Ларикмахерск','Парикмахерск'),
       (r'Машиность','Машинистъ'),(r'Помощники машиности','Помощники машиниста'),(r'Экивописецъ','Живописецъ'),(r'Юстюмершъ','Костюмерша'),(r'Гл\.авный','Главный'),
       (r'Гардеробмѣйстерши','Гардеробмейстерши'),(r'Гардеробмейтерши','Гардеробмейстерши'),(r'Мариинскій','Маріинскій'),(r'\bтеатр\b','театръ'),(r'\bтеатр\.','театръ.'),(r'−','-'),(r'И\. обв\.','И. обяз.'),(r'И\. обяв\.','И. обяз.')]
def fix_text(s):
    if not s: return s
    for a,b in SPELL: s=re.sub(a,b,s)
    return s
def norm_surname(s): return re.sub(r'[^а-яѣѳі]','',(s or '').lower().replace('ъ','').replace('ь',''))
def strip_leaks(hp,e):
    if not hp: return hp
    segs=[x.strip() for x in hp.split(' / ')]
    fam=e.get('family_name') or ''; nf=norm_surname(re.sub(r'\d-[йя]','',fam)); ln=(e.get('list_number') or '').strip()
    out=[]
    for sg in segs:
        if re.fullmatch(r'\d+\.?',sg): continue                       # leaked list number
        if '(съ' in sg and re.search(r'[А-ЯЁ][а-яё]+, ',sg): continue  # whole entry text
        if re.match(r'^[А-ЯЁ][а-яёѣѳіъь\-]+, [А-ЯЁ]',sg): continue      # "Surname, First Patronymic"
        if nf and len(nf)>3 and norm_surname(sg)==nf: continue       # row's own surname leaked
        out.append(sg)
    return ' / '.join(out) if out else None
def run(log,fails):
    for f in sorted(glob.glob(E.R+'productionteam_*.raw.json')):
        pg=f.split('/')[-1][:-9]; d=E.load(pg)['entries']
        for i,e in enumerate(d):
            for k in ('institution','heading_path'):
                old=e.get(k); new=fix_text(old)
                if k=='heading_path': new=strip_leaks(new,e)
                if new!=old: e[k]=new; log.append((pg,'e%03d'%(i+1),k,old,new))
if __name__=='__main__':
    log=[];fails=[]; run(log,fails)
    import collections
    print(len(log),'heading/institution value changes on',len({l[0] for l in log}),'pages')
    c=collections.Counter((l[3],l[4]) for l in log)
    for (a,b),n in c.most_common(60): print(n,'|',(a or '')[:70],'=>',(b or '')[:70])
