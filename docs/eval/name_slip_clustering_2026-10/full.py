import pymupdf,io,sys,duckdb
from PIL import Image
c=duckdb.connect('outputs/full_run/imperial_theaters.duckdb',read_only=True)
dirs={'BalletArtists':'Spiski_BalletArtists','Musicians':'Spiski_Musicians'}
for pid,ln,tag in [a.split(',') for a in sys.argv[1:]]:
    et,src,idx=c.execute("select entity_type,source_file,source_page_index from raw.source_pages where page_id=?",[pid]).fetchone()
    doc=pymupdf.open(f"pdf/{dirs[et]}/{src}"); pg=doc[idx]
    im=Image.open(io.BytesIO(doc.extract_image(pg.get_images()[0][0])['image'])).convert('L')
    s=2400/im.width; im=im.resize((2400,int(im.height*s)))
    im.save(f'/private/tmp/claude-502/x/f_{tag}.jpg',quality=80); print(tag,im.size, c.execute("select list_number,family_name from raw.person_entry where entry_id like ? order by 1",[pid+'__e%']).fetchall()[:3])
