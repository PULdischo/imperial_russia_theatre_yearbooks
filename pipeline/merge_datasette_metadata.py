#!/usr/bin/env python3
"""Copy the site title, description and table descriptions from docs/datasette_metadata.json
into the metadata file used to publish (which also holds the plugin settings and password hash).

The tracked file has no "plugins" block on purpose, so no secret is kept in git. This script
replaces only "title", "description" and "databases" in the publish file and leaves "plugins"
(and any other key) as it is.

    uv run python pipeline/merge_datasette_metadata.py \
        --publish-file outputs/full_run/datasette_metadata_cloudrun.json
"""
import argparse
import json
import shutil
from pathlib import Path

TRACKED = Path(__file__).parent.parent / "docs" / "datasette_metadata.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish-file", type=Path, required=True)
    ap.add_argument("--tracked-file", type=Path, default=TRACKED)
    a = ap.parse_args()
    tracked = json.loads(a.tracked_file.read_text(encoding="utf-8"))
    if "plugins" in tracked:
        raise SystemExit(f"{a.tracked_file} must not hold a plugins block (secrets stay out of git)")
    publish = json.loads(a.publish_file.read_text(encoding="utf-8")) if a.publish_file.exists() else {}
    if a.publish_file.exists():
        shutil.copy2(a.publish_file, a.publish_file.with_suffix(".json.bak"))
    for key in ("title", "description", "databases"):
        publish[key] = tracked[key]
    a.publish_file.write_text(json.dumps(publish, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = len(tracked["databases"]["research_dataset"]["tables"])
    print(f"{a.publish_file}: title, description and {n} table descriptions updated; "
          f"other keys kept ({', '.join(k for k in publish if k not in ('title', 'description', 'databases')) or 'none'})")


if __name__ == "__main__":
    main()
