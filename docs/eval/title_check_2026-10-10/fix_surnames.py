"""Two roster surnames misread by the model, each read blind by two readers on the scan (issue #151 follow-up 2):
  balletartists_1900-01_MSK_p006__e010 (no. 15): stored «Гельперъ», printed «Гельцеръ, Василій Федоровичъ» (47 other records of the man print Гельцеръ)
  balletartists_1897-98_MSK_p004__e030 (no. 6):  stored «Бенъ», printed «Бекъ, Константинъ Александровичъ» (24 other records print Бекъ)
uv run python docs/eval/title_check_2026-10-10/fix_surnames.py [--write]"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "balletartists_credit_audit_2026-10-10"))
import rawjson_pairs as rp
RAW = HERE.parents[2] / "outputs" / "full_run" / "raw"
FIX = [("balletartists_1900-01_MSK_p006", 10, "Гельперъ", "Гельцеръ"), ("balletartists_1897-98_MSK_p004", 30, "Бенъ", "Бекъ")]
for page, n, old, new in FIX:
    p = RAW / f"{page}.raw.json"
    doc = rp.loads(p.read_text(encoding="utf-8")); e = doc.get("entries")[n - 1]
    assert e.get("family_name") == old, (page, e.get("family_name"))
    print(page, n, old, "->", new)
    e.set("family_name", new)
    if "--write" in sys.argv: p.write_text(rp.dumps(doc), encoding="utf-8")
print("WROTE" if "--write" in sys.argv else "DRY RUN")
