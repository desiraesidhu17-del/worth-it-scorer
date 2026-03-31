# UX Polish Pass — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve result card readability, label clarity, and verdict copy across 4 files — no backend scoring logic changes.

**Architecture:** Pure frontend + content changes. `verdict_library.py` gets rewritten verdict sentences (content only, no structural change). `index.html`, `style.css`, and `app.js` get layout, label, and animation fixes. No new dependencies. All 33 existing tests should continue to pass unchanged.

**Tech Stack:** Flask, vanilla JS, CSS custom properties, Space Mono font. Tests: pytest.

---

### Task 1: Rewrite verdict sentences in `verdict_library.py`

**Files:**
- Modify: `scoring/verdict_library.py:18-129`

No tests needed — this is a content change. The structure of `WORTH_IT_VERDICTS` stays identical; only the string values change.

**Step 1: Replace `WORTH_IT_VERDICTS` dict values**

Open `scoring/verdict_library.py`. Replace the entire `WORTH_IT_VERDICTS` dict (lines 18–129) with:

```python
WORTH_IT_VERDICTS: dict[tuple[str, str], str] = {

    # Very low (0–25)
    ("very_low", "synthetic"): (
        "Expect pilling within one season. "
        "Not worth mid-range pricing."
    ),
    ("very_low", "cellulosic"): (
        "This blend is predicted to lose structure quickly. "
        "The material science doesn't support the price."
    ),
    ("very_low", "mixed"): (
        "Low predicted durability across the board. "
        "The fiber combination is associated with early wear."
    ),
    ("very_low", "natural"): (
        "Natural fibers, but a combination associated with poor durability. "
        "Short lifespan for the price."
    ),
    ("very_low", "premium"): (
        "Premium branding, low durability. "
        "Price does not reflect the likely wear experience."
    ),

    # Low (26–45)
    ("low", "synthetic"): (
        "Will pill noticeably within the first season. "
        "Durability doesn't justify a mid-range price."
    ),
    ("low", "cellulosic"): (
        "Viscose and rayon lose structure faster than comparable naturals at this price. "
        "Handle with care."
    ),
    ("low", "mixed"): (
        "Mixed signals from the fiber composition. "
        "Some components hold up; others will show wear early."
    ),
    ("low", "natural"): (
        "Natural fiber content helps, but durability is still a concern. "
        "Best for light, occasional wear."
    ),
    ("low", "premium"): (
        "Premium fiber name, below-average blend ratio. "
        "Predicted performance doesn't match the price."
    ),

    # Mid (46–65)
    ("mid", "synthetic"): (
        "Decent predicted durability for synthetics. "
        "Reasonable quality for the category and price."
    ),
    ("mid", "cellulosic"): (
        "Moderate durability with good drape. "
        "Should hold up for regular rotation with proper care."
    ),
    ("mid", "mixed"): (
        "Balanced composition with middle-of-the-road predicted performance. "
        "No major red flags."
    ),
    ("mid", "natural"): (
        "Good natural fiber content with moderate durability. "
        "Care routine will drive actual lifespan."
    ),
    ("mid", "premium"): (
        "Premium fibers at a mid-range blend. "
        "Solid performance if priced accordingly."
    ),

    # Good (66–80)
    ("good", "synthetic"): (
        "Strong durability for a synthetic blend. "
        "Built to handle regular rotation."
    ),
    ("good", "cellulosic"): (
        "Above-average durability for a cellulosic blend. "
        "The fiber science backs up the price."
    ),
    ("good", "mixed"): (
        "Well-balanced composition with strong predicted durability. "
        "Worth the price at this level."
    ),
    ("good", "natural"): (
        "Solid natural fiber performance. "
        "This is the quality level where the fiber science earns its keep."
    ),
    ("good", "premium"): (
        "Premium fibers doing real work here. "
        "Durability is strong and the composition backs the investment."
    ),

    # Excellent (81–100)
    ("excellent", "synthetic"): (
        "Exceptional durability for this fiber class. "
        "Engineered for performance and longevity."
    ),
    ("excellent", "cellulosic"): (
        "Best-in-class durability for a cellulosic blend. "
        "This is what quality looks like at the fiber level."
    ),
    ("excellent", "mixed"): (
        "Genuinely good value — the fiber composition backs it up. "
        "Top-tier durability for the category."
    ),
    ("excellent", "natural"): (
        "Excellent natural fiber composition with top-tier predicted durability. "
        "Worth the investment."
    ),
    ("excellent", "premium"): (
        "Premium fibers, premium performance. "
        "The material science earns the price."
    ),
}
```

**Step 2: Run tests to confirm no regressions**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_extractor.py -v
```

Expected: 33 passed

**Step 3: Commit**

```bash
git add scoring/verdict_library.py
git commit -m "content: rewrite verdict sentences to decision-assistant tone"
```

---

### Task 2: Tighten top section (`style.css`)

**Files:**
- Modify: `static/style.css:317-341`

**Step 1: Reduce verdict-sentence margin and lighten confidence label**

Find `.verdict-sentence` (line ~317) and `.confidence-badge` / `#confidence-label` (line ~323):

Change `.verdict-sentence`:
```css
.verdict-sentence {
  font-size: 1rem;
  line-height: 1.5;
  margin-bottom: 6px;   /* was 12px */
}
```

Change `#confidence-label`:
```css
#confidence-label {
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  font-weight: 400;   /* was 700 */
}
```

**Step 2: Verify locally**

Start server: `cd /Users/desiraesidhu/clothing_quality_backend && python app.py`

Open http://localhost:5000, score a product. Confirm:
- Verdict sentence and confidence label stack tighter
- Confidence label is the same color but thinner weight (reads as metadata)

**Step 3: Commit**

```bash
git add static/style.css
git commit -m "style: tighten top section — verdict margin, confidence label weight"
```

---

### Task 3: Rename "Price pressure" → "Price fit" (`index.html`)

**Files:**
- Modify: `templates/index.html:169`

**Step 1: Change the label text**

Find line 169:
```html
<span class="stat-label">Price pressure</span>
```

Change to:
```html
<span class="stat-label">Price fit</span>
```

**Step 2: Verify locally**

Reload http://localhost:5000, score a product. Confirm the stats row shows "Price fit" not "Price pressure".

**Step 3: Commit**

```bash
git add templates/index.html
git commit -m "copy: rename 'Price pressure' to 'Price fit'"
```

---

### Task 4: Add cost-per-wash context note (`index.html` + `app.js`)

The API already returns `cpw.note` — it just needs to be displayed.

**Files:**
- Modify: `templates/index.html` (after line 177 stats row close)
- Modify: `static/app.js:178-185` (renderResult function, cpw section)

**Step 1: Add `#cpw-note` element in `index.html`**

Find the closing `</div>` of `.stats-row` (after the cost-per-wash stat, around line 177). Add immediately after:

```html
        </div>

        <div id="cpw-note" class="price-detail" hidden></div>
```

So the block reads:
```html
        <div class="stats-row">
          <div class="stat">
            <span class="stat-label">Material durability</span>
            <span id="stat-material" class="stat-value">—</span>
          </div>
          <div class="stat">
            <span class="stat-label">Price fit</span>
            <span id="stat-pressure" class="stat-value">—</span>
          </div>
          <div class="stat">
            <span class="stat-label">Cost per wash</span>
            <span id="stat-cpw" class="stat-value">—</span>
          </div>
        </div>

        <div id="cpw-note" class="price-detail" hidden></div>
```

**Step 2: Populate `#cpw-note` in `app.js`**

In `renderResult()`, find the cost-per-wash block (around lines 178–181):

```js
  if (cpw.cost_per_wash_low != null) {
    document.getElementById("stat-cpw").textContent =
      `$${cpw.cost_per_wash_low.toFixed(2)}–$${cpw.cost_per_wash_high.toFixed(2)}`;
  }
```

Replace with:
```js
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
```

**Step 3: Verify locally**

Score a product with a price. Confirm:
- Stats row shows cost-per-wash range
- Below it, small gray text shows "Estimated lifespan: X–Y wash cycles…"

**Step 4: Commit**

```bash
git add templates/index.html static/app.js
git commit -m "feat: show cost-per-wash lifespan context below stats"
```

---

### Task 5: Unify construction section with property bars

**Files:**
- Modify: `templates/index.html:191-205` (construction-row block)
- Modify: `static/style.css:429-500` (construction CSS)
- Modify: `static/app.js:195-240` (renderConstruction function)

**Step 1: Replace the construction HTML block in `index.html`**

Find the `<div id="construction-row"...>` block (lines 191–205). Replace entirely with:

```html
        <!-- Construction score -->
        <div id="construction-row" class="construction-row" hidden>
          <div class="prop-row">
            <span>Construction</span>
            <div class="bar-track"><div class="bar" id="bar-construction"></div></div>
            <span id="construction-score" class="prop-val">—</span>
          </div>
          <p id="construction-floor-note" class="construction-floor-note"></p>
          <ul id="construction-signals" class="construction-signals"></ul>
        </div>
```

**Step 2: Update `renderConstruction()` in `app.js`**

Replace the entire `renderConstruction` function (lines 195–240) with:

```js
function renderConstruction(c) {
  const row = document.getElementById("construction-row");
  const constrHeader = document.querySelector(".section-header-construction");
  if (!c) {
    row.hidden = true;
    if (constrHeader) constrHeader.hidden = true;
    return;
  }
  row.hidden = false;
  if (constrHeader) constrHeader.hidden = false;

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
```

**Step 3: Remove now-unused construction CSS in `style.css`**

Delete these selectors (lines ~435–498):
- `.construction-header { ... }`
- `.construction-label { ... }`
- `.construction-score-wrap { ... }`
- `#construction-score { ... }`
- `.construction-denom { ... }`
- `.construction-conf { ... }`

Keep:
- `.construction-row { ... }` — still needed for padding
- `.construction-floor-note { ... }` — still needed
- `.construction-signals { ... }` and `li` — still needed

**Step 4: Verify locally**

Score a product. Check the `/CONSTRUCTION` section:
- Shows a single bar row: "Construction [===-------] 3.5 / 10"
- Floor note appears below (if present)
- Chip signals appear below that
- Visual style matches `/PROPERTIES` bars above

**Step 5: Commit**

```bash
git add templates/index.html static/style.css static/app.js
git commit -m "style: unify construction section with property bar pattern"
```

---

### Task 6: Fix download button animation (`style.css` + `app.js`)

**Files:**
- Modify: `static/style.css` (add after `.btn-download` block, around line 525)
- Modify: `static/app.js:257-263` (download button handler)

**Step 1: Add animated ellipsis CSS**

In `style.css`, after the `.btn-download:hover` rule, add:

```css
@keyframes ellipsis {
  0%   { content: "[ EXPORTING ]"; }
  33%  { content: "[ EXPORTING . ]"; }
  66%  { content: "[ EXPORTING .. ]"; }
  100% { content: "[ EXPORTING ... ]"; }
}

.btn-download.exporting {
  opacity: 0.7;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-download.exporting::before {
  content: "[ EXPORTING ]";
  animation: ellipsis 1.2s steps(1) infinite;
}
```

Note: because `::before` content is used for animation, we need to hide the button's text content when exporting. We'll handle this in JS.

**Step 2: Update download button handler in `app.js`**

Find the `btn-download` click handler (lines 257–263):

```js
document.getElementById("btn-download").addEventListener("click", () => {
  const btn = document.getElementById("btn-download");
  btn.disabled = true;
  btn.textContent = "Preparing…";

  const finish = () => { btn.disabled = false; btn.textContent = "[ DOWNLOAD CARD ]"; };
```

Replace with:

```js
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
```

**Step 3: Verify locally**

Click `[ DOWNLOAD CARD ]`. Confirm:
- Button text clears and animated `[ EXPORTING ]` → `[ EXPORTING . ]` → `[ EXPORTING .. ]` cycles
- After download completes, button returns to `[ DOWNLOAD CARD ]`

**Step 4: Commit**

```bash
git add static/style.css static/app.js
git commit -m "style: animated exporting state for download button"
```

---

### Task 7: Deploy and final check

**Step 1: Run full test suite one more time**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_extractor.py -v
```

Expected: 33 passed

**Step 2: Push to Railway**

```bash
git push origin main
```

Railway auto-deploys. Takes ~60 seconds.

**Step 3: Verify live at `https://web-production-adff3.up.railway.app`**

Check:
- Verdict sentences are short and punchy
- "Price fit" label shows (not "Price pressure")
- CPW lifespan note appears below stats
- Construction section looks like a property bar
- Download button shows animated state when clicked

**Step 4: Update CLAUDE.md session log**

In `CLAUDE.md`, add to Session Log:
```
| 2026-03-31 | UX polish: verdict rewrite (decision-assistant tone), Price fit label, CPW context, construction unification, download button animation |
```
