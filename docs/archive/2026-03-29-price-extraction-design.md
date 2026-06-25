# Price Extraction Design
**Date:** 2026-03-29
**Status:** Approved

## Problem

The extension never sends price to the backend, so cost-per-wash and price-pressure scores are always blank. The backend already has price extraction logic (JSON-LD, meta tags) but it fails on non-USD currencies like `CA$217` because `_parse_price` only strips `$`.

## Approach: Active DOM Scraping in popup.js + Currency-Robust Parsing

### Data Flow

1. `popup.js` runs `extractPrice()` after the accordion expansion wait (sale prices have rendered)
2. Returns the first match from this priority cascade:
   - `[itemprop="price"]` → `content` attribute, then text content
   - `[data-price]` → attribute value
   - `r.meta["og:price:amount"]` or `r.meta["product:price:amount"]` (already collected)
   - First `[class*="price" i]` element whose text matches a price pattern
3. Raw price string (e.g. `"CA$217.00"`) sent as top-level `price` field in payload

### Backend

`_parse_price` in `app.py` currently only strips `$` and `,`. Replace with a regex that strips everything non-numeric except `.` and `,`, then parse. Handles:
- Currency codes: `CA$`, `AU$`, `NZ$`, `US$`, `GBP`
- Currency symbols: `£`, `€`, `¥`, `₩`, `₹`

### Files Changed

| File | Change |
|------|--------|
| `extension/popup.js` | Add `extractPrice()` function; add `price: extractPrice()` to payload |
| `app.py` | Fix `_parse_price` to strip non-numeric characters via regex |
| `scoring/tests.py` or `test_extractor.py` | Tests for `_parse_price` with CA$, £, €, AU$ inputs |

### Out of Scope

- No changes to `extractor.py` — it already reads `payload["price"]` as an override
- No UI changes — result page already displays cost per wash and price pressure when price is present
