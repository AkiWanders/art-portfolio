"""Entry point for the local art-portfolio studio.

This never runs on the internet: it binds to 127.0.0.1 so only this machine can
reach it. Start it with:

    ./launch.sh                 (double-click friendly)
    ./venv/bin/python run.py    (or directly)

Then open http://127.0.0.1:5050 in a browser.

Port 5050 is on purpose: the Bakery app already uses 5000, and two apps cannot
share a port.
"""

import webbrowser

from app import create_app

PORT = 5050

app = create_app()

if __name__ == "__main__":
    # Only open a browser tab when launched directly (not under pytest).
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
