#!/usr/bin/env bash
# Double-click launcher for the Art Portfolio studio.
#
# Starts the private admin app at http://127.0.0.1:5050 and opens it in your
# browser. Safe to run twice: if the studio is already answering we just open
# the browser instead of starting a second copy.
#
# It uses port 5050 on purpose — the Bakery app already uses 5000, and two apps
# fighting over one port would make the "already running" check open the wrong
# thing.
set -uo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PORT=5050
URL="http://127.0.0.1:${PORT}/"

cd "$APP_DIR" || exit 1

# Already running? Just show it.
if curl -fsS -o /dev/null --max-time 2 "$URL" 2>/dev/null; then
    echo "The studio is already running — opening your browser."
    xdg-open "$URL" >/dev/null 2>&1 &
    sleep 1
    exit 0
fi

# First run of a fresh copy: build the Python environment.
if [ ! -x "$APP_DIR/venv/bin/python" ]; then
    echo "Setting up the Python environment (this happens once)…"
    python3 -m venv "$APP_DIR/venv" \
        || { echo "Could not create the virtual environment."; exit 1; }
    "$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt" \
        || { echo "Could not install the dependencies."; exit 1; }
fi

echo "Starting the Art Portfolio studio at $URL   (Ctrl+C to stop)"
"$APP_DIR/venv/bin/python" "$APP_DIR/run.py"
status=$?

# If it died, hold the window open so the message stays readable.
# 130 = Ctrl+C and 143 = SIGTERM (the Stop action) — don't nag on those.
if [ "$status" -ne 0 ] && [ "$status" -ne 130 ] && [ "$status" -ne 143 ]; then
    echo
    echo "The studio exited with status $status."
    read -r -p "Press Enter to close. " _
fi
exit "$status"
