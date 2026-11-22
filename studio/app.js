(function studioApp() {
  "use strict";

  // Every entry is an illustrated design exercise, NEVER a retailer listing.
  // The demo's "material" attribute is a placeholder, not an independently
  // verified product specification or a durability claim.
  const PRODUCTS = [
    { id: "everyday", name: "The Everyday", silhouette: "tailored", neckline: "crew", material: "merino", colour: "brown", note: "A fitted, wear-anywhere starting point." },
    { id: "daydream", name: "The Daydream", silhouette: "relaxed", neckline: "v", material: "cotton", colour: "cream", note: "A softer, slower interpretation." },
    { id: "studio", name: "The Studio", silhouette: "cropped", neckline: "crew", material: "cashmere", colour: "burgundy", note: "Playful proportions with a familiar neckline." },
    { id: "library", name: "The Library", silhouette: "tailored", neckline: "v", material: "cotton", colour: "slate", note: "Understated lines and a deeper opening." },
    { id: "weekend", name: "The Weekend", silhouette: "relaxed", neckline: "crew", material: "merino", colour: "olive", note: "The same easy feeling, with more structure." },
    { id: "little", name: "The Little One", silhouette: "cropped", neckline: "v", material: "merino", colour: "brown", note: "A shorter, sharper version of the idea." },
    { id: "gallery", name: "The Gallery", silhouette: "tailored", neckline: "crew", material: "cotton", colour: "cream", note: "A clean silhouette with a lighter finish." },
    { id: "afterhours", name: "The After Hours", silhouette: "tailored", neckline: "v", material: "cashmere", colour: "burgundy", note: "A little dressier, with the same familiar shape." },
    { id: "sunday", name: "The Sunday", silhouette: "relaxed", neckline: "crew", material: "cotton", colour: "brown", note: "Volume, comfort, and an uncomplicated feel." },
    { id: "atelier", name: "The Atelier", silhouette: "cropped", neckline: "crew", material: "merino", colour: "slate", note: "An architectural take on the everyday cardigan." },
    { id: "elsewhere", name: "The Elsewhere", silhouette: "relaxed", neckline: "v", material: "cashmere", colour: "olive", note: "A gentle detour in both colour and texture." },
    { id: "petite", name: "The Petite", silhouette: "cropped", neckline: "v", material: "cotton", colour: "cream", note: "Lighthearted proportions and a clean front." }
  ];
  const COLOURS = {
    brown: { hex: "#725044", dark: "#4d342f", light: "#997366", bg: "#e8e0d9" },
    cream: { hex: "#e1d0b5", dark: "#bba789", light: "#f3e7d3", bg: "#e5ded3" },
    burgundy: { hex: "#773e48", dark: "#532a35", light: "#986674", bg: "#e9dfdf" },
    slate: { hex: "#777d80", dark: "#575d63", light: "#a0a5a6", bg: "#e2e5e3" },
    olive: { hex: "#78775b", dark: "#53543d", light: "#9b9b79", bg: "#e3e4dc" }
  };
  const LABELS = {
    silhouette: { tailored: "Fitted", relaxed: "Relaxed", cropped: "Cropped" },
    neckline: { crew: "Round neck", v: "V-neck" },
    material: { merino: "Merino", cotton: "Cotton", cashmere: "Cashmere" },
    colour: { brown: "Chocolate", cream: "Cream", burgundy: "Burgundy", slate: "Slate", olive: "Olive" }
  };
  const ATTRIBUTES = ["silhouette", "neckline", "material", "colour"];
  const KEY = "barefax.studio.demo-finds.v1";

  let state = { seedId: "everyday", keep: ["silhouette", "neckline"], mode: "close", turn: 0 };
  let history = [];
  let saved = readSaved();
  let compareSelection = [];

  const $ = (selector) => document.querySelector(selector);
  const productById = (id) => PRODUCTS.find((p) => p.id === id);
  const label = (key, value) => LABELS[key][value];

  function readSaved() {
    try {
      const found = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(found) ? [...new Set(found.filter((id) => PRODUCTS.some((p) => p.id === id)))] : [];
    } catch (_) {
      return [];
    }
  }

  function storeSaved() {
    try { localStorage.setItem(KEY, JSON.stringify(saved)); }
    catch (_) { /* local-only saving may be blocked; keep current-session state */ }
  }

  function update(mutator) {
    history.push({ ...state, keep: [...state.keep] });
    if (history.length > 40) history.shift();
    mutator();
    render();
  }

  function chooseSeed(id) {
    if (!productById(id) || state.seedId === id) return;
    update(() => { state.seedId = id; state.turn = 0; });
    $("#hero-art").scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function toggleKeep(attribute) {
    update(() => {
      state.keep = state.keep.includes(attribute)
        ? state.keep.filter((key) => key !== attribute)
        : [...state.keep, attribute];
      state.turn = 0;
    });
  }

  function toggleSaved(id) {
    saved = saved.includes(id) ? saved.filter((item) => item !== id) : [...saved, id];
    compareSelection = compareSelection.filter((item) => saved.includes(item));
    storeSaved();
    render();
    if ($("#saved-dialog").open) renderSavedDialog();
  }

  function undo() {
    if (!history.length) return;
    state = history.pop();
    render();
  }

  function reset() {
    update(() => { state = { seedId: "everyday", keep: ["silhouette", "neckline"], mode: "close", turn: 0 }; });
  }

  function garmentSVG(product) {
    const c = COLOURS[product.colour];
    const group = product.silhouette;
    const body = group === "relaxed"
      ? "M100 87 Q161 75 220 87 L229 300 Q161 311 91 300 Z"
      : group === "cropped"
        ? "M111 87 Q161 78 211 87 L209 254 Q161 263 112 254 Z"
        : "M116 87 Q161 81 206 87 Q194 181 205 307 Q160 316 115 307 Q130 192 116 87 Z";
    const sleeves = group === "relaxed"
      ? ["M101 91 C78 99 64 133 49 191 L31 281 Q44 295 62 285 L116 171 Z",
         "M219 91 C243 101 258 133 272 191 L289 281 Q273 295 257 285 L204 171 Z"]
      : ["M116 90 Q83 93 75 145 L55 267 Q67 277 82 268 L133 148 Z",
         "M206 90 Q238 93 246 145 L267 267 Q253 277 239 268 L189 148 Z"];
    const neck = product.neckline === "v"
      ? `<path d="M137 87 L161 154 L184 87" fill="${c.bg}" stroke="${c.dark}" stroke-width="3" stroke-linejoin="round"/>`
      : `<path d="M138 85 Q158 121 183 85" fill="${c.bg}" stroke="${c.dark}" stroke-width="3"/>`;
    const firstButton = product.neckline === "v" ? 167 : 136;
    const endButton = group === "cropped" ? 245 : 290;
    const buttons = Array.from({ length: Math.floor((endButton - firstButton) / 33) + 1 }, (_, i) => `<circle cx="163" cy="${firstButton + i * 33}" r="3.5" fill="${c.dark}" stroke="${c.light}" stroke-width="1.5"/>`).join("");
    const stripes = Array.from({ length: 12 }, (_, i) => `<path d="M${111 + i * 9} 102 L${110 + i * 9} ${group === "cropped" ? 250 : 302}" stroke="${c.dark}" stroke-width=".45" opacity=".11"/>`).join("");
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 355" role="img" aria-label="Illustrated ${label("colour", product.colour).toLowerCase()} ${label("silhouette", product.silhouette).toLowerCase()} cardigan">
      <defs><linearGradient id="knit-${product.id}" x1="0" x2="1" y1="0" y2="1">
        <stop offset="0%" stop-color="${c.light}"/><stop offset="52%" stop-color="${c.hex}"/><stop offset="100%" stop-color="${c.dark}"/>
      </linearGradient></defs>
      <ellipse cx="159" cy="333" rx="92" ry="9" fill="#4a3930" opacity=".11"/>
      ${sleeves.map((d) => `<path d="${d}" fill="url(#knit-${product.id})" stroke="${c.dark}" stroke-width="1.4"/>`).join("")}
      <path d="${body}" fill="url(#knit-${product.id})" stroke="${c.dark}" stroke-width="1.6"/>
      ${stripes}
      <path d="M160 107 L160 ${group === "cropped" ? 254 : 305}" fill="none" stroke="${c.dark}" stroke-width="3" opacity=".5"/>
      <path d="M166 107 L166 ${group === "cropped" ? 254 : 305}" fill="none" stroke="${c.light}" stroke-width="1.6" opacity=".7"/>
      ${neck}${buttons}
      <path d="M${group === "relaxed" ? 91 : 114} ${group === "cropped" ? 252 : 302} Q159 ${group === "cropped" ? 263 : 314} ${group === "relaxed" ? 229 : 205} ${group === "cropped" ? 252 : 302}" fill="none" stroke="${c.dark}" stroke-width="3.5" opacity=".6"/>
    </svg>`;
  }

  function art(p, extraClass = "") {
    return `<div class="product-visual ${extraClass}" style="--visual-bg:${COLOURS[p.colour].bg}">${garmentSVG(p)}</div>`;
  }

  function matches(p, seed) {
    return state.keep.every((key) => p[key] === seed[key]);
  }

  function rankAlternatives() {
    const seed = productById(state.seedId);
    const matchesAll = PRODUCTS.filter((p) => p.id !== seed.id && matches(p, seed));
    const score = (p) => {
      const differences = ATTRIBUTES.filter((key) => p[key] !== seed[key]).length;
      const keptMatches = state.keep.filter((key) => p[key] === seed[key]).length;
      // All preserved details are always hard constraints. "Surprise" only
      // changes ordering amongst items that still satisfy those constraints.
      return state.mode === "surprise" ? differences * 3 + keptMatches : 10 - differences * 2;
    };
    matchesAll.sort((a, b) => score(b) - score(a) || a.name.localeCompare(b.name));
    if (!matchesAll.length) return [];
    const rotate = state.turn % matchesAll.length;
    return [...matchesAll.slice(rotate), ...matchesAll.slice(0, rotate)].slice(0, 4);
  }

  function describeVariation(p, seed) {
    const retained = state.keep.filter((key) => p[key] === seed[key]);
    const changed = ATTRIBUTES.filter((key) => p[key] !== seed[key]);
    const good = retained.length ? `Keeps your ${retained.join(" and ")}.` : "A different take on the idea.";
    const differences = changed.length ? ` Changes the ${changed.slice(0, 2).join(" and ")}.` : " Very similar to your starting point.";
    return good + differences;
  }

  function productCard(p, index) {
    const seed = productById(state.seedId);
    const isSaved = saved.includes(p.id);
    return `<article class="product-card">
      <div class="product-visual" style="--visual-bg:${COLOURS[p.colour].bg}">
        ${garmentSVG(p)}
        <span class="top-badge">DIRECTION ${String(index + 1).padStart(2, "0")}</span>
        <button class="save-button ${isSaved ? "is-saved" : ""}" type="button" data-save="${p.id}" aria-label="${isSaved ? "Remove" : "Save"} ${p.name} ${isSaved ? "from" : "to"} My finds" aria-pressed="${isSaved}">${isSaved ? "♥" : "♡"}</button>
      </div>
      <div class="product-body">
        <h3>${p.name}</h3>
        <div class="sub">${label("silhouette", p.silhouette)} · ${label("neckline", p.neckline)} · ${label("material", p.material)}</div>
        <p class="reason">${describeVariation(p, seed)}</p>
        <button class="card-action" type="button" data-start="${p.id}">Explore this direction ↗</button>
      </div>
    </article>`;
  }

  function renderHero() {
    const seed = productById(state.seedId);
    $("#hero-art").innerHTML = garmentSVG(seed);
    $("#hero-name").textContent = seed.name;
    $("#hero-description").textContent = seed.note;
    $("#hero-details").innerHTML = ATTRIBUTES.map((key) => `<div><span>${key[0].toUpperCase() + key.slice(1)}</span><strong>${label(key, seed[key])}</strong></div>`).join("");
  }

  function renderControls() {
    document.querySelectorAll("[data-keep]").forEach((button) => {
      const selected = state.keep.includes(button.dataset.keep);
      button.setAttribute("aria-pressed", String(selected));
      button.querySelector("span").textContent = selected ? "✓" : "+";
    });
    document.querySelectorAll("[data-mode]").forEach((button) =>
      button.setAttribute("aria-pressed", String(button.dataset.mode === state.mode))
    );
    $("#undo").disabled = !history.length;
  }

  function renderResults() {
    const results = rankAlternatives();
    $("#results").innerHTML = results.map((p, i) => productCard(p, i)).join("");
    $("#empty-results").hidden = !!results.length;
    $("#results").hidden = !results.length;
    const keptLabels = state.keep.length ? state.keep.join(", ") : "no fixed details";
    const allCount = PRODUCTS.filter((p) => p.id !== state.seedId && matches(p, productById(state.seedId))).length;
    $("#result-explanation").textContent = `${allCount} of 11 sample alternatives match ${keptLabels}. Showing ${results.length}.`;
    $("#reshuffle").disabled = allCount < 2;
    $("#reshuffle").title = allCount < 2 ? "No other matching options to rotate" : "Rotate the sample selection";
  }

  function renderRack() {
    $("#rack").innerHTML = PRODUCTS.map((p) => `<button type="button" class="rack-item" data-start="${p.id}" aria-current="${p.id === state.seedId}">
      <div class="rack-visual" style="--visual-bg:${COLOURS[p.colour].bg}">${garmentSVG(p)}</div>
      <span class="rack-caption">${p.name}<small>${label("silhouette", p.silhouette)} · ${label("colour", p.colour)}</small></span>
    </button>`).join("");
  }

  function render() {
    renderHero();
    renderControls();
    renderResults();
    renderRack();
    $("#saved-count").textContent = String(saved.length);
  }

  function renderSavedDialog() {
    const container = $("#saved-items");
    if (!saved.length) {
      container.innerHTML = `<div class="no-saves">Nothing here yet. Save a piece you like while exploring and it'll show up here.</div>`;
      $("#compare-saved").disabled = true;
      return;
    }
    container.innerHTML = saved.map((id) => {
      const p = productById(id);
      return `<div class="saved-item">
        <div class="saved-thumb" aria-hidden="true">${garmentSVG(p)}</div>
        <div class="saved-copy"><strong>${p.name}</strong><span>${label("silhouette", p.silhouette)} · ${label("neckline", p.neckline)} · ${label("material", p.material)} · ${label("colour", p.colour)}</span><br>
          <button class="remove-saved" type="button" data-save="${p.id}">Remove</button>
        </div>
        <label class="saved-choice"><input type="checkbox" data-compare="${p.id}" ${compareSelection.includes(p.id) ? "checked" : ""} ${!compareSelection.includes(p.id) && compareSelection.length >= 3 ? "disabled" : ""}> Compare</label>
      </div>`;
    }).join("");
    $("#compare-saved").disabled = compareSelection.length < 2;
    $("#compare-saved").textContent = compareSelection.length >= 2
      ? `Compare ${compareSelection.length} pieces`
      : "Select 2–3 to compare";
  }

  function openDialog(id) {
    const dialog = document.getElementById(id);
    if (!dialog.open) dialog.showModal();
  }

  function showComparison() {
    if (compareSelection.length < 2 || compareSelection.length > 3) return;
    const chosen = compareSelection.map(productById).filter(Boolean);
    const table = $("#comparison");
    const firstRow = `<div class="table-label">PIECE</div>` + chosen.map((p) =>
      `<div class="compare-product">${garmentSVG(p)}<strong>${p.name}</strong></div>`).join("");
    const rows = ATTRIBUTES.map((attr) => `<div class="table-label">${attr[0].toUpperCase() + attr.slice(1)}</div>` +
      chosen.map((p) => `<div>${label(attr, p[attr])}</div>`).join("")).join("");
    table.innerHTML = `<div class="comparison-columns" style="--cols:${chosen.length}">${firstRow}${rows}</div>`;
    $("#saved-dialog").close();
    openDialog("compare-dialog");
  }

  // Event delegation works for cards and buttons rerendered after each choice.
  document.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.keep) toggleKeep(button.dataset.keep);
    else if (button.dataset.mode) update(() => { state.mode = button.dataset.mode; state.turn = 0; });
    else if (button.dataset.start) chooseSeed(button.dataset.start);
    else if (button.dataset.save) toggleSaved(button.dataset.save);
    else if (button.dataset.close) document.getElementById(button.dataset.close).close();
  });

  document.addEventListener("change", (event) => {
    const input = event.target.closest("[data-compare]");
    if (!input) return;
    if (input.checked && !compareSelection.includes(input.dataset.compare) && compareSelection.length < 3) {
      compareSelection.push(input.dataset.compare);
    } else if (!input.checked) {
      compareSelection = compareSelection.filter((id) => id !== input.dataset.compare);
    }
    renderSavedDialog();
  });

  $("#undo").addEventListener("click", undo);
  $("#reset").addEventListener("click", reset);
  $("#reshuffle").addEventListener("click", () => update(() => { state.turn += 1; }));
  $("#change-seed").addEventListener("click", () => $("#inspiration").scrollIntoView({ behavior: "smooth" }));
  $("#open-saved").addEventListener("click", () => { renderSavedDialog(); openDialog("saved-dialog"); });
  $("#compare-saved").addEventListener("click", showComparison);

  render();
})();