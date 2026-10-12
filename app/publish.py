"""One-click publishing.

When the admin writes a new artwork it only changes files on this computer.
This module is what puts those changes on the internet: it stages everything,
makes a commit, and pushes to GitHub. GitHub Pages then rebuilds the site.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def is_repo() -> bool:
    try:
        return _run("rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def status() -> dict:
    """A small summary the dashboard shows: branch, dirty files, remote."""
    if not is_repo():
        return {"repo": False, "branch": "", "changed": [], "remote": "", "has_remote": False}

    branch = _run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    porcelain = _run("status", "--porcelain").stdout.strip()
    changed = [line[3:] for line in porcelain.splitlines() if line.strip()]

    try:
        remote = _run("remote", "get-url", "origin").stdout.strip()
    except subprocess.CalledProcessError:
        remote = ""

    ahead = 0
    if remote:
        counts = _run("rev-list", "--left-right", "--count", f"origin/{branch}...HEAD",
                      check=False)
        if counts.returncode == 0 and counts.stdout.strip():
            try:
                ahead = int(counts.stdout.split()[1])
            except (IndexError, ValueError):
                ahead = 0

    return {
        "repo": True,
        "branch": branch,
        "changed": changed,
        "remote": remote,
        "has_remote": bool(remote),
        "ahead": ahead,
    }


def publish(message: str = "") -> dict:
    """Stage, commit and (if a remote exists) push every pending change."""
    if not is_repo():
        return {"ok": False, "committed": False, "pushed": False,
                "message": "This folder is not a git repository yet."}

    _run("add", "-A")

    staged = _run("diff", "--cached", "--name-only").stdout.strip()
    if not staged:
        return {"ok": True, "committed": False, "pushed": False,
                "message": "Nothing changed since the last publish."}

    files = [line for line in staged.splitlines() if line.strip()]
    commit_message = message.strip() or f"Update portfolio ({len(files)} file(s))"
    _run("commit", "-m", commit_message)

    state = status()
    if not state["has_remote"]:
        return {"ok": True, "committed": True, "pushed": False, "files": files,
                "message": "Committed locally. No GitHub remote is set up yet, so "
                           "nothing was pushed."}

    branch = state["branch"]
    push = _run("push", "-u", "origin", branch, check=False)
    if push.returncode != 0:
        return {"ok": False, "committed": True, "pushed": False, "files": files,
                "message": f"Committed, but the push failed:\n{push.stderr.strip()}"}

    return {"ok": True, "committed": True, "pushed": True, "files": files,
            "message": f"Published {len(files)} file(s) to GitHub. "
                       "The live site updates in about half a minute."}
