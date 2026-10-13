"""Tests for the data layer.

Each test runs against a throwaway copy of the project folders (``tmp_path``)
so nothing here can touch your real gallery.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from PIL import Image

from app import store


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Point store at a temporary site folder instead of docs/."""
    site = tmp_path / "docs"
    monkeypatch.setattr(store, "SITE_DIR", site)
    monkeypatch.setattr(store, "DATA_DIR", site / "data")
    monkeypatch.setattr(store, "ART_DIR", site / "art")
    monkeypatch.setattr(store, "DATA_FILE", site / "data" / "artworks.json")
    return site


def png_bytes(width=2400, height=1200, colour=(200, 90, 40)) -> io.BytesIO:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def kra_bytes(width=800, height=600) -> io.BytesIO:
    """A .kra file is a zip holding mergedimage.png."""
    image = io.BytesIO()
    Image.new("RGBA", (width, height), (10, 200, 150, 255)).save(image, "PNG")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("mergedimage.png", image.getvalue())
    buffer.seek(0)
    return buffer


# ---- basics --------------------------------------------------------------

def test_ensure_dirs_creates_default_json(sandbox):
    store.ensure_dirs()
    assert store.DATA_FILE.exists()
    data = store.load_data()
    assert data["artworks"] == []
    assert data["site"]["artist"]


def test_save_and_load_roundtrip(sandbox):
    store.ensure_dirs()
    data = store.load_data()
    data["site"]["artist"] = "Tester"
    store.save_data(data)
    assert store.load_data()["site"]["artist"] == "Tester"


def test_missing_file_falls_back_to_defaults(sandbox):
    store.DATA_DIR.mkdir(parents=True)
    assert store.load_data()["artworks"] == []


def test_slugify():
    assert store.slugify("Fire Maiden!") == "fire-maiden"
    assert store.slugify("  A  B  ") == "a-b"


def test_parse_tags_cleans_and_dedupes():
    assert store.parse_tags("hero, Sand , hero,,") == ["hero", "Sand"]


# ---- images --------------------------------------------------------------

def test_import_image_resizes_and_converts_to_webp(sandbox):
    info = store.import_image("big.png", png_bytes(4000, 2000))
    assert info["file"].endswith(".webp")
    assert max(info["w"], info["h"]) == store.MAX_EDGE          # shrunk
    assert round(info["w"] / info["h"]) == 2                    # shape kept
    assert (store.ART_DIR / info["file"]).exists()


def test_import_small_image_is_left_at_size(sandbox):
    info = store.import_image("small.png", png_bytes(300, 200))
    assert (info["w"], info["h"]) == (300, 200)


def test_import_from_kra_reads_merged_image(sandbox):
    info = store.import_image("piece.kra", kra_bytes(800, 600))
    assert info["w"] == 800 and info["h"] == 600
    assert info["file"].startswith("piece-")


# ---- artworks ------------------------------------------------------------

def test_add_artwork_stores_fields_and_image(sandbox):
    art = store.add_artwork(
        {"title": "Hero", "year": "2025", "medium": "Painting", "tags": "hero, sand"},
        "hero.png", png_bytes(1000, 1000),
    )
    assert art["title"] == "Hero"
    assert art["tags"] == ["hero", "sand"]
    assert art["file"].startswith("art/")
    assert art["images"] == [{"file": art["file"], "w": 1000, "h": 1000}]
    assert (store.SITE_DIR / art["file"]).exists()
    assert store.get_artwork(art["id"])["year"] == "2025"


def test_add_artwork_with_several_images(sandbox):
    art = store.add_artwork(
        {"title": "Process"},
        uploads=[("sketch.png", png_bytes(400, 400)), ("final.png", png_bytes(500, 500))],
    )
    assert len(art["images"]) == 2
    # The first uploaded image becomes the cover.
    assert art["file"] == art["images"][0]["file"]
    for image in art["images"]:
        assert (store.SITE_DIR / image["file"]).exists()


def test_legacy_artwork_gains_an_images_list(sandbox):
    """A record written before multi-image pieces still loads cleanly."""
    store.ensure_dirs()
    data = store.load_data()
    data["artworks"].append({"id": "old", "title": "Old", "file": "art/old-1.webp", "w": 10, "h": 20})
    store.save_data(data)

    art = store.get_artwork("old")
    assert art["images"] == [{"file": "art/old-1.webp", "w": 10, "h": 20}]
    assert art["file"] == "art/old-1.webp"      # cover mirrors the only image

    # Saving it back must not lose the promoted image.
    store.update_artwork("old", {"title": "Old", "tags": "x"})
    assert store.get_artwork("old")["images"] == [{"file": "art/old-1.webp", "w": 10, "h": 20}]


def test_default_title_when_blank(sandbox):
    art = store.add_artwork({"title": "  "})
    assert art["title"] == "Untitled"


def test_update_artwork_adds_images_without_touching_the_others(sandbox):
    art = store.add_artwork({"title": "Draft"}, "one.png", png_bytes(400, 400))
    first = art["file"]

    updated = store.update_artwork(art["id"], {"title": "Final", "tags": "x"},
                                   "two.png", png_bytes(400, 400))
    assert updated["title"] == "Final"
    assert len(updated["images"]) == 2
    assert updated["file"] == first                      # cover unchanged
    assert (store.SITE_DIR / first).exists()             # old file kept


def test_update_without_image_keeps_file(sandbox):
    art = store.add_artwork({"title": "Keep"}, "k.png", png_bytes(400, 400))
    updated = store.update_artwork(art["id"], {"title": "Renamed"})
    assert updated["file"] == art["file"]
    assert len(updated["images"]) == 1
    assert updated["title"] == "Renamed"


def test_set_cover_moves_the_chosen_image_first(sandbox):
    art = store.add_artwork({"title": "Set"},
                            uploads=[("a.png", png_bytes()), ("b.png", png_bytes())])
    second = art["images"][1]["file"]

    assert store.set_cover(art["id"], second) is True
    after = store.get_artwork(art["id"])
    assert after["file"] == second
    assert after["images"][0]["file"] == second

    assert store.set_cover(art["id"], "art/not-there.webp") is False


def test_move_image_changes_order(sandbox):
    art = store.add_artwork({"title": "Move"},
                            uploads=[("a.png", png_bytes()), ("b.png", png_bytes())])
    first, second = (image["file"] for image in art["images"])

    assert store.move_image(art["id"], second, "up") is True
    assert [i["file"] for i in store.get_artwork(art["id"])["images"]] == [second, first]
    assert store.move_image(art["id"], second, "up") is False   # already first
    assert store.move_image(art["id"], "art/nope.webp", "down") is False


def test_remove_image_deletes_only_that_file(sandbox):
    art = store.add_artwork({"title": "Trim"},
                            uploads=[("a.png", png_bytes()), ("b.png", png_bytes())])
    first, second = (image["file"] for image in art["images"])

    assert store.remove_image(art["id"], first) is True
    after = store.get_artwork(art["id"])
    assert [i["file"] for i in after["images"]] == [second]
    assert after["file"] == second                       # cover re-pointed
    assert not (store.SITE_DIR / first).exists()
    assert (store.SITE_DIR / second).exists()


def test_delete_artwork_removes_every_image(sandbox):
    art = store.add_artwork({"title": "Bye"},
                            uploads=[("a.png", png_bytes()), ("b.png", png_bytes())])
    files = [image["file"] for image in art["images"]]

    assert store.delete_artwork(art["id"]) is True
    assert store.get_artwork(art["id"]) is None
    for relative in files:
        assert not (store.SITE_DIR / relative).exists()


def test_update_site_saves_and_removes_a_banner(sandbox):
    site = store.update_site({"artist": "Me"}, "wide.png", png_bytes(3000, 1000))
    banner = site["banner"]
    assert banner.startswith("art/banner-")
    assert (store.SITE_DIR / banner).exists()

    # The banner is capped at its own, larger size.
    info = store.import_image("wide.png", png_bytes(3000, 1000),
                              max_edge=store.BANNER_MAX_EDGE, prefix="banner-")
    assert max(info["w"], info["h"]) == store.BANNER_MAX_EDGE

    store.update_site({"artist": "Me", "remove_banner": "1"})
    assert store.load_data()["site"]["banner"] == ""
    assert not (store.SITE_DIR / banner).exists()


def test_delete_artwork_removes_record_and_image(sandbox):
    art = store.add_artwork({"title": "Bye"}, "b.png", png_bytes(400, 400))
    assert store.delete_artwork(art["id"]) is True
    assert store.get_artwork(art["id"]) is None
    assert not (store.SITE_DIR / art["file"]).exists()
    assert store.delete_artwork("nope") is False


def test_reorder_moves_pieces(sandbox):
    a = store.add_artwork({"title": "A"})
    b = store.add_artwork({"title": "B"})
    c = store.add_artwork({"title": "C"})
    assert [x["id"] for x in store.list_artworks()] == [a["id"], b["id"], c["id"]]

    assert store.reorder(c["id"], "up") is True
    assert [x["id"] for x in store.list_artworks()] == [a["id"], c["id"], b["id"]]

    assert store.reorder(a["id"], "up") is False   # already first


def test_update_site_and_links(sandbox):
    store.update_site({
        "artist": "New Name", "tagline": "Tag", "accent": "#123456",
        "link_label": ["Instagram", ""], "link_url": ["https://ig", ""],
    })
    site = store.load_data()["site"]
    assert site["artist"] == "New Name"
    assert site["accent"] == "#123456"
    assert site["links"] == [{"label": "Instagram", "url": "https://ig"}]
