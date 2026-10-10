"""Complete BalletArtists credit summaries that stop mid-sentence (issue #150 follow-up 5).

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/apply_continuations.py            # dry run
    uv run python docs/eval/balletartists_credit_audit_2026-10-10/apply_continuations.py --write

For each entry of worklist4.csv a blind reader read the WHOLE printed summary, following it into the next column or
page (BRIEF2.md). The stored head is kept exactly as stored; the reader's text supplies only what comes after the
point where the two overlap. An entry is touched only if
  * the stored text is a clean prefix of the reader's text (all but possibly the last, cut-off, stored word match);
  * the reader's tail has no unreadable character (‹?›) and the new summary ends in «.» or «)»;
  * the credit rows already in the file are consistent with the new text (the category rows equal the parsed head;
    the existing named_work rows are, modulo spelling, a prefix of the parsed role list).
Otherwise it is listed for a manual look. New named_work rows (one per role, label = the work, role_name = the role,
count) are appended, after the existing ones, in text order. Entry order and count never change (#131).
"""
from __future__ import annotations

import argparse
import csv
import difflib
import glob
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rawjson_pairs as rp  # noqa: E402

RAW = HERE.parent.parent.parent / "outputs" / "full_run" / "raw"
SPAN = re.compile(r"[^\W\d_]+|\d+", re.U)
CY = re.compile("[а-яёѣіѳѵА-ЯЁѢІѲѴ]")
LA = re.compile("[A-Za-zα-ωΑ-Ω]")


def wspans(s):
    return [(m.group(), m.start(), m.end()) for m in SPAN.finditer(s or "")]


def norm(s):
    return re.sub(r"[\s\-—]+", "", (s or "").lower().replace("ь", "ъ"))


def parse_roles(text):
    """[(work, role, count)] from the «Въ томъ числѣ: ...» part; None if it does not parse."""
    m = re.search(r"Въ томъ числѣ\s*:\s*(.*)$", text, re.S)
    if m:
        body = m.group(1).strip().rstrip(".")
    elif re.search(r"\(.*[—-]\s*\d", text) and not re.match(r"\s*[Вв]ъ\s", text):
        # 1908-09 format: the role list comes first and «Всего—въ N балетахъ—M» ends the entry
        body = re.split(r"\s*Всего\s*[—-]", text)[0].strip().rstrip(".")
    else:
        return []
    items, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth <= 0:
            items.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip():
        items.append(cur)
    out = []
    for it in items:
        mm = re.match(r"^\s*(.+?)\s*\((.*)\)\s*[,.]?\s*$", it, re.S)
        if not mm:
            return None
        work, inner = mm.group(1).strip(), mm.group(2)
        buf = ""
        for part in inner.split(","):
            buf = (buf + ", " + part.strip()) if buf else part
            pm = re.match(r"^\s*(.+?)\s*[—-]+\s*(\d+(?:\.\d+)?)\s*$", buf, re.S)
            if pm:
                out.append((work, pm.group(1).strip(), float(pm.group(2)))); buf = ""
        if buf:
            return None
    return out


def parse_head(text):
    """[(label, count)] of the category sentences and the total: «Въ N label—X; ... Всего—T»."""
    head = text.split("Въ томъ числѣ")[0]
    cats = [(m[1], float(m[2])) for m in re.findall(r"[Вв]ъ\s+(?:\d+\s+)?([^\W\d_]+)\s*[—-]?\s*(\d+(?:\.\d+)?)", head)
            for m in [("", m[0], m[1])]] if False else []
    for m in re.finditer(r"[Вв]ъ\s+(?:\d+\s+)?([^\W\d_]+)\s*[—-]?\s*(\d+(?:\.\d+)?)", head):
        cats.append((m.group(1), float(m.group(2))))
    t = re.search(r"Всего\s*[—-]?\s*(\d+(?:\.\d+)?)", head)
    return cats, (float(t.group(1)) if t else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    work = {r["entry_id"]: r for r in csv.DictReader(open(HERE / "worklist4.csv", encoding="utf-8"))}
    reads, notes = {}, {}
    for f in sorted(glob.glob(str(HERE / "reader_reports" / "chunk_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["entry_id"] in work:
                reads[r["entry_id"]] = (r["printed_summary"] or "").strip()
                notes[r["entry_id"]] = r.get("note") or ""
    plan, manual = {}, []
    for eid, w in work.items():
        S, R = w["stored_summary"].strip(), reads.get(eid)
        if not R or R in ("NOT FOUND", "NONE PRINTED"):
            manual.append((eid, "no usable reading")); continue
        if "‹?›" in R:
            manual.append((eid, "reader text has an unreadable character")); continue
        sa, sb = wspans(S), wspans(R)
        A, B = [x[0] for x in sa], [x[0] for x in sb]
        sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
        if not blocks:
            manual.append((eid, "no overlap with the reader's text")); continue
        # the last stored word that is part of the overlap
        last = blocks[-1]
        ia_end, ib_end = last.a + last.size, last.b + last.size       # exclusive word indices
        matched = sum(b.size for b in blocks)
        if matched < 0.8 * len(A):
            manual.append((eid, f"only {matched}/{len(A)} stored words match the reader's text")); continue
        if ia_end == len(A):                                          # stored ends on a matched word
            cut_s, cut_r = sa[ia_end - 1][2], sb[ib_end - 1][2]
            new = S[:cut_s] + R[cut_r:]
        elif ia_end == len(A) - 1 and ib_end < len(B) and (B[ib_end].startswith(A[-1]) or len(__import__("os").path.commonprefix([A[-1].lower(), B[ib_end].lower()])) >= 4):
            new = S[:sa[-1][1]] + R[sb[ib_end][1]:]                   # last stored word is a cut-off prefix
        else:
            manual.append((eid, f"stored text does not end inside the overlap ({ia_end}/{len(A)})")); continue
        if new == S:
            manual.append((eid, "reader's text adds nothing (the print may end here)")); continue
        if not re.search(r"[.)]\s*$", new):
            manual.append((eid, "new text does not end in «.» or «)»: " + new[-40:])); continue
        tail = new[len(S[:len(new)]) - 0:]
        if any(CY.search(w_) and LA.search(w_) for w_ in re.findall(r"[^\W\d_]+", new[len(S) - 15:])):
            manual.append((eid, "mixed-script word in the tail")); continue
        # rows
        page = eid.split("__e")[0]; idx = int(eid.split("__e")[1]) - 1
        path = RAW / f"{page}.raw.json"
        plan[eid] = dict(old=S, new=new, path=path, idx=idx)
    # ---- check rows and apply
    changed = 0
    by_page = {}
    for eid, p in plan.items():
        by_page.setdefault(p["path"], []).append(eid)
    for path, eids in sorted(by_page.items(), key=lambda x: str(x[0])):
        doc = rp.loads(path.read_text(encoding="utf-8"))
        entries = doc.get("entries")
        for eid in sorted(eids):
            p = plan[eid]
            e = entries[p["idx"]]
            if (e.get("credit_summary_text") or "").strip() != p["old"]:
                manual.append((eid, "raw text changed since the worklist")); continue
            roles = parse_roles(p["new"])
            cats, total = parse_head(p["new"])
            if roles is None:
                manual.append((eid, "role list does not parse")); continue
            rows = e.get("credits") or []
            cat_rows = [r for r in rows if r.get("credit_type") == "category_totals"]
            named = [r for r in rows if r.get("credit_type") == "named_work"]
            # category rows already equal the parsed head (labels and counts, in order, the total as «Всего»)
            have_cat = [r for r in cat_rows if r.get("label") != "Всего"]
            have_tot = next((float(r.get("count")) for r in cat_rows if r.get("label") == "Всего" and r.get("count") is not None), None)
            m_end = re.search(r"Всего\s*[—-]\s*въ\s+(\d+)\s+([^\W\d_]+)\s*[—-]\s*(\d+)", p["new"])
            add_cat = []
            if not cat_rows and m_end:                       # 1908-09 format: «Всего—въ N балетахъ—M» at the end, no category rows yet
                add_cat = [(m_end.group(2), int(m_end.group(1))), ("Всего", int(m_end.group(3)))]
            elif cat_rows:
                if len(have_cat) != len(cats) or (have_tot is not None and total is not None and have_tot != total):
                    manual.append((eid, f"category rows do not match the parsed head ({len(have_cat)} rows vs {len(cats)}; total {have_tot} vs {total})")); continue
            have_named = [(norm(r.get("label")), norm(r.get("role_name"))) for r in named]
            exp_named = [(norm(w_), norm(r_)) for w_, r_, _ in roles]
            pref = sum(1 for a_, b_ in zip(have_named, exp_named) if a_ == b_)
            if len(have_named) > 3 and pref < len(have_named) * 0.7:
                manual.append((eid, f"existing named rows do not line up with the text ({pref}/{len(have_named)})")); continue
            template = named[0] if named else None
            if template is None:
                template = next((r for r in rows), None)
            if template is None:
                manual.append((eid, "no template row")); continue
            # rebuild the named rows from the text, keep category rows as they are
            new_named = []
            for w_, r_, n_ in roles:
                r = rp.Obj(list(template))
                r.set("credit_type", "named_work"); r.set("label", w_); r.set("role_name", r_ or None)
                r.set("count", int(n_) if n_ == int(n_) else n_)
                new_named.append(r)
            new_cat_rows = []
            for lab, cnt in add_cat:
                r = rp.Obj(list(template)); r.set("credit_type", "category_totals"); r.set("label", lab); r.set("role_name", None); r.set("count", cnt)
                new_cat_rows.append(r)
            cat_rows = new_cat_rows + cat_rows
            p["rows_before"], p["rows_after"] = len(rows), len(cat_rows) + len(new_named)
            p["added"] = len(new_named) - len(named)
            if args.write:
                e.set("credit_summary_text", p["new"])
                e.set("credits", cat_rows + new_named)
            changed += 1
        if args.write:
            path.write_text(rp.dumps(doc), encoding="utf-8")
    print(("WROTE" if args.write else "DRY RUN"), "-", changed, "entries completed;", len(manual), "need a manual look")
    for eid, why in manual:
        print("  MANUAL", eid[-30:], "|", why)
    if not args.write:
        k = 0
        for eid, p in plan.items():
            if "rows_after" in p and k < 99:
                k += 1
                print("\n", eid[-30:], "| rows", p["rows_before"], "->", p["rows_after"], f"(+{p['added']} roles)")
                print("   OLD tail:", p["old"][-70:]); print("   NEW tail:", p["new"][len(p["old"]) - 25:][:200])


if __name__ == "__main__":
    main()
