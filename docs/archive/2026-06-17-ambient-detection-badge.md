# Ambient Detection + Badge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the extension ambient — auto-detect product pages, score silently in the background, and show a verdict badge on the extension icon without any user click.

**Architecture:** A content script runs on every https page at `document_idle`, does a lightweight product-page check (2+ of 3 signals), and if it passes, extracts the full DOM payload and messages the background service worker. The background POSTs to the backend in passive mode (no GPT fallback, 30-min TTL), reads `verdict_bucket` from the response, stores `{result_id, verdict}` in `chrome.storage.session[tab_${tabId}]`, and sets a colored badge. The popup reads from session storage and either opens the cached result card or falls back to the existing manual scan.

**Tech Stack:** Chrome MV3, `chrome.storage.session`, `chrome.action` badge API, Flask backend, existing scoring engine

---

**Scope note:** This plan covers spec sections 1–3 (passive detection, badge, result card caching) and section 6 (verdict buckets). Sections 4–5 (Compare feature) are a separate Plan B to be written after this ships.

---

## File Structure

### New files
- `extension/content.js` — Passive detection content script: lightweight product-page check → full extraction → sends payload to background
- `extension/background.js` — MV3 service worker: receives payload, POSTs to backend (passive mode), manages badge + `chrome.storage.session`

### Modified files
- `scoring/engine.py` — Add `get_verdict_bucket()` helper; add `verdict_bucket: str` field to `ScoreResult`; compute in `score_item()`
- `scoring/tests.py` — Add 7 verdict bucket tests + register in runner
- `app.py` — `passive` flag in `/api/score-page`: skip GPT, extend TTL to 1800s, return `verdict_bucket` in response
- `extension/manifest.json` — Register background service worker, content scripts, add `storage` + `tabs` permissions
- `extension/popup.html` — 3-state UI: scanning, done (verdict chip + button), manual fallback
- `extension/popup.js` — Read `chrome.storage.session`; route to correct state; manual scan fallback
- `templates/index.html` — Add construction stat to stats row
- `static/app.js` — Populate construction stat in `renderResult()`

---

## Task 1: Verdict bucket — backend function + tests

**Files:**
- Modify: `scoring/engine.py`
- Modify: `scoring/tests.py`

**Threshold logic:**
- `not_enough_info`: `confidence == "low"` OR `price_pressure_level == "unknown"` (no price = can't evaluate value)
- `overpriced`: `price_pressure_level in ("high", "extreme")` — price is the problem regardless of material score
- `worth_it`: `worth_it_score >= 65` with a real price signal
- `mixed`: everything else

This correctly separates "good material at high price" (→ overpriced) from "bad material at fair price" (→ mixed).

- [ ] **Step 1: Write failing tests in `scoring/tests.py`**

Add these 7 functions immediately before the `run_all()` function:

```python
def test_verdict_bucket_worth_it():
    """Merino sweater at fair price → worth_it."""
    result = score_item(
        composition=[{"fiber": "wool", "pct": 100}],
        price=80.0,
        category="sweater",
    )
    assert result.verdict_bucket == "worth_it", (
        f"Merino at fair price should be worth_it, got {result.verdict_bucket} "
        f"(score={result.worth_it_score}, level={result.price_pressure['level']})"
    )


def test_verdict_bucket_overpriced_extreme():
    """Cotton t-shirt at $300 → overpriced (extreme price pressure)."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=300.0,
        category="t-shirt",
    )
    assert result.verdict_bucket == "overpriced", (
        f"Cotton t-shirt at $300 should be overpriced, got {result.verdict_bucket} "
        f"(score={result.worth_it_score}, level={result.price_pressure['level']})"
    )


def test_verdict_bucket_mixed_low_score_fair_price():
    """Acrylic tee at fair price → mixed (not overpriced — price is fair)."""
    result = score_item(
        composition=[{"fiber": "acrylic", "pct": 100}],
        price=25.0,
        category="t-shirt",
    )
    assert result.verdict_bucket == "mixed", (
        f"Acrylic tee at fair price should be mixed, got {result.verdict_bucket} "
        f"(score={result.worth_it_score}, level={result.price_pressure['level']})"
    )


def test_verdict_bucket_not_enough_info_low_confidence():
    """Unknown fiber → low confidence → not_enough_info."""
    result = score_item(
        composition=[{"fiber": "unknown_fiber_xyz", "pct": 100}],
        price=50.0,
        category="t-shirt",
    )
    assert result.verdict_bucket == "not_enough_info", (
        f"Unknown fiber should give not_enough_info, got {result.verdict_bucket}"
    )


def test_verdict_bucket_not_enough_info_no_price():
    """No price → unknown pressure level → not_enough_info."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=None,
        category="t-shirt",
    )
    assert result.verdict_bucket == "not_enough_info", (
        f"No price should give not_enough_info, got {result.verdict_bucket}"
    )


def test_verdict_bucket_overpriced_high_pressure():
    """Polyester tee at $120 → high pressure → overpriced."""
    result = score_item(
        composition=[{"fiber": "polyester", "pct": 100}],
        price=120.0,
        category="t-shirt",
    )
    assert result.price_pressure["level"] in ("high", "extreme"), (
        f"Poly tee at $120 should have high/extreme pressure, got {result.price_pressure['level']}"
    )
    assert result.verdict_bucket == "overpriced", (
        f"Should be overpriced, got {result.verdict_bucket}"
    )


def test_verdict_bucket_field_always_present():
    """verdict_bucket is always one of the four valid values."""
    result = score_item(
        composition=[{"fiber": "silk", "pct": 100}],
        price=180.0,
        category="dress",
    )
    assert result.verdict_bucket in ("worth_it", "mixed", "overpriced", "not_enough_info"), (
        f"verdict_bucket must be one of four values, got {result.verdict_bucket!r}"
    )
```

Also add these 7 entries to the `tests` list inside `run_all()`:

```python
        ("Verdict bucket: worth_it",                   test_verdict_bucket_worth_it),
        ("Verdict bucket: overpriced extreme",         test_verdict_bucket_overpriced_extreme),
        ("Verdict bucket: mixed low score fair price", test_verdict_bucket_mixed_low_score_fair_price),
        ("Verdict bucket: not_enough_info low conf",  test_verdict_bucket_not_enough_info_low_confidence),
        ("Verdict bucket: not_enough_info no price",  test_verdict_bucket_not_enough_info_no_price),
        ("Verdict bucket: overpriced high pressure",  test_verdict_bucket_overpriced_high_pressure),
        ("Verdict bucket: field always present",       test_verdict_bucket_field_always_present),
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && python -m scoring.tests 2>&1 | grep -E "FAIL|ERROR|verdict_bucket"
```

Expected: `ERROR  Verdict bucket: ...` for each of the 7 new tests (AttributeError on missing field).

- [ ] **Step 3: Add `get_verdict_bucket()` to `scoring/engine.py`**

Add this function immediately before `_no_data_result()` (around line 470):

```python
def get_verdict_bucket(
    worth_it_score: float,
    confidence: str,
    price_pressure_level: str,
) -> str:
    """
    Map score + confidence + price pressure → one of four verdict labels.

    not_enough_info: low confidence or no price data
    overpriced:      price pressure is high or extreme
    worth_it:        worth_it_score >= 65 with adequate price signal
    mixed:           everything else
    """
    if confidence == "low" or price_pressure_level == "unknown":
        return "not_enough_info"
    if price_pressure_level in ("high", "extreme"):
        return "overpriced"
    if worth_it_score >= 65:
        return "worth_it"
    return "mixed"
```

- [ ] **Step 4: Add `verdict_bucket` field to `ScoreResult` dataclass**

In the `ScoreResult` dataclass (after the `unknown_fibers` field, around line 93), add:

```python
    verdict_bucket: str = ""              # "worth_it" | "mixed" | "overpriced" | "not_enough_info"
```

- [ ] **Step 5: Compute and set `verdict_bucket` in `score_item()`**

Immediately before the `return ScoreResult(...)` statement (line ~255), add:

```python
    verdict_bucket = get_verdict_bucket(worth_it_score, confidence, price_pressure["level"])
```

In the `return ScoreResult(...)` block, add:

```python
        verdict_bucket=verdict_bucket,
```

Also update `_no_data_result()` — in its `return ScoreResult(...)` call, add:

```python
        verdict_bucket="not_enough_info",
```

- [ ] **Step 6: Run tests to verify all pass**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && python -m scoring.tests 2>&1 | tail -5
```

Expected: `34/34 tests passed`

- [ ] **Step 7: Commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add scoring/engine.py scoring/tests.py && git commit -m "feat: add verdict_bucket to ScoreResult (worth_it/mixed/overpriced/not_enough_info)"
```

---

## Task 2: Backend passive mode

**Files:**
- Modify: `app.py` — `score_page_endpoint`

`passive: true` in the request body skips the GPT fallback (no API cost for passive scans) and extends the result TTL to 30 minutes (so the badge is still valid when the user opens the popup several minutes after page load). The response now includes `verdict_bucket`.

- [ ] **Step 1: Add passive mode to `score_page_endpoint`**

Find this block in `app.py` (around lines 563–582):

```python
        data = request.get_json(force=True, silent=True) or {}
        price = _parse_price(data.get("price"))
        category = data.get("category") or "other"

        # Run production extraction pipeline
        from scoring.extractor import extract_from_payload, _call_gpt_resolver
        result_extraction = extract_from_payload(data)

        # GPT fallback if still no composition
        if not result_extraction.composition_blocks:
            candidate_text = " ".join(data.get("candidate_blocks") or [])
            if candidate_text:
                result_extraction = _call_gpt_resolver(candidate_text, openai_client)

        if not result_extraction.composition_blocks:
            return jsonify({
                "error": "No fiber composition found on this page.",
                "error_type": "empty"
            }), 422
```

Replace with:

```python
        data = request.get_json(force=True, silent=True) or {}
        passive = bool(data.get("passive", False))
        price = _parse_price(data.get("price"))
        category = data.get("category") or "other"

        # Run production extraction pipeline
        from scoring.extractor import extract_from_payload, _call_gpt_resolver
        result_extraction = extract_from_payload(data)

        # GPT fallback if still no composition — skipped for passive scans (cost control)
        if not result_extraction.composition_blocks and not passive:
            candidate_text = " ".join(data.get("candidate_blocks") or [])
            if candidate_text:
                result_extraction = _call_gpt_resolver(candidate_text, openai_client)

        if not result_extraction.composition_blocks:
            return jsonify({
                "error": "No fiber composition found on this page.",
                "error_type": "empty",
                "passive": passive,
            }), 422
```

- [ ] **Step 2: Extend TTL and include `verdict_bucket` in response**

Find this block (around lines 616–624):

```python
        # Store with TTL
        result_id = str(_uuid_module.uuid4())
        _result_store[result_id] = {
            "result": result_dict,
            "expires_at": time.time() + _RESULT_TTL_SECONDS,
        }
        _cleanup_result_store()

        return jsonify({"result_id": result_id})
```

Replace with:

```python
        # Store with TTL — 30 min for passive scans (badge must survive until popup opens)
        ttl = 1800 if passive else _RESULT_TTL_SECONDS
        result_id = str(_uuid_module.uuid4())
        _result_store[result_id] = {
            "result": result_dict,
            "expires_at": time.time() + ttl,
        }
        _cleanup_result_store()

        return jsonify({
            "result_id": result_id,
            "verdict_bucket": result_dict.get("verdict_bucket", "not_enough_info"),
        })
```

- [ ] **Step 3: Run tests to confirm nothing broke**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && pytest scoring/test_extractor.py scoring/test_verdict.py -q && python -m scoring.tests 2>&1 | tail -5
```

Expected: `54 passed` + `34/34 tests passed`

- [ ] **Step 4: Commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add app.py && git commit -m "feat: passive mode for /api/score-page (skip GPT, 30min TTL, return verdict_bucket)"
```

---

## Task 3: content.js — product page detection + extraction

**Files:**
- Modify/create: `extension/content.js`

Runs at `document_idle` on every https page. Lightweight product-page check first (2+ of 3 signals). If it passes, runs the same full extraction as popup.js, then messages the background with the payload.

Note: extraction logic is intentionally duplicated from popup.js — this is a v1 tradeoff to avoid a build step for shared modules. A comment in both files marks the section to keep in sync.

- [ ] **Step 1: Write `extension/content.js`**

```javascript
/**
 * content.js — Passive product detection + extraction.
 *
 * Runs at document_idle on every https page. Lightweight check first;
 * full extraction only if the page looks like a product page.
 *
 * Extraction logic is kept in sync with the manual-scan injection
 * function in popup.js. If you update one, update the other.
 */

(async () => {
  "use strict";

  // ── 1. Lightweight product-page check ──────────────────────────────────────
  // Requires 2+ of 3 signals to avoid false positives on search/category pages.

  function isProductPage() {
    const hasPriceEl = !!(
      document.querySelector('[itemprop="price"]') ||
      document.querySelector("[data-price]") ||
      document.querySelector("[data-product-price]") ||
      document.querySelector("[class*='price__amount']") ||
      document.querySelector("[class*='product-price']")
    );

    const hasCartBtn = Array.from(
      document.querySelectorAll('button, [role="button"], input[type="submit"]')
    ).some(el =>
      /\b(add to (bag|cart|basket)|buy now)\b/i.test(
        (el.textContent || el.value || "").trim()
      )
    );

    const h1 = document.querySelector("h1");
    const hasTitle = !!(h1 && h1.textContent.trim().length > 3);

    return [hasPriceEl, hasCartBtn, hasTitle].filter(Boolean).length >= 2;
  }

  if (!isProductPage()) return;

  // ── 2. Full extraction (sync with popup.js injection function) ─────────────

  const r = {
    url: window.location.href,
    json_ld: [],
    json_ld_raw: [],
    meta: {},
    candidate_blocks: [],
    price: null,
    category: null,
    passive: true,
  };

  const LABEL_RE =
    /\b(material|fabric|composition|fibre?|shell|lining|body|trim|care|details?|construction|content|description|specifications?|product\s*info)\b/i;

  // Expand collapsed accordions
  document.querySelectorAll("button,summary,[role='button'],[role='tab']").forEach(el => {
    const txt = (el.textContent || "").trim();
    if (txt.length <= 80 && LABEL_RE.test(txt)) { try { el.click(); } catch (_) {} }
  });
  document.querySelectorAll("[aria-expanded='false']").forEach(el => {
    const txt = (el.textContent || "").trim();
    if (txt.length <= 80 && LABEL_RE.test(txt)) { try { el.click(); } catch (_) {} }
  });
  await new Promise(resolve => setTimeout(resolve, 600));

  // JSON-LD
  document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
    const raw = (s.textContent || "").trim();
    if (!raw) return;
    try { r.json_ld.push(JSON.parse(raw)); }
    catch { r.json_ld_raw.push(raw); }
  });

  // Meta tags
  const WANTED = new Set([
    "og:title", "og:description", "og:price:amount",
    "product:price:amount", "og:site_name", "og:brand",
  ]);
  document.querySelectorAll("meta[property],meta[name]").forEach(t => {
    const k = t.getAttribute("property") || t.getAttribute("name") || "";
    const v = t.getAttribute("content") || "";
    if (WANTED.has(k) && v) r.meta[k] = v;
  });

  // Price extraction (6-step cascade, same as popup.js)
  try {
    // Step 0: JSON-LD offers.price
    for (const block of r.json_ld) {
      if (r.price) break;
      const items = Array.isArray(block["@graph"]) ? block["@graph"] : [block];
      for (const item of items) {
        if (r.price) break;
        let offers = item.offers;
        if (!offers) continue;
        if (Array.isArray(offers)) offers = offers[0];
        if (!offers) continue;
        const pRaw = offers.price ?? offers.lowPrice;
        if (pRaw == null) continue;
        const n = parseFloat(String(pRaw).replace(/[^0-9.]/g, ""));
        if (!isNaN(n) && n > 0) r.price = n;
      }
    }
    // Step 0b: OG meta
    if (!r.price) {
      for (const k of ["og:price:amount", "product:price:amount"]) {
        if (r.meta[k]) {
          const n = parseFloat(String(r.meta[k]).replace(/[^0-9.]/g, ""));
          if (!isNaN(n) && n > 0) { r.price = n; break; }
        }
      }
    }
    // Step 1: itemprop
    if (!r.price) {
      const el = document.querySelector("[itemprop='price']");
      if (el) {
        const raw = (el.getAttribute("content") || el.textContent || "").trim();
        const cleaned = raw.replace(/,/g, "").replace(/[^\d.]/g, "");
        const n = parseFloat(cleaned);
        if (!isNaN(n) && n > 0) r.price = n;
      }
    }
    // Step 2: Shopify data attrs
    if (!r.price) {
      const dpEl = document.querySelector(
        "[data-price],[data-product-price],[data-variant-price],[data-sale-price]"
      );
      if (dpEl) {
        for (const a of ["data-price", "data-product-price", "data-variant-price", "data-sale-price"]) {
          const raw = dpEl.getAttribute(a);
          if (!raw) continue;
          let n = parseFloat(raw.replace(/[^0-9.]/g, ""));
          if (!isNaN(n) && n > 0) {
            if (n >= 1000 && !raw.includes(".")) n = n / 100;
            r.price = Math.round(n * 100) / 100;
            break;
          }
        }
      }
    }
    // Step 3: CSS class heuristics
    if (!r.price) {
      const isStrikethrough = el => {
        try {
          const s = window.getComputedStyle(el);
          return s.textDecorationLine.includes("line-through") ||
                 s.textDecoration.includes("line-through");
        } catch { return false; }
      };
      for (const group of [
        "[class*='sale-price'],[class*='price--sale'],[class*='price__sale'],[class*='price__current']",
        "[class*='price-item'],[class*='product-price'],[class*='price__amount']",
        "[class*='price']",
      ]) {
        if (r.price) break;
        for (const el of document.querySelectorAll(group)) {
          if (isStrikethrough(el)) continue;
          const m = (el.textContent || "").match(/[\$£€¥]\s*(\d[\d,]*(?:\.\d{1,2})?)/);
          if (m) { r.price = parseFloat(m[1].replace(/,/g, "")); break; }
        }
      }
    }
    // Step 4: Broad DOM scan
    if (!r.price) {
      const PRICE_RE = /(?:[A-Z]{0,3}\$|[£€¥])\s*([\d,]+(?:\.\d{1,2})?)/;
      const els = Array.from(document.querySelectorAll("span,strong,b,ins"));
      for (let i = 0; i < Math.min(els.length, 500); i++) {
        const el = els[i];
        if (el.children.length > 1) continue;
        const txt = (el.textContent || "").trim();
        if (txt.length < 2 || txt.length > 20) continue;
        const m = txt.match(PRICE_RE);
        if (m) {
          const n = parseFloat(m[1].replace(/,/g, ""));
          if (!isNaN(n) && n > 0 && n < 100000) { r.price = n; break; }
        }
      }
    }
  } catch (_) {}

  // Candidate blocks
  const seen = new Set();
  document.querySelectorAll(
    "h1,h2,h3,h4,h5,h6,button,label,summary,dt,th,span,div,p,li"
  ).forEach(node => {
    const lbl = (node.textContent || "").trim();
    if (lbl.length > 80 || !LABEL_RE.test(lbl)) return;
    const parts = [];
    let sib = node.nextElementSibling, cc = 0;
    while (sib && cc < 500) {
      const t = sib.textContent.trim();
      if (t) { parts.push(t); cc += t.length; }
      sib = sib.nextElementSibling;
    }
    if (node.parentElement) {
      const pt = node.parentElement.textContent.trim();
      if (pt.length < 700) parts.push(pt);
    }
    if (parts.length) {
      const block = parts.join(" ").trim().slice(0, 600);
      const h = block.slice(0, 100);
      if (!seen.has(h) && block.length > 10) { seen.add(h); r.candidate_blocks.push(block); }
    }
  });

  const PCT_SCAN_RE = /\d+\s*%\s*[a-zA-Z]/;
  document.querySelectorAll("li,p,td,span").forEach(el => {
    const txt = (el.textContent || "").trim();
    if (txt.length < 5 || txt.length > 300 || !PCT_SCAN_RE.test(txt)) return;
    const h = txt.slice(0, 100);
    if (!seen.has(h)) { seen.add(h); r.candidate_blocks.push(txt); }
  });

  document.querySelectorAll("details").forEach(details => {
    const summary = details.querySelector("summary");
    if (!summary) return;
    if (LABEL_RE.test(summary.textContent.trim())) {
      const text = details.textContent.trim().slice(0, 600);
      const h = text.slice(0, 100);
      if (!seen.has(h) && text.length > 10) { seen.add(h); r.candidate_blocks.push(text); }
    }
  });

  if (!r.candidate_blocks.length) {
    const bodyText = (document.body.innerText || "").trim().slice(0, 3000);
    if (bodyText.length > 100) r.candidate_blocks.push(bodyText);
  }

  // Category detection
  const CATEGORY_SIGNALS = [
    ["dress",      /\b(dress(?:es)?|skirt)\b/i],
    ["sweater",    /\b(sweater|knitwear|cardigan|pullover|crewneck|turtleneck)\b/i],
    ["t-shirt",    /\b(t-shirt|tee|tank[-\s]?top|crop[-\s]?top)\b/i],
    ["jeans",      /\b(jeans?|denim|trousers?|pants?|chinos?)\b/i],
    ["outerwear",  /\b(jacket|coat|parka|puffer|anorak|windbreaker|blazer)\b/i],
    ["activewear", /\b(leggings?|activewear|sports?[-\s]?bra|yoga|athletic)\b/i],
  ];
  const detectCategory = text => {
    for (const [cat, re] of CATEGORY_SIGNALS) {
      if (re.test(text)) return cat;
    }
    return null;
  };

  r.category = detectCategory(window.location.pathname);
  if (!r.category) {
    for (const sel of ["[aria-label='breadcrumb']", "[class*='breadcrumb']", "nav ol", "nav ul"]) {
      const el = document.querySelector(sel);
      if (el) { r.category = detectCategory(el.textContent || ""); if (r.category) break; }
    }
  }
  if (!r.category) {
    const h1 = document.querySelector("h1");
    if (h1) r.category = detectCategory(h1.textContent || "");
  }

  // ── 3. Send to background ──────────────────────────────────────────────────
  if (r.candidate_blocks.length || r.json_ld.length) {
    chrome.runtime.sendMessage({ type: "PASSIVE_PAYLOAD", payload: r });
  }
})();
```

- [ ] **Step 2: Commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add extension/content.js && git commit -m "feat: content.js — passive product detection and extraction"
```

---

## Task 4: background.js — passive scan orchestration + badge

**Files:**
- Create: `extension/background.js`

Receives extraction payloads, POSTs to backend in passive mode, sets per-tab badge, stores result in `chrome.storage.session`. Also clears stale badge state when tabs navigate or close.

- [ ] **Step 1: Create `extension/background.js`**

```javascript
/**
 * background.js — MV3 service worker.
 *
 * Listens for PASSIVE_PAYLOAD from content.js.
 * Posts payload to /api/score-page with passive:true (no GPT fallback).
 * Reads verdict_bucket from response → sets per-tab badge.
 * Stores {status, result_id, verdict} in chrome.storage.session[tab_${tabId}].
 *
 * Badge and session are cleared whenever a tab navigates or closes.
 */

"use strict";

const API_BASE = "https://web-production-adff3.up.railway.app";

const BADGE = {
  worth_it:        { text: "WI", color: "#4caf50" },
  mixed:           { text: "MX", color: "#f5820a" },
  overpriced:      { text: "OP", color: "#e53935" },
  not_enough_info: { text: "?",  color: "#9e9e9e" },
};

// ── Message listener ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type !== "PASSIVE_PAYLOAD") return;
  const tabId = sender.tab?.id;
  if (!tabId) return;
  handlePassiveScan(tabId, msg.payload);
});

// ── Tab lifecycle ─────────────────────────────────────────────────────────────

// Clear badge and session data when tab navigates to a new page
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "loading") {
    chrome.action.setBadgeText({ text: "", tabId });
    chrome.storage.session.remove(`tab_${tabId}`);
  }
});

// Clean up when tab closes
chrome.tabs.onRemoved.addListener(tabId => {
  chrome.storage.session.remove(`tab_${tabId}`);
});

// ── Passive scan ──────────────────────────────────────────────────────────────

async function handlePassiveScan(tabId, payload) {
  const sessionKey = `tab_${tabId}`;

  // Idempotent: skip if already scanning or complete for this tab
  const existing = await chrome.storage.session.get(sessionKey);
  const current = existing[sessionKey];
  if (current?.status === "scoring" || current?.status === "done") return;

  await chrome.storage.session.set({ [sessionKey]: { status: "scoring" } });

  try {
    const resp = await fetch(`${API_BASE}/api/score-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      await chrome.storage.session.set({ [sessionKey]: { status: "error" } });
      setBadge(tabId, "not_enough_info");
      return;
    }

    const data = await resp.json();
    const verdict = data.verdict_bucket || "not_enough_info";

    await chrome.storage.session.set({
      [sessionKey]: {
        status: "done",
        result_id: data.result_id,
        verdict,
      },
    });

    setBadge(tabId, verdict);
  } catch (_) {
    await chrome.storage.session.set({ [sessionKey]: { status: "error" } });
    setBadge(tabId, "not_enough_info");
  }
}

function setBadge(tabId, verdict) {
  const cfg = BADGE[verdict] || BADGE.not_enough_info;
  chrome.action.setBadgeText({ text: cfg.text, tabId });
  chrome.action.setBadgeBackgroundColor({ color: cfg.color, tabId });
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add extension/background.js && git commit -m "feat: background.js — passive scan, badge colors, session storage"
```

---

## Task 5: manifest.json — register everything

**Files:**
- Modify: `extension/manifest.json`

- [ ] **Step 1: Rewrite `extension/manifest.json`**

Replace the entire file with:

```json
{
  "manifest_version": 3,
  "name": "worth it? — fiber science scorer",
  "version": "0.2.0",
  "description": "Score any clothing item's quality using fiber science. Works on Zara, ASOS, and all major retailers.",
  "permissions": ["activeTab", "scripting", "storage", "tabs"],
  "host_permissions": [
    "https://web-production-adff3.up.railway.app/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://*/*"],
      "js": ["content.js"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

Changes from current: version → 0.2.0, added `"storage"` + `"tabs"` to permissions, added `"background"` block, added `"content_scripts"` block.

- [ ] **Step 2: Commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add extension/manifest.json && git commit -m "feat: manifest v0.2.0 — background worker, content scripts, storage+tabs perms"
```

---

## Task 6: popup.html — 3-state UI

**Files:**
- Modify: `extension/popup.html`

Three states, shown/hidden by popup.js:
- **scanning** — passive scan in progress
- **done** — colored verdict chip + "OPEN FULL CARD" + "RE-SCAN" buttons
- **manual** — original "SCAN PRODUCT" button (fallback when no passive result)

- [ ] **Step 1: Rewrite `extension/popup.html`**

Replace the entire file with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>worth it?</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      width: 280px;
      font-family: 'Space Mono', 'Courier New', monospace;
      background: #111;
      color: #eee;
      padding: 20px;
    }
    .logo { font-size: 18px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; }
    .tagline {
      font-size: 10px; color: #888; text-transform: uppercase;
      letter-spacing: 1px; margin-bottom: 20px;
    }

    /* ── Verdict chip ── */
    .verdict-chip {
      display: inline-block;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }
    .verdict-chip.worth_it        { background: #4caf50; color: #111; }
    .verdict-chip.mixed           { background: #f5820a; color: #111; }
    .verdict-chip.overpriced      { background: #e53935; color: #eee; }
    .verdict-chip.not_enough_info { background: #555;    color: #eee; }

    .verdict-label { font-size: 11px; color: #888; margin-bottom: 16px; line-height: 1.5; }

    /* ── Buttons ── */
    .btn {
      display: block; width: 100%;
      padding: 10px;
      background: transparent;
      color: #eee;
      border: 1px solid #555;
      font-family: inherit;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.05em;
      cursor: pointer;
      transition: background 0.15s, color 0.15s;
      margin-bottom: 8px;
    }
    .btn:hover:not(:disabled) { background: #eee; color: #111; }
    .btn:disabled { opacity: 0.4; cursor: default; }
    .btn.primary { background: #f5820a; color: #111; border-color: #f5820a; }
    .btn.primary:hover:not(:disabled) { background: #d46a00; border-color: #d46a00; }

    #status { margin-top: 8px; font-size: 11px; color: #888; min-height: 16px; }
    #status.error { color: #e07070; }

    /* States hidden by default; popup.js shows the right one */
    #state-scanning, #state-done, #state-manual { display: none; }
  </style>
</head>
<body>
  <div class="logo">worth it?</div>
  <div class="tagline">Fiber science, not opinion</div>

  <!-- State: passive scan in progress -->
  <div id="state-scanning">
    <p style="color:#888;font-size:12px;line-height:1.6;">Scanning product…</p>
  </div>

  <!-- State: passive scan complete — show verdict + open card -->
  <div id="state-done">
    <div id="verdict-chip" class="verdict-chip"></div>
    <p id="verdict-label" class="verdict-label"></p>
    <button id="btn-open-card" class="btn primary">[ OPEN FULL CARD ]</button>
    <button id="btn-rescan" class="btn">[ RE-SCAN ]</button>
  </div>

  <!-- State: no passive result — manual scan fallback -->
  <div id="state-manual">
    <button id="btn-scan" class="btn primary">[ SCAN PRODUCT ]</button>
  </div>

  <div id="status"></div>

  <script src="popup.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add extension/popup.html && git commit -m "feat: popup.html — 3-state UI (scanning, done with verdict, manual fallback)"
```

---

## Task 7: popup.js — session-aware routing

**Files:**
- Modify: `extension/popup.js`

On `DOMContentLoaded`, reads `chrome.storage.session` for the current tab and routes to the correct state. Manual scan fallback (btn-scan and btn-rescan) preserves the same extraction + POST + open-tab flow as before, just triggered differently.

- [ ] **Step 1: Rewrite `extension/popup.js`**

Replace the entire file with:

```javascript
/**
 * popup.js — session-aware routing.
 *
 * On open, reads chrome.storage.session for the current tab:
 *   status "done"    → show verdict chip + Open Full Card button
 *   status "scoring" → show scanning state
 *   else             → show manual scan button (original flow)
 *
 * Manual scan (btn-scan / btn-rescan) is the same flow as before:
 * inject extraction into page → POST to backend → open result tab.
 */

"use strict";

const API_BASE = "https://web-production-adff3.up.railway.app";

const VERDICT_LABELS = {
  worth_it:        "Good material, fair price.",
  mixed:           "Some tradeoffs — check the full card.",
  overpriced:      "Not worth what they're charging.",
  not_enough_info: "Couldn't read the material composition.",
};

// ── State routing ──────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) { showManual(); return; }

  const sessionKey = `tab_${tab.id}`;
  const session = await chrome.storage.session.get(sessionKey);
  const tabData = session[sessionKey];

  if (tabData?.status === "done" && tabData.result_id) {
    showDone(tabData.verdict, tabData.result_id);
  } else if (tabData?.status === "scoring") {
    showScanning();
  } else {
    showManual();
  }
});

// ── State renderers ────────────────────────────────────────────────────────────

function showScanning() {
  document.getElementById("state-scanning").style.display = "block";
}

function showDone(verdict, resultId) {
  const el = document.getElementById("state-done");
  el.style.display = "block";

  const v = verdict || "not_enough_info";
  const chip = document.getElementById("verdict-chip");
  chip.textContent = v.replace(/_/g, " ").toUpperCase();
  chip.className = `verdict-chip ${v}`;
  document.getElementById("verdict-label").textContent = VERDICT_LABELS[v] || "";

  document.getElementById("btn-open-card").addEventListener("click", () => {
    chrome.tabs.create({ url: `${API_BASE}?result=${resultId}` });
    window.close();
  });

  document.getElementById("btn-rescan").addEventListener("click", runManualScan);
}

function showManual() {
  document.getElementById("state-manual").style.display = "block";
  document.getElementById("btn-scan").addEventListener("click", runManualScan);
}

// ── Manual scan (preserved from previous popup.js) ────────────────────────────

async function runManualScan() {
  const statusEl = document.getElementById("status");
  document.querySelectorAll(".btn").forEach(b => (b.disabled = true));
  statusEl.textContent = "Scanning page\u2026";
  statusEl.className = "";

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("no_tab");

    // Inject extraction function — same logic as content.js passive extraction
    // (see content.js sync comment)
    const [{ result: payload }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: async () => {
        const r = {
          url: window.location.href,
          json_ld: [], json_ld_raw: [], meta: {},
          candidate_blocks: [], price: null, category: null,
        };
        const LABEL_RE = /\b(material|fabric|composition|fibre?|shell|lining|body|trim|care|details?|construction|content|description|specifications?|product\s*info)\b/i;
        document.querySelectorAll("button,summary,[role='button'],[role='tab']").forEach(el => {
          const t = (el.textContent||"").trim();
          if (t.length<=80&&LABEL_RE.test(t)){try{el.click();}catch(_){}}
        });
        document.querySelectorAll("[aria-expanded='false']").forEach(el => {
          const t=(el.textContent||"").trim();
          if(t.length<=80&&LABEL_RE.test(t)){try{el.click();}catch(_){}}
        });
        await new Promise(res=>setTimeout(res,600));
        document.querySelectorAll('script[type="application/ld+json"]').forEach(s=>{
          const raw=(s.textContent||"").trim();if(!raw)return;
          try{r.json_ld.push(JSON.parse(raw));}catch{r.json_ld_raw.push(raw);}
        });
        const WANTED=new Set(["og:title","og:description","og:price:amount","product:price:amount","og:site_name","og:brand"]);
        document.querySelectorAll("meta[property],meta[name]").forEach(t=>{
          const k=t.getAttribute("property")||t.getAttribute("name")||"";
          const v=t.getAttribute("content")||"";
          if(WANTED.has(k)&&v)r.meta[k]=v;
        });
        try {
          for(const block of r.json_ld){
            if(r.price)break;
            const items=Array.isArray(block["@graph"])?block["@graph"]:[block];
            for(const item of items){
              if(r.price)break;let offers=item.offers;if(!offers)continue;
              if(Array.isArray(offers))offers=offers[0];if(!offers)continue;
              const pRaw=offers.price??offers.lowPrice;if(pRaw==null)continue;
              const n=parseFloat(String(pRaw).replace(/[^0-9.]/g,""));
              if(!isNaN(n)&&n>0)r.price=n;
            }
          }
          if(!r.price){for(const k of["og:price:amount","product:price:amount"]){if(r.meta[k]){const n=parseFloat(String(r.meta[k]).replace(/[^0-9.]/g,""));if(!isNaN(n)&&n>0){r.price=n;break;}}}}
          if(!r.price){const el=document.querySelector("[itemprop='price']");if(el){const n=parseFloat((el.getAttribute("content")||el.textContent||"").replace(/,/g,"").replace(/[^\d.]/g,""));if(!isNaN(n)&&n>0)r.price=n;}}
          if(!r.price){const dpEl=document.querySelector("[data-price],[data-product-price],[data-variant-price],[data-sale-price]");if(dpEl){for(const a of["data-price","data-product-price","data-variant-price","data-sale-price"]){const raw=dpEl.getAttribute(a);if(!raw)continue;let n=parseFloat(raw.replace(/[^0-9.]/g,""));if(!isNaN(n)&&n>0){if(n>=1000&&!raw.includes("."))n=n/100;r.price=Math.round(n*100)/100;break;}}}}
          if(!r.price){const isSt=el=>{try{const s=window.getComputedStyle(el);return s.textDecorationLine.includes("line-through")||s.textDecoration.includes("line-through");}catch{return false;}};for(const g of["[class*='sale-price'],[class*='price--sale'],[class*='price__sale'],[class*='price__current']","[class*='price-item'],[class*='product-price'],[class*='price__amount']","[class*='price']"]){if(r.price)break;for(const el of document.querySelectorAll(g)){if(isSt(el))continue;const m=(el.textContent||"").match(/[\$£€¥]\s*(\d[\d,]*(?:\.\d{1,2})?)/);if(m){r.price=parseFloat(m[1].replace(/,/g,""));break;}}}}
          if(!r.price){const PR=/(?:[A-Z]{0,3}\$|[£€¥])\s*([\d,]+(?:\.\d{1,2})?)/;const els=Array.from(document.querySelectorAll("span,strong,b,ins"));for(let i=0;i<Math.min(els.length,500);i++){const el=els[i];if(el.children.length>1)continue;const txt=(el.textContent||"").trim();if(txt.length<2||txt.length>20)continue;const m=txt.match(PR);if(m){const n=parseFloat(m[1].replace(/,/g,""));if(!isNaN(n)&&n>0&&n<100000){r.price=n;break;}}}}
        } catch(_){}
        const seen=new Set();
        document.querySelectorAll("h1,h2,h3,h4,h5,h6,button,label,summary,dt,th,span,div,p,li").forEach(node=>{
          const lbl=(node.textContent||"").trim();if(lbl.length>80||!LABEL_RE.test(lbl))return;
          const parts=[];let sib=node.nextElementSibling,cc=0;
          while(sib&&cc<500){const t=sib.textContent.trim();if(t){parts.push(t);cc+=t.length;}sib=sib.nextElementSibling;}
          if(node.parentElement){const pt=node.parentElement.textContent.trim();if(pt.length<700)parts.push(pt);}
          if(parts.length){const block=parts.join(" ").trim().slice(0,600);const h=block.slice(0,100);if(!seen.has(h)&&block.length>10){seen.add(h);r.candidate_blocks.push(block);}}
        });
        const PCT=/\d+\s*%\s*[a-zA-Z]/;
        document.querySelectorAll("li,p,td,span").forEach(el=>{const txt=(el.textContent||"").trim();if(txt.length<5||txt.length>300||!PCT.test(txt))return;const h=txt.slice(0,100);if(!seen.has(h)){seen.add(h);r.candidate_blocks.push(txt);}});
        document.querySelectorAll("details").forEach(details=>{const summary=details.querySelector("summary");if(!summary)return;if(LABEL_RE.test(summary.textContent.trim())){const text=details.textContent.trim().slice(0,600);const h=text.slice(0,100);if(!seen.has(h)&&text.length>10){seen.add(h);r.candidate_blocks.push(text);}}});
        if(!r.candidate_blocks.length){const bt=(document.body.innerText||"").trim().slice(0,3000);if(bt.length>100)r.candidate_blocks.push(bt);}
        const CS=[["dress",/\b(dress(?:es)?|skirt)\b/i],["sweater",/\b(sweater|knitwear|cardigan|pullover|crewneck|turtleneck)\b/i],["t-shirt",/\b(t-shirt|tee|tank[-\s]?top|crop[-\s]?top)\b/i],["jeans",/\b(jeans?|denim|trousers?|pants?|chinos?)\b/i],["outerwear",/\b(jacket|coat|parka|puffer|anorak|windbreaker|blazer)\b/i],["activewear",/\b(leggings?|activewear|sports?[-\s]?bra|yoga|athletic)\b/i]];
        const dc=t=>{for(const[c,re]of CS){if(re.test(t))return c;}return null;};
        r.category=dc(window.location.pathname);
        if(!r.category){for(const sel of["[aria-label='breadcrumb']","[class*='breadcrumb']","[itemtype*='BreadcrumbList']","nav ol","nav ul"]){const el=document.querySelector(sel);if(el){r.category=dc(el.textContent||"");if(r.category)break;}}}
        if(!r.category){const h1=document.querySelector("h1");if(h1)r.category=dc(h1.textContent||"");}
        return r;
      },
    });

    if (!payload) throw new Error("no_data");
    if (!payload.candidate_blocks.length && !payload.json_ld.length) throw new Error("no_product");

    statusEl.textContent = "Scoring\u2026";

    const response = await fetch(`${API_BASE}/api/score-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      if (err.error_type === "empty") throw new Error("no_composition");
      throw new Error("api_error");
    }

    const { result_id } = await response.json();
    if (!result_id) throw new Error("api_error");

    await chrome.tabs.create({ url: `${API_BASE}?result=${result_id}` });
    window.close();

  } catch (err) {
    const messages = {
      no_tab:         "Could not access the current tab.",
      no_data:        "Could not read this page.",
      no_product:     "No product info found \u2014 try the paste text tab on the web app.",
      no_composition: "No material composition found on this page.",
      api_error:      "Scoring failed \u2014 try again.",
    };
    statusEl.textContent = messages[err.message] || "Something went wrong. Try again.";
    statusEl.className = "error";
    document.querySelectorAll(".btn").forEach(b => (b.disabled = false));
  }
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add extension/popup.js && git commit -m "feat: popup.js — session-aware routing, open cached result, manual fallback"
```

---

## Task 8: Construction score visual prominence

**Files:**
- Modify: `templates/index.html` — add construction stat to stats row
- Modify: `static/app.js` — populate it in `renderConstruction()`

Surfaces construction score alongside material durability in the top stats row rather than buried in the `/CONSTRUCTION` section. Hidden when no real signals were found (price_floor source with no signals).

- [ ] **Step 1: Add construction stat to stats row in `templates/index.html`**

Find the stats-row div (search for `id="price-fit-stat"`). Replace the entire `<div class="stats-row">` block with:

```html
      <div class="stats-row">
        <div class="stat">
          <span class="stat-label">Material durability</span>
          <span id="stat-material">—</span>
        </div>
        <div id="construction-stat-row" class="stat" hidden>
          <span class="stat-label">Construction</span>
          <span id="stat-construction">—</span>
        </div>
        <div id="price-fit-stat" class="stat">
          <span class="stat-label">Price fit</span>
          <span id="stat-pressure">—</span>
        </div>
        <div id="cpw-stat-row" class="stat">
          <span class="stat-label">Est. cost per wear</span>
          <span id="stat-cpw">—</span>
        </div>
      </div>
```

- [ ] **Step 2: Populate construction stat in `static/app.js`**

Find `function renderConstruction(c)` in `static/app.js`. Add these lines at the very top of the function body, before any existing if/else:

```javascript
  // Stat row entry — visible when construction has real signals
  const constructionStatRow = document.getElementById("construction-stat-row");
  const statConstruction = document.getElementById("stat-construction");
  if (c && c.score != null && c.source !== "price_floor") {
    statConstruction.textContent = `${c.score}/10`;
    constructionStatRow.removeAttribute("hidden");
  } else {
    constructionStatRow.setAttribute("hidden", "");
  }
```

Also find the reset function in `app.js` (search for `btn-reset` click handler or a `resetCard` function). In the reset block, add:

```javascript
    document.getElementById("construction-stat-row").setAttribute("hidden", "");
    document.getElementById("stat-construction").textContent = "—";
```

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && pytest scoring/test_extractor.py scoring/test_verdict.py -q && python -m scoring.tests 2>&1 | tail -5
```

Expected: `54 passed` + `34/34 tests passed`

- [ ] **Step 4: Commit and push to Railway**

```bash
cd /Users/desiraesidhu/clothing_quality_backend && git add templates/index.html static/app.js && git commit -m "feat: construction score surfaced in stats row alongside material durability"
git push origin main
```

---

## Self-Review

### Spec coverage

| Spec section | Task |
|---|---|
| §1 Content script trigger, not service worker | Task 3 ✓ |
| §1 Lightweight check before full extraction | Task 3 ✓ |
| §1 Local regex only for passive, no GPT fallback | Task 2 ✓ |
| §1 `chrome.storage.session` for per-tab results | Task 4 ✓ |
| §1 Runs after load, doesn't block page | Task 3 (async IIFE, `document_idle`) ✓ |
| §2 Badge per tab, not global | Task 4 (`setBadge(tabId, ...)`) ✓ |
| §2 Color + word abbreviation | Task 4 (WI/MX/OP/?) + Task 6 (chip) ✓ |
| §2 Clear badge on non-product page navigation | Task 4 (`tabs.onUpdated` on `loading`) ✓ |
| §3 Open cached result, not re-scan on click | Task 7 ✓ |
| §3 Clear state for "still analyzing" | Task 6 + 7 (scanning state) ✓ |
| §3 Construction score visual weight | Task 8 ✓ |
| §6 Four verdict labels | Task 1 ✓ |
| §6 Not Enough Info when confidence=low | Task 1 (`get_verdict_bucket`) ✓ |

**Not in this plan (Plan B):** "Add to Compare" button on result card (§3 last bullet, §4–5).

### Type consistency
- `verdict_bucket` Python field is `str`; JSON key is `"verdict_bucket"`; stored in session as `verdict`; accessed in popup.js as `tabData.verdict`. Consistent.
- `BADGE` keys in background.js exactly match `get_verdict_bucket()` return values.
- CSS class names in popup.html (`.worth_it`, `.mixed`, `.overpriced`, `.not_enough_info`) match the verdict bucket strings exactly (underscores, not hyphens).

### No placeholder check
All steps contain complete, runnable code. No "TBD", "implement later", or "similar to Task N" patterns.
