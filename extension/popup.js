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
    const [{ result: payload }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const r = {
          url: window.location.href,
          json_ld: [],
          json_ld_raw: [],
          meta: {},
          candidate_blocks: [],
        };

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

        // Candidate block isolation
        const LABELS = new Set([
          "materials", "material", "fabric", "composition", "care", "details",
          "shell", "lining", "body", "trim", "content", "construction",
          "product details", "fabric & care", "material & care",
          "fiber content", "fibre content", "fabric content",
        ]);
        const seen = new Set();

        document.querySelectorAll(
          "h1,h2,h3,h4,h5,h6,button,label,summary,dt,th,span,div,p"
        ).forEach(node => {
          const lbl = (node.textContent || "").trim().toLowerCase();
          if (lbl.length > 60 || !LABELS.has(lbl)) return;

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

        // Fallback: <details>/<summary> accordions
        document.querySelectorAll("details").forEach(details => {
          const summary = details.querySelector("summary");
          if (!summary) return;
          const st = summary.textContent.trim().toLowerCase();
          if (LABELS.has(st)) {
            const text = details.textContent.trim().slice(0, 600);
            const h = text.slice(0, 100);
            if (!seen.has(h) && text.length > 10) {
              seen.add(h);
              r.candidate_blocks.push(text);
            }
          }
        });

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
