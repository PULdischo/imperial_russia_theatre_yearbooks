"""Apply the scan-verified corrections to the BalletArtists raw JSON (issue #150).

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/apply_fixes.py            # dry run
    uv run python docs/eval/balletartists_credit_audit_2026-10-10/apply_fixes.py --write    # edit raw JSON

Evidence required for each change (the stored text is the model's reading; a change needs more than one
reader's say-so):
  * script fix (a Latin/Greek look-alike inside a Cyrillic word) -- the blind reader read the same word in
    Cyrillic; the word is otherwise unchanged;
  * digit fix -- the reader's printed numbers differ from the stored ones AND add up to the printed total;
  * spelling / structure fix -- a third reader (an arbiter shown the two candidate readings in shuffled
    order, so it does not know which is the stored one) picked the reader's reading;
  * a summary that was EMPTY in the raw JSON on 1908-09 SP p006 is filled from the blind reading.
Everything else is left as stored and listed in the report (stored kept by the arbiter, unreadable, notes).

Edits are in place on the ordered-pair view of the file (rawjson_pairs.py), so layout and duplicate keys are
untouched, entries are never inserted or removed (the #131 person_link hazard), and for every changed word
the entry's credit rows (label / role_name) and, for a digit, the matching count are changed with it.
"""
from __future__ import annotations

import argparse
import collections
import csv
import difflib
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rawjson_pairs as rp  # noqa: E402

RAW = HERE.parent.parent.parent / "outputs" / "full_run" / "raw"
HOMO = str.maketrans({'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у', 'k': 'к', 'A': 'А', 'B': 'В',
                      'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т', 'X': 'Х', 'κ': 'к', 'ο': 'о'})
TOKEN = re.compile(r"[^\W\d_]+|\d+|[^\w\s]", re.U)
SPAN = re.compile(r"[^\W\d_]+|\d+", re.U)
PUNCT = set('-—;:,.()«»')

#: Whole summary taken from the blind reading (stored one was empty, truncated or garbled beyond a token fix).
WHOLE_TEXT = {
    "balletartists_1890-91_MSK_p001__e021",   # stored «Все—10—64», printed «Всего—64», second figure 18
    "balletartists_1906-07_MSK_p008__e004",   # stored lacks «29. Всего—»
} | {f"balletartists_1908-09_SP_p006__e{n:03d}" for n in (4, 5, 6, 7, 8, 9, 13, 16, 17, 18, 20, 21)}
#: Arbiter answered OTHER: use the arbiter's reading for just that word.
OTHER_REPLACEMENTS = {
    ("balletartists_1892-93_MSK_p003__e032", "Алонза Гонделорінъ"): "Алонза Гонделорія",
    ("balletartists_1894-95_SP_p005__e022", "коммиссарь"): "коммиссаръ",
}
#: Readings that give a non-word and that I checked myself at zoom (2026-10-10): all are printer's slips, legible and
#: crisp, not worn type, so they are applied AS PRINTED and logged in docs/eval/genuine_print_typos.md. (Had one been
#: worn type, the project convention would keep the intended letter and it would belong here.)
KEEP_STORED: set = set()
#: Entry whose stored summary + credit rows are a copy of the NEXT entry's (the print has no summary here).
CLEAR_ENTRIES = {"balletartists_1903-04_MSK_p005__e001"}
#: Row-count fixes for whole-text entries (credit rows hold the performance count).
ROW_COUNT_FIXES = {("balletartists_1890-91_MSK_p001__e021", "операхъ"): (13, 18)}


def words(s):
    return SPAN.findall(s or "")


def spans(s):
    return [(m.group(), m.start(), m.end()) for m in SPAN.finditer(s or "")]


def load_decisions():
    key = json.load(open(HERE / "arbitration_key.json", encoding="utf-8"))
    ans = {}
    for f in sorted(glob.glob(str(HERE / "arbiter_reports" / "arb_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            ans[r["item_id"]] = r
    out = collections.defaultdict(list)       # (entry, stored, reader) -> [(side, answer_text)]
    missing = [k for k in key if k not in ans]
    for iid, k in key.items():
        if iid not in ans:
            continue
        v = (ans[iid]["answer"] or "").strip()
        side = k[v] if v in ("A", "B") else ("OTHER" if v.startswith("OTHER") else "UNREADABLE")
        out[(k["entry_id"], k["stored"], k["reader"])].append((side, v, ans[iid]["note"]))
    return out, missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    stored, reader_text, reader_note = {}, {}, {}
    for wl in ("worklist.csv", "worklist2.csv"):
        for r in csv.DictReader(open(HERE / wl, encoding="utf-8")):
            stored[r["entry_id"]] = r["stored_summary"]
    for f in sorted(glob.glob(str(HERE / "reader_reports" / "chunk_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            reader_text[r["entry_id"]] = (r["printed_summary"] or "").strip()
            reader_note[r["entry_id"]] = r.get("note") or ""
    adds = {r["entry_id"]: r["reader_adds_up"] for r in csv.DictReader(open(HERE / "comparison.csv", encoding="utf-8"))}
    decisions, missing = load_decisions()
    if missing:
        print("WARNING: no arbiter answer yet for", len(missing), "items:", missing[:3])
        if args.write:
            return 2
    consumed = collections.Counter()
    by_entry_stored = {}
    for (e_, s_, t_), v_ in decisions.items():
        by_entry_stored.setdefault((e_, s_), v_)

    plan = {}          # entry -> dict(new_text, subs=[(old,new,kind)], digit_subs=[(old,new)], kept=[...], region_subs=[...])
    report = collections.defaultdict(list)
    for eid, st in stored.items():
        rd = reader_text.get(eid)
        if rd is None or rd in ("NOT FOUND", "NONE PRINTED") or not rd:
            report["no usable reading"].append(eid)
            continue
        if eid in WHOLE_TEXT:
            plan[eid] = dict(new_text=rd, subs=[], digit_subs=[], whole=True)
            continue
        a, b = words(st), words(rd)
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        sp = spans(st)
        wspans = [s for s in sp if s[0] in set(a)] if False else sp
        # words() drops punctuation tokens only, so `a` lines up with the word/number spans of the stored text
        if [w for w, _, _ in sp] != a:
            report["alignment mismatch (left alone)"].append(eid)
            continue
        edits = []      # (start, end, new_text)
        subs, dsubs = [], []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            if op == "replace" and i2 - i1 == j2 - j1:
                pairs = [(a[i], b[j], i) for i, j in zip(range(i1, i2), range(j1, j2))]
                token_level = True
            else:
                pairs = [(" ".join(a[i1:i2]), " ".join(b[j1:j2]), None)]
                token_level = False
            for s, t, idx in pairs:
                if (eid, s, t) in KEEP_STORED:
                    report["kept stored (worn type / possible slip; intended letter kept)"].append((eid, s, t)); continue
                if token_level and s.translate(HOMO) == t:
                    action = "apply"; kind = "script"
                elif token_level and s.casefold() == t.casefold():
                    continue                                   # capitalisation only: left as stored
                elif token_level and s.isdigit() and t.isdigit() and (eid, s, t) not in decisions:
                    action = "apply" if adds.get(eid) == "True" else "keep"; kind = "digit"
                else:
                    kind = "digit" if (token_level and s.isdigit() and t.isdigit()) else ("letters" if token_level else "structure")
                    q = decisions.get((eid, s, t)) or by_entry_stored.get((eid, s))
                    if not q:
                        if kind == "structure" and (not s or "Оставил" in s):
                            continue                           # reader left out a departure note on purpose
                        report["no arbiter decision (kept stored)"].append((eid, s, t)); continue
                    side, ans, note = q[consumed[(eid, s, t)] % len(q)]; consumed[(eid, s, t)] += 1
                    if side == "reader":
                        action = "apply"
                    elif side == "stored":
                        report["arbiter kept stored"].append((eid, s, t)); continue
                    elif side == "OTHER" and (eid, s) in OTHER_REPLACEMENTS:
                        action = "other"
                    else:
                        report["unresolved (kept stored)"].append((eid, s, t, ans, note[:70])); continue
                if action == "keep":
                    report["digit differs but reader's numbers do not add up (kept stored)"].append((eid, s, t)); continue
                new = OTHER_REPLACEMENTS[(eid, s)] if action == "other" else t
                if token_level:
                    _, st0, en0 = sp[idx]
                else:
                    first, last = sp[i1], sp[i2 - 1] if i2 > i1 else None
                    if i2 == i1:
                        report["insertion only (kept stored)"].append((eid, s, t)); continue
                    st0, en0 = sp[i1][1], sp[i2 - 1][2]
                edits.append((st0, en0, new))
                (dsubs if kind == "digit" else subs).append((s, new) if not (kind != "digit" and not token_level) else (s, new))
                if kind == "digit":
                    # preceding word (the category label or «Всего») for finding the credit row
                    prev = next((w for w, ss, ee in reversed(sp[:idx]) if not w.isdigit()), "") if idx is not None else ""
                    dsubs[-1] = (s, new, prev)
        new_text = st
        for st0, en0, new in sorted(edits, reverse=True):
            new_text = new_text[:st0] + new + new_text[en0:]
        if new_text != st:
            plan[eid] = dict(new_text=new_text, subs=subs, digit_subs=dsubs, whole=False)

    for eid in CLEAR_ENTRIES:
        plan[eid] = dict(new_text=None, subs=[], digit_subs=[], whole=False, clear=True)
    # ---- apply
    by_page = collections.defaultdict(list)
    for eid in plan:
        by_page[eid.split("__e")[0]].append(eid)
    n_text = n_rows = 0
    row_log, unmatched = [], []
    for page, eids in sorted(by_page.items()):
        path = RAW / f"{page}.raw.json"
        text0 = path.read_text(encoding="utf-8")
        doc = rp.loads(text0)
        entries = doc.get("entries")
        for eid in sorted(eids):
            idx = int(eid.split("__e")[1]) - 1
            e = entries[idx]
            cur = e.get("credit_summary_text") or ""
            if cur != stored[eid]:
                unmatched.append((eid, "raw text changed since the worklist was built"))
                continue
            p = plan[eid]
            if p.get("clear"):
                e.set("credit_summary_text", None)
                e.set("credits", [])
                n_text += 1; row_log.append((eid, "CLEARED (copy of the next entry)", cur[:50], ""))
                continue
            e.set("credit_summary_text", p["new_text"])
            n_text += 1
            rows = e.get("credits") or []
            for item in p["digit_subs"]:
                old, new, prev = item
                cands = [r for r in rows if r.get("count") is not None and str(r.get("count")) == old
                         and (prev == "" or (r.get("label") or "").split(" ")[-1].lower() == prev.lower()
                              or (r.get("role_name") or "").split(" ")[-1].lower() == prev.lower())]
                if len(cands) == 1:
                    cands[0].set("count", int(new)); n_rows += 1; row_log.append((eid, "count", old, new))
                else:
                    if not any(str(r.get("count")) == old for r in rows):
                        row_log.append((eid, "text only: credit rows hold the production count, not " + old, old, new))
                    else:
                        unmatched.append((eid, f"digit {old}->{new} after «{prev}»: {len(cands)} matching credit rows"))
            for r in rows:
                for field in ("label", "role_name"):
                    v = r.get(field)
                    if not v:
                        continue
                    nv = v
                    for old, new in p["subs"]:
                        nv = re.sub(r"(?<![^\W\d_])" + re.escape(old) + r"(?![^\W\d_])", new, nv)
                    if nv != v:
                        r.set(field, nv); n_rows += 1; row_log.append((eid, field, v, nv))
            for (e2, label), (old, new) in ROW_COUNT_FIXES.items():
                if e2 == eid:
                    for r in rows:
                        if r.get("label") == label and r.get("count") == old:
                            r.set("count", new); n_rows += 1; row_log.append((eid, "count", old, new))
        if args.write:
            path.write_text(rp.dumps(doc), encoding="utf-8")

    print(("WROTE" if args.write else "DRY RUN"), "-", len(plan), "entries with a text change on", len(by_page), "pages;",
          n_text, "summaries,", n_rows, "credit-row fields")
    for k, v in report.items():
        print(f"\n[{k}] {len(v)}")
        for x in v[:40]:
            print("   ", x)
    if unmatched:
        print("\n[needs a manual look]", len(unmatched))
        for x in unmatched:
            print("   ", x)
    if not args.write:
        print("\nsample of changes:")
        for eid, p in [x for x in plan.items() if not x[1].get("clear")][:6]:
            print(" ", eid[-30:]); print("    OLD:", stored[eid][:110]); print("    NEW:", p["new_text"][:110])
    json.dump({e: dict(new=p["new_text"], old=stored[e]) for e, p in plan.items()},
              open(HERE / "planned_changes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
