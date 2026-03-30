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
**Deploy:** `git push origin main` → Railway auto-deploys

---

## Current State

### ✅ Working
- Fabric extraction on Madewell, Aritzia, Free People, most retailers
- Price extraction (4-level cascade: itemprop → Shopify data attrs → CSS class → broad DOM scan)
- All price selectors in `try/catch` so failures never break fabric reading
- `extractor.py` has `_parse_price_raw()` handling CA$, £, €, AU$ etc.
- 33/33 tests passing

### 🔲 Next Up — Cold Data Visual Redesign (APPROVED, NOT STARTED)
Full plan at: `docs/plans/2026-03-29-cold-data-redesign-plan.md`

**Use `superpowers:executing-plans` to run the 8 tasks. Start with Task 1.**

Summary of the design:
- Font: Space Mono (Google Fonts)
- Background: cream `#f5f2eb` (was dark `#0f0f0f`)
- Score: large orange number replaces SVG circle
- Section headers: `/MATERIAL ANALYSIS`, `/PROPERTIES`, `/CONSTRUCTION`
- Stat rows with dotted leaders
- Zero border-radius everywhere
- Bracket-style buttons: `[ DOWNLOAD CARD ]`

### Known Issues
- Claude in Chrome MCP not connected (workaround: DevTools console snippets)
- Low score + "fairly priced" verdict can feel contradictory (UX debt, not a bug)

---

## Architecture

```
app.py                     Flask app + all API routes
scoring/
  extractor.py             DOM payload → fiber composition
  engine.py                score_item() → ScoreResult
  construction_rubric.py   Construction score 0–10
  test_extractor.py        33 tests — run with: pytest scoring/test_extractor.py
extension/
  popup.js                 Chrome MV3 — DOM scraping + price extraction
templates/index.html       Web frontend
static/style.css           All styles (currently dark — redesign pending)
static/app.js              Frontend JS — renders result card
docs/plans/                Design docs + implementation plans
```

### Key Routes
| Route | Method | What it does |
|-------|--------|-------------|
| `/api/score` | POST | Score from URL / text / manual entry |
| `/api/score-page` | POST | Extension endpoint — pre-scraped payload → `{result_id}` |
| `/api/result/<id>` | GET | Fetch result by UUID (10 min TTL) |

---

## Run Locally
```bash
cd /Users/desiraesidhu/clothing_quality_backend
python app.py          # http://localhost:5000
pytest scoring/test_extractor.py   # should be 33 passed
```

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
