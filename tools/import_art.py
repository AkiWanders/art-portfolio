"""Import a batch of images from a folder into the gallery.

Handy for the first big fill-up, or if you keep your art in a folder and would
rather not upload piece by piece through the browser.

    ./venv/bin/python tools/import_art.py "/path/to/folder" --tag concept

Only files directly inside the folder (not sub-folders) are imported, and the
file name becomes the title. Safe to run more than once: existing titles are
skipped.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="folder containing the images")
    parser.add_argument("--year", default="", help="year to set on every piece")
    parser.add_argument("--medium", default="", help="medium to set on every piece")
    parser.add_argument("--tag", action="append", default=[], help="tag (repeatable)")
    parser.add_argument("--recursive", action="store_true", help="also look in sub-folders")
    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error(f"not a folder: {args.folder}")

    pattern = args.folder.rglob("*") if args.recursive else args.folder.glob("*")
    files = sorted(p for p in pattern if p.is_file() and p.suffix.lower() in store.VALID_EXTS)
    if not files:
        print("No importable images found.")
        return 1

    existing = {a["title"].lower() for a in store.list_artworks()}
    imported = 0

    for path in files:
        title = path.stem.strip().replace("  ", " ").title()
        if title.lower() in existing:
            print(f"skip  {title}")
            continue
        with path.open("rb") as fh:
            store.add_artwork(
                {
                    "title": title,
                    "year": args.year,
                    "medium": args.medium,
                    "tags": ",".join(args.tag),
                    "alt": "",
                    "featured": False,
                },
                path.name,
                fh,
            )
        existing.add(title.lower())
        imported += 1
        print(f"added {title}")

    print(f"\n{imported} artwork(s) imported into {store.SITE_DIR}.")
    print("Open the admin and press Publish to put them online.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
