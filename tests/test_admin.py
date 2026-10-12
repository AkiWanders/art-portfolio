"""Tests for the admin routes, using Flask's own test client.

No real server is started: ``create_app`` is pointed at a temporary folder and
called directly.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app import create_app, store


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    site = tmp_path / "docs"
    monkeypatch.setattr(store, "ROOT", tmp_path)
    monkeypatch.setattr(store, "SITE_DIR", site)
    monkeypatch.setattr(store, "DATA_DIR", site / "data")
    monkeypatch.setattr(store, "ART_DIR", site / "art")
    monkeypatch.setattr(store, "DATA_FILE", site / "data" / "artworks.json")
    site.mkdir(parents=True)
    (site / "index.html").write_text("<h1>preview</h1>", encoding="utf-8")
    return site


@pytest.fixture()
def client(sandbox):
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def png(width=600, height=600) -> io.BytesIO:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 60, 200)).save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def test_dashboard_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Publish" in response.data


def test_preview_serves_the_public_site(client):
    response = client.get("/preview/index.html")
    assert response.status_code == 200
    assert b"preview" in response.data


def test_create_artwork_from_form(client, sandbox):
    response = client.post(
        "/artwork/new",
        data={"title": "New Piece", "year": "2025", "tags": "a, b",
              "image": (png(), "new.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    artworks = store.list_artworks()
    assert len(artworks) == 1
    assert artworks[0]["title"] == "New Piece"
    assert (sandbox / artworks[0]["file"]).exists()


def test_edit_and_delete_artwork(client):
    client.post("/artwork/new",
                data={"title": "Before", "image": (png(), "x.png")},
                content_type="multipart/form-data")
    art = store.list_artworks()[0]

    client.post(f"/artwork/{art['id']}/edit",
                data={"title": "After", "tags": "z"},
                content_type="multipart/form-data")
    assert store.get_artwork(art["id"])["title"] == "After"

    client.post(f"/artwork/{art['id']}/delete")
    assert store.list_artworks() == []


def test_edit_missing_artwork_redirects(client):
    response = client.get("/artwork/does-not-exist/edit")
    assert response.status_code == 302


def test_move_artwork(client):
    for n in ("A", "B"):
        client.post("/artwork/new", data={"title": n, "image": (png(), f"{n}.png")},
                    content_type="multipart/form-data")
    last = store.list_artworks()[1]
    client.post(f"/artwork/{last['id']}/move/up")
    assert store.list_artworks()[0]["title"] == "B"

    client.post(f"/artwork/{last['id']}/move/sideways")  # unknown direction
    assert store.list_artworks()[0]["title"] == "B"


def test_save_settings(client):
    client.post("/settings", data={
        "artist": "Studio", "tagline": "Cool art", "intro": "hi", "about": "me",
        "accent": "#ff0000", "email": "a@b.c",
        "link_label": ["X"], "link_url": ["https://x.com"],
    })
    site = store.load_data()["site"]
    assert site["artist"] == "Studio"
    assert site["links"][0]["label"] == "X"


def test_publish_without_repo_reports_gracefully(client):
    response = client.post("/publish", data={"message": "try"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"not a git repository" in response.data
