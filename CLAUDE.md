# worth it? — Project Handoff

> This file is automatically read at the start of every session. Update it before ending any session with meaningful changes.

---

## What This Project Is

A clothing quality scoring Chrome extension + Flask backend.

- User visits a product page → clicks extension → it scrapes fabric + price from the DOM
- Backend scores fiber quality (0–100), price pressure, cost per wash, construction
- Opens a result tab with the full score card

**Live backend:** `https://web-production-adff3.up.railway.app`
**GitHub:** `https://github.com/desiraesidhu17-del/worth-it-scorer`
**Deploy:** `git push origin main` → Railway auto-deploys (Hobby plan, $5/month)

---

## Current State

### ✅ Working
- Fabric extraction on Madewell, Aritzia, Free People, most retailers
- Price extraction (6-level cascade: JSON-LD offers.price → OG meta → itemprop → Shopify data attrs → CSS class → broad DOM scan)
- Sale prices correctly detected on Aritzia, Revolve, and other retailers with crossed-out original prices
- All price selectors in `try/catch` so failures never break fabric reading
- `extractor.py` has `_parse_price_raw()` handling CA$, £, €, AU$ etc.
- 54/54 pytest + 35/35 engine tests passing
- **Cold Data visual redesign — COMPLETE and deployed to Railway**
- **Headline card redesign — COMPLETE and deployed to Railway**
- **Technical signal detection — COMPLETE and deployed to Railway** (GORE-TEX, seam sealing, PrimaLoft etc. → full card suppression for technical gear)
- T-shirt category weights rebalanced (tensile down, moisture up; cotton pilling bumped)
- **Scoring differentiation — COMPLETE and deployed to Railway** (GSM extraction + modifier, fiber dominance ±2, category-fit adjustments, construction → worth_it_score, confidence-aware GSM penalty)
- **Ambient Detection + Badge (Plan A) — COMPLETE and deployed to Railway** (auto-detect product pages, passive scan, colored verdict badge WI/MX/OP/?, 3-state popup, construction stat in stats row)
- Railway upgraded to Hobby plan ($5/month) — app stays live

### Cold Data Theme (live)
- Font: Space Mono throughout
- Background: cream `#f5f2eb`
- Score: large `4rem` orange number (`#f5820a`), thin rule, `/100`
- Section headers: `/MATERIAL ANALYSIS`, `/PROPERTIES`, `/CONSTRUCTION`
- Stat rows: vertical with dotted leaders (`....`)
- Confidence: `[HIGH CONFIDENCE]` bracket style
- Buttons: `[ SCAN PRODUCT ]` / `[ DOWNLOAD CARD ]` — invert on hover
- Zero border-radius everywhere
- Construction signals: outlined `[ chip ]` style
- `[hidden] { display: none !important }` in style.css — required so CSS flex rules don't override `hidden` attribute on stat divs

### Technical Override Card State (when isTech)
- Headline → "Technical performance gear"
- Sub → "Score reflects fiber composition only. Value is driven by membrane technology and construction."
- Score line → "Fiber score" in muted 1rem text; `/ 100 ·` separator hidden
- Watch-for row → hidden
- Verdict sentence → cleared
- Price fit stat row (`#price-fit-stat`) → hidden
- Cost per wear stat row (`#cpw-stat-row`) → hidden
- CPW note (`#cpw-note`) → hidden
- Price detail paragraph → hidden
- Technical override panel → visible with `[ signal ]` bracket list
- All suppressions reset correctly on "Score Another" and for non-tech results

### Ambient Mode State (Plan A — live)
- **content.js** runs on every https page at `document_idle`; `isProductPage()` requires 2+ of 3 signals (price element, add-to-cart button, H1). If it passes → full extraction → `chrome.runtime.sendMessage({type:"PASSIVE_PAYLOAD", payload})`
- **background.js** (MV3 service worker): `handlePassiveScan(tabId, payload)` POSTs to `/api/score-page` with `passive:true`, reads `verdict_bucket`, stores `{status, result_id, verdict}` in `chrome.storage.session[tab_${tabId}]`, sets per-tab badge. Idempotent (skips if already scoring/done). Clears badge + session on tab navigate (`onUpdated` status==loading) and close (`onRemoved`)
- **Badge map**: `worth_it→WI #4caf50` (green) · `mixed→MX #f5820a` (orange) · `overpriced→OP #e53935` (red) · `not_enough_info→? #9e9e9e` (gray)
- **popup.html / popup.js**: 3 states — `#state-scanning` (passive scan in progress), `#state-done` (verdict chip + `[ OPEN FULL CARD ]` + `[ RE-SCAN ]`), `#state-manual` (`[ SCAN PRODUCT ]` fallback). popup.js routes on `DOMContentLoaded` by reading session storage; `runManualScan()` is the preserved manual flow (inject extraction → POST → open result tab)
- **Verdict bucket** (`get_verdict_bucket` in engine.py): `not_enough_info` (low confidence OR no price) → `overpriced` (high/extreme pressure) → `mixed` (undercut) → `worth_it` (score≥65) → `mixed` (else)
- **Passive mode** (`/api/score-page`): `passive:true` skips GPT fallback (cost control), uses 1800s (30min) TTL vs 300s manual, returns `verdict_bucket` in response
- **Construction stat**: `#construction-stat-row` in stats row, shows `X/10` when `c.source !== "price_floor"` and score present; hidden otherwise
- content.js and popup.js share the SAME extraction logic (kept in sync manually — v1 tech debt, noted in both file headers)

### 🔲 Next Up (backlog — lower priority)
- **Plan B: Compare feature** (spec sections 4–5) — "Add to Compare" button + Compare view in extension-local HTML. Not yet planned. This was the deferred second half of the ambient_mode_spec.
- Fix verdict/price-label messaging inconsistency (low score + "fairly priced" contradiction)
- Test more retailers (H&M, Zara, Uniqlo)
- Add more metrics to result card (needs brainstorm + plan first)

### Known Issues
- Claude in Chrome MCP not connected (native host path fixed — `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.anthropic.claude_browser_extension.json` updated to point to `/Users/desiraesidhu/.local/share/claude/versions/2.1.71` — may need Chrome restart)
- Low score + "fairly priced" verdict can feel contradictory (UX debt, not a bug)

---

## Architecture

```
app.py                     Flask app + all API routes
scoring/
  extractor.py             DOM payload → fiber composition + price + gsm (Optional[float])
  engine.py                score_item() → ScoreResult; get_verdict_bucket(); GSM modifier, dominance/category adj, construction contrib
  construction_rubric.py   Construction score 0–10
  verdict_library.py       HEADLINE_MATRIX (25-entry), get_headline(), get_watch_for()
  technical_signals.py     detect_technical_signals() — 6 categories, is_technical at 2+
  fiber_properties.py      Per-fiber scores + per-category CATEGORY_WEIGHTS
  test_extractor.py        39 extractor tests
  test_verdict.py          15 verdict tests (headline + watch_for)
  tests.py                 35 engine integration tests (incl. 8 verdict_bucket tests)
extension/
  content.js               Passive detection — product-page check → extraction → message background
  background.js            MV3 service worker — receives payload, POSTs (passive), badge + session storage
  popup.html               3-state popup UI (scanning / done+verdict / manual fallback)
  popup.js                 Session-aware routing — reads chrome.storage.session, manual scan fallback
  manifest.json            v0.2.0 — background, content_scripts, storage+tabs perms
templates/index.html       Web frontend
static/style.css           All styles (Cold Data theme — cream, Space Mono, zero radius)
static/app.js              Frontend JS — renders result card (incl. construction stat row)
docs/active/               Current specs (e.g. current-card-spec.md)
docs/archive/              Completed plans + old session summaries (history, not active)
```

### Documentation map (source-of-truth split)
Three top-level files, each with one job — don't let them compete:
- **CLAUDE.md** (this file) — engineering state: what works, what's deployed, architecture, how to run/test/deploy.
- **PRODUCT_DECISIONS.md** — product logic & strategy: what the score means, polyester/technical handling, what we're not building.
- **CURRENT_ROADMAP.md** — what's next, what's frozen, what's "do not build yet."
- `docs/active/` = current specs · `docs/archive/` = completed/history (read for context, not direction).

### Price Extraction Cascade (popup.js)
The extension tries these in order, stopping at the first hit:
1. **JSON-LD `offers.price`** — most reliable; set by sites for Google Shopping, always reflects current selling price. Handles `@graph` wrapper and array offers.
2. **OG/product meta tags** — `og:price:amount`, `product:price:amount` — server-rendered, reliable
3. **`itemprop="price"`** — Schema.org microdata (checks `content` attr first, then text)
4. **Shopify data attrs** — `data-price`, `data-product-price`, `data-variant-price`, `data-sale-price` — converts cents when value ≥ 1000 with no decimal
5. **CSS class heuristics** — tries sale-specific selectors first (`sale-price`, `price--sale`, `price__current`), then general. Skips elements with `text-decoration: line-through`. Excludes `[class*='regular-price']` (always the crossed-out price).
6. **Broad DOM scan** — scans `span/strong/b/ins` leaf elements for currency patterns

### Key Routes
| Route | Method | What it does |
|-------|--------|-------------|
| `/api/score` | POST | Score from URL / text / manual entry |
| `/api/score-page` | POST | Extension endpoint — pre-scraped payload → `{result_id, verdict_bucket}`; accepts `passive: true` to skip GPT + extend TTL |
| `/api/result/<id>` | GET | Fetch result by UUID (10 min TTL) |

### Backend Price Handling (extractor.py)
`extract_from_payload()` receives the extension payload. Price priority:
- `payload["price"]` (from extension's 6-step cascade above) overrides everything
- If no payload price: JSON-LD `offers.price` from the backend's own parse
- If still none: `og:price:amount` / `product:price:amount` meta tags
- `_parse_price_raw()` strips all currency symbols/codes (CA$, £, €, AU$, etc.)

---

## Run Locally
```bash
cd /Users/desiraesidhu/clothing_quality_backend
python app.py          # http://localhost:5000
pytest scoring/test_extractor.py scoring/test_verdict.py   # should be 54 passed
python -m scoring.tests   # should be 35 passed
```

`.claude/launch.json` is configured — use `preview_start` with name `worth-it-server` (runs on port 5001).

---

## Skills Reference
| Situation | Use |
|-----------|-----|
| New feature / UI change | `superpowers:brainstorming` first |
| Have a spec, need a plan | `superpowers:writing-plans` |
| Executing a written plan | `superpowers:executing-plans` |
| Bug / unexpected behavior | `superpowers:systematic-debugging` |
| Done with a chunk of work | `superpowers:requesting-code-review` |

---

## Session Log
| Date | What was done |
|------|--------------|
| 2026-03-10 | Built extension + extraction pipeline, deployed to Railway |
| 2026-03-29 | Fixed fabric extraction (context window, LABELS bug), added price extraction |
| 2026-03-30 | Fixed price bugs (CA$ parsing, itemprop selector, DOM scan crash), designed Cold Data redesign |
| 2026-03-30 | Implemented Cold Data redesign (all 8 tasks): Space Mono, cream palette, flat score number, /SECTION headers, dotted stat rows, bracket UI, deployed to Railway |
| 2026-03-31 | UX polish: verdict rewrite (decision-assistant tone), Price fit label, CPW context, construction unification, download button animation |
| 2026-04-15 | Fixed sale price extraction on Aritzia + Revolve. Root cause: extension was reading the crossed-out original price from the DOM before the sale price. Fix: added JSON-LD offers.price as Step 0 (most reliable source — e-commerce sets this for Google Shopping, always the current price) and OG meta as Step 0b. Also added strikethrough detection + sale-selector priority to CSS class step, removed [class*='regular-price']. Backend extractor.py: payload price overrides structured data (extension now sends the right price). Native messaging host JSON fixed (AppTranslocation stale path → correct `.local/share/claude` path). Railway trial expired mid-session → upgraded to Hobby plan ($5/mo). |
| 2026-04-22 | Headline card redesign (7 tasks, TDD, subagent-driven). Score demoted from hero to supporting line; outcome headline now leads. New: `get_headline()` 25-entry matrix (band × price_pressure), B-override for premium fibers ("Built for feel, not longevity"), `get_watch_for()` 3-layer failure-mode lookup. `ScoreResult` gains `headline/headline_sub/watch_for`. Frontend: card-top → vertical stack, construction hidden at price-floor, CPW → "Est. cost per wear", ASTM attribution under /PROPERTIES. Fixed "below-average blend ratio" verdict bug on 100% silk. Merged to main, pushed to Railway. |
| 2026-04-22 | T-shirt scoring rebalanced: tensile 0.35→0.25, moisture 0.15→0.28, pilling 0.30→0.25, colorfastness 0.20→0.22. Cotton pilling 45→50. Added `"moisture": (30.0, "Traps heat, low breathability")` to `_WATCH_PROPERTY_GENERIC` — polyester tees now flag heat-trapping. Result: cotton t-shirt 63→69 (good band), polyester 76→67 (good band + moisture flag). 48 pytest + 12 engine tests passing. Pushed to Railway. |
| 2026-04-22 | Technical signal detection: `scoring/technical_signals.py` with `detect_technical_signals()` — 6 categories (membrane brands, DWR, seam sealing, shell terms, performance ratings, insulation), `is_technical=True` at 2+ categories. `app.py` runs detection on `candidate_text` in extension path, attaches `technical_override: [signals]` to result. Frontend: if `technical_override` present, hide price-fit row and show Cold Data override panel with bracket-style signal list. Pushed to Railway. |
| 2026-04-22 | Scoring differentiation (7 tasks, TDD, subagent-driven): GSM extraction in extractor.py (`_extract_gsm`, `_CELLULOSE_FIBERS`); GSM modifier ±10 in engine.py; fiber dominance ±2 and category-fit adjustments (acrylic sweater -5, cotton activewear -4, etc.) combined into ±15 cap; construction score wired into `worth_it_score` via `_construction_contribution()` formula; confidence-aware -3 penalty for cotton/linen t-shirt/dress with unknown weight. GSM threaded through app.py (extension path + Path C). 54 pytest + 27 engine tests. Pushed to Railway. |
| 2026-04-25 | Continued scoring differentiation (Tasks 5–7 + quality fixes). Task 5 quality: extracted `_CELLULOSE_FIBERS` frozenset constant (shared by `_gsm_modifier_for_score` + step 5.5), dropped leading-underscore locals, tightened dress test to exact 3-pt delta, updated stale `_assess_confidence` comment. Task 6: GSM wired through app.py — extension path passes `gsm=result_extraction.gsm`; Path C accepts `gsm` from JSON body with float-cast guard; `float | None` annotation consistent with file style. Task 7: all 54 pytest + 27 engine tests verified passing. CLAUDE.md + MEMORY.md updated. Pushed to Railway. |
| 2026-04-30 | Technical override card suppression (static/app.js + templates/index.html + static/style.css). When `technical_override` signals present: headline → "Technical performance gear"; sub → fiber-only disclaimer; score → "Fiber score" muted label (number + separator hidden); watch-for, verdict sentence, price fit stat, cost-per-wear stat + note all hidden. Added `id="price-fit-stat"`, `id="score-sep"`, `id="cpw-stat-row"` to HTML for JS targeting. Added `[hidden] { display: none !important }` CSS reset so flex rules don't override `hidden` attribute. Verified `technical_override` is a plain array from backend (not `{signals_found: [...]}`) — confirmed via live API test. Commits: 9d5c544, 2cd2d6f. Pushed to Railway. |
| 2026-06-17 | Ambient Detection + Badge (Plan A, 8 tasks, subagent-driven). Extension now auto-detects product pages and shows a colored badge (WI/MX/OP/?) without user interaction. Key changes: `get_verdict_bucket()` + `verdict_bucket` field on `ScoreResult`; `passive` flag on `/api/score-page` (skips GPT, 30-min TTL, returns `verdict_bucket`); new `content.js` (passive detection — product-page check + extraction); new `background.js` (service worker: receives payload, POSTs to backend, sets per-tab badge + `chrome.storage.session`); `manifest.json` bumped to v0.2.0 (background, content_scripts, storage+tabs perms); `popup.html` 3-state UI (scanning/done/manual); `popup.js` session-aware routing (reads session, shows verdict chip or falls back to manual scan); construction stat added to stats row (hidden at price_floor). 54 pytest + 35 engine tests passing. Pushed to Railway. |
| 2026-06-19 | Docs reorg — split source-of-truth into three files: `CLAUDE.md` (engineering state), new `PRODUCT_DECISIONS.md` (product logic/strategy — incl. 3 🟡 NEEDS INPUT sections: brand ownership, Shop positioning, discovery sequencing), new `CURRENT_ROADMAP.md` (next/frozen/do-not-build). Created `docs/active/` (current-card-spec.md) and `docs/archive/` (moved all 12 completed plan docs + both old session summaries out of root and `docs/plans/`). Removed empty `docs/plans/` + `docs/superpowers/`. No code changes. |
