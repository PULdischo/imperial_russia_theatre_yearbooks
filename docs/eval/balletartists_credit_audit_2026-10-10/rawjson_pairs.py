"""Read and write the raw *.raw.json files WITHOUT losing duplicate keys or changing the layout.

23 of the 392 BalletArtists raw files contain objects with a repeated key (Python's json keeps the
last one, so the pipeline never sees the others). A plain json.load / json.dump would silently drop the
earlier copies and rewrite those files. This module keeps objects as ordered lists of pairs, so
load -> dump is byte-identical (checked on all 392 files by selftest()) and an edit touches only what
it changes. When a key is repeated, `get`/`set` act on the LAST one, which is the one Python (and so the
pipeline) reads.

Layout reproduced: json.dumps(indent=2, ensure_ascii=False), no trailing newline.
"""
from __future__ import annotations

import glob
import json
import sys


class Obj(list):
    """A JSON object as an ordered list of (key, value) pairs, duplicates preserved."""

    def last_index(self, key):
        for i in range(len(self) - 1, -1, -1):
            if self[i][0] == key:
                return i
        return None

    def get(self, key, default=None):
        i = self.last_index(key)
        return default if i is None else self[i][1]

    def set(self, key, value):
        i = self.last_index(key)
        if i is None:
            self.append((key, value))
        else:
            self[i] = (key, value)


def loads(text: str):
    return json.loads(text, object_pairs_hook=Obj)


def _dump(v, level: int, out: list):
    pad = "  " * (level + 1)
    end = "  " * level
    if isinstance(v, Obj):
        if not v:
            out.append("{}")
            return
        out.append("{\n")
        for n, (k, x) in enumerate(v):
            out.append(pad + json.dumps(k, ensure_ascii=False) + ": ")
            _dump(x, level + 1, out)
            out.append(",\n" if n < len(v) - 1 else "\n")
        out.append(end + "}")
    elif isinstance(v, list):
        if not v:
            out.append("[]")
            return
        out.append("[\n")
        for n, x in enumerate(v):
            out.append(pad)
            _dump(x, level + 1, out)
            out.append(",\n" if n < len(v) - 1 else "\n")
        out.append(end + "]")
    else:
        out.append(json.dumps(v, ensure_ascii=False))


def dumps(v) -> str:
    out: list = []
    _dump(v, 0, out)
    return "".join(out)


def selftest(pattern: str) -> int:
    files = sorted(glob.glob(pattern))
    bad = [f for f in files if dumps(loads(open(f, encoding="utf-8").read())) != open(f, encoding="utf-8").read().rstrip("\n")]
    print(f"{len(files)} files, {len(bad)} do not round-trip byte for byte")
    for f in bad[:10]:
        print("  ", f)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selftest(sys.argv[1] if len(sys.argv) > 1 else "outputs/full_run/raw/*.raw.json"))
