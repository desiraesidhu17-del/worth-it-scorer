/**
 * content.js — reference file for the DOM extraction logic.
 * The actual extraction is inlined in popup.js as a func: injection
 * for MV3 compatibility (executeScript with files[] doesn't return values).
 *
 * This file is kept for reference and maintenance — changes here should
 * be mirrored in the func: injection inside popup.js.
 */

(function extractProductData() {
  const result = {
    url: window.location.href,
    json_ld: [],
    json_ld_raw: [],
    meta: {},
    candidate_blocks: [],
  };

  // ── JSON-LD blocks ─────────────────────────────────────────────────────────
  document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
    const raw = (script.textContent || '').trim();
    if (!raw) return;
    try {
      result.json_ld.push(JSON.parse(raw));
    } catch {
      result.json_ld_raw.push(raw);  // malformed — preserve for backend fallback
    }
  });

  // ── Meta tags ──────────────────────────────────────────────────────────────
  const WANTED_META = new Set([
    'og:title', 'og:description', 'og:price:amount',
    'product:price:amount', 'og:site_name', 'og:brand',
  ]);
  document.querySelectorAll('meta[property], meta[name]').forEach(tag => {
    const key = tag.getAttribute('property') || tag.getAttribute('name') || '';
    const val = tag.getAttribute('content') || '';
    if (WANTED_META.has(key) && val) result.meta[key] = val;
  });

  // ── Candidate block isolation (Step 0, runs in live DOM) ──────────────────
  const DETAIL_LABELS = new Set([
    'materials', 'material', 'fabric', 'composition', 'care', 'details',
    'shell', 'lining', 'body', 'trim', 'content', 'construction',
    'product details', 'fabric & care', 'material & care', 'materials & care',
    'fiber content', 'fibre content', 'fabric content',
  ]);

  const seenHashes = new Set();

  function textHash(s) {
    let h = 0;
    for (let i = 0; i < Math.min(s.length, 200); i++) {
      h = (h * 31 + s.charCodeAt(i)) >>> 0;
    }
    return h;
  }

  function addCandidate(text) {
    if (!text || text.length < 10 || text.length > 800) return;
    const h = textHash(text.trim());
    if (seenHashes.has(h)) return;
    seenHashes.add(h);
    result.candidate_blocks.push(text.trim());
  }

  // Walk all nodes looking for label matches
  const allNodes = document.querySelectorAll(
    'h1,h2,h3,h4,h5,h6,button,label,summary,dt,th,span,div,p,li'
  );

  allNodes.forEach(node => {
    const labelText = (node.textContent || '').trim().toLowerCase();
    if (labelText.length > 60) return;  // too long to be a label
    if (!DETAIL_LABELS.has(labelText)) return;

    // Collect this node + nearby siblings + parent container
    const parts = [];

    // Next siblings (bounded)
    let sibling = node.nextElementSibling;
    let charCount = 0;
    while (sibling && charCount < 500) {
      const t = sibling.textContent.trim();
      if (t) { parts.push(t); charCount += t.length; }
      sibling = sibling.nextElementSibling;
    }

    // Parent container
    if (node.parentElement) {
      const parentText = node.parentElement.textContent.trim();
      if (parentText.length < 700) parts.push(parentText);
    }

    if (parts.length > 0) addCandidate(parts.join(' '));
  });

  // Fallback: grab <details>/<summary> contents (accordions)
  document.querySelectorAll('details').forEach(details => {
    const summaryText = (details.querySelector('summary') || {}).textContent || '';
    if (DETAIL_LABELS.has(summaryText.trim().toLowerCase())) {
      addCandidate(details.textContent.trim().slice(0, 600));
    }
  });

  // Last resort: full body text so the backend can GPT-extract composition
  if (!result.candidate_blocks.length) {
    const bodyText = (document.body.innerText || '').trim().slice(0, 3000);
    if (bodyText.length > 100) result.candidate_blocks.push(bodyText);
  }

  return result;
})();
