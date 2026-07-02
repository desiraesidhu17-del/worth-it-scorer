# 02 · Current Card Spec

> The result card as it should read for a shopper. Implementation lives in `static/app.js`,
> `templates/index.html`, `static/style.css`. See `CLAUDE.md` for the engineering detail.

## Card hierarchy (top → bottom)
1. **Barefax take / outcome headline** — the one-line verdict.
2. **Likely outcome** — how this item is likely to wear over time.
3. **Material durability** — fiber-based durability read.
4. **Build read** — construction quality.
5. **Price fit** — is the price fair for what you get.
6. **Watch for** — the most likely failure mode / tradeoff to know about.
7. **Confidence** — how sure we are (separate reads for build vs material — see open questions).
8. **Details / properties** — supporting data (ASTM properties, cost per wear, etc.).

## Principles
- **Material durability, build read, and price fit must be visually distinct.** They are three
  different axes and should never blur into one number that reads as a single "quality" verdict.
- The card should help a **non-expert shopper make a decision quickly** — outcome first,
  evidence second.


`02_CURRENT_CARD_SPEC.md` describes only the _normal_ card. The technical panel that just shipped is invisible in your product brain. Add a short "Technical gear variant" section:

- When it triggers (2+ technical signals detected)
- The hierarchy: headline "Technical performance gear" → **type-aware comparison subline** → spec rows → "Compare next:" line
- What's suppressed and why (numeric score, price fit, cost-per-wear — because fiber score isn't the value driver)