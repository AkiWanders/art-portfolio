"""The application factory.

``create_app()`` builds a fresh Flask app: it makes sure the folders exist,
loads a secret key, and plugs in the admin routes. Tests call this too, so the
app never depends on module-level state.
"""

from __future__ import annotations

import os

from flask import Flask

from . import store


def _secret_key() -> bytes:
    """A stable key for flash messages, stored beside the project (gitignored)."""
    path = store.ROOT / ".secret_key"
    if not path.exists():
        path.write_bytes(os.urandom(32))
        path.chmod(0o600)
    return path.read_bytes()


def create_app() -> Flask:
    store.ensure_dirs()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = _secret_key()
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # allow big .kra uploads

    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    return app
