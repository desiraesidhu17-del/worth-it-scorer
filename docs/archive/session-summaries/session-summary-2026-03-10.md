# Worth It? — Session Summary (2026-03-10)

## What This App Is

**worth it?** is a clothing quality scoring tool built on fiber science, not opinion.
Users paste a product URL, paste product text, or enter composition manually — the app
extracts the fiber composition and returns a science-backed durability score.

Live backend: `https://web-production-adff3.up.railway.app`
Repo: `https://github.com/desiraesidhu17-del/worth-it-scorer`

---

## Architecture Overview

```
Browser (Chrome Extension)
  └─ popup.js: extracts DOM data → POST /api/score-page → opens web app with ?result=UUID

Web App (Flask on Railway)
  ├─ GET  /             → index.html (manual form + URL tab + paste-text tab)
  ├─ POST /api/score    → scores a manually-entered composition
  ├─ POST /api/score-page → scores a full page payload (from extension)
  └─ GET  /api/result/<uuid> → fetches a cached score result (5-min TTL)

Scoring Engine (Python)
  ├─ scoring/fiber_vocab.py       — fiber normalization, aliases, known fiber registry
  ├─ scoring/extractor.py         — 6-step pipeline: regex → JSON-LD → GPT fallback
  ├─ scoring/fiber_properties.py  — ASTM-backed property scores per fiber
  └─ scoring/scorer.py            — blend interaction tables, final score calculation

Chrome Extension
  ├─ extension/manifest.json  — MV3, activeTab + scripting permissions
  ├─ extension/popup.html     — dark UI, "Score this page" button
  ├─ extension/popup.js       — orchestrates DOM extraction + API call
  └─ extension/content.js     — reference mirror of popup.js extraction logic
```

---

## What Was Built This Session

### 1. Scoring Engine (`scoring/`)

**`fiber_vocab.py`** — Fiber normalization
- Canonical fiber names + alias map (e.g. "poly" → "polyester", "modal" → "modal")
- Modifier handling: `normalize_fiber("organic cotton") → "cotton"` (strips non-functional modifiers)
- `normalize_fiber("recycled polyester") → "recycled polyester"` (recycled is preserved — different properties)
- `is_known_fiber()` function for filtering false-positive regex matches

**`extractor.py`** — 6-step extraction pipeline
1. Contextual regex (finds `NN% fiber` patterns near material keywords)
2. Short-text bypass (texts ≤300 chars skip the keyword context check)
3. JSON-LD structured data parsing
4. Candidate block scoring
5. GPT-4o-mini fallback for ambiguous text
6. Returns `ExtractionResult` dataclass with confidence level

**`scoring/test_extractor.py`** — 20 tests, all passing
- Fiber normalization, contextual regex, JSON-LD, candidate blocks, GPT fallback path

Key bug fixed: "recycled polyester" was missing from `FIBER_ALIASES` in `fiber_properties.py`.
Added: `"recycled polyester": "polyester"`, `"recycled nylon"`, `"recycled cotton"`, `"recycled wool"`.

---

### 2. New Flask Endpoints (`app.py`)

**`POST /api/score-page`**
- Accepts: `{url, json_ld, json_ld_raw, meta, candidate_blocks}` (the extension's DOM payload)
- Runs the production extraction pipeline on the payload
- Stores result in `_result_store` (in-memory dict) with 5-minute TTL
- Returns: `{result_id: UUID}`

**`GET /api/result/<result_id>`**
- Fetches the cached result by UUID
- Returns 404 if not found or expired
- Used by the web app to render the score after redirect from extension

Both endpoints have CORS headers for cross-origin requests from the extension.

---

### 3. Web App UUID Rendering (`static/app.js`)

Added IIFE at page load that checks `?result=UUID` in the URL.
If present, fetches the result from `/api/result/<uuid>` and auto-renders the score card.
This is how the extension hands off results to the web app.

---

### 4. Chrome Extension (`extension/`)

**`manifest.json`** — MV3
- Permissions: `activeTab`, `scripting`
- Host permissions: the Railway production domain

**`popup.js`** — Main extension logic
1. Gets the active tab
2. Injects an async `func:` into the page (MV3 requirement for return values)
3. Extraction runs in the page's context, returns DOM data
4. POSTs to `/api/score-page`
5. Opens the web app at `?result=<uuid>`

**Why `func:` injection, not `files:`?**
In MV3, `executeScript` with `files:` doesn't return the script's return value.
Using `func:` (inline function) captures the return value correctly.

---

## Bugs Fixed During Real-World Testing

### Bug 1: Aritzia returned score 0
**Cause:** `"recycled polyester"` not in `FIBER_ALIASES` in `fiber_properties.py`.
Scoring engine got `None` for it and returned 0.
**Fix:** Added recycled fiber variants to `FIBER_ALIASES`.

### Bug 2: Composition hidden inside collapsed accordion (Aritzia "Details" button)
**Cause:** The extension read the DOM before the accordion was opened — the composition
text simply wasn't in the DOM yet.
**Fix:** Before extraction, the injected script now:
1. Clicks all `button`/`summary`/`[role=button]`/`[role=tab]` elements whose text matches the LABEL_RE
2. Clicks all `[aria-expanded='false']` elements whose text mentions material/fabric/detail
3. Waits 600ms for animations to complete
4. Then runs DOM extraction on the expanded page

### Bug 3: Retailer label naming inconsistency
**Cause:** Original code used an exact-match `Set` for label names. This worked for
"Materials & Care" but not "Composition, Care & Origin" (Zara), "Content" (Free People),
or "Product Details" (Madewell).
**Fix:** Replaced the exact Set with a keyword regex:
```javascript
const LABEL_RE = /\b(material|fabric|composition|fibre?|shell|lining|body|trim|care|details?|construction|content)\b/i;
```
Now any label containing one of those root words matches — regardless of how each
retailer phrases it. Label max length also increased from 60 → 80 chars to accommodate
longer compound labels like "Composition, Care & Origin".

---

## Coverage by Retailer (After Fixes)

| Retailer | Their label | Matched by |
|----------|-------------|-----------|
| Aritzia | "Materials & Care" | `material`, `care` + accordion auto-expand |
| Free People | "Content" | `content` |
| Madewell | "Product Details" | `details` |
| Zara | "Composition, Care & Origin" | `composition` |
| Generic | "Fabric & Care", "Fiber Content", "Shell" | regex keywords |

---

## Body Text Fallback

If `candidate_blocks` is still empty after the label walk and `<details>` check,
the extension appends `document.body.innerText.slice(0, 3000)` as a fallback block.
The backend's GPT extractor can then find composition from raw page text.

---

## What's NOT Yet Built (From the Full Plan)

1. **Construction quality score** — GPT-4o vision rubric (stitch type, seam finish, lining, etc.)
2. **Resale retention rate** — ThredUp/eBay scraping for brand-level value signals
3. **Cost-per-wear model** — pure math from durability score + price
4. **Brand construction database** — seed 50 brands with manual construction ratings
5. **Comparable retail pricing** — "items like this retail for $X–Y"
6. **Share card export** — designed for cost-per-wash as headline stat
7. **Wardrobe tracker + outcome loop** — user reports at 90 days calibrate predictions
8. **Three-tab web app input** — URL scan, paste text, manual (currently only manual + URL)

---

## Known Limitations

- **Construction score is a stub** — currently returns 5/10 with "low confidence" for all items.
  This is honest but the rubric isn't built yet.
- **Value/price score** — without resale data or a comparable product database, price pressure
  shows "unknown" unless user enters a price manually.
- **Result store is in-memory** — Railway restarts wipe all stored results. Fine for 5-min TTL
  use case (extension → web app handoff), but long-term storage would need Redis or a DB.
- **pyenv shell issue** — `preview_start` tool fails locally due to a pyenv `getcwd` error.
  Verification done via curl against the Railway production endpoint instead.

---

## How to Test the Extension

1. Go to `chrome://extensions`
2. Enable "Developer mode"
3. "Load unpacked" → select `/Users/desiraesidhu/clothing_quality_backend/extension/`
4. Navigate to any clothing product page (Aritzia, Zara, Free People, Madewell, ASOS, etc.)
5. Click the "worth it?" extension icon → "Score this page"
6. Extension auto-expands accordions, extracts composition, scores it, opens result tab

**To update the extension after code changes:** go to `chrome://extensions` → Reload.
Railway redeploys automatically on every `git push origin main`.
