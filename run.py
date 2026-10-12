"""Entry point for the local art-portfolio admin.

This never runs on the internet: it binds to 127.0.0.1 so only this machine can
reach it. Start it with:

    ./venv/bin/python run.py

Then open http://127.0.0.1:5000 in a browser.
"""

import webbrowser

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Only open a browser tab when launched directly (not under pytest).
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
