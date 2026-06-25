# Current Roadmap — worth it?

> **What to build next. What is frozen. What is "do not build yet."**
> Engineering state lives in `CLAUDE.md`. Product logic lives in `PRODUCT_DECISIONS.md`.
> This file answers only: *what's next?*

Last updated: 2026-06-19

---

## ✅ Shipped & deployed (do not re-plan)
All of these are live on Railway. See `CLAUDE.md` session log for detail.

- Chrome extension + Flask backend
- Fabric + price extraction (6-level price cascade, sale-price detection)
- Cold Data visual redesign
- Headline card redesign (outcome-first, score demoted)
- Technical-gear override card
- GSM extraction + scoring differentiation
- Ambient detection + verdict badge (Plan A)
- Construction stat in result card

---

## 🔜 Next up (active backlog)
Priority order. Pull the top item when starting new work.

1. **Fix verdict / price-label messaging tension** — low material score + "fairly priced"
   reads as contradictory. UX wording problem, not a scoring bug. (See PRODUCT_DECISIONS.md.)
2. **Test more retailers** — H&M, Zara, Uniqlo (extraction parity check).
3. **Add more metrics to the result card** — needs brainstorm + plan first (don't build blind).

## ❄️ Frozen / do not build yet
- **Plan B: Compare feature** (ambient_mode_spec sections 4–5) — "Add to Compare" button +
  Compare view. Deferred until Plan A is validated with real use. Needs its own plan doc.

## 🐞 Known issues (track, fix opportunistically)
- Claude in Chrome MCP not connected (native host path fixed; may need Chrome restart).
- Low score + "fairly priced" verdict tension (UX debt — also item #1 above).
- `result_dict.update(result_extraction.to_dict())` in `score_page_endpoint` clobbers
  `composition`/`price`/`category`/`gsm` — pre-existing, non-blocking.

---

## Workflow reminder
New feature/UI → `superpowers:brainstorming` first. Have a spec → `superpowers:writing-plans`.
Always `git push origin main` after feature work (Railway auto-deploys).
