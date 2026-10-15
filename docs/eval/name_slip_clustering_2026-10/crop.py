import pandas as pd,pymupdf,duckdb,io,random
from PIL import Image
sub=pd.read_pickle('/private/tmp/claude-502/x/sub2.pkl'); d=pd.read_pickle('/private/tmp/claude-502/x/d2.pkl')
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
sp=c.execute("select page_id,entity_type,season,source_file,source_page_index from raw.source_pages").df().set_index('page_id')
npg=d.groupby('page_id').pos.max()
dirs={'BalletArtists':'Spiski_BalletArtists','Musicians':'Spiski_Musicians','ProductionTeam':'Spiski_ProductionTeam','Administrators':'Spiski_Administration','TheaterSchoolStaff':'Spiski_TheaterSchoolStaff','Graduates':'Spiski_Graduates'}
rs=sub[~sub.same_season & sub['list'].isin(['BalletArtists','Musicians','ProductionTeam'])]
random.seed(7)
sel=[]
for k,n in (('surname (1-2 letters)',7),('first name (1-2 letters)',2),('patronymic (1-2 letters)',2),('patronymic (different)',2),('surname (different)',1)):
    g=rs[rs.kind==k]; sel+=g.sample(n,random_state=11).index.tolist()
out=[]
def crop(pid,entry,tag):
    r=sp.loc[pid]; path=f"pdf/{dirs[r.entity_type]}/{r.source_file}"
    doc=pymupdf.open(path); pg=doc[int(r.source_page_index)]
    imgs=pg.get_images()
    xref=imgs[0][0]; im=Image.open(io.BytesIO(doc.extract_image(xref)['image'])).convert('L')
    pos=int(entry.split('__e')[1]); n=max(npg[pid],1)
    W,H=im.size
    # table body roughly 8%-95% height
    y=0.08*H+(pos-0.5)/n*0.87*H
    box=(0,int(max(0,y-0.045*H)),W,int(min(H,y+0.045*H)))
    return im.crop(box),(W,H,len(imgs))
for i,ix in enumerate(sel):
    r=sub.loc[ix]
    try:
        a,ia=crop(r.page_old,r.entry_old,'old'); b,ib=crop(r.page_new,r.entry_new,'new')
    except Exception as e: print(i,'ERR',e); continue
    w=max(a.width,b.width); m=Image.new('L',(w,a.height+b.height+10),255); m.paste(a,(0,0)); m.paste(b,(0,a.height+10))
    m.save(f'/private/tmp/claude-502/x/c{i:02d}.png')
    print(i,r.kind,'|',r.s_old,r.page_old,r.entry_old.split('__')[1],'|',r.old,'->',r.s_new,r.page_new,r.entry_new.split('__')[1],'|',r.new,ia,m.size)
