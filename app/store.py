"""All file I/O for the project lives here.

Every other file (the admin routes, the tools script, the tests) goes through
these functions instead of opening files itself. That keeps one rule true for
the whole project: if data is read or written, it happened in this file.

Two kinds of data live here:

* ``docs/data/artworks.json`` -- the site settings and the list of artworks.
  This is the single source of truth. The public page fetches this exact file.
* ``docs/art/*.webp`` -- the compressed images, written when you upload.

The functions check module-level paths (``DATA_FILE``, ``ART_DIR`` ...) each
time they run, so tests can point them at a temporary folder.
"""

from __future__ import annotations

import io
import json
import re
import threading
import unicodedata
import uuid
import zipfile
from datetime import date
from pathlib import Path

from PIL import Image

# --------------------------------------------------------------------------
# Where things live on disk
# --------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "docs"          # the folder GitHub Pages serves
DATA_DIR = SITE_DIR / "data"
ART_DIR = SITE_DIR / "art"
DATA_FILE = DATA_DIR / "artworks.json"

# Images are shrunk so the longest side is at most this many pixels. Big enough
# to look sharp, small enough that the site stays fast.
MAX_EDGE = 1800
WEBP_QUALITY = 82

# Files we accept in an upload / import.
VALID_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".kra"}

# A file-based lock. If two requests arrive at once, this makes them take turns
# so the JSON file can never be half-written.
_LOCK = threading.RLock()

# What the JSON looks like the very first time the project runs.
DEFAULT_DATA = {
    "site": {
        "artist": "SandGrace",
        "tagline": "Concept art, characters and strange worlds",
        "intro": "I paint worlds that do not exist yet.",
        "about": (
            "I am SandGrace, a concept artist. I design characters, creatures "
            "and the places they live in -- then colour them until they feel real."
        ),
        "accent": "#ff5e3a",
        "email": "",
        "links": [
            {"label": "Instagram", "url": ""},
            {"label": "ArtStation", "url": ""},
        ],
    },
    "artworks": [],
}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Turn a title into a safe file name piece: 'Fire Maiden!' -> 'fire-maiden'."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)[:60]


def parse_tags(raw) -> list[str]:
    """Accept 'hero, sand ,, golden' or a real list and return clean tags."""
    if isinstance(raw, list):
        parts = raw
    else:
        parts = re.split(r"[,\n]", str(raw or ""))
    seen, out = set(), []
    for part in parts:
        tag = part.strip()
        key = tag.lower()
        if tag and key not in seen:
            seen.add(key)
            out.append(tag)
    return out


def clean_text(value) -> str:
    return str(value or "").strip()


# --------------------------------------------------------------------------
# Loading and saving the JSON
# --------------------------------------------------------------------------

def ensure_dirs() -> None:
    """Create the folders we need and write the default JSON if it is missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        save_data(json.loads(json.dumps(DEFAULT_DATA)))


def load_data() -> dict:
    """Read artworks.json. If it is missing or broken, fall back to defaults."""
    ensure_dirs()
    try:
        with DATA_FILE.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return json.loads(json.dumps(DEFAULT_DATA))

    # Fill in anything a hand-edit may have removed so the rest of the code
    # never has to check for missing keys.
    base = json.loads(json.dumps(DEFAULT_DATA))
    base["site"].update(data.get("site") or {})
    base["artworks"] = data.get("artworks") or []
    return base


def save_data(data: dict) -> None:
    """Write artworks.json safely: write a temp file, then swap it in."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(DATA_FILE)


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------

def _open_source(filename: str, stream) -> Image.Image:
    """Open an uploaded or on-disk image, understanding Krita .kra files.

    A .kra file is a ZIP archive; inside it, ``mergedimage.png`` is the picture
    flattened to one layer. We pull that out so you can upload a .kra directly.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".kra":
        blob = stream.read() if hasattr(stream, "read") else stream
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            with zf.open("mergedimage.png") as inner:
                image = Image.open(io.BytesIO(inner.read()))
                image.load()
                return image
    if isinstance(stream, (bytes, bytearray)):
        image = Image.open(io.BytesIO(stream))
    else:
        stream.seek(0)
        image = Image.open(stream)
    image.load()
    return image


def import_image(filename: str, stream, art_dir: Path | None = None) -> dict:
    """Save an image into docs/art as a right-sized .webp.

    Returns ``{"file": "...", "w": ..., "h": ...}``. The width and height let
    the public grid reserve the right space before the image loads.
    """
    art_dir = art_dir or ART_DIR
    art_dir.mkdir(parents=True, exist_ok=True)

    image = _open_source(filename, stream)
    if image.mode not in ("RGB", "RGBA", "L"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    original_w, original_h = image.size
    image.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    out_w, out_h = image.size

    stem = slugify(Path(filename).stem) or "artwork"
    name = f"{stem}-{uuid.uuid4().hex[:8]}.webp"
    image.save(art_dir / name, "WEBP", quality=WEBP_QUALITY, method=6)
    return {"file": name, "w": out_w, "h": out_h, "source_w": original_w, "source_h": original_h}


def delete_image(relative_file: str, art_dir: Path | None = None) -> None:
    """Remove an image from docs/art. Missing files are not an error."""
    if not relative_file:
        return
    art_dir = art_dir or ART_DIR
    target = (art_dir / Path(relative_file).name)
    try:
        target.unlink()
    except FileNotFoundError:
        pass


# --------------------------------------------------------------------------
# Artworks
# --------------------------------------------------------------------------

def sort_key(art: dict):
    return (int(art.get("order") or 0), art.get("title", "").lower())


def list_artworks() -> list[dict]:
    return sorted(load_data()["artworks"], key=sort_key)


def get_artwork(art_id: str) -> dict | None:
    for art in load_data()["artworks"]:
        if art.get("id") == art_id:
            return art
    return None


def _next_order(artworks: list[dict]) -> int:
    return max((int(a.get("order") or 0) for a in artworks), default=0) + 1


def _renumber(artworks: list[dict]) -> None:
    """Number the pieces 1, 2, 3 ... in the order they are given."""
    for position, art in enumerate(artworks, start=1):
        art["order"] = position


def add_artwork(fields: dict, image_filename=None, image_stream=None) -> dict:
    """Create one artwork. If an image is given it is imported first."""
    with _LOCK:
        data = load_data()
        art = {
            "id": uuid.uuid4().hex[:12],
            "title": clean_text(fields.get("title")) or "Untitled",
            "year": clean_text(fields.get("year")),
            "medium": clean_text(fields.get("medium")),
            "tags": parse_tags(fields.get("tags")),
            "alt": clean_text(fields.get("alt")),
            "featured": bool(fields.get("featured")),
            "order": _next_order(data["artworks"]),
            "added": date.today().isoformat(),
            "file": "",
            "w": 0,
            "h": 0,
        }
        if image_filename and image_stream is not None:
            info = import_image(image_filename, image_stream)
            art.update({"file": f"art/{info['file']}", "w": info["w"], "h": info["h"]})
        data["artworks"].append(art)
        save_data(data)
        return art


def update_artwork(art_id: str, fields: dict, image_filename=None, image_stream=None) -> dict | None:
    """Change an existing artwork. Replacing the image deletes the old file."""
    with _LOCK:
        data = load_data()
        for art in data["artworks"]:
            if art.get("id") != art_id:
                continue
            art["title"] = clean_text(fields.get("title")) or art.get("title") or "Untitled"
            art["year"] = clean_text(fields.get("year"))
            art["medium"] = clean_text(fields.get("medium"))
            art["tags"] = parse_tags(fields.get("tags"))
            art["alt"] = clean_text(fields.get("alt"))
            art["featured"] = bool(fields.get("featured"))
            if image_filename and image_stream is not None:
                info = import_image(image_filename, image_stream)
                delete_image(art.get("file", ""))
                art.update({"file": f"art/{info['file']}", "w": info["w"], "h": info["h"]})
            save_data(data)
            return art
    return None


def delete_artwork(art_id: str) -> bool:
    with _LOCK:
        data = load_data()
        keep = [a for a in data["artworks"] if a.get("id") != art_id]
        if len(keep) == len(data["artworks"]):
            return False
        for art in data["artworks"]:
            if art.get("id") == art_id:
                delete_image(art.get("file", ""))
        data["artworks"] = sorted(keep, key=sort_key)
        _renumber(data["artworks"])
        save_data(data)
        return True


def reorder(art_id: str, direction: str) -> bool:
    """Move an artwork one place earlier or later in the gallery order."""
    with _LOCK:
        data = load_data()
        arts = sorted(data["artworks"], key=sort_key)
        index = next((i for i, a in enumerate(arts) if a.get("id") == art_id), None)
        if index is None:
            return False
        other = index - 1 if direction == "up" else index + 1
        if not (0 <= other < len(arts)):
            return False
        arts[index], arts[other] = arts[other], arts[index]
        _renumber(arts)
        data["artworks"] = arts
        save_data(data)
        return True


def update_site(fields: dict) -> dict:
    """Save the site-wide settings (name, tagline, about, accent, links)."""
    with _LOCK:
        data = load_data()
        site = data["site"]
        for key in ("artist", "tagline", "intro", "about", "accent", "email"):
            if key in fields:
                site[key] = clean_text(fields.get(key))
        labels = fields.get("link_label") or []
        urls = fields.get("link_url") or []
        links = [
            {"label": clean_text(lbl), "url": clean_text(url)}
            for lbl, url in zip(labels, urls)
            if clean_text(lbl) or clean_text(url)
        ]
        if links:
            site["links"] = links
        save_data(data)
        return site


def update_site_links(links: list[dict]) -> dict:
    """Replace the contact links list wholesale (used by tests and tools)."""
    with _LOCK:
        data = load_data()
        data["site"]["links"] = [
            {"label": clean_text(l.get("label")), "url": clean_text(l.get("url"))}
            for l in links
        ]
        save_data(data)
        return data["site"]
