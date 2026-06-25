# Cold Data Visual Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restyle the Worth It? web app from dark minimal to "Cold Data" — cream background, Space Mono font throughout, zero border-radius, Bloomberg-orange score, bracket-style UI, flat section headers.

**Architecture:** Pure CSS + minimal HTML structure changes. No backend changes. The SVG score circle is replaced with a plain number block in HTML; a small JS change removes the arc animation. Everything else is CSS token swaps, border-radius removal, and new section-header markup.

**Tech Stack:** HTML/CSS/JS (vanilla). Space Mono via Google Fonts CDN.

---

## Reference: Design Spec
See `docs/plans/2026-03-29-cold-data-redesign.md` for full palette, typography, and layout spec.

---

## Task 1: Load Space Mono font + swap CSS tokens

**Files:**
- Modify: `templates/index.html` (add `<link>` in `<head>`)
- Modify: `static/style.css` (lines 1–26 — `:root` variables + `body` font)

**Step 1: Add Google Fonts link to `<head>` in `index.html`**

After `<meta name="viewport" .../>`, add:
```html
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet" />
```

**Step 2: Replace `:root` variables in `style.css`**

Replace the entire `:root` block (lines 4–16):
```css
:root {
  --bg:       #f5f2eb;
  --surface:  #ede9df;
  --border:   #ccc8be;
  --text:     #1a1a1a;
  --muted:    #8a8070;
  --red:      #c0392b;
  --yellow:   #a07800;
  --green:    #2d6e3e;
  --score:    #f5820a;
  --radius:   0px;
  --mono:     "Space Mono", "Courier New", Courier, monospace;
}
```

**Step 3: Replace `html, body` font-family in `style.css`**

Replace line 21:
```css
  font-family: var(--mono);
  font-size: 14px;
```

**Step 4: Verify locally**

Start server: `cd /Users/desiraesidhu/clothing_quality_backend && python app.py`
Open `http://localhost:5000` — page should now be cream background with monospace font.

**Step 5: Commit**
```bash
git add templates/index.html static/style.css
git commit -m "style: load Space Mono + swap to cream Cold Data palette"
```

---

## Task 2: Remove all border-radius

**Files:**
- Modify: `static/style.css` — remove every `border-radius` except `--radius` already 0

**Step 1: Set all border-radius values to 0**

In `style.css`, find and replace every occurrence of `border-radius` with `border-radius: 0`:
- Line 128: `border-radius: 8px;` → `border-radius: 0;` (inputs)
- Line 254: `border-radius: var(--radius);` → `border-radius: 0;` (`#card-inner`)
- Line 392: `border-radius: 3px;` → `border-radius: 0;` (`.bar-track`)
- Line 398: `border-radius: 3px;` → `border-radius: 0;` (`.bar`)
- Line 469: `border-radius: 4px;` → `border-radius: 0;` (`.construction-signals li`)
- Line 485: `border-radius: 8px;` → `border-radius: 0;` (`.btn-download`)
- Line 499: `border-radius: 8px;` → `border-radius: 0;` (`.btn-reset`)
- Line 151: `border-radius: 8px;` → `border-radius: 0;` (`.btn-score`)
- Line 191: `border-radius: 50%;` → remove (`.spinner` — keep as circle via `border-radius: 50%`)
- Line 166: `border-radius: var(--radius);` → `border-radius: 0;` (`.drop-zone`)
- Line 192: `border-radius: var(--radius);` → `border-radius: 0;` (`#image-preview`)
- Line 204: `border-radius: 50%;` → keep (`.#remove-image` is a circle button — acceptable exception)

**Step 2: Verify**

Page should have sharp corners everywhere.

**Step 3: Commit**
```bash
git add static/style.css
git commit -m "style: remove all border-radius — zero everywhere"
```

---

## Task 3: Replace SVG score circle with flat number block

**Files:**
- Modify: `templates/index.html` (lines 144–164 — `.card-top` section)
- Modify: `static/style.css` (score circle styles → score block styles)
- Modify: `static/app.js` (lines 160–165 — remove SVG arc animation)

**Step 1: Replace score circle HTML**

Replace the entire `.card-top` div (lines 144–164) with:
```html
        <div class="card-top">
          <div class="score-block">
            <span id="score-number" class="score-number">—</span>
            <div class="score-rule"></div>
            <span class="score-denom">/ 100</span>
          </div>

          <div class="card-top-right">
            <p id="verdict-sentence" class="verdict-sentence"></p>
            <div class="confidence-badge">
              <span id="confidence-label"></span>
              <span id="confidence-note" class="confidence-note"></span>
            </div>
          </div>
        </div>
```

**Step 2: Replace score circle CSS**

Remove the `.score-circle`, `.score-circle svg`, `.track`, `.arc`, `.score-number-wrap`, `.score-label` blocks (lines 267–305).

Add in their place:
```css
.score-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  flex-shrink: 0;
  width: 90px;
}

.score-number {
  font-size: 4rem;
  font-weight: 700;
  line-height: 1;
  color: var(--score);
  font-variant-numeric: tabular-nums;
}

.score-rule {
  width: 100%;
  height: 1px;
  background: var(--border);
  margin: 6px 0 4px;
}

.score-denom {
  font-size: 0.75rem;
  color: var(--muted);
  letter-spacing: 0.04em;
}
```

**Step 3: Remove SVG animation from `app.js`**

Remove lines 160–165 in `app.js`:
```js
  const CIRCUMFERENCE = 326.73;
  const offset = CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE;
  const arc = document.getElementById("score-arc");
  arc.style.strokeDashoffset = offset;
  arc.style.stroke = scoreColor(score);
```

Keep line 159 and 165:
```js
  document.getElementById("score-number").textContent = score;
  // ... keep this line:
  document.getElementById("score-number").style.color = scoreColor(score);
```

Also update `scoreColor()` in `app.js` (line 251) to use CSS vars matching new palette:
```js
function scoreColor(score) {
  if (score >= 66) return "var(--green)";
  if (score >= 41) return "var(--yellow)";
  return "var(--red)";
}
```
(No change needed — already uses CSS vars. Just verify it still works.)

**Step 4: Fix the `btn-reset` reset handler** — line 310 in `app.js` references `score-arc`:
```js
  document.getElementById("score-arc").style.strokeDashoffset = 326.73;
```
Replace with:
```js
  document.getElementById("score-number").textContent = "—";
  document.getElementById("score-number").style.color = "";
```

**Step 5: Verify**

Score a product. Should show large orange number `70`, a thin rule, and `/100` beneath it. No circle.

**Step 6: Commit**
```bash
git add templates/index.html static/style.css static/app.js
git commit -m "style: replace SVG score circle with flat mono number block"
```

---

## Task 4: Add /SECTION headers + style stat rows

**Files:**
- Modify: `templates/index.html` (add section header divs before `.stats-row`, `.property-bars`, `.construction-row`)
- Modify: `static/style.css` (new `.section-header` class, stat row dots)

**Step 1: Add section header markup to `index.html`**

Before `.stats-row` (line 166), add:
```html
        <div class="section-header">/MATERIAL ANALYSIS</div>
```

Before `.property-bars` (line 183), add:
```html
        <div class="section-header">/PROPERTIES</div>
```

Before `#construction-row` (line 191), add:
```html
        <div class="section-header-construction section-header">/CONSTRUCTION</div>
```
(Note: `.section-header-construction` is hidden when construction is hidden — handled in JS)

**Step 2: Add section header CSS**

Add to `style.css` after the `#result-card` block:
```css
.section-header {
  padding: 10px 24px 6px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
  border-bottom: 1px solid var(--border);
}
```

**Step 3: Style stat rows with dotted leaders**

Replace the existing `.stat`, `.stat-label`, `.stat-value` rules with:
```css
.stats-row {
  display: flex;
  flex-direction: column;
  border-bottom: 1px solid var(--border);
}

.stat {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 8px 24px;
  border-bottom: 1px solid var(--border);
  gap: 8px;
}

.stat:last-child { border-bottom: none; }

.stat-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  flex-shrink: 0;
}

.stat-label::after {
  content: " ....................................................";
  color: var(--border);
  letter-spacing: 0;
  overflow: hidden;
  white-space: nowrap;
  display: inline-block;
  max-width: 100px;
}

.stat-value {
  font-size: 0.95rem;
  font-weight: 700;
  text-align: right;
  flex-shrink: 0;
}
```

**Step 4: Update construction section-header visibility**

In `renderConstruction()` in `app.js`, find the `row.hidden = true` line and add:
```js
  const constrHeader = document.querySelector(".section-header-construction");
  if (!c) {
    row.hidden = true;
    if (constrHeader) constrHeader.hidden = true;
    return;
  }
  row.hidden = false;
  if (constrHeader) constrHeader.hidden = false;
```

**Step 5: Verify**

Stat rows should show `DURABILITY` on the left with dots and `70 / 100` right-aligned.

**Step 6: Commit**
```bash
git add templates/index.html static/style.css static/app.js
git commit -m "style: add /SECTION headers and dotted stat-row leaders"
```

---

## Task 5: Square bars + bracket confidence badge

**Files:**
- Modify: `static/style.css` (bars already 0 from Task 2; update bar height + prop-row)
- Modify: `static/app.js` (confidence label format → `[HIGH CONFIDENCE]`)

**Step 1: Increase bar height and update prop-row label style**

In `style.css`, update:
```css
.bar-track {
  height: 4px;
  background: var(--border);
  border-radius: 0;
  overflow: hidden;
}

.prop-row {
  display: grid;
  grid-template-columns: 150px 1fr 32px;
  align-items: center;
  gap: 16px;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.prop-val {
  font-size: 0.78rem;
  color: var(--text);
  text-align: right;
  font-weight: 700;
}
```

**Step 2: Confidence badge bracket style**

Confidence label is already set in JS as `${conf.toUpperCase()} CONFIDENCE`. Wrap it in brackets in `app.js` line 171:
```js
  confLabel.textContent = `[${conf.toUpperCase()} CONFIDENCE]`;
```

Update `.confidence-badge` CSS:
```css
.confidence-badge {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

#confidence-label {
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  font-weight: 700;
}
```

Also update construction confidence in `app.js` line 220:
```js
  confEl.textContent = `[${conf.toUpperCase()} CONFIDENCE]`;
```

**Step 3: Verify**

Property bars should be thin square lines. Confidence should show `[MEDIUM CONFIDENCE]` with brackets.

**Step 4: Commit**
```bash
git add static/style.css static/app.js
git commit -m "style: square property bars, bracket confidence labels"
```

---

## Task 6: Bracket-style buttons + input styling

**Files:**
- Modify: `templates/index.html` (button text)
- Modify: `static/style.css` (button styles)
- Modify: `static/app.js` (download button text reset)

**Step 1: Update button text in `index.html`**

- Line 56: `Scan product` → `[ SCAN PRODUCT ]`
- Line 90: `Extract &amp; score` → `[ EXTRACT + SCORE ]`
- Line 123: `Score it` → `[ SCORE IT ]`
- Line 208: `Download card` → `[ DOWNLOAD CARD ]`
- Line 209: `Score another` → `[ SCORE ANOTHER ]`

**Step 2: Update `.btn-score` CSS**
```css
.btn-score {
  width: 100%;
  background: var(--text);
  color: var(--bg);
  border: 1px solid var(--text);
  border-radius: 0;
  padding: 12px;
  font-size: 0.8rem;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: 0.08em;
  cursor: pointer;
  margin-top: 8px;
  transition: background 0.15s, color 0.15s;
  text-transform: uppercase;
}

.btn-score:hover { background: var(--bg); color: var(--text); }
.btn-score:disabled { opacity: 0.4; cursor: not-allowed; }
```

**Step 3: Update `.btn-download` and `.btn-reset` CSS**
```css
.btn-download {
  flex: 1;
  background: var(--text);
  color: var(--bg);
  border: 1px solid var(--text);
  border-radius: 0;
  padding: 10px;
  font-size: 0.78rem;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  text-transform: uppercase;
}

.btn-download:hover { background: var(--bg); color: var(--text); }

.btn-reset {
  background: none;
  border: 1px solid var(--border);
  color: var(--muted);
  border-radius: 0;
  padding: 10px 20px;
  font-size: 0.78rem;
  font-weight: 700;
  font-family: var(--mono);
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  text-transform: uppercase;
}

.btn-reset:hover { color: var(--text); border-color: var(--text); }
```

**Step 4: Update download button reset text in `app.js`**

Line 262: `btn.textContent = "Download card"` → `btn.textContent = "[ DOWNLOAD CARD ]"`

**Step 5: Square input fields**
```css
input[type="text"],
input[type="number"],
input[type="url"],
textarea,
select {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text);
  border-radius: 0;
  padding: 10px 14px;
  font-size: 0.88rem;
  font-family: var(--mono);
  outline: none;
  width: 100%;
  transition: border-color 0.15s;
}

input:focus, select:focus, textarea:focus { border-color: var(--text); }
```

**Step 6: Style tabs as uppercase underline**
```css
.tab {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 0.72rem;
  font-family: var(--mono);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 8px 16px 8px 0;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}

.tab.active { color: var(--text); border-bottom-color: var(--text); }
```

**Step 7: Verify**

Buttons should be `[ SCAN PRODUCT ]` style, sharp corners, invert on hover. Inputs sharp and monospace.

**Step 8: Commit**
```bash
git add templates/index.html static/style.css static/app.js
git commit -m "style: bracket buttons, monospace inputs, uppercase tabs"
```

---

## Task 7: Error box + loading spinner + misc cleanup

**Files:**
- Modify: `static/style.css`
- Modify: `static/app.js` (update `extension-status` inline style)

**Step 1: Update error box for cream theme**
```css
#error-box {
  background: #f5ece9;
  border: 1px solid #c0392b;
  border-radius: 0;
  padding: 16px 20px;
  color: var(--red);
  margin-top: 24px;
  font-size: 0.85rem;
}
```

**Step 2: Update spinner for cream theme**
```css
.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border);
  border-top-color: var(--text);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin: 0 auto 16px;
}
```

**Step 3: Update `captureCard` backgroundColor in `app.js`**

Line 284: `backgroundColor: "#1a1a1a"` → `backgroundColor: "#f5f2eb"`

**Step 4: Update extension loading status inline style in `app.js`**

Line 14: `status.style.cssText = 'padding:20px;color:#aaa;font-size:14px;'`
→ `status.style.cssText = 'padding:20px;color:#8a8070;font-size:13px;font-family:monospace;'`

**Step 5: Update `#card-inner` background**
```css
#card-inner {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 0;
  overflow: hidden;
}
```

**Step 6: Update `.price-detail`**
```css
.price-detail {
  padding: 10px 24px 14px;
  font-size: 0.82rem;
  color: var(--muted);
  border-bottom: 1px solid var(--border);
  line-height: 1.5;
}
```

**Step 7: Update `.construction-signals li` to bracket style**
```css
.construction-signals li {
  font-size: 0.72rem;
  border: 1px solid var(--border);
  padding: 2px 8px;
  border-radius: 0;
  color: var(--muted);
  background: none;
}

.construction-signals li::before { content: "[ "; }
.construction-signals li::after  { content: " ]"; }
```

**Step 8: Commit**
```bash
git add static/style.css static/app.js
git commit -m "style: error box, spinner, card-inner, construction chips cream theme"
```

---

## Task 8: Final polish + deploy

**Files:**
- Modify: `static/style.css` (responsive fixes)
- Verify visual across all sections

**Step 1: Update responsive styles**
```css
@media (max-width: 520px) {
  .card-top { flex-direction: column; gap: 16px; }
  .card-top-right { text-align: left; }
  .stats-row { flex-direction: column; }
  .prop-row { grid-template-columns: 110px 1fr 32px; }
  .field-row.two-col { grid-template-columns: 1fr; }
  header { padding: 16px; }
  .score-number { font-size: 3rem; }
}
```

**Step 2: Full visual check**

Score a real product (Madewell jeans URL or manual `61% cotton, 39% lyocell`).
Verify:
- [ ] Header: `worth it?` monospace + `FIBER SCIENCE, NOT OPINION`
- [ ] Score: large orange number, thin rule, `/100`
- [ ] `[MEDIUM CONFIDENCE]` in brackets
- [ ] `/MATERIAL ANALYSIS` section header
- [ ] Dotted stat rows
- [ ] `/PROPERTIES` section header
- [ ] Thin square property bars
- [ ] `/CONSTRUCTION` header (hidden when no construction)
- [ ] `[ DOWNLOAD CARD ]` button inverts on hover
- [ ] All inputs sharp corners + monospace
- [ ] No rounded corners anywhere

**Step 3: Push to Railway**
```bash
git push origin main
```

**Step 4: Verify on Railway**

Open `https://web-production-adff3.up.railway.app` — confirm cream background deployed.

---

## Summary of files changed

| File | Changes |
|------|---------|
| `templates/index.html` | Font link, score block HTML, section headers, button text |
| `static/style.css` | Complete restyle — palette, font, border-radius, new components |
| `static/app.js` | Remove SVG arc, bracket confidence, download text, captureCard bg |
