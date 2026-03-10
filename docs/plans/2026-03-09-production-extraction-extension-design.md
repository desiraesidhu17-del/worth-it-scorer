# Production Extraction Pipeline + Chrome Extension Design
**Date:** 2026-03-09
**Status:** Approved
**Scope:** Full production upgrade — extraction quality + blocked-site fix in one build

---

## Problem

1. Current extraction dumps 8000 chars of messy page text at GPT for every request — expensive, slow, inaccurate
2. 13 major retailers (Zara, ASOS, Free People, etc.) block server-side scraping entirely — users must paste text manually
3. No extraction validation — bad compositions silently produce bad scores, eroding trust

---

## Architecture Overview

```
Chrome Extension                  Railway Backend              Web App (existing)
─────────────────                 ───────────────              ──────────────────
User on any product page
  ↓ clicks extension icon
popup shows "Score this page"
  ↓ user clicks
content.js extracts:
  • page URL
  • JSON-LD blocks (parsed)   →  POST /api/score-page   →   new extraction pipeline
  • meta tags                     (new endpoint)             Steps 0-6 (see below)
  • candidate DOM blocks              ↓                      returns { result_id }
                               stores result (TTL)
background.js opens:
  web app?result=<uuid>    ←──────────────────────────
                               GET /api/result/<uuid>
                               Web app renders score
```

**Three backend additions:**
1. New extraction pipeline (`scoring/extractor.py`) replacing current GPT-first approach
2. `POST /api/score-page` — accepts pre-extracted extension payload, returns `{ result_id }`
3. `GET /api/result/<uuid>` — serves cached result; in-memory TTL for MVP, Redis/Postgres for production

**Web app:** one new behaviour — on load, if `?result=<uuid>` in URL, fetch and render score, skip input form.

---

## Extraction Pipeline (Steps 0–6)

### Step 0 — Candidate block isolation
From rendered DOM when available (extension capture), otherwise raw fetched HTML:
- Iterate headings, buttons, labels, `<summary>`/`<details>` nodes, divs/spans
- Text-match labels: `Materials|Fabric|Composition|Care|Details|Shell|Lining|Body|Trim|Content|Construction` (case-insensitive, in JS)
- Collect bounded nearby sibling/child text (capped by text length/node count, not fixed depth)
- Deduplicate repeated mobile/desktop DOM variants (text hash)
- Rank candidates by proximity to product-detail headers
- Retain full page text as fallback metadata only — not primary extraction input

### Step 1 — JSON-LD candidate (confidence weight: high)
- Parse all `<script type="application/ld+json">` blocks
- Look for `@type: Product` → `offers.price`, `description`, material-like fields
- Tag as high-confidence **candidate**, not automatic final answer
- Treated as final only if: single composition block + percentages present + unambiguous fibers

### Step 2 — Meta tags (price/brand only)
- Extract: `og:title`, `product:price:amount`, `og:price:amount`, `og:description`
- Does not produce composition — supplements price and brand signals only

### Step 3 — Contextual regex (run on candidate blocks, NOT full page)
**Primary rule:** only trust `%` matches when nearby text contains material context keywords:
`material|fabric|shell|lining|body|composition|trim|care|content|fibre|fiber`

Pattern: `r"(\d+(?:\.\d+)?)\s*%\s*([a-zA-Z][a-zA-Z\s]{2,25})"`

**Controlled fiber vocabulary (canonical form → aliases):**
| Canonical | Aliases |
|---|---|
| polyester | — |
| recycled polyester | recycled polyester |
| cotton | organic cotton → cotton + modifier |
| nylon | polyamide, recycled nylon → nylon + modifier |
| viscose | rayon (both → `viscose` internally; original preserved in `composition_raw`) |
| elastane | spandex |
| lyocell | tencel, tencel lyocell |
| wool | merino wool → wool + modifier |
| linen | flax |
| polyurethane | PU |
| silk, cashmere, mohair, hemp, bamboo, modal, cupro, acetate, acrylic | — |

**Non-fiber materials** (tagged separately, not scored as `%` composition):
leather, suede, down — get `material_type: "non-fiber" | "fill"`

**Multi-block detection:** detect prefixes `Outer:`, `Lining:`, `Shell:`, `Body:` → produce separate `composition_blocks[]`

**After regex match:** strip trailing noise (`"exclusive of trims"`, `"imported"`, `"body"`, `"shell"`) — keep base fiber + recycled/organic modifier only.

### Step 4 — LLM resolver (GPT-4o-mini)
Runs **only if** Steps 1+3 yield no composition, OR candidates conflict.

Input: title + price + candidate blocks only (hard cap 1500 chars)

Output schema (strict JSON):
```json
{
  "product_name": "string",
  "price": "number | null",
  "brand": "string | null",
  "composition_blocks": [
    {"part": "shell|lining|trim|body|unknown",
     "fibers": [{"fiber": "string", "pct": "number"}]}
  ],
  "main_composition": ["array | null"],
  "confidence": "high|medium|low",
  "reasoning": "string (one sentence, logs only — not used in logic)"
}
```

### Step 5 — Normalization
- Apply canonical fiber map (see Step 3 table)
- Flag `recycled polyester` vs `polyester` as distinct (different scoring weight)
- Lowercase, strip whitespace, remove duplicates within a block
- Viscose/rayon → `viscose` internally, original preserved in `composition_raw`

### Step 6 — Validation + reconciliation
**Confidence is a numeric score (0.0–1.0) mapped to labels at output:**

| Percentage sum per block | Confidence weight |
|---|---|
| 95–105% | +high |
| 60–94% (partial disclosure) | +medium |
| <60% or >115% (suspect) | −low, flag |

**Conflict resolution priority (highest wins):**
1. Explicit structured data (JSON-LD with percentages)
2. More detailed explicit block over less detailed
3. Labeled block (shell/body) over unlabeled
4. Keyword-adjacent regex over free-floating match
5. GPT inference (lowest)

**`main_composition` selection:**
- Shell or body block when explicitly labeled → use that
- Single unambiguous block → use that
- Otherwise → `null` (return `composition_blocks[]` only, let UI explain)
- Never force a main composition when page doesn't clearly support it

**Final output adds:**
```json
{
  "extraction_method": "json_ld|regex|gpt",
  "extraction_confidence": "high|medium|low",
  "composition_blocks": [...],
  "main_composition": [...] | null,
  "composition_raw": "verbatim text found"
}
```

---

## Chrome Extension (4 files)

```
extension/
  manifest.json    — Manifest V3
  content.js       — DOM extraction (runs against live rendered DOM, isolated world)
  popup.html       — UI
  popup.js         — orchestration
  icons/           — 16/48/128px
```
No background service worker needed for MVP flow.

### manifest.json
```json
{
  "manifest_version": 3,
  "name": "worth it?",
  "permissions": ["activeTab", "scripting"],
  "host_permissions": ["https://web-production-adff3.up.railway.app/*"],
  "action": { "default_popup": "popup.html" }
}
```

### content.js — extracts on demand
Runs against the live rendered DOM in the active tab (isolated world — DOM access, not page JS variables).

Extracts and returns:
- `window.location.href`
- All `<script type="application/ld+json">` blocks: parse if valid JSON → send as object; if malformed → send raw string in `json_ld_raw` fallback field
- Meta tags: `og:title`, `og:price:amount`, `product:price:amount`, `og:description`
- Candidate blocks: iterate headings/buttons/labels/summary/details nodes, text-match material labels in JS, collect bounded nearby sibling/child text, deduplicate

Sends compact payload (~5–10KB). No full HTML transmitted.

### popup.js — flow
```
1. User clicks extension icon → popup.html opens
2. popup.js injects content.js via chrome.scripting.executeScript (activeTab)
3. content.js extracts payload, returns to popup.js
4. popup.js shows "Scanning..."
5. POST /api/score-page to Railway
6. Receives { result_id }
7. chrome.tabs.create({ url: "...railway.app?result=<uuid>" })
8. Popup closes
```

### Popup error states
| State | Message |
|---|---|
| Not a product page | "Open a product page first" |
| No candidate blocks found | "No material info found on this page — try paste text" |
| Backend timeout | "Scoring timed out — try again" |
| Result expired | "Result expired — re-scan the page" |
| Low confidence | Pass-through from score card |

---

## Backend API Changes

### `POST /api/score-page` (new)
```
Input:  { url, json_ld[], json_ld_raw?, meta{}, candidate_blocks[], price?, category? }
Output: { result_id: "uuid" }
```
- Runs the new extraction pipeline (Steps 0–6)
- Stores full score result keyed by UUID
- MVP: in-memory dict with 5-min TTL + strong random UUID
- Production: Redis or Postgres

### `GET /api/result/<uuid>` (new)
```
Output: full score result JSON (same shape as existing /api/score)
404 if expired or not found
```

### CORS
Allow specific production extension origin (`chrome-extension://<extension-id>`) on both new endpoints. Not wildcard.

### Existing `/api/score` endpoint
Updated to use the new extraction pipeline for URL path (Steps 0–6 instead of current GPT-first approach).

---

## Web App Change

In `static/app.js`, on `DOMContentLoaded`:
```javascript
const params = new URLSearchParams(window.location.search);
const resultId = params.get('result');
if (resultId) {
  // fetch GET /api/result/<resultId>
  // render score card directly, skip input form
  // show graceful fallback if 404 (expired)
}
```

---

## Files Changed / Created

**New:**
- `scoring/extractor.py` — full extraction pipeline (Steps 0–6)
- `app.py` — `POST /api/score-page`, `GET /api/result/<uuid>`, CORS, updated URL path
- `extension/manifest.json`
- `extension/content.js`
- `extension/popup.html`
- `extension/popup.js`
- `extension/icons/` (placeholder PNGs)

**Modified:**
- `static/app.js` — result UUID render-on-load
- `app.py` — existing URL extraction path uses new extractor
- `scoring/__init__.py` — export new extractor

---

## What This Does Not Include

- User accounts / saved history (future)
- Firefox port (future, ~10 min once Chrome works)
- Chrome Web Store submission (manual step after build)
- Redis/Postgres for result persistence (noted, deferred to post-MVP)
