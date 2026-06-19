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
          if(!r.price){const isSt=el=>{try{const s=window.getComputedStyle(el);return s.textDecorationLine.includes("line-through")||s.textDecoration.includes("line-through");}catch{return false;}};for(const g of["[class*='sale-price'],[class*='price--sale'],[class*='price__sale'],[class*='price__current']","[class*='price-item'],[class*='product-price'],[class*='price__amount']","[class*='price']:not([class*='regular-price'])"]) {if(r.price)break;for(const el of document.querySelectorAll(g)){if(isSt(el))continue;const m=(el.textContent||"").match(/[\$£€¥]\s*(\d[\d,]*(?:\.\d{1,2})?)/);if(m){r.price=parseFloat(m[1].replace(/,/g,""));break;}}}}
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
