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
