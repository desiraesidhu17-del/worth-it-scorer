# Current Card Spec — Result Card

> **Status:** ACTIVE. This describes the result card as it is built and deployed *right now*.
> Source of truth for what the card shows and why. Implementation lives in `static/app.js`,
> `templates/index.html`, `static/style.css`. Update this file when card behavior changes.

---

## Card hierarchy (top → bottom)

1. **Headline** — outcome-first verdict (e.g. "Strong durability, fair price"). From `get_headline()`.
2. **Headline sub** — one-line explanation (e.g. "Performance backs up the price — this is what good value looks like.").
3. **Watch for** — the most likely failure mode (e.g. "Traps heat, low breathability"). From `get_watch_for()`.
4. **Score line** — large orange number `XX / 100 · BAND LABEL`. Score is supporting, not hero.
5. **Score caption** — "This score measures durability vs price — not comfort or feel."
6. **Confidence** — `[HIGH CONFIDENCE]` bracket + one-line reason.
7. **Verdict sentence** — plain-language summary.
8. **/MATERIAL ANALYSIS** — material durability `XX / 100`.
9. **/CONSTRUCTION** — construction `X/10` (hidden when `source == "price_floor"` and no real signals).
10. **/PROPERTIES** — price fit, est. cost per wear, ASTM attribution.

## What the score means / does NOT mean
- **Means:** durability vs price — will this hold up, and is the price fair for that durability.
- **Does NOT mean:** comfort, feel, style, or whether *you personally* will like it.
- This is stated on the card itself (score caption) so users don't over-read the number.

## Verdict buckets (badge + popup chip)
`worth_it` (WI green) · `mixed` (MX orange) · `overpriced` (OP red) · `not_enough_info` (? gray).
Logic in `get_verdict_bucket()` — see PRODUCT_DECISIONS.md.

## Technical-gear override (isTech)
When backend returns `technical_override` signals (GORE-TEX, seam sealing, PrimaLoft, etc.):
- Headline → "Technical performance gear"
- Sub → "Score reflects fiber composition only. Value is driven by membrane technology and construction."
- Score → "Fiber score" muted label; `/ 100 ·` separator + band label hidden
- Watch-for, verdict sentence, price-fit stat, cost-per-wear stat + note, price detail → all hidden
- Technical override panel shown with `[ signal ]` bracket list
- Rationale: a fiber-only durability score is misleading for gear whose value comes from membrane tech.

## Known UX tension (not a bug)
A low material score paired with "fairly priced" / "worth it" can read as contradictory
(price fairness and material quality are scored separately). Tracked in CURRENT_ROADMAP.md.
