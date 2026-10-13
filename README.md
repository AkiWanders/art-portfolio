# SandGrace — art portfolio

A minimal, vibrant art portfolio in two halves that share one file:

| Half | What it is | Where it runs |
|---|---|---|
| **Public site** | Static HTML/CSS/JS in `docs/` | GitHub Pages (everyone) |
| **Studio (admin)** | A small Flask app that edits the gallery | `127.0.0.1` on your computer only |

Both sides read and write the same `docs/data/artworks.json`. The public page
fetches it in the browser; the studio writes it. That is why the studio can
never be reached from the internet — it is only ever started on your machine,
bound to `127.0.0.1`, on port **5050** (the Bakery app has 5000).

To install the double-click launcher:

```bash
chmod +x launch.sh
cp art-portfolio.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications
```

**Art Portfolio** then appears in your launcher, with right-click **Stop** and
**Restart** actions.

## How it looks

- Dark and light themes with a one-tap switch (remembered between visits).
- Masonry gallery built from each image's real proportions, so nothing is
  cropped or squashed.
- Featured pieces span two columns.
- Tag filters, a keyboard-friendly lightbox, and captions on hover.
- **Pieces can hold several images** — a sketch-to-final set, for example. Those
  get a small count badge on the tile and a thumbnail strip in the lightbox.
- **An optional hero banner** — one wide image behind your name on the first
  screen.
- `prefers-reduced-motion` is respected; every image has alt text.
- The accent colour is read from the data file — change it in Settings.

Keyboard: in the lightbox, **← →** move between pieces and **↑ ↓** move between
the images inside one piece.

## Setup

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Add and edit artwork (the studio)

Double-click **Art Portfolio** in your app launcher, or from a terminal:

```bash
./launch.sh
```

Your browser opens at <http://127.0.0.1:5050>. From there you can:

- **Add artwork** — pick a PNG, JPG, WEBP or a Krita `.kra` file. Each is
  automatically resized (1800px on the long edge) and converted to `.webp`.
- **Several images per piece** — select more than one file at once, or add more
  later from the edit page. The first image is the cover shown in the gallery;
  *Make cover*, ↑ ↓ and *Remove* reorder or drop the rest.
- **Edit / reorder / delete** — the ↑ ↓ buttons change the gallery order, and
  *featured* pieces span two columns on the site.
- **Settings** — artist name, tagline, intro, about, accent colour, email,
  contact links, and the hero banner.
- **Preview site ↗** — opens the real public page before you publish.
- **Publish** — commits every change and pushes to GitHub in one click.

## Publishing

The **Publish** button stages everything, commits with your message, and pushes
to `origin`. GitHub Pages rebuilds `docs/` and the change is live in about half
a minute. A dotted summary at the top of the studio always shows what is
unpublished.

## Deploy on GitHub Pages (once)

1. Push this repo to GitHub.
2. Repository **Settings → Pages**.
3. **Source:** *Deploy from a branch* · **Branch:** `main` · **Folder:** `/docs`.
4. Save. The site appears at `https://<user>.github.io/<repo>/`.

`docs/.nojekyll` tells Pages to serve the files exactly as they are.

## Bulk import

To load a whole folder of pictures at once:

```bash
./venv/bin/python tools/import_art.py "/path/to/folder" --tag concept --year 2025
```

The file name becomes the title; existing titles are skipped, so it is safe to
re-run.

## Tests

```bash
./venv/bin/python -m pytest -q
```

They run against a temporary folder, so they never touch your real gallery.

## Project layout

```
run.py                    starts the local studio
app/                      the studio (never deployed)
  store.py                all reading and writing of data and images
  admin.py                studio pages and routes
  publish.py              git add / commit / push
  templates/              studio pages
  static/                 studio styles + a little JS
docs/                     the public site — this is what GitHub Pages serves
  index.html app.js styles.css
  art/                    web-ready images
  data/artworks.json      the shared list of artwork + site settings
tools/import_art.py       bulk import from a folder
tests/                    pytest suite
```

## Adding a new field later

Because every read and write goes through `app/store.py`, adding a field (say a
"sold" flag) means touching that one file for the data, `edit.html` for the
form, and `app.js` for the display. Nothing else.
