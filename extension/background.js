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
