# Price Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract price from any product page DOM in the extension and send it to the backend so cost-per-wash and price-pressure scores are always populated.

**Architecture:** `popup.js` runs a `extractPrice()` helper after accordion expansion, tries four DOM sources in priority order, and sends the raw price string as a top-level `price` field. The backend's `_parse_price` is fixed to strip any currency symbol/code via regex so it handles CA$, £, €, AU$, etc.

**Tech Stack:** JavaScript (MV3 extension), Python/Flask backend, pytest

---

### Task 1: Fix `_parse_price` in `app.py`

**Files:**
- Modify: `app.py:532-539`
- Test: `scoring/test_extractor.py` (append at bottom)

**Step 1: Write the failing tests**

Append to `scoring/test_extractor.py`:

```python
# ── Task 1: _parse_price currency handling ────────────────────────────────────

def test_parse_price_usd():
    from app import _parse_price
    assert _parse_price("$217.00") == 217.0

def test_parse_price_cad():
    from app import _parse_price
    assert _parse_price("CA$217.00") == 217.0

def test_parse_price_gbp():
    from app import _parse_price
    assert _parse_price("£89.99") == 89.99

def test_parse_price_eur():
    from app import _parse_price
    assert _parse_price("€120") == 120.0

def test_parse_price_aud():
    from app import _parse_price
    assert _parse_price("AU$145.00") == 145.0

def test_parse_price_thousands():
    from app import _parse_price
    assert _parse_price("$1,234.00") == 1234.0

def test_parse_price_none():
    from app import _parse_price
    assert _parse_price(None) is None

def test_parse_price_numeric():
    from app import _parse_price
    assert _parse_price(217) == 217.0
```

**Step 2: Run tests to confirm they fail**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
python -m pytest scoring/test_extractor.py::test_parse_price_cad scoring/test_extractor.py::test_parse_price_gbp -v
```

Expected: FAIL — `_parse_price("CA$217.00")` returns `None`, not `217.0`

**Step 3: Fix `_parse_price` in `app.py`**

Replace lines 532–539 with:

```python
def _parse_price(value) -> float | None:
    if value is None:
        return None
    try:
        # Strip all non-numeric characters except decimal point.
        # Handles: $217, CA$217, £89.99, €120, AU$145, 1,234.56
        import re
        cleaned = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None
```

**Step 4: Run all new tests**

```bash
python -m pytest scoring/test_extractor.py::test_parse_price_usd \
  scoring/test_extractor.py::test_parse_price_cad \
  scoring/test_extractor.py::test_parse_price_gbp \
  scoring/test_extractor.py::test_parse_price_eur \
  scoring/test_extractor.py::test_parse_price_aud \
  scoring/test_extractor.py::test_parse_price_thousands \
  scoring/test_extractor.py::test_parse_price_none \
  scoring/test_extractor.py::test_parse_price_numeric -v
```

Expected: all 8 PASS

**Step 5: Run full test suite to check no regressions**

```bash
python -m pytest scoring/test_extractor.py -v
```

Expected: all tests PASS

**Step 6: Commit**

```bash
git add app.py scoring/test_extractor.py
git commit -m "fix: handle non-USD currency symbols in _parse_price"
```

---

### Task 2: Add `extractPrice()` to `popup.js`

**Files:**
- Modify: `extension/popup.js`

The extraction logic lives inside the `func: async () => { ... }` block injected via `chrome.scripting.executeScript`. All changes go inside that block.

**Step 1: Add `price: null` to the payload object**

In `popup.js`, find the `r` object declaration (around line 33):

```javascript
const r = {
  url: window.location.href,
  json_ld: [],
  json_ld_raw: [],
  meta: {},
  candidate_blocks: [],
};
```

Change to:

```javascript
const r = {
  url: window.location.href,
  json_ld: [],
  json_ld_raw: [],
  meta: {},
  candidate_blocks: [],
  price: null,
};
```

**Step 2: Add `extractPrice()` helper and call it**

Add this function definition and call immediately after the `await new Promise(resolve => setTimeout(resolve, 600));` line (after accordion expansion, so sale prices have rendered):

```javascript
// Price extraction — tries structured attributes first, falls back to
// CSS class heuristic. Sends raw string; backend strips currency symbols.
function extractPrice() {
  // 1. Schema.org microdata
  const byItemprop = document.querySelector('[itemprop="price"]');
  if (byItemprop) {
    const v = (byItemprop.getAttribute("content") || byItemprop.textContent || "").trim();
    if (v) return v;
  }
  // 2. data-price attribute
  const byDataAttr = document.querySelector("[data-price]");
  if (byDataAttr) {
    const v = (byDataAttr.getAttribute("data-price") || "").trim();
    if (v) return v;
  }
  // 3. og/product meta tags (already in r.meta, but also check directly)
  for (const name of ["og:price:amount", "product:price:amount"]) {
    const meta = document.querySelector(
      `meta[property="${name}"],meta[name="${name}"]`
    );
    if (meta) {
      const v = (meta.getAttribute("content") || "").trim();
      if (v) return v;
    }
  }
  // 4. First element with "price" in its class whose text looks like a price
  const PRICE_TEXT_RE = /[\d,]+\.?\d{0,2}/;
  const byClass = document.querySelector('[class*="price" i]:not(script):not(style)');
  if (byClass) {
    const txt = byClass.textContent.trim();
    if (PRICE_TEXT_RE.test(txt)) return txt;
  }
  return null;
}

r.price = extractPrice();
```

**Step 3: Manual smoke test**

1. Reload the extension at `chrome://extensions`
2. Open a Madewell product page (e.g. the Dean Jean used earlier)
3. Open DevTools → Console, paste and run this to simulate what the extension does:
   ```javascript
   const byItemprop = document.querySelector('[itemprop="price"]');
   console.log('itemprop:', byItemprop?.getAttribute('content') || byItemprop?.textContent);
   console.log('data-price:', document.querySelector('[data-price]')?.getAttribute('data-price'));
   ```
4. Confirm a price value is returned
5. Click the extension button — result page should now show populated cost-per-wash and price-pressure

**Step 4: Commit**

```bash
git add extension/popup.js
git commit -m "feat: extract price from product page DOM in extension"
```

---

### Task 3: Verify end-to-end on multiple retailers

**Step 1: Test on Madewell**
- Open any Madewell product page
- Click extension → result should show price-pressure and cost-per-wash populated

**Step 2: Test on one more retailer**
- Try Aritzia or any other working retailer
- Confirm price appears in result

**Step 3: If price still missing on a specific site**
- Open DevTools console on that page
- Run the manual probe from Task 2 Step 3 to identify which DOM source is missing
- Note the site's actual price element structure for a follow-up fix

**Step 4: Commit any follow-up fixes found**

```bash
git add extension/popup.js
git commit -m "fix: improve price extraction for [retailer]"
```
