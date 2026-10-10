"""Complete the credit summary of entry 40 (Мордкинъ, Михаилъ Михайловичъ; 1907-08 Moscow BalletArtists) whose
printed text runs from the foot of printed p. 52 (MSK p006) onto the top of p. 53 (MSK p007); the raw JSON stopped at
the page break and the continuation lines were never captured (issue #150 follow-up).

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/fix_entry40.py            # dry run
    uv run python docs/eval/balletartists_credit_audit_2026-10-10/fix_entry40.py --write

Read by me on both scans at zoom (2026-10-10). Printed, with the page break after «(англича-»:
  Въ 9 балетахъ—23; въ 4 дивертиссементахъ—4; въ 3 операхъ — 22. Всего—45 разъ. Въ томъ числѣ: Два вора (Робертъ — 1);
  Донъ-Кихотъ (Базиль—1, Эспада—4); Дочь фараона (англичанинъ—1, Хитарисъ—2); Жизель (герцогъ Альбертъ—3);
  Нуръ и Анитра (Нуръ—2); Тщетная предосторожность (Колэнъ—2).
The entry keeps its first fragment's place (p006 entry 40); p007 starts at entry 41, so nothing is removed there.
The credit rows follow the existing convention (one named_work row per role); the old row «Эспада» (no role) was
the model's misparse of «Донъ-Кихотъ (Базиль—1, Эспада—4)».
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rawjson_pairs as rp  # noqa: E402

PATH = HERE.parent.parent.parent / "outputs" / "full_run" / "raw" / "balletartists_1907-08_MSK_p006.raw.json"
TEXT = ("Въ 9 балетахъ—23; въ 4 дивертиссементахъ—4; въ 3 операхъ — 22. Всего—45 разъ. Въ томъ числѣ: "
        "Два вора (Робертъ — 1); Донъ-Кихотъ (Базиль—1, Эспада—4); Дочь фараона (англичанинъ—1, Хитарисъ—2); "
        "Жизель (герцогъ Альбертъ—3); Нуръ и Анитра (Нуръ—2); Тщетная предосторожность (Колэнъ—2).")
NAMED = [("Два вора", "Робертъ", 1), ("Донъ-Кихотъ", "Базиль", 1), ("Донъ-Кихотъ", "Эспада", 4),
         ("Дочь фараона", "англичанинъ", 1), ("Дочь фараона", "Хитарисъ", 2), ("Жизель", "герцогъ Альбертъ", 3),
         ("Нуръ и Анитра", "Нуръ", 2), ("Тщетная предосторожность", "Колэнъ", 2)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    doc = rp.loads(PATH.read_text(encoding="utf-8"))
    e = doc.get("entries")[23]
    assert e.get("list_number") == "40." and e.get("family_name") == "Мордкинъ", "wrong entry"
    rows = e.get("credits")
    template = next(r for r in rows if r.get("credit_type") == "named_work")
    kept = [r for r in rows if r.get("credit_type") == "category_totals"]
    new_named = []
    for label, role, n in NAMED:
        r = rp.Obj(list(template))
        r.set("label", label); r.set("role_name", role); r.set("count", n)
        new_named.append(r)
    before = [(r.get("credit_type")[:4], r.get("label"), r.get("role_name"), r.get("count")) for r in rows]
    e.set("credit_summary_text", TEXT)
    e.set("credits", kept + new_named)
    after = [(r.get("credit_type")[:4], r.get("label"), r.get("role_name"), r.get("count")) for r in e.get("credits")]
    print("rows before:", len(before), "after:", len(after))
    for x in after:
        print("  ", x)
    if a.write:
        PATH.write_text(rp.dumps(doc), encoding="utf-8")
        print("WROTE")
    else:
        print("DRY RUN (nothing written)")


if __name__ == "__main__":
    main()
