"""The admin routes -- the private half of the project.

Everything here is reached only from 127.0.0.1, because that is the only place
``run.py`` binds the server. The routes read and write through ``store`` and
call ``publish`` when you press the publish button.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from . import publish, store

bp = Blueprint("admin", __name__)


def _upload():
    """Return ``(filename, stream)`` for the posted image, or ``(None, None)``."""
    file = request.files.get("image")
    if file and file.filename:
        return file.filename, file.stream
    return None, None


def _form_fields() -> dict:
    """Flask form data as a plain dict, keeping repeated link fields as lists."""
    fields = request.form.to_dict()
    fields["link_label"] = request.form.getlist("link_label")
    fields["link_url"] = request.form.getlist("link_url")
    return fields


@bp.get("/")
def dashboard():
    data = store.load_data()
    return render_template(
        "dashboard.html",
        artworks=store.list_artworks(),
        site=data["site"],
        git=publish.status(),
    )


@bp.route("/artwork/new", methods=["GET", "POST"])
def new_artwork():
    if request.method == "POST":
        filename, stream = _upload()
        art = store.add_artwork(_form_fields(), filename, stream)
        flash(f'Added "{art["title"]}".', "success")
        return redirect(url_for("admin.dashboard"))
    return render_template(
        "edit.html", art=None, site=store.load_data()["site"],
        heading="Add a new artwork", action=url_for("admin.new_artwork"),
    )


@bp.route("/artwork/<art_id>/edit", methods=["GET", "POST"])
def edit_artwork(art_id: str):
    art = store.get_artwork(art_id)
    if art is None:
        flash("That artwork no longer exists.", "error")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        filename, stream = _upload()
        updated = store.update_artwork(art_id, _form_fields(), filename, stream)
        flash(f'Saved "{updated["title"]}".', "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "edit.html", art=art, site=store.load_data()["site"],
        heading=f'Edit "{art["title"]}"',
        action=url_for("admin.edit_artwork", art_id=art_id),
    )


@bp.post("/artwork/<art_id>/delete")
def delete_artwork(art_id: str):
    if store.delete_artwork(art_id):
        flash("Artwork deleted.", "success")
    else:
        flash("That artwork no longer exists.", "error")
    return redirect(url_for("admin.dashboard"))


@bp.post("/artwork/<art_id>/move/<direction>")
def move_artwork(art_id: str, direction: str):
    if direction not in ("up", "down"):
        flash("Unknown move direction.", "error")
    elif store.reorder(art_id, direction):
        flash("Gallery order updated.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        store.update_site(_form_fields())
        flash("Site settings saved.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("settings.html", site=store.load_data()["site"])


@bp.post("/publish")
def do_publish():
    result = publish.publish(request.form.get("message", ""))
    flash(result["message"], "success" if result["ok"] else "error")
    return redirect(url_for("admin.dashboard"))


@bp.get("/preview/")
@bp.get("/preview/<path:path>")
def preview(path: str = "index.html"):
    """Serve the public site from docs/ so you can check it before publishing."""
    return send_from_directory(store.SITE_DIR, path)
