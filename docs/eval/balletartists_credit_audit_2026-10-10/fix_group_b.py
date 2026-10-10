"""The five BalletArtists summaries that apply_continuations.py could not complete on a reader's say-so alone
(issue #150 follow-up 5). Each was zoomed on the scan by me (2026-10-10); the printed text is below.

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/fix_group_b.py            # dry run
    uv run python docs/eval/balletartists_credit_audit_2026-10-10/fix_group_b.py --write

  * 1896-97 MSK p002 e013, no. 53 Крылова 2-я: NO summary is printed (entry 54 follows directly). The stored «Всего—»
    was a model fragment; the summary becomes null, the project's convention for a printed entry without one.
  * 1898-99 SP p006 e022, no. 35 Легатъ 3-й: head «Алисъ» is printed «Ацисъ». Last digit of «Всего—36» is clogged
    (closed loop) but 31 + 5 = 36, so it is a 6; the e of «Галатея» is clogged, the intended letter is kept.
  * 1903-04 SP p006 e009, no. 17 Гердтъ: head «Балдерка (Соляръ» is printed «Баядерка (Солоръ»; the role of Ручей is
    printed with a descender on the 3rd letter, «Моцдокъ» (the form the corpus carries six times). The 18 roles sum
    to the printed 31 and number the 18 ballets.
  * 1904-05 SP p006 e019, no. 20 Гиллертъ: «Пахи:а» (damaged т, intended letter kept); role «м?ръ» of Голубая георгина
    is printed with an э-shaped glyph, «мэръ»; «Въ 2о» is a damaged 0 (14 + 6 listed ballets = 20; roles sum to 51).
  * 1907-08 MSK p001 e003, no. 5 Балашева: the print ends «Фея куколъ (фея куколъ—1),» with a comma, entry 6 follows.
    The model's «1); Жуаннита—3)» is printed «1, Жуаннита—3)» (a speck of ink after the comma). The header's parts
    (41 + 4 + 21 = 66) do not add up to the printed 67, as on the scan (already on credit_totals_scan_verified.csv).
Rows: category rows are kept; the named_work rows are regenerated from the text (one per role).
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rawjson_pairs as rp  # noqa: E402
from apply_continuations import parse_head, parse_roles  # noqa: E402

ROOT = HERE.parent.parent.parent
RAW = ROOT / "outputs" / "full_run" / "raw"
VERIFIED = ROOT / "pipeline" / "entity_curation" / "credit_totals_scan_verified.csv"
E = "balletartists_"

NEW_TEXT = {
    E + "1896-97_MSK_p002__e013": None,
    E + "1898-99_SP_p006__e022": (
        "Въ 7 балетахъ—31; въ 2 операхъ—5. Всего—36 разъ. Въ томъ числѣ: Ацисъ и Галатея (Ацисъ—1); "
        "Дочь фараона (рыбакъ—13); Привалъ кавалеріи (уланскій корнетъ — 3); Раймонда (Жанъ де Бріенъ—7); "
        "Спящая красавица (принцъ Шери—3)."),
    E + "1903-04_SP_p006__e009": (
        "Въ 18 балетахъ — 31; въ 1 оперѣ—5. Всего—36 разъ. Въ томъ числѣ: Баядерка (Солоръ — 1); "
        "Волшебная флейта (маркизъ — 3); Волшебное зеркало (король—2); Гарлемскій тюльпанъ (Питерсъ—1); "
        "Дочь Фараона (Фараонъ—2); Жавотта (владѣлецъ селенія—2); Жизель (Гансъ — 2); Конекъ-Горбунокъ (ханъ — 1); "
        "Коппелія (Коппеліусъ—1); Корсаръ (Конрадъ — 1); Пахита (донъ Лопецъ де-Мендоза — 3); "
        "Привалъ кавалеріи (гусарскій полковникъ — 1); Раймонда (Абдеррахманъ — 4); Ручей (Моцдокъ — 1); "
        "Синяя борода (Синяя борода — 1); Спящая красавица (Флорестанъ XIV — 3); Фея куколъ (главный прикащикъ—1); "
        "Эсмеральда (Клодъ Фроло—1)."),
    E + "1904-05_SP_p006__e019": (
        "Въ 20 балетахъ — 51. Всего — 51 разъ. Въ томъ числѣ: Конекъ-Горбунокъ (Петръ — 5); "
        "На перепутьи (Обермюллеръ — 4); Пахита (графъ д’Эрвильи — 4); Раймонда (Андрей II — 5); "
        "Лебединое озеро (Вольфгангъ — 2); Спящая красавица (Галлифронъ—5); Жизель (герцогъ — 3); "
        "Жемчужина (царь коралловъ — 3); Фея куколъ (хозяинъ лавки—3); Граціелла (Донъ Фортунато — 3); "
        "Фіаметта (опекунъ — 2); Голубая георгина (мэръ—2); Тщетная предосторожность (Мишо—2); "
        "Волшебное зеркало (оберъ-гофмаршалъ — 1); Путешествующая танцовщица (Нюнецъ — 2); Жавотта (Франсуа — 1); "
        "Щелкунчикъ (Зильбергаузъ—1); Дочь Фараона (Нилъ—1); Ручей (ханъ—1); Привалъ кавалеріи (старшина—1)."),
    E + "1907-08_MSK_p001__e003": (
        "Въ 11 балетахъ—41; въ 4 дивертиссментахъ—4; въ 5 операхъ—21. Всего—67 разъ. Въ томъ числѣ: "
        "Волшебное зеркало (принцесса—4); Донъ-Кихотъ (повелительница дріадъ—1, Жуаннита—3); Дочь фараона (Небъ—2); "
        "Жизель (Батильда—3); Конекъ-горбунокъ (царь-дѣвица—6); Фея куколъ (фея куколъ—1),"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    old_text = {}
    for eid, new in NEW_TEXT.items():
        page, idx = eid.split("__e")[0], int(eid.split("__e")[1]) - 1
        path = RAW / f"{page}.raw.json"
        doc = rp.loads(path.read_text(encoding="utf-8"))
        e = doc.get("entries")[idx]
        old_text[eid] = e.get("credit_summary_text")
        rows = e.get("credits") or []
        print("\n", eid[len(E):], "| rows", len(rows))
        if new is None:
            assert not rows
            e.set("credit_summary_text", None)
        else:
            roles = parse_roles(new)
            cats, total = parse_head(new)
            assert roles is not None
            cat_rows = [r for r in rows if r.get("credit_type") == "category_totals"]
            have = [(r.get("label"), r.get("count")) for r in cat_rows if r.get("label") != "Всего"]
            tot = next((r.get("count") for r in cat_rows if r.get("label") == "Всего"), None)
            assert len(have) == len(cats) and tot == total, (have, cats, tot, total)
            template = next(r for r in rows if r.get("credit_type") == "named_work")
            named = []
            for w_, r_, n_ in roles:
                r = rp.Obj(list(template))
                r.set("label", w_); r.set("role_name", r_); r.set("count", int(n_))
                named.append(r)
            print("   roles:", len(roles), "sum", sum(n for _, _, n in roles), "| head", cats, total, "| rows now", len(rows), "->", len(cat_rows) + len(named))
            e.set("credit_summary_text", new)
            e.set("credits", cat_rows + named)
        if a.write:
            path.write_text(rp.dumps(doc), encoding="utf-8")
    # the scan-verified list: an entry whose text changed lapses unless its row is updated
    raw = open(VERIFIED, encoding="utf-8", newline="").read()      # the file uses CRLF
    rd = list(csv.reader(io.StringIO(raw, newline="")))
    buf = io.StringIO(newline=""); csv.writer(buf, lineterminator="\r\n").writerows(rd)
    if buf.getvalue() != raw:
        print("verified list does not round-trip through csv; update it by hand"); return 1
    hits = 0
    for row in rd[1:]:
        if row[0] in NEW_TEXT and NEW_TEXT[row[0]] is not None:
            print("verified row updated:", row[0][len(E):]); row[1] = NEW_TEXT[row[0]]; hits += 1
    if a.write and hits:
        buf = io.StringIO(newline=""); csv.writer(buf, lineterminator="\r\n").writerows(rd)
        open(VERIFIED, "w", encoding="utf-8", newline="").write(buf.getvalue())
    print("WROTE" if a.write else "DRY RUN (nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
