"""Build arbitration packets for a reading round (issue #150).

    uv run python docs/eval/balletartists_credit_audit_2026-10-10/make_arbitration.py \
        --comparison comparison3.csv --worklist worklist3.csv --prefix r3 --first-chunk 6 --n-chunks 3

Uses the same word alignment as apply_fixes.py (word/number tokens only). Differences are sorted into:
script (applied without arbitration), case (left as stored), digit (applied when the reader's own numbers add up,
else arbitrated), letters / structure (arbitrated). Candidates are shuffled per item so an arbiter cannot tell which
is the stored reading. Writes chunks/arb_NN.csv and extends arbitration_key.json.
"""
import argparse, csv, difflib, json, os, random, re, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOMO = str.maketrans({'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у', 'k': 'к', 'A': 'А', 'B': 'В',
                      'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т', 'X': 'Х', 'κ': 'к', 'ο': 'о'})
SPAN = re.compile(r"[^\W\d_]+|\d+", re.U)
words = lambda s: SPAN.findall(s or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--comparison", required=True)
    ap.add_argument("--worklist", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--first-chunk", type=int, required=True)
    ap.add_argument("--n-chunks", type=int, default=3)
    ap.add_argument("--seed", type=int, default=31)
    a = ap.parse_args()
    comp = list(csv.DictReader(open(HERE / a.comparison, encoding="utf-8")))
    work = {r["entry_id"]: r for r in csv.DictReader(open(HERE / a.worklist, encoding="utf-8"))}
    key = json.load(open(HERE / "arbitration_key.json", encoding="utf-8"))
    random.seed(a.seed)
    cnt = collections.Counter(); packets = []; kinds = collections.Counter()
    for x in comp:
        if x["verdict"] in ("AGREE", "NO_REPORT"):
            continue
        if x["read"] in ("NONE PRINTED", "NOT FOUND", ""):
            continue
        A, B = words(x["stored"]), words(x["read"])
        sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            if op == "replace" and i2 - i1 == j2 - j1:
                pairs = [(A[i], B[j]) for i, j in zip(range(i1, i2), range(j1, j2))]
            else:
                pairs = [(" ".join(A[i1:i2]), " ".join(B[j1:j2]))]
                if not pairs[0][0] or "Оставил" in pairs[0][0]:
                    kinds["structure (skipped: insert / departure note)"] += 1
                    continue
            for s, t in pairs:
                if s.translate(HOMO) == t:
                    kinds["script (auto)"] += 1; continue
                if s.casefold() == t.casefold():
                    kinds["case (skipped)"] += 1; continue
                if s.isdigit() and t.isdigit() and x["reader_adds_up"] == "True":
                    kinds["digit (auto: reader adds up)"] += 1; continue
                kinds["arbitrated"] += 1
                eid = x["entry_id"]; cnt[eid] += 1
                iid = f"{a.prefix}_{eid.split('_')[1]}_{eid.split('_')[2]}_{eid.split('_')[3].split('__')[0]}_{eid.split('__')[1]}_i{cnt[eid]}"
                sf = random.random() < 0.5
                oa, ob = (s, t) if sf else (t, s)
                key[iid] = dict(entry_id=eid, A="stored" if sf else "reader", B="reader" if sf else "stored", stored=s, reader=t, kind="digit" if s.isdigit() else "letters")
                w = work[eid]
                packets.append(dict(item_id=iid, entry_id=eid, image=os.path.abspath(w["image"]), list_number=w["list_number"],
                                    name=f"{w['family_name']} {w['first_name']} {w['patronymic']}".strip(),
                                    context=" ".join(B[max(0, j1 - 3):j2 + 3]), option_A=oa or "(nothing there)", option_B=ob or "(nothing there)"))
    json.dump(key, open(HERE / "arbitration_key.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(dict(kinds), "| packets:", len(packets), "in", len({p["entry_id"] for p in packets}), "entries")
    if not packets:
        return
    packets.sort(key=lambda p: p["entry_id"])
    n = min(a.n_chunks, max(1, len(packets) // 12)); per = len(packets) / n
    chunks = [[] for _ in range(n)]; i = 0; seen = 0; last = None
    for p in packets:
        if p["entry_id"] != last and seen >= per * (i + 1) and i < n - 1:
            i += 1
        chunks[i].append(p); seen += 1; last = p["entry_id"]
    for k, ch in enumerate(chunks, a.first_chunk):
        with open(HERE / "chunks" / f"arb_{k:02d}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(packets[0])); w.writeheader(); w.writerows(ch)
        print("arb", k, len(ch), "items")


if __name__ == "__main__":
    main()
