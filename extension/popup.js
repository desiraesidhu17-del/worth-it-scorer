/**
 * popup.js — orchestrates the extension flow:
 * 1. Inject extraction logic into current tab via chrome.scripting.executeScript
 * 2. Receive extracted payload
 * 3. POST to /api/score-page
 * 4. Open web app with ?result=UUID
 */

const API_BASE = "https://web-production-adff3.up.railway.app";
const btn = document.getElementById("score-btn");
const status = document.getElementById("status");

function setStatus(msg, isError = false) {
  status.textContent = msg;
  status.className = isError ? "error" : "";
}

btn.addEventListener("click", async () => {
  btn.disabled = true;
  setStatus("Scanning page\u2026");

  try {
    // Step 1: Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("no_tab");

    // Step 2: Inject extraction logic and get payload
    // Using func: injection so the return value is captured (MV3 requirement)
    // async func so we can await accordion expansion before reading the DOM
    const [{ result: payload }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: async () => {
        const r = {
          url: window.location.href,
          json_ld: [],
          json_ld_raw: [],
          meta: {},
          candidate_blocks: [],
          price: null,
        };

        // Regex that matches any label mentioning fiber/material/composition keywords.
        // Covers: "Content", "Fabric & Care", "Composition, Care & Origin" (Zara),
        // "Product Details" (Madewell), "Materials & Care" (Aritzia), etc.
        const LABEL_RE = /\b(material|fabric|composition|fibre?|shell|lining|body|trim|care|details?|construction|content)\b/i;

        // Step 0: Auto-expand collapsed accordions whose label matches LABEL_RE
        // so that hidden composition text is in the DOM before we read it.
        document.querySelectorAll(
          "button,summary,[role='button'],[role='tab']"
        ).forEach(el => {
          const txt = (el.textContent || "").trim();
          if (txt.length <= 80 && LABEL_RE.test(txt)) {
            try { el.click(); } catch (_) {}
          }
        });
        // Also expand aria-expanded=false elements matching the same keywords
        document.querySelectorAll("[aria-expanded='false']").forEach(el => {
          const txt = (el.textContent || "").trim();
          if (txt.length <= 80 && LABEL_RE.test(txt)) {
            try { el.click(); } catch (_) {}
          }
        });
        // Wait for accordion animations to finish
        await new Promise(resolve => setTimeout(resolve, 600));

        // JSON-LD blocks
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

        // Price extraction — cascade through most-reliable to least-reliable sources
        // 1. Schema.org microdata: <* itemprop="price" content="128.00">
        //    or <* itemprop="price">CA$217.00</*> (text content only, no content attr)
        const itempropEl = document.querySelector("[itemprop='price']");
        if (itempropEl) {
          const raw = (itempropEl.getAttribute("content") || itempropEl.textContent || "").trim();
          if (raw) {
            const cleaned = raw.replace(/,/g, "").replace(/[^\d.]/g, "");
            const n = parseFloat(cleaned);
            if (!isNaN(n) && n > 0) r.price = n;
          }
        }

        // 2. Shopify / common data attributes (prices often stored in cents)
        if (!r.price) {
          const dpEl = document.querySelector(
            "[data-price],[data-product-price],[data-variant-price],[data-sale-price]"
          );
          if (dpEl) {
            const attrs = ["data-price","data-product-price","data-variant-price","data-sale-price"];
            for (const a of attrs) {
              const raw = dpEl.getAttribute(a);
              if (!raw) continue;
              let n = parseFloat(raw.replace(/[^0-9.]/g, ""));
              if (!isNaN(n) && n > 0) {
                // Shopify stores in cents when value >= 1000 and raw has no decimal
                if (n >= 1000 && !raw.includes(".")) n = n / 100;
                r.price = Math.round(n * 100) / 100;
                break;
              }
            }
          }
        }

        // 3. Visible price element — class-name heuristics
        if (!r.price) {
          const priceEl = document.querySelector(
            "[class*='sale-price'],[class*='price--sale'],[class*='price__sale']," +
            "[class*='price__current'],[class*='price-item'],[class*='product-price']," +
            "[class*='regular-price'],[class*='price__amount'],[class*='price']"
          );
          if (priceEl) {
            const txt = priceEl.textContent || "";
            const m = txt.match(/[\$£€¥]\s*(\d[\d,]*(?:\.\d{1,2})?)/);
            if (m) r.price = parseFloat(m[1].replace(/,/g, ""));
          }
        }

        // Candidate block isolation
        const seen = new Set();

        document.querySelectorAll(
          "h1,h2,h3,h4,h5,h6,button,label,summary,dt,th,span,div,p,li"
        ).forEach(node => {
          const lbl = (node.textContent || "").trim();
          // Skip nodes that are clearly not section labels (too long or no keyword)
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
            if (!seen.has(h) && block.length > 10) {
              seen.add(h);
              r.candidate_blocks.push(block);
            }
          }
        });

        // Direct fiber percentage scan — catches elements like:
        //   <li>61% cotton/39% TENCEL™ Lyocell.</li>
        // These are short blocks (< 300 chars) so the backend skips the
        // long-text context check and extracts the fibers directly.
        const PCT_SCAN_RE = /\d+\s*%\s*[a-zA-Z]/;
        document.querySelectorAll("li,p,td,span").forEach(el => {
          const txt = (el.textContent || "").trim();
          if (txt.length < 5 || txt.length > 300) return;
          if (!PCT_SCAN_RE.test(txt)) return;
          const h = txt.slice(0, 100);
          if (!seen.has(h)) {
            seen.add(h);
            r.candidate_blocks.push(txt);
          }
        });

        // Fallback: <details>/<summary> accordions (native HTML, not React)
        document.querySelectorAll("details").forEach(details => {
          const summary = details.querySelector("summary");
          if (!summary) return;
          const st = summary.textContent.trim();
          if (st.length <= 80 && LABEL_RE.test(st)) {
            const text = details.textContent.trim().slice(0, 600);
            const h = text.slice(0, 100);
            if (!seen.has(h) && text.length > 10) {
              seen.add(h);
              r.candidate_blocks.push(text);
            }
          }
        });

        // Last resort: full body text so the backend can GPT-extract composition
        if (!r.candidate_blocks.length) {
          const bodyText = (document.body.innerText || "").trim().slice(0, 3000);
          if (bodyText.length > 100) r.candidate_blocks.push(bodyText);
        }

        return r;
      },
    });

    if (!payload) throw new Error("no_data");
    if (!payload.candidate_blocks.length && !payload.json_ld.length) {
      throw new Error("no_product");
    }

    setStatus("Scoring\u2026");

    // Step 3: POST to /api/score-page
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

    // Step 4: Open web app with result
    await chrome.tabs.create({ url: `${API_BASE}?result=${result_id}` });
    window.close();

  } catch (err) {
    const messages = {
      no_tab: "Could not access the current tab.",
      no_data: "Could not read this page.",
      no_product: "No product info found \u2014 try the paste text tab on the web app.",
      no_composition: "No material composition found on this page.",
      api_error: "Scoring failed \u2014 try again.",
    };
    setStatus(messages[err.message] || "Something went wrong. Try again.", true);
    btn.disabled = false;
  }
});
