"""1901-02 Repertoire: extraction errors found by the blind read of every column, both cities (2026-10-29,
docs/eval/scan_audit/1901-02_scan_reads.csv) and checked by Claude on ForUpload_1901-02_Repertoire.pdf (page index = pNNN).
Reconciliation ledger 1901-02.

1. Copied receipts (8 cells). These charity cells print NO receipts; the extraction gave each the figure of the
   neighbouring column on the same row:
   - Александринскій 26 Jan 1902 (p024), «Нищіе духомъ» for the Клиническій Повивальный Институтъ: 2006 р. is the
     Михайловскій's (Rousselle benefit);
   - Маріинскій 7, 8, 10, 11, 12, 13, 14 Mar 1902 (p030), charity bills (Vienna operetta, Japanese troupe, Glinka
     concert, Любимовъ's opera, …): each holds the Александринскій German troupe's figure for that day.
   Together 12,373.14 р.; with them removed the SP German line is exact (with its half-kopecks) and every SP charity
   event without printed receipts is outside the printed totals, as in other seasons.
2. Новый 6 Nov 1901 (p011), «Разрывъ-трава»: «400 р. 83 к.» -> «400 р. 88 к.» (clear on the scan; with it Новый drama
   + its three drama/ballet bills is exact to the kopeck).

Not here (damaged glyphs, RG to read in the volume): Большой 30 Dec 1901 matinée «1?31 р. 35 к.», Малый 24 Jan 1902
«9?5 р. 81 к.» (stored 955), Маріинскій 14 Dec 1901 «3?33 р. 50 к.» (stored 3133), Маріинскій 24 Jan 1902
«35?0 р. 5? к.» (stored 3590.59). Not changed either: 14 Nov 1901 Александринскій and Михайловскій stay one event each
(RG 2026-10-12, unlabelled two-session cells stay as printed).

uv run python docs/eval/reconciliation/fix_1901_02_scan_reads.py [--raw-dir DIR] [--write]"""
import json, sys
from pathlib import Path
RAW = Path(sys.argv[sys.argv.index("--raw-dir") + 1]) if "--raw-dir" in sys.argv else \
    Path(__file__).resolve().parents[3] / "outputs/full_run/raw"
TAG = "scan 2026-10-29 (blind column read, 1901-02 reconciliation)"


def load(pg):
    p = RAW / f"repertoire_1901-02_{pg}.raw.json"; t = p.read_text(encoding="utf-8"); d = json.loads(t)
    for ind in (2, 4, 1, None):
        for ea in (False, True):
            for tr in ("", "\n"):
                if json.dumps(d, indent=ind, ensure_ascii=ea) + tr == t:
                    return p, d, (ind, ea, tr)
    raise SystemExit(f"format not recognised: {p}")


def note(S, msg):
    S["_fix_note"] = (S["_fix_note"] + "; " if S.get("_fix_note") else "") + f"{TAG}: {msg}"


def save(p, d, fmt):
    if "--write" in sys.argv:
        p.write_text(json.dumps(d, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2], encoding="utf-8")


def norm(r):
    return (r or "").replace(" ", "").replace("¹/₂", "½")


def find(ss, day, theater, receipts):
    hits = [S for S in ss if S["date_text"].split()[0] == day and S["theater"].startswith(theater)
            and S["receipts_text"] == receipts]
    assert len(hits) == 1, (day, theater, receipts, len(hits))
    return hits[0]


# 1. copied receipts
COPIES = {"p024": [("26", "Александрин", "2006 р. — к.", "Михайловскій")],
          "p030": [("7", "Маріин", "999 р. 70 к.", "Александринскій"), ("8", "Маріин", "1502 р. 87 к.", "Александринскій"),
                   ("10", "Маріин", "2240 р. 20 к.", "Александринскій"), ("11", "Маріин", "1896 р. 68 к.", "Александринскій"),
                   ("12", "Маріин", "1024 р. 30 к.", "Александринскій"), ("13", "Маріин", "1551 р. 74½ к.", "Александринскій"),
                   ("14", "Маріин", "1151 р. 65 к.", "Александринскій")]}
for pg, cells in COPIES.items():
    p, d, f = load(pg)
    for day, th, rec, owner in cells:
        S = find(d["sessions"], day, th, rec)
        # the owner column prints the same figure on the same row
        assert [T for T in d["sessions"] if T["date_text"].split()[0] == day and T["theater"].startswith(owner[:8])
                and norm(T["receipts_text"]) == norm(rec)], \
            (pg, day, owner)
        S["receipts_text"] = None
        note(S, f"receipts «{rec}» removed: the cell prints none; the figure is the {owner}'s on the same row")
        print(pg, S["date_text"], S["theater"][:12], "receipts -> None")
    save(p, d, f)

# 2. Новый 6 Nov 1901
p, d, f = load("p011"); S = find(d["sessions"], "6", "Новый", "400 р. 83 к.")
assert S["works"][0]["work_title"].startswith("Разрывъ"), S
S["receipts_text"] = "400 р. 88 к."; note(S, "receipts «400 р. 83 к.» -> «400 р. 88 к.» (second 8 read as 3)")
save(p, d, f); print("p011", S["date_text"], S["receipts_text"])

print("WROTE" if "--write" in sys.argv else "DRY RUN", RAW)
