"""1911-12 Repertoire, Малый 16 Oct 1911 morning (p010, printed p. 11), «Спектакль для учащейся молодежи.»: the print reads
«Грова, др.». RG 2026-11-12, on the zoom: "it's a misprinted з" -- store the intended letter, as for the broken о of «ком.»
and «Герцогиня» -> «Гроза». The blind column read had already given «Гроза»; the 2026-11-11 sweep logged «Грова» as a print
typo (genuine_print_typos.md, updated).

uv run python docs/eval/reconciliation/fix_1911_12_groza.py [--write]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
FILES = [ROOT / "outputs/full_run/raw/repertoire_1911-12_p010.raw.json",
         ROOT / "outputs/repertoire_1911-12/raw_columnwise_repaired/repertoire_1911-12_p010.raw.json"]
NOTE = "scan 2026-11-12: printed «Грова», a misprinted з (RG) -> «Гроза»"
for f in FILES:
    d = json.loads(f.read_text(encoding="utf-8"))
    hits = [(s, w) for s in d["sessions"] for w in s["works"] if w["work_title"] == "Грова"]
    assert len(hits) == 1, (f, len(hits))
    s, w = hits[0]
    assert s["date_text"].startswith("16") and s["theater"].startswith("Малый"), s
    w["work_title"] = "Гроза"
    s["_fix_note"] = (s["_fix_note"] + "; " if s.get("_fix_note") else "") + NOTE
    print(f.name, "->", s["date_text"], s["theater"], s["session"], w)
    if "--write" in sys.argv:
        f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("written" if "--write" in sys.argv else "dry run")
