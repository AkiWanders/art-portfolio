/* ==========================================================================
   SandGrace portfolio — builds the gallery from data/artworks.json.

   The page itself is static; this script fetches the same JSON file the admin
   writes, then renders a masonry grid, a tag filter, a lightbox and the
   light/dark switch.
   ========================================================================== */

const state = {
  site: {},
  all: [],
  visible: [],
  filter: "all",
  openIndex: -1,
  imageIndex: 0,
};

const $ = (id) => document.getElementById(id);

const GAP_ROW = 8; // must match --row in styles.css

// ---- helpers -------------------------------------------------------------

/** Every image of a piece, oldest format included (one image stored as `file`). */
function imagesOf(art) {
  if (Array.isArray(art.images) && art.images.length) {
    return art.images.filter((image) => image && image.file);
  }
  return art.file ? [{ file: art.file, w: art.w, h: art.h }] : [];
}

function columnsFor(width) {
  if (width < 560) return 1;
  if (width < 900) return 2;
  return 3;
}

function debounce(fn, wait) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function tagCounts(artworks) {
  const counts = new Map();
  for (const art of artworks) {
    for (const tag of art.tags || []) {
      counts.set(tag, (counts.get(tag) || 0) + 1);
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

// ---- site chrome ---------------------------------------------------------

function applySite(site) {
  state.site = site || {};
  const name = site.artist || "Portfolio";

  document.title = `${name} · Portfolio`;
  document.documentElement.style.setProperty("--accent", site.accent || "#ff5e3a");

  $("artist").textContent = name;
  $("hero-name").textContent = name;
  $("footer-name").textContent = name;
  $("year").textContent = new Date().getFullYear();

  $("hero-tagline").textContent = site.tagline || "";
  $("hero-intro").textContent = site.intro || "";
  $("about-text").textContent = site.about || "";

  const meta = document.querySelector('meta[name="description"]');
  if (meta && site.tagline) meta.setAttribute("content", `${site.tagline} — ${name}`);

  const links = $("links");
  links.innerHTML = "";
  const entries = [];
  if (site.email) entries.push({ label: "Email", url: `mailto:${site.email}` });
  for (const link of site.links || []) {
    if (link && link.label && link.url) entries.push(link);
  }
  for (const entry of entries) {
    const a = document.createElement("a");
    a.href = entry.url;
    a.textContent = entry.label;
    if (!entry.url.startsWith("mailto:")) a.target = "_blank", a.rel = "noopener";
    links.appendChild(a);
  }
  if (!entries.length) links.innerHTML = '<span class="lb-meta">Links coming soon.</span>';

  applyBanner(site);
}

/** Put a chosen image behind the name, or leave the plain text hero. */
function applyBanner(site) {
  const hero = $("hero");
  if (site.banner) {
    hero.style.setProperty("--banner", `url("${site.banner}")`);
    hero.classList.add("has-banner");
    document.body.classList.add("has-banner");
  } else {
    hero.style.removeProperty("--banner");
    hero.classList.remove("has-banner");
    document.body.classList.remove("has-banner");
  }
}

// ---- filters -------------------------------------------------------------

function buildFilters() {
  const box = $("filters");
  box.innerHTML = "";

  const makeButton = (label, value, count) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = count ? `${label} ${count}` : label;
    button.setAttribute("aria-pressed", String(state.filter === value));
    button.addEventListener("click", () => {
      state.filter = value;
      applyFilter();
      buildFilters();
    });
    return button;
  };

  box.appendChild(makeButton("All", "all", state.all.length));
  for (const [tag, count] of tagCounts(state.all)) {
    box.appendChild(makeButton(tag, tag, count));
  }
}

function applyFilter() {
  const shown = state.filter === "all"
    ? state.all
    : state.all.filter((art) => (art.tags || []).includes(state.filter));
  state.visible = shown;
  render(shown);

  const note = $("empty-note");
  note.hidden = shown.length > 0;
  // A whole empty gallery and a filtered-down-to-nothing gallery read differently.
  note.textContent = state.all.length === 0
    ? "Nothing here yet — new work is on its way."
    : "No pieces with that tag yet.";
}

// ---- gallery -------------------------------------------------------------

function render(artworks) {
  const gallery = $("gallery");
  gallery.innerHTML = "";

  if (!artworks.length) return;

  artworks.forEach((art, index) => {
    const images = imagesOf(art);
    const cover = images[0];
    const piece = document.createElement("figure");
    piece.className = "piece" + (art.featured ? " is-featured" : "");
    piece.tabIndex = 0;
    piece.dataset.index = String(index);
    piece.dataset.featured = art.featured ? "1" : "0";
    piece.dataset.ratio = cover && cover.w && cover.h ? String(cover.h / cover.w) : "0.75";
    piece.setAttribute("role", "button");
    piece.setAttribute("aria-label", `View ${art.title}`);

    if (cover) {
      const img = document.createElement("img");
      img.src = cover.file;
      img.alt = art.alt || art.title || "";
      img.loading = index < 4 ? "eager" : "lazy";
      img.decoding = "async";
      if (cover.w) img.width = cover.w;
      if (cover.h) img.height = cover.h;
      piece.appendChild(img);

      if (images.length > 1) {
        const badge = document.createElement("span");
        badge.className = "count";
        badge.textContent = String(images.length);
        badge.title = `${images.length} images`;
        piece.appendChild(badge);
      }

      const caption = document.createElement("figcaption");
      const meta = [art.year, art.medium].filter(Boolean).join(" · ");
      caption.innerHTML = `<strong></strong><br><span></span>`;
      caption.querySelector("strong").textContent = art.title;
      caption.querySelector("span").textContent = meta;
      piece.appendChild(caption);
    }

    const open = () => openLightbox(index);
    piece.addEventListener("click", open);
    piece.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        open();
      }
    });

    gallery.appendChild(piece);
  });

  layout();
}

function layout() {
  const gallery = $("gallery");
  const width = gallery.clientWidth;
  if (!width) return;

  const cols = columnsFor(width);
  gallery.style.setProperty("--cols", String(cols));

  const styles = getComputedStyle(gallery);
  const gap = parseFloat(styles.gap) || 16;
  const colWidth = (width - gap * (cols - 1)) / cols;

  for (const piece of gallery.children) {
    const span = piece.dataset.featured === "1" && cols > 1 ? 2 : 1;
    const boxWidth = span * colWidth + (span - 1) * gap;
    const ratio = parseFloat(piece.dataset.ratio) || 0.75;
    const imageHeight = boxWidth * ratio;
    const rows = Math.max(3, Math.round((imageHeight + gap) / (GAP_ROW + gap)));
    piece.style.gridRowEnd = `span ${rows}`;
  }
}

// ---- lightbox ------------------------------------------------------------

const lightbox = {
  el: null,
  init() {
    this.el = $("lightbox");
    $("lb-close").addEventListener("click", () => this.close());
    $("lb-prev").addEventListener("click", () => this.step(-1));
    $("lb-next").addEventListener("click", () => this.step(1));
    this.el.addEventListener("click", (event) => {
      if (event.target === this.el) this.close();
    });
    document.addEventListener("keydown", (event) => this.onKey(event));
  },
  open(index) {
    if (index < 0 || index >= state.visible.length) return;
    state.openIndex = index;
    const art = state.visible[index];
    state.imageIndex = 0;

    $("lb-title").textContent = art.title;
    $("lb-meta").textContent = [art.year, art.medium, (art.tags || []).join(", ")]
      .filter(Boolean).join(" · ");

    this.buildThumbs(art);
    this.showImage(0);

    this.el.hidden = false;
    document.body.style.overflow = "hidden";
    $("lb-close").focus();
  },
  /** The strip of little images, shown only when a piece has more than one. */
  buildThumbs(art) {
    const images = imagesOf(art);
    const strip = $("lb-thumbs");
    strip.innerHTML = "";
    strip.dataset.count = String(images.length);

    for (let i = 0; i < images.length; i += 1) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "lb-thumb";
      button.setAttribute("aria-label", `Show image ${i + 1} of ${images.length}`);
      const thumb = document.createElement("img");
      thumb.src = images[i].file;
      thumb.alt = "";
      button.appendChild(thumb);
      button.addEventListener("click", () => this.showImage(i));
      strip.appendChild(button);
    }
  },
  /** Point the big image at one of the piece's pictures and mark its thumb. */
  showImage(index) {
    const art = state.visible[state.openIndex];
    const images = imagesOf(art);
    if (!images.length) return;

    state.imageIndex = (index + images.length) % images.length;
    const image = images[state.imageIndex];
    const img = $("lb-image");
    img.src = image.file;
    img.alt = art.alt || art.title || "";

    const strip = $("lb-thumbs");
    strip.hidden = images.length < 2;
    this.el.classList.toggle("has-thumbs", images.length > 1);
    strip.querySelectorAll(".lb-thumb").forEach((button, i) => {
      const current = i === state.imageIndex;
      button.setAttribute("aria-current", String(current));
      button.tabIndex = current ? 0 : -1;
    });
  },
  close() {
    this.el.hidden = true;
    state.openIndex = -1;
    document.body.style.overflow = "";
  },
  step(direction) {
    if (state.visible.length < 2) return;
    const next = (state.openIndex + direction + state.visible.length) % state.visible.length;
    this.open(next);
  },
  onKey(event) {
    if (this.el.hidden) return;
    if (event.key === "Escape") this.close();
    else if (event.key === "ArrowRight") { event.preventDefault(); this.step(1); }
    else if (event.key === "ArrowLeft") { event.preventDefault(); this.step(-1); }
    // Up / Down walk the pictures inside one piece.
    else if (event.key === "ArrowUp") { event.preventDefault(); this.showImage(state.imageIndex - 1); }
    else if (event.key === "ArrowDown") { event.preventDefault(); this.showImage(state.imageIndex + 1); }
  },
};

// ---- theme ---------------------------------------------------------------

function initTheme() {
  const toggle = $("theme-toggle");
  toggle.addEventListener("click", () => {
    const root = document.documentElement;
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
  });
}

// ---- boot ----------------------------------------------------------------

async function init() {
  initTheme();
  lightbox.init();
  window.addEventListener("resize", debounce(layout, 150));

  // The header sits over the banner until you scroll past it.
  const onScroll = () => document.body.classList.toggle("scrolled", window.scrollY > 40);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  try {
    const res = await fetch("data/artworks.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    applySite(data.site);
    state.all = (data.artworks || []).filter((a) => imagesOf(a).length);
    buildFilters();
    applyFilter();
  } catch (err) {
    $("gallery").innerHTML =
      `<p class="empty-note">Could not load the artwork list (${err.message}).</p>`;
  }
}

init();
