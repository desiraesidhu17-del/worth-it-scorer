/* ── Extension result: render score if ?result=UUID is in URL ───────────── */
(function checkExtensionResult() {
  const params = new URLSearchParams(window.location.search);
  const resultId = params.get('result');
  if (!resultId) return;

  // Show loading state
  const inputSection = document.querySelector('.tabs') || document.querySelector('form');
  if (inputSection) inputSection.hidden = true;

  const status = document.createElement('p');
  status.id = 'extension-status';
  status.textContent = 'Loading score\u2026';
  status.style.cssText = 'padding:20px;color:#8a8070;font-size:13px;font-family:monospace;';
  document.body.prepend(status);

  fetch(`/api/result/${resultId}`)
    .then(r => {
      if (r.status === 404) throw new Error('expired');
      if (!r.ok) throw new Error('fetch_failed');
      return r.json();
    })
    .then(data => {
      status.remove();
      if (inputSection) inputSection.hidden = false;
      renderResult(data);
    })
    .catch(err => {
      status.textContent = err.message === 'expired'
        ? 'Score expired \u2014 please re-scan the page with the extension.'
        : 'Could not load score. Please try again.';
      if (inputSection) inputSection.hidden = false;
    });
})();

/* ── Tab switching ───────────────────────────────────────────────────────── */
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`${target}-form`).classList.add("active");
    hideError();
  });
});

/* ── Tab A: URL scan ─────────────────────────────────────────────────────── */
document.getElementById("btn-score-url").addEventListener("click", async () => {
  const url = document.getElementById("url-input").value.trim();
  if (!url) { showError("Please enter a product URL.", null); return; }
  if (!url.startsWith("http")) { showError("Please enter a full URL starting with https://", null); return; }

  const price = parseFloat(document.getElementById("price-url").value) || null;
  const category = document.getElementById("category-url").value || "other";

  setLoading("Fetching product page…");
  await submitScore({ url, price, category }, "url");
});

/* ── Tab B: Paste text ───────────────────────────────────────────────────── */
document.getElementById("btn-score-text").addEventListener("click", async () => {
  const raw_text = document.getElementById("raw-text").value.trim();
  if (!raw_text) { showError("Please paste some product text first.", null); return; }

  const price = parseFloat(document.getElementById("price-text").value) || null;
  const category = document.getElementById("category-text").value || "other";

  setLoading("Extracting fiber composition…");
  await submitScore({ raw_text, price, category }, "text");
});

/* ── Tab C: Manual form ──────────────────────────────────────────────────── */
document.getElementById("manual-form").addEventListener("submit", async e => {
  e.preventDefault();
  const raw = document.getElementById("composition-text").value.trim();
  const price = parseFloat(document.getElementById("price-manual").value) || null;
  const category = document.getElementById("category-manual").value;

  const composition = parseCompositionText(raw);
  if (!composition.length) {
    showError("Couldn't parse the composition. Try: \"52% acrylic, 48% polyester\"", null);
    return;
  }

  setLoading("Scoring fiber composition…");
  await submitScore({ composition, price, category }, "json");
});

/* ── Score submission ────────────────────────────────────────────────────── */
async function submitScore(data, mode) {
  try {
    let body;

    if (mode === "url") {
      body = JSON.stringify({ url: data.url, price: data.price, category: data.category });
    } else if (mode === "text") {
      body = JSON.stringify({ raw_text: data.raw_text, price: data.price, category: data.category });
    } else {
      body = JSON.stringify({ composition: data.composition, price: data.price, category: data.category });
    }

    const response = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });

    const result = await response.json();

    if (!response.ok) {
      const msg = result.error || "Something went wrong. Please try again.";
      const action = _errorAction(result.error_type, mode, msg);
      showError(msg, action);
      return;
    }

    renderResult(result);

  } catch (err) {
    showError("Network error — is the server running?", null);
  }
}

function _errorAction(errorType, currentMode, serverMsg) {
  // For URL-mode blocked/timeout errors the server often includes site-specific
  // instructions in the error message itself — don't add a generic duplicate.
  if ((errorType === "blocked" || errorType === "timeout") && currentMode === "url") {
    // If the server message already tells them what to do, the action line is redundant.
    const alreadyInstructed = serverMsg && (
      serverMsg.toLowerCase().includes("paste text") ||
      serverMsg.toLowerCase().includes("scroll") ||
      serverMsg.toLowerCase().includes("copy")
    );
    return alreadyInstructed
      ? null
      : "Switch to the 'Paste text' tab, copy the product description from the site, and paste it there.";
  }
  if (errorType === "empty" && currentMode === "url") {
    return "Switch to the 'Paste text' tab and paste the materials section of the product page.";
  }
  if (errorType === "empty") {
    return "No fiber composition was found. Make sure you've copied the materials section of the product page.";
  }
  return null;
}

/* ── Render result ───────────────────────────────────────────────────────── */
function renderResult(r) {
  hideAll();
  document.getElementById("result-card").hidden = false;

  const score = Math.round(r.worth_it_score || 0);
  const material = Math.round(r.material_score || 0);
  const props = r.property_scores || {};
  const pp = r.price_pressure || {};
  const cpw = r.cost_per_wash || {};

  // Headline — technical override replaces with neutral copy
  const isTech = r.technical_override && r.technical_override.length > 0;
  document.getElementById("card-headline").textContent = isTech ? "Technical performance gear" : (r.headline || "");
  document.getElementById("card-headline-sub").textContent = isTech
    ? "Score reflects fiber composition only. Value is driven by membrane technology and construction."
    : (r.headline_sub || "");

  // Watch for — always hidden for technical gear (fiber warnings are misleading for membrane products)
  const watchItems = r.watch_for || [];
  const watchRow = document.getElementById("watch-for-row");
  if (!isTech && watchItems.length > 0) {
    document.getElementById("watch-for-items").textContent = watchItems.join("  ·  ");
    watchRow.hidden = false;
  } else {
    watchRow.hidden = true;
  }

  // Score line — suppress numeric score for technical gear; show muted label instead
  const scoreNumEl = document.getElementById("score-number");
  const scoreSepEl = document.getElementById("score-sep");
  const bandLabels = {
    very_low:  "VERY LOW DURABILITY",
    low:       "LOW DURABILITY",
    mid:       "AVERAGE DURABILITY",
    good:      "ABOVE AVERAGE DURABILITY",
    excellent: "STRONG DURABILITY",
  };
  if (isTech) {
    scoreNumEl.textContent = "Fiber score";
    scoreNumEl.style.color = "var(--muted)";
    scoreNumEl.style.fontSize = "1rem";
    scoreNumEl.style.fontWeight = "normal";
    if (scoreSepEl) scoreSepEl.hidden = true;
    document.getElementById("score-band-label").textContent = "";
  } else {
    scoreNumEl.textContent = score;
    scoreNumEl.style.color = scoreColor(score);
    scoreNumEl.style.fontSize = "";
    scoreNumEl.style.fontWeight = "";
    if (scoreSepEl) scoreSepEl.hidden = false;
    document.getElementById("score-band-label").textContent = bandLabels[r.score_band] || "";
  }

  // Confidence
  const conf = r.confidence || "low";
  const confLabel = document.getElementById("confidence-label");
  confLabel.textContent = `[${conf.toUpperCase()} CONFIDENCE]`;
  confLabel.style.color = conf === "high" ? "var(--green)" : conf === "medium" ? "var(--yellow)" : "var(--red)";
  const notes = r.confidence_notes || [];
  document.getElementById("confidence-note").textContent = notes[notes.length - 1] || "";

  // Verdict sentence (tertiary)
  document.getElementById("verdict-sentence").textContent = r.verdict_sentence || "";

  document.getElementById("stat-material").textContent = `${material} / 100`;
  document.getElementById("stat-material").style.color = scoreColor(material);

  if (!isTech) {
    const pressureColors = { low: "var(--green)", moderate: "var(--yellow)", high: "var(--red)", extreme: "var(--red)", unknown: "var(--muted)" };
    document.getElementById("stat-pressure").textContent = pp.label || "—";
    document.getElementById("stat-pressure").style.color = pressureColors[pp.level] || "var(--muted)";
  }

  const cpwNote = document.getElementById("cpw-note");
  if (cpw.cost_per_wash_low != null) {
    document.getElementById("stat-cpw").textContent =
      `$${cpw.cost_per_wash_low.toFixed(2)}–$${cpw.cost_per_wash_high.toFixed(2)}`;
  }
  if (cpw.note) {
    cpwNote.textContent = cpw.note;
    cpwNote.hidden = false;
  } else {
    cpwNote.hidden = true;
  }

  const pd = document.getElementById("price-detail");
  const techOverrideEl = document.getElementById("technical-override");
  const techSignalsList = document.getElementById("technical-signals-list");
  const priceFitStat = document.getElementById("price-fit-stat");

  if (isTech) {
    // Hide price fit stat + price detail; show technical override panel
    if (priceFitStat) priceFitStat.hidden = true;
    pd.hidden = true;
    techSignalsList.innerHTML = "";
    r.technical_override.forEach(sig => {
      const li = document.createElement("li");
      li.textContent = sig;
      techSignalsList.appendChild(li);
    });
    techOverrideEl.hidden = false;
    // Explicit resets — ensure no stale values from a prior non-tech render
    document.getElementById("card-headline").textContent = "Technical performance gear";
    document.getElementById("card-headline-sub").textContent = "Score reflects fiber composition only. Value is driven by membrane technology and construction.";
    scoreNumEl.textContent = "Fiber score";
    scoreNumEl.style.color = "var(--muted)";
    document.getElementById("score-band-label").textContent = "";
    document.getElementById("stat-pressure").textContent = "—";
    document.getElementById("stat-pressure").style.color = "var(--muted)";
    document.getElementById("verdict-sentence").textContent = "";
    const cpwStatRow = document.getElementById("cpw-stat-row");
    if (cpwStatRow) cpwStatRow.hidden = true;
    cpwNote.hidden = true;
  } else {
    if (priceFitStat) priceFitStat.hidden = false;
    techOverrideEl.hidden = true;
    if (pp.detail) { pd.textContent = pp.detail; pd.hidden = false; }
    else { pd.hidden = true; }
    const cpwStatRow = document.getElementById("cpw-stat-row");
    if (cpwStatRow) cpwStatRow.hidden = false;
  }

  setBar("pilling",      props.pilling);
  setBar("tensile",      props.tensile);
  setBar("colorfastness",props.colorfastness);
  setBar("moisture",     props.moisture);

  renderConstruction(r.construction);
}

function renderConstruction(c) {
  const row = document.getElementById("construction-row");
  const notAssessed = document.getElementById("construction-not-assessed");
  const constrHeader = document.querySelector(".section-header-construction");

  if (!c) {
    row.hidden = true;
    notAssessed.hidden = true;
    if (constrHeader) constrHeader.hidden = true;
    return;
  }

  if (constrHeader) constrHeader.hidden = false;

  // Hide numeric score when only price-floor inference — no real signals
  const isPriceFloorOnly =
    c.source === "price_floor" && (!c.signals_found || c.signals_found.length === 0);

  if (isPriceFloorOnly) {
    row.hidden = true;
    notAssessed.hidden = false;
    const noteEl = document.getElementById("construction-floor-note-na");
    if (noteEl && c.price_floor_note) {
      noteEl.textContent = c.price_floor_note;
      noteEl.hidden = false;
    }
    return;
  }

  // Real signals found — show full construction row
  row.hidden = false;
  notAssessed.hidden = true;

  const scoreVal = c.score || 0;
  const scoreEl = document.getElementById("construction-score");
  scoreEl.textContent = `${scoreVal.toFixed(1)} / 10`;
  scoreEl.style.color = scoreColor(scoreVal * 10);

  const bar = document.getElementById("bar-construction");
  bar.style.width = `${scoreVal * 10}%`;
  bar.style.background = scoreColor(scoreVal * 10);

  const noteEl = document.getElementById("construction-floor-note");
  if (c.price_floor_note) {
    noteEl.textContent = c.price_floor_note;
    noteEl.hidden = false;
  } else {
    noteEl.hidden = true;
  }

  const sigList = document.getElementById("construction-signals");
  sigList.innerHTML = "";
  (c.signals_found || []).forEach(sig => {
    const li = document.createElement("li");
    li.textContent = sig;
    sigList.appendChild(li);
  });
}

function setBar(prop, value) {
  const pct = Math.round(value || 0);
  document.getElementById(`bar-${prop}`).style.width = `${pct}%`;
  document.getElementById(`bar-${prop}`).style.background = scoreColor(pct);
  const v = document.getElementById(`val-${prop}`);
  if (v) v.textContent = pct;
}

function scoreColor(score) {
  if (score >= 66) return "var(--green)";
  if (score >= 41) return "var(--yellow)";
  return "var(--red)";
}

/* ── Download card ───────────────────────────────────────────────────────── */
document.getElementById("btn-download").addEventListener("click", () => {
  const btn = document.getElementById("btn-download");
  btn.disabled = true;
  btn.classList.add("exporting");
  btn.dataset.label = btn.textContent;
  btn.textContent = "";

  const finish = () => {
    btn.disabled = false;
    btn.classList.remove("exporting");
    btn.textContent = btn.dataset.label || "[ DOWNLOAD CARD ]";
  };

  if (typeof html2canvas !== "undefined") {
    captureCard(finish);
    return;
  }

  const script = document.createElement("script");
  script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";
  script.onload = () => captureCard(finish);
  script.onerror = () => {
    finish();
    alert("Couldn't load the image library. Check your internet connection and try again.");
  };
  document.head.appendChild(script);
});

function captureCard(finish) {
  // Resolve CSS variables to actual hex values before capture
  // html2canvas doesn't support CSS custom properties on older browsers
  const card = document.getElementById("card-inner");
  html2canvas(card, {
    backgroundColor: "#f5f2eb",
    scale: 2,
    useCORS: true,
    logging: false,
  }).then(canvas => {
    const link = document.createElement("a");
    link.download = "worth-it-score.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
    if (finish) finish();
  }).catch(() => {
    if (finish) finish();
    alert("Screenshot failed. Try right-clicking the card and saving as image instead.");
  });
}

/* ── Reset ───────────────────────────────────────────────────────────────── */
document.getElementById("btn-reset").addEventListener("click", () => {
  hideAll();
  document.getElementById("input-panel").hidden = false;
  ["url-input","price-url","category-url","raw-text","price-text","category-text",
   "composition-text","price-manual"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  document.getElementById("category-manual").value = "other";
  const resetScoreEl = document.getElementById("score-number");
  resetScoreEl.textContent = "—";
  resetScoreEl.style.color = "";
  resetScoreEl.style.fontSize = "";
  resetScoreEl.style.fontWeight = "";
  const resetSepEl = document.getElementById("score-sep");
  if (resetSepEl) resetSepEl.hidden = false;
  document.getElementById("card-headline").textContent = "";
  document.getElementById("card-headline-sub").textContent = "";
  document.getElementById("watch-for-items").textContent = "";
  document.getElementById("watch-for-row").hidden = true;
  document.getElementById("score-band-label").textContent = "";
  document.getElementById("construction-not-assessed").hidden = true;
  document.getElementById("technical-override").hidden = true;
  document.getElementById("technical-signals-list").innerHTML = "";
  const priceFitReset = document.getElementById("price-fit-stat");
  if (priceFitReset) priceFitReset.hidden = false;
  const cpwRowReset = document.getElementById("cpw-stat-row");
  if (cpwRowReset) cpwRowReset.hidden = false;
});

/* ── UI helpers ──────────────────────────────────────────────────────────── */
function setLoading(msg) {
  hideAll();
  document.getElementById("loading").hidden = false;
  document.getElementById("loading-msg").textContent = msg || "Analysing…";
}

function showError(msg, action) {
  hideAll();
  document.getElementById("input-panel").hidden = false;
  document.getElementById("error-box").hidden = false;
  document.getElementById("error-msg").textContent = msg;
  const actionEl = document.getElementById("error-action");
  if (action) { actionEl.textContent = action; actionEl.hidden = false; }
  else { actionEl.hidden = true; }
}

function hideError() {
  document.getElementById("error-box").hidden = true;
}

function hideAll() {
  ["input-panel","loading","error-box","result-card"].forEach(id => {
    document.getElementById(id).hidden = true;
  });
}

/* ── Composition text parser (manual tab) ────────────────────────────────── */
function parseCompositionText(text) {
  const results = [];
  const pattern = /(\d+(?:\.\d+)?)\s*%?\s*([a-zA-Z][a-zA-Z\s\-]+?)(?=\s*[\d%,\/]|$)|([a-zA-Z][a-zA-Z\s\-]+?)\s+(\d+(?:\.\d+)?)\s*%/g;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    if (match[1] && match[2]) results.push({ fiber: match[2].trim().toLowerCase(), pct: parseFloat(match[1]) });
    else if (match[3] && match[4]) results.push({ fiber: match[3].trim().toLowerCase(), pct: parseFloat(match[4]) });
  }
  return results;
}
