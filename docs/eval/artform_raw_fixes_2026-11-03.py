"""Raw misreadings found while giving research.work an art form (2026-11-03), scan-checked by
Claude and applied with RG's approval ("Yes, apply them" / "Yes, promote"). Exact-string
edits to the raw JSON, so the files keep their formatting; the script stops without writing
anything if a string is not found exactly as expected (already applied, or the file changed).

    uv run python docs/eval/artform_raw_fixes_2026-11-03.py <raw dir>

- 1898-99 p.24, Маріинскій 23 Jan 1899: print «Прологъ и 1-е д. оп. Паяцы.» with no genre;
  raw had «Палцы» and a genre «др.» that is not on the page.
- 1896-97 p.16, Маріинскій 9 Jan 1897: print «Паяцы, оп.»; raw had «Палцы».
- 1898-99 p.36, Михайловскій: print «Chéri! vaud.» on 2 printings read as «Chéri vaud.».
"""
import sys
from pathlib import Path

FIXES = [
    ("repertoire_1898-99_p022.raw.json",
     '"work_title": "Прологъ и 1-е д. оп. Палцы",\n          "genre": "др."',
     '"work_title": "Прологъ и 1-е д. оп. Паяцы",\n          "genre": null', 1),
    ("repertoire_1896-97_pair016.raw.json", '"work_title": "Палцы"', '"work_title": "Паяцы"', 1),
    ("repertoire_1898-99_p034.raw.json", '"work_title": "Chéri vaud."', '"work_title": "Chéri! vaud."', 2),
]


def main(raw_dir: Path) -> None:
    new = {}
    for name, old, rep, count in FIXES:
        text = new.get(name) or (raw_dir / name).read_text(encoding="utf-8")
        found = text.count(old)
        if found != count:
            raise SystemExit(f"{name}: expected {count} x {old!r}, found {found}; nothing written")
        new[name] = text.replace(old, rep)
    for name, text in new.items():
        (raw_dir / name).write_text(text, encoding="utf-8")
        print(f"fixed {name}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
