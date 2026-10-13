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


def _uploads():
    """Every posted image, as a list of ``(filename, stream)`` pairs.

    The form posts them under ``images`` (multiple). ``image`` (singular) is
    still read so an old form or a script keeps working.
    """
    pairs = []
    for key in ("images", "image"):
        for file in request.files.getlist(key):
            if file and file.filename:
                pairs.append((file.filename, file.stream))
    return pairs


def _form_fields() -> dict:
    """Flask form data as a plain dict, keeping repeated link fields as lists."""
    fields = request.form.to_dict()
    fields["link_label"] = request.form.getlist("link_label")
    fields["link_url"] = request.form.getlist("link_url")
    return fields


def _posted_banner():
    """``(filename, stream)`` for a posted banner image, or ``(None, None)``."""
    file = request.files.get("banner")
    if file and file.filename:
        return file.filename, file.stream
    return None, None


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
        art = store.add_artwork(_form_fields(), uploads=_uploads())
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
        updated = store.update_artwork(art_id, _form_fields(), uploads=_uploads())
        flash(f'Saved "{updated["title"]}".', "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "edit.html", art=art, site=store.load_data()["site"],
        heading=f'Edit "{art["title"]}"',
        action=url_for("admin.edit_artwork", art_id=art_id),
    )


@bp.post("/artwork/<art_id>/image/cover")
def cover_image(art_id: str):
    if store.set_cover(art_id, request.form.get("image", "")):
        flash("Cover image updated.", "success")
    else:
        flash("That image is no longer there.", "error")
    return redirect(url_for("admin.edit_artwork", art_id=art_id))


@bp.post("/artwork/<art_id>/image/move/<direction>")
def move_image(art_id: str, direction: str):
    if direction not in ("up", "down"):
        flash("Unknown move direction.", "error")
    elif store.move_image(art_id, request.form.get("image", ""), direction):
        flash("Image order updated.", "success")
    return redirect(url_for("admin.edit_artwork", art_id=art_id))


@bp.post("/artwork/<art_id>/image/delete")
def delete_image(art_id: str):
    if store.remove_image(art_id, request.form.get("image", "")):
        flash("Image removed.", "success")
    else:
        flash("That image is no longer there.", "error")
    return redirect(url_for("admin.edit_artwork", art_id=art_id))


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
        filename, stream = _posted_banner()
        store.update_site(_form_fields(), filename, stream)
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
