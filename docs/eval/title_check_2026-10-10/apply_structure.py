"""Repertoire cell structure fixes (issue #151 follow-up 3): banner lines stored as works, and works stored in the annotation.

    uv run python docs/eval/title_check_2026-10-10/apply_structure.py            # dry run
    uv run python docs/eval/title_check_2026-10-10/apply_structure.py --write

Every cell was read line by line on the scan by a blind reader (BRIEF_CELL.md, reader_reports/cells_*.csv; cells_33 is a
second reading of the cells a fix rests on). Two classes:

A. BANNER IN WORKS (83 sessions, almost all in the 1890-98 spread seasons): the occasion line printed in the cell
   («Бенефисъ г. Рыбакова.», «Спектакль въ пользу инвалидовъ.», «Концертъ въ пользу инвалидовъ.» ...), genre-less and set
   as a heading, was stored as work no. 1. The annotation field is where the schema puts it (docs/schema.md: "benefit-performance /
   anniversary notes printed in the cell, verbatim"; 305 annotations already start «Бенефисъ»), and as a work it became a pseudo-work in
   research.work and shifted performance_order. The line is moved to `annotation` (kept if the annotation already holds it) and
   removed from `works`. A session left without works is an annotation-only special, the state RG's issue #141 decision left the
   other 106 in. NOT touched: genre-less lines set like work lines («Концертное отдѣленіе», «Дивертиссементъ», «Гимнъ»,
   «Концертъ русской оперы», «Кинематографическій спектакль», «Сцена г. ...», «Юбилей, шутка», «Праздникъ у Плутона»).
B. WORK IN ANNOTATION (the 8 cells where the annotation held a titled work the works list lacked, or swapped with the banner).

The page JSON is read and written with plain json (all 49 pages were checked to round-trip byte for byte before editing).
"""
from __future__ import annotations

import csv
import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from classify_cells import get, norm, priv, rd  # noqa: E402

ROOT = HERE.parents[2]
RAW = ROOT / "outputs" / "full_run" / "raw"
KEEP_AS_WORK = {"C008", "C025"}           # program items that merely contain "спектакль"/"концертъ": stay works
BANNER = re.compile(r"(бенефис|въ пользу|спектакль|вокально|повторен.. концерта|генеральная репет|концертъ соед)", re.I)


def clean_line(t: str) -> str:
    t = re.sub(r"^.*?half\b[^:]*:\s*(?:\d+:\s*)?", "", t).strip()
    return re.sub(r"^(УТРО|ВЕЧЕРЪ)\s*:\s*\d+:\s*", "", t)


#: banner text to use where the stored title is not the printed line (reader text, scan-read); others keep the stored title
BANNER_TEXT = {
    "C006": "Прощальный бенефисъ капельмейстера А. Ю. Герберъ.",
    "C037": "Бенефисъ балетмейстера І. Мендеса.",
    "C057": "Спектакль въ пользу фонда на образованіе стипендіи имени М. С. Щепкина.",
}
#: B. explicit cell rebuilds: item -> (new annotation, [(title, genre) of works to be (kept|added)] in printed order)
B_FIX = {
    "C086": ("Спектакль въ пользу Благотворительнаго Общества при Императорскомъ Клиническомъ Повивальномъ Институтѣ.", [("Фимка", "пьеса")]),
    "C088": ("Въ пользу недостаточныхъ слушателей драматическихъ курсовъ при Императорскомъ Спб. Театральномъ Училищѣ.", [("Побѣда", "сц.")]),
    "C094": ("Спектакль въ пользу семьи умершаго товарища.", [("Мѣсяцъ въ деревнѣ", "ком.")]),
    "C097": (None, [("Антонъ-горемыка", "сц."), ("@keep", None)]),
    "C098": (None, [("Собака садовника", "ком."), ("@keep", None), ("@keep", None)]),
    "C099": (None, [("@keep", None), ("Изъ за мышенка", "ком.")]),
    "C100": (None, [("@keep", None), ("Шашки", "ш.")]),
    "C101": (None, [("@keep", None), ("На тотъ свѣтъ", "ш.")]),
}
#: other single-field fixes, each decided from the readings: item -> list of (kind, args)
EXTRA = {
    "C054": [("retitle", ("Жены", "Женя"))],                                  # two readers: «Женя, этюдъ.»
    "C099": [("retitle", ("Спорный вопрос", "Спорный вопросъ"))],             # two readers: final ъ was dropped
    "C098": [("regenre", ("Угнетенная невинность, опер.", "Угнетенная невинность, вод", "вод"))],   # two readers: «вод» (no full stop)
    "C057": [("add_work_after_banner", ("Орлеанская дѣва", "траг."))],
    "C034": [("set_annotation", "Прощальный бенефисъ г-жи Рыкаловой.")],     # the annotation said «Социальный бенефисъ»
}


def build_plan():
    plan = {}
    for k, p in priv.items():
        ev = p["event_id"]
        page, sidx = re.match(r"^(.*)__s(\d+)$", ev).groups()
        ops = {"item": k, "event": ev, "page": page, "s": int(sidx)}
        r = rd[k]
        lines = [(clean_line(t), g) for h in __import__("classify_cells").parse_lines(r["lines"]) for t, g in h]
        if p["kind"] == "annotation_work":
            if k in B_FIX:
                ops["kind"] = "B"; ops["spec"] = B_FIX[k]; ops["extra"] = EXTRA.get(k, [])
            else:
                continue                                  # annotation merely repeats the stored works: left as printed
        else:
            if k in KEEP_AS_WORK:
                continue
            works = json.loads(p["stored_works"])
            ban = [w for w in works if not w[2] and BANNER.search(w[1])]
            ops["kind"] = "A"; ops["remove_orders"] = [w[0] for w in ban]; ops["banner_titles"] = [w[1] for w in ban]
            txt = BANNER_TEXT.get(k)
            if txt is None:
                # stored title, completed with the full stop the reader saw
                t0 = ban[0][1].strip()
                rt = next((t for t, g in lines if g is None and norm(t) == norm(t0)), None)
                txt = rt if rt else t0
                if k == "C012": txt = ban[0][1].strip()
            ops["banner_text"] = [txt] if k != "C007" else []
            if k == "C007": ops["extra_ann_lines"] = [ban[0][1].strip()]   # 2nd genre-less line: goes into the annotation
            ops["extra"] = EXTRA.get(k, [])
        plan[k] = ops
    for k in EXTRA:
        if k in priv and k not in plan and priv[k]["kind"] == "annotation_work":
            pass
    return plan


def merge_annotation(old, lines):
    """annotation = banner line(s) in print order, keeping what the annotation already holds."""
    old = old or ""
    add = [l for l in lines if norm(l) not in norm(old)]
    if not old: return "\n".join(add) if add else None
    return "\n".join(add + [old]) if add else old


def apply_to_session(S, ops, log):
    works = S.get("works") or []
    kind = ops["kind"]
    if kind == "A":
        keep = [w for i, w in enumerate(works, 1) if str(i) not in {str(x) for x in ops["remove_orders"]}]
        S["annotation"] = merge_annotation(S.get("annotation"), ops.get("banner_text", []))
        for l in ops.get("extra_ann_lines", []):              # a second genre-less line: after what the annotation already holds
            if norm(l) not in norm(S["annotation"] or ""):
                S["annotation"] = ((S["annotation"] + "\n") if S["annotation"] else "") + l
        for op in ops.get("extra", []):
            if op[0] == "add_work_after_banner":
                keep.insert(0, {"work_title": op[1][0], "genre": op[1][1]})
            elif op[0] == "set_annotation":
                S["annotation"] = op[1]
        S["works"] = keep
    else:
        ann, spec = ops["spec"]
        old = list(works); new = []
        for title, genre in spec:
            if title == "@keep":
                new.append(old.pop(0) if old else None)
            else:
                new.append({"work_title": title, "genre": genre})
        # a banner stored as a work (C086) is replaced, not kept
        S["works"] = [w for w in new if w is not None]
        S["annotation"] = ann
    for op in ops.get("extra", []):
        if op[0] == "retitle":
            hit = [w for w in S["works"] if w.get("work_title") == op[1][0]]
            assert len(hit) == 1, (ops["item"], op)
            hit[0]["work_title"] = op[1][1]
        elif op[0] == "regenre":
            hit = [w for w in S["works"] if w.get("work_title") == op[1][0]]
            assert len(hit) == 1, (ops["item"], op)
            hit[0]["work_title"], hit[0]["genre"] = op[1][1], op[1][2]
    log.append(ops["item"])


def main() -> int:
    write = "--write" in sys.argv
    plan = build_plan()
    by_page = defaultdict(list)
    for k, o in plan.items():
        by_page[o["page"]].append(o)
    nA = sum(1 for o in plan.values() if o["kind"] == "A"); nB = sum(1 for o in plan.values() if o["kind"] == "B")
    print(f"{len(plan)} sessions: {nA} banner-in-works, {nB} work-in-annotation, on {len(by_page)} pages")
    for page, ops in sorted(by_page.items()):
        path = RAW / f"{page}.raw.json"
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
        fmt = None                                            # the file's own layout: (indent, ensure_ascii, trailing newline)
        for ind in (2, 4, None):
            for ea in (False, True):
                for tr in ("", "\n"):
                    if json.dumps(doc, indent=ind, ensure_ascii=ea) + tr == text:
                        fmt = (ind, ea, tr)
        assert fmt, f"{page} does not round-trip"
        ind, ea, trail = fmt
        log = []
        for o in sorted(ops, key=lambda x: x["s"]):
            S = doc["sessions"][o["s"] - 1]
            before = (json.dumps(S.get("works"), ensure_ascii=False)[:150], (S.get("annotation") or "")[:50])
            apply_to_session(S, o, log)
            print(f"  {o['item']} {o['event'].replace('repertoire_','')}: works {len(json.loads(priv[o['item']]['stored_works']))} -> {len(S['works'])}; annotation -> {(S.get('annotation') or '')[:70]!r}")
        if write:
            path.write_text(json.dumps(doc, indent=ind, ensure_ascii=ea) + trail, encoding="utf-8")
    print("WROTE" if write else "DRY RUN (nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
