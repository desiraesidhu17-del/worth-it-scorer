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
- 33/33 tests passing
- **Cold Data visual redesign — COMPLETE and deployed to Railway**
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

### 🔲 Next Up (backlog — lower priority)
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
  extractor.py             DOM payload → fiber composition + price
  engine.py                score_item() → ScoreResult
  construction_rubric.py   Construction score 0–10
  test_extractor.py        33 tests — run with: pytest scoring/test_extractor.py
extension/
  popup.js                 Chrome MV3 — DOM scraping + price extraction cascade
templates/index.html       Web frontend
static/style.css           All styles (Cold Data theme — cream, Space Mono, zero radius)
static/app.js              Frontend JS — renders result card
docs/plans/                Design docs + implementation plans
```

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
| `/api/score-page` | POST | Extension endpoint — pre-scraped payload → `{result_id}` |
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
pytest scoring/test_extractor.py   # should be 33 passed
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
