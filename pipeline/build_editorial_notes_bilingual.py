"""Build the side-by-side Russian/English reading file of the editors' notes.

Companion to docs/editorial_notes.md (the finding list). Same conventions as
the Season Reviews bilingual files (pipeline/build_bilingual.py): a reading
copy, not an edition -- quote from the scan, never from this file. Russian
keeps pre-1918 orthography as printed, reflowed (line breaks and soft hyphens
joined); English is a plain, faithful translation with names transliterated.

Source: docs/editorial_notes/text.json, one record per note (transcribed
from the scans 2026-10-20). **The .md is DERIVED.** Edit the JSON, re-run.

Usage:
    uv run python pipeline/build_editorial_notes_bilingual.py \
        [--src docs/editorial_notes/text.json] \
        [--out docs/editorial_notes_bilingual.md]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

KIND = {
    "A": "Editors' note",
    "B": "Editors' note in the text",
    "C": "Announcement in the editors' voice",
    "D": "Unsigned publisher's note",
}


def cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ").strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="docs/editorial_notes/text.json")
    ap.add_argument("--out", default="docs/editorial_notes_bilingual.md")
    a = ap.parse_args()
    raw = Path(a.src).read_bytes()
    notes = json.loads(raw)
    h = hashlib.sha256(raw).hexdigest()[:12]

    out = [
        "# Editors' notes in the Ежегодникъ — Russian / English",
        "",
        f"<!-- generated, do not hand-edit · build: pipeline/build_editorial_notes_bilingual.py",
        f"     source: docs/editorial_notes/text.json · source-hash: {h} · built: {date.today()} -->",
        "",
        "Reading copy, not an edition: quote from the scan. Russian keeps the printed",
        "pre-1918 orthography, reflowed; English is a plain translation with names",
        "transliterated. Finding list with summaries: `docs/editorial_notes.md`.",
        "",
        "## Contents",
        "",
    ]
    for n in notes:
        out.append(f"- [{n['season']} · {n['title']}](#{n['anchor']}) — {KIND[n['kind']]}")
    out.append("")
    for n in notes:
        out += [
            f'<a id="{n["anchor"]}"></a>',
            f"## {n['season']} · {n['title']}",
            "",
            f"*{KIND[n['kind']]}* · `{n['file']}`, PDF p. {n['pdf_page']}"
            + (f" · printed p. {n['printed_page']}" if n.get("printed_page") else ""),
            "",
        ]
        if n.get("context"):
            out += [f"> {n['context']}", ""]
        out += ["| Русскій | English |", "| --- | --- |"]
        for p in n["paragraphs"]:
            out.append(f"| {cell(p['ru'])} | {cell(p['en'])} |")
        out.append("")
        if n.get("notes"):
            out += [f"*Transcription notes:* {n['notes']}", ""]
    Path(a.out).write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {a.out}: {len(notes)} notes, "
          f"{sum(len(n['paragraphs']) for n in notes)} paragraphs")


if __name__ == "__main__":
    main()
