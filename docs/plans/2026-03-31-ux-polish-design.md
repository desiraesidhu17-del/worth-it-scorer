# UX Polish Pass — Design Doc
**Date:** 2026-03-31
**Scope:** 6 improvements across `templates/index.html`, `static/style.css`, `static/app.js`, `scoring/verdict_library.py`

---

## Problem

The result card is functional but reads as spreadsheet-translated rather than a decision tool. Six issues were identified:

1. Top section is text-heavy and stacks too quickly
2. "Price pressure" label is abstract/unintuitive
3. Cost-per-wash shows a number with no context
4. Construction section uses different visual language than the rest of the card
5. Download button "PREPARING…" state looks like a debug artifact
6. Verdict sentences are 2–3 sentence academic descriptions; should be short, punchy, action-oriented

---

## Changes

### 1. Tighten the top section (`style.css`)
- `verdict-sentence` margin-bottom: `12px → 6px`
- `confidence-label`: `font-weight: 700 → 400` (keep color coding via JS; reduce visual weight)
- Goal: confidence reads as metadata, not a second headline

### 2. Rename "Price pressure" → "Price fit" (`index.html`)
- Single label change on line 169
- "Price fit" is short, concrete, and brand-consistent

### 3. Cost-per-wash context (`index.html` + `app.js`)
- Add `<div id="cpw-note" class="price-detail"></div>` below the stats row
- Populate from `cpw.note` in `renderResult()`: *"Estimated lifespan: 25–50 wash cycles…"*
- Show/hide same pattern as `#price-detail`
- No backend change needed (note already in API response)

### 4. Construction section — unify with property bars (`index.html`, `style.css`, `app.js`)
- Replace custom `construction-header` block with a standard `.prop-row`:
  ```
  Construction  [========--]  3.5
  ```
- Remove inline `[LOW CONFIDENCE]` tag (redundant with confidence badge at top)
- `construction-floor-note` stays as small gray paragraph below the bar
- Chip signals stay as-is ([ chip ] style already consistent)
- Remove now-unused `.construction-header`, `.construction-label`, `.construction-score-wrap`, `.construction-conf` CSS

### 5. Download button animation (`style.css`, `app.js`)
- Change loading text: `"Preparing…"` → `"[ EXPORTING ]"`
- Add CSS class `.btn-exporting` with animated ellipsis via `@keyframes`
- Button text becomes `"[ EXPORTING ]"` with three dots animating in/out
- Resets to `"[ DOWNLOAD CARD ]"` on completion/error

### 6. Verdict sentence rewrite (`scoring/verdict_library.py`)
- Rewrite all 25 entries in `WORTH_IT_VERDICTS`
- New tone: 1–2 short punchy sentences. First = outcome. Second = use-case implication.
- No structural change to the dict or calling code

**Tone examples:**

| Band | Fiber | Before | After |
|------|-------|--------|-------|
| very_low | synthetic | "The fiber composition here is associated with fast-fashion quality. Expect visible pilling and shape loss within a few months of regular wear." | "Expect pilling within one season. Not worth mid-range pricing." |
| good | natural | "Solid natural fiber composition with good predicted performance. This is the quality level where the fiber science earns its keep." | "Good natural fiber content with strong predicted durability. Worth the rotation." |
| excellent | premium | "Premium fibers used correctly. This composition is associated with exceptional longevity and is worth the investment." | "Premium fibers, premium performance. The material science earns the price." |

---

## Files Changed

| File | Changes |
|------|---------|
| `templates/index.html` | Rename label; add `#cpw-note`; restructure construction block |
| `static/style.css` | Confidence badge weight; CPW note style; construction prop-row; button animation |
| `static/app.js` | Populate `#cpw-note`; update `renderConstruction()`; button animation state |
| `scoring/verdict_library.py` | Rewrite 25 verdict entries |

---

## Out of Scope
- Backend scoring logic (no changes to engine.py, extractor.py)
- Test coverage (verdict sentences are content, not logic; existing 33 tests unaffected)
- New metrics or scoring categories
