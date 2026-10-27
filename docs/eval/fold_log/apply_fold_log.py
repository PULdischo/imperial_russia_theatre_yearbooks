"""Apply RG's physical-volume readings from the Binding Fold Log (claude.ai/artifact/C5n3ckdTBn2JCn1AQCTN9Y) to the raw JSON.
Input: docs/eval/fold_log/readings_<season>.csv, one row per card cell (exported from the log's store, with the event_id each
cell maps to and the receipts stored at export time). A receipts reading is applied only where it differs from the stored
figure in value (a missing final period or «04» for «4» is not a difference); the stored figure is asserted unchanged first.
A transcription that isn't a receipts figure (RG sometimes wrote a title or annotation there) is skipped; corrections from
her notes are written out below. RG's "[?]" (digits hidden by the binding thread) becomes the dataset's "?", as in
«11?7 р. 08 к.» (the rubles still count; build_duckdb reads «?» kopecks as 0).
  WORKS      whole-cell corrections (works and receipts) RG gave in a note;
  ADD_WORKS  works missing from a cell, appended after the stored ones (so no performance id shifts);
  SET_WORK   one stored work's title and/or genre corrected in place: (event_id, order) -> (old (title, genre), new (title, genre)).
uv run python docs/eval/fold_log/apply_fold_log.py <season> [--write]"""
import csv, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "outputs" / "full_run" / "raw"
NOTE = {"1893-94": "RG, physical volume, Binding Fold Log 2026-10-14", "1892-93": "RG, physical volume, Binding Fold Log 2026-10-14",
        "1897-98": "RG, physical volume, Binding Fold Log 2026-10-27", "1895-96": "RG, physical volume, Binding Fold Log 2026-10-27",
        "1894-95": "RG, physical volume, Binding Fold Log 2026-10-27"}
# event_id -> (works [(title, genre)], receipts). Issue #153: 24 Понед. held a copy of 23 Воскрес.
WORKS = {"repertoire_1893-94_pair016__s046": ([("Жизнь за Царя", "оп.")], "2168 р. 23 к.")}
# event_id -> works to append. Lines hidden at the fold, read by RG in the volume.
ADD_WORKS = {"repertoire_1892-93_pair020__s055": [("Ma Femme est troublée", "com.")],
             "repertoire_1892-93_pair018__s100": [("La Soucoupe", "com.")],
             "repertoire_1892-93_pair022__s015": [("Чудовище", "ком.")],
             # 1897-98, 6 Пятница (p. 18): the Большой cell had no works stored; the Малый cell was missing its second play.
             "repertoire_1897-98_pair018__s044": [("Марія Стюартъ", "тр.")],
             "repertoire_1897-98_pair018__s045": [("Кто любитъ миръ....", "ком.")]}
# (event_id, performance_order) -> (stored (title, genre), corrected (title, genre)). 1897-98, RG's notes:
SET_WORK = {("repertoire_1897-98_pair008__s011", 2): (("2-е д. бал. Млада.", "бал."), ("2-е д. бал. Млада.", None)),  # no genre printed
            ("repertoire_1897-98_pair016__s045", 2): (("1-е д. бал. Коппелія", None), ("1-е д. бал. Коппелія.", None)),
            ("repertoire_1897-98_p012__s036", 3): (("[?]-е д. бал. Пахита", None), ("3-е д. бал. Пахита", None)),
            # 1895-96, RG: the «оп.» after the excerpt is not printed (the excerpt names the genre itself)
            ("repertoire_1895-96_pair024__s031", 1): (("1-я и 2-я карт. 1-го д. и 2-я карт. 3-го д. оп. Пиковая дама.", "оп."),
                                                      ("1-я и 2-я карт. 1-го д. и 2-я карт. 3-го д. оп. Пиковая дама.", None)),
            # 1894-95, 18 Апрѣля (p. 16) Малый: RG reads «Ирэнъ, ком.» (the form used 20 times elsewhere), not «Иронъ»
            ("repertoire_1894-95_pair016__s031", 2): (("Иронъ", "ком."), ("Ирэнъ", "ком."))}
FIGURE = re.compile(r"^[\d?]+ р\.(?: [\d?—–-]+ ?к\.?)?$")


def value(s):  # comparable value of a receipts text: digits of rubles and kopecks, leading zeros dropped
    m = re.match(r"^\s*([\d?]+)\s*р\.?\s*(?:([\d?—–-]+)\s*к?)?", s or "")
    return None if not m else (m.group(1).lstrip("0"), (m.group(2) or "").lstrip("0"))


season = sys.argv[1]; write = "--write" in sys.argv
changes, skipped = {}, []
for r in csv.DictReader(open(Path(__file__).parent / f"readings_{season}.csv", encoding="utf-8")):
    eid = r["event_id"]
    if eid in WORKS:
        changes[eid] = (r["stored"], WORKS[eid][1], WORKS[eid][0]); continue
    new = re.sub(r"\s+", " ", re.sub(r"\?к", "? к", r["reading"].replace("[?]", "?")).strip())
    new = re.sub(r"(\d) р (\S)", r"\1 р. \2", new)
    if new and not FIGURE.match(new):
        skipped.append((eid, new)); new = ""
    if eid in ADD_WORKS or any(k[0] == eid for k in SET_WORK):
        changes[eid] = (r["stored"], new if new and value(new) != value(r["stored"]) else r["stored"], None); continue
    if not new or value(new) == value(r["stored"]): continue
    changes[eid] = (r["stored"], new, None)
for k in list(ADD_WORKS) + [k[0] for k in SET_WORK]:
    assert k in changes or not k.startswith(f"repertoire_{season}_"), f"correction for {k} has no row in the readings"
by = {}
for eid, ch in changes.items():
    page, s = eid.rsplit("__s", 1); by.setdefault(page, []).append((int(s), eid, ch))
for page, items in sorted(by.items()):
    p = RAW / f"{page}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t); fmt = None
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t: fmt = (ind, ea, tr)
    assert fmt, page
    for s, eid, (stored, new, works) in sorted(items):
        S = d["sessions"][s - 1]
        assert (S.get("receipts_text") or "") == stored, (eid, S.get("receipts_text"), stored)
        old_w = [(w["work_title"], w.get("genre")) for w in S["works"]]
        S["receipts_text"] = new or None
        if works: S["works"] = [{"work_title": t_, "genre": g} for t_, g in works]
        for (k_eid, order), (old, fixed) in SET_WORK.items():
            if k_eid != eid: continue
            w = S["works"][order - 1]
            assert (w["work_title"], w.get("genre")) == old, (eid, order, w)
            w["work_title"], w["genre"] = fixed; works = True
        for t_, g in ADD_WORKS.get(eid, []):
            assert t_ not in [x[0] for x in old_w], (eid, t_)
            S["works"].append({"work_title": t_, "genre": g}); works = True
        S["_fix_note"] = (S.get("_fix_note", "") + "; " if S.get("_fix_note") else "") + NOTE[season]
        print(f"{eid}: {S['date_text']} {S['theater']} {S['session']}  {stored or '(blank)'} -> {new or '(blank)'}"
              + (f"\n      works {old_w} -> {[(w['work_title'], w.get('genre')) for w in S['works']]}" if works else ""))
    if write: p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")
for eid, txt in skipped: print(f"not a figure, skipped: {eid}: {txt!r}")
print(len(changes), "cells,", len(by), "pages:", "WROTE" if write else "DRY RUN")
