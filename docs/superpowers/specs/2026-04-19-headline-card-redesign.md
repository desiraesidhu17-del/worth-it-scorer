# Headline Card Redesign — Spec
**Date:** 2026-04-19
**Status:** Approved for implementation

---

## What This Changes and Why

The result card currently presents three very different types of claims with equal visual authority:
- **Fiber science** (property bars — ASTM-backed, real)
- **Model inference** (price fit, verdict — reasoned, not measured)
- **Estimates** (construction from price, cost per wear — assumption-based)

Users can't tell which is which. And the score number — a modeled composite — sits as the hero of the card, implying precision it doesn't have.

This spec makes two changes:
1. **Headline system** — a primary outcome label + sub-line replaces the score number as the card's top-level message; a "Watch for" list adds specific, user-visible failure modes
2. **Layer differentiation** — construction estimates and cost-per-wear are visually and linguistically marked as estimates, not measurements

---

## 1. Headline System

### Architecture (Three Steps)

**Step 1 — Base headline (Approach A)**
A 2D matrix keyed on `(score_band, price_pressure_level)`. Gives consistency and editorial control. Always runs.

**Step 2 — Fiber-class override (Approach B-lite)**
For cases where the standard framing misleads. Swaps the headline only; sub-line from Step 1 stays.
Currently one override: premium fiber (silk, cashmere, alpaca, merino) at low/very_low score.

**Step 3 — "Watch for" (Approach C, controlled)**
2–3 specific user-visible failure modes. A lookup, not generation — pre-written strings selected by logic.

### New Fields on `ScoreResult`

```python
headline: str        # Primary outcome label
headline_sub: str    # Supporting sub-line (from Step 1 matrix, always)
watch_for: list[str] # 2–3 specific failure modes (from Step 3 lookup)
```

### Step 2: Premium Fiber Override

**Condition:** `score_band in ("very_low", "low")` AND `get_dominant_fiber_class(composition) == "premium"`

```
Headline:  Built for feel, not longevity
Sub-line:  Fine fibers like silk prioritize softness and drape over durability.
```

The Step 1 sub-line is replaced. Step 3 (Watch for) still runs normally.

### Step 1: Headline Matrix (25 entries)

**Language rules applied throughout:**
- Headlines: "durability" not "material" or "fiber" (exception: "Luxury price, budget fiber" kept — user-approved phrasing)
- Sub-lines: real-world outcome language ("expect visible wear") not academic framing ("fiber composition doesn't justify")
- Price criticism: "price runs ahead of performance" not "doesn't justify" — confident, not aggressive

| Band | Pressure | Headline | Sub-line |
|---|---|---|---|
| very_low | low | Weak durability, fair price | Durability is low — the price at least reflects it. |
| very_low | moderate | Weak durability, priced too high | Likely to show wear early relative to the price. |
| very_low | high | Poor durability, high price | Expect visible wear sooner than this price suggests. |
| very_low | extreme | Luxury price, budget fiber | You're paying for positioning, not performance. |
| very_low | unknown | Very low durability | Likely to show visible wear early in regular use. |
| low | low | Below-average durability, fair price | Performance is below average — the price is honest about that. |
| low | moderate | Below-average durability, priced too high | Wear resistance doesn't match what the price suggests. |
| low | high | Overpriced for durability | Wear resistance is below what this price suggests. |
| low | extreme | Luxury price, low durability | You're paying for positioning, not how it holds up. |
| low | unknown | Below-average durability | Expect earlier wear than most alternatives in this category. |
| mid | low | Average durability, fair price | Nothing exceptional — but the price is honest about that. |
| mid | moderate | Average durability, slight premium | Solid for the category — with a modest premium on top. |
| mid | high | Average durability, overpriced | Performance is average — the price runs ahead of it. |
| mid | extreme | Average durability, luxury pricing | Performance is typical — the price goes far beyond what it warrants. |
| mid | unknown | Average durability | Should hold up fine under normal rotation. |
| good | low | Strong durability, fair price | Performance backs up the price — this is what good value looks like. |
| good | moderate | Strong durability, slight premium | Good performance, with a modest brand premium on top. |
| good | high | Good durability, overpriced | Performance is strong — but the price runs well ahead of it. |
| good | extreme | Good durability, steep premium | Solid performance — but you're paying well beyond what it warrants. |
| good | unknown | Above-average durability | Built to hold up over regular rotation. |
| excellent | low | Exceptional durability, great value | Top-tier performance at a price that reflects how it holds up. |
| excellent | moderate | Exceptional durability, modest premium | Top-tier performance — the slight premium is the cost of this quality level. |
| excellent | high | Exceptional durability, steep price | Top-tier performance — but the price runs well ahead of it. |
| excellent | extreme | Exceptional durability, extreme price | Performance is exceptional — but the price goes far beyond what even that justifies. |
| excellent | unknown | Exceptional durability | Built for longevity — top-tier performance across the board. |

### Step 3: Watch For (Approach C, controlled)

Output: 2–3 strings. Specific, user-visible consequences — not generalizations.

**Layer 1 — Property-based (generic fallback)**

Applied when no fiber-specific string overrides the slot.

| Property | Threshold | Watch for string |
|---|---|---|
| pilling | < 50 | Surface pilling or fuzzing |
| tensile | < 50 | Seam stress, distortion over time |
| colorfastness | < 65 | Color fading with repeated washing |

**Layer 2 — Fiber-specific (overrides generic when matched)**

"Dominant fiber" = highest-percentage canonical fiber in composition.

| Dominant fiber | Condition | Replaces generic string for |
|---|---|---|
| acrylic | pilling < 50 | Heavy pilling within 1–2 seasons |
| silk | pilling < 55 OR tensile < 60 | Snagging, delicate handling required |
| viscose / rayon | tensile < 50 | Shrinks or distorts when wet |
| cashmere | pilling < 35 | Visible pilling after early wears |
| wool | pilling < 60 | Pilling under arms and at seams |
| cotton | colorfastness < 75 | Fading after repeated washing |

**Layer 3 — Price flag**

Condition: `price > 100` AND `score_band in ("very_low", "low")`
Append: `"High care cost relative to expected lifespan"`

**Algorithm:**
1. Find properties below threshold (Layer 1)
2. For dominant fiber: if Layer 2 match, replace that property's generic string with specific string
3. If Layer 3 condition met: append price flag
4. Truncate to 3 items max; prefer fiber-specific strings over generic

**New functions in `verdict_library.py`:**

```python
def get_headline(
    score: float,
    price_pressure_level: str,  # "low" | "moderate" | "high" | "extreme" | "unknown"
    composition: list[dict],    # [{"canonical": str, "pct": float}]
) -> tuple[str, str]:           # (headline, headline_sub)

def get_watch_for(
    composition: list[dict],
    property_scores: dict,       # {"pilling": x, "tensile": x, "colorfastness": x, "moisture": x}
    price: float | None,
    score_band: str,
) -> list[str]
```

---

## 2. Card Layout

### New Structure

**Current card-top:**
```
[31]     "Lower predicted durability than the premium label suggests."
/100     [LOW CONFIDENCE] Full fiber composition listed...
```

**New card-top:**
```
Built for feel, not longevity
Fine fibers like silk prioritize softness and drape over durability.

Watch for: Snagging · Delicate handling required · High care cost relative to expected lifespan

31 / 100  ·  LOW DURABILITY
[MEDIUM CONFIDENCE] Full fiber composition listed — score confidence is high.
```

### Score Line Format

`{score} / 100  ·  {BAND LABEL}`

| score_band | Band label in score line |
|---|---|
| very_low | VERY LOW DURABILITY |
| low | LOW DURABILITY |
| mid | AVERAGE DURABILITY |
| good | ABOVE AVERAGE DURABILITY |
| excellent | STRONG DURABILITY |

The `{score}` value stays orange (existing color). Everything else in the line is muted.

### Existing Verdict Sentence

Moves below the confidence badge. Smaller, tertiary. Still renders — provides fiber-class context. Not the primary takeaway.

---

## 3. Layer Differentiation

Three small changes. No backend changes required — the data to drive these already exists.

### Construction — Hide Number at Price-Floor Only

**Condition:** `construction.source === "price_floor"` AND `construction.signals_found.length === 0`

**Before:**
```
Construction  [====        ]  6.0 / 10
At $150: expect full lining, quality closures, clean seams
```

**After:**
```
Construction not assessed
At $150: expect full lining, quality closures, clean seams
```

The bar and score number are hidden. The price-floor note stays — it's genuinely useful context. When text signals ARE found (source = "text"), the bar and score render normally.

### Cost Per Wear — Relabel

- `"Cost per wash"` → `"Est. cost per wear"`
- No backend change. The existing note already uses "Estimated lifespan" language.

### Property Bars — Attribution Line

Below the `/PROPERTIES` section header, add:

`Fiber class averages — ASTM D4970/D5034`

Small, muted. Transforms the bars from "measurements of this garment" to "here's the science behind this fiber type." One line of copy, significant trust change.

---

## 4. Files Changed

| File | What changes |
|---|---|
| `scoring/verdict_library.py` | Add `HEADLINE_MATRIX`, `HEADLINE_OVERRIDES`, `FIBER_WATCH_FORS`; add `get_headline()`, `get_watch_for()` |
| `scoring/engine.py` | Add `headline`, `headline_sub`, `watch_for` to `ScoreResult`; call both new functions in `score_item()` |
| `static/app.js` | Update `renderResult()` to render headline/sub/watch-for; hide construction bar+score when price-floor only; rename CPW label |
| `templates/index.html` | Add headline, sub, watch-for HTML elements; restructure score line to inline format; add ASTM attribution line; add construction fallback text elements |
| `static/style.css` | Headline styles (large, prominent); score-line styles (compact, inline, orange score + muted rest); watch-for display; construction fallback; attribution text |
| `app.py` | No changes — `to_dict()` picks up new ScoreResult fields automatically |

---

## 5. Testing

- Unit tests for `get_headline()`: every band/pressure combination, premium override at low + very_low, unknown price fallback
- Unit tests for `get_watch_for()`: acrylic (heavy pilling), silk (snagging), viscose (wet distortion), high-price + low-score flag, max-3 truncation
- Existing 33 extractor tests must still pass
- Manual spot-check set (run through full stack, verify card output):
  - 100% silk dress, $340 → expect "Built for feel, not longevity" + snagging watch-for
  - 100% acrylic sweater, $50 → expect "Weak durability, fair price" + heavy pilling watch-for
  - 100% merino, $120 → expect above-average or good band headline
  - 80% polyester activewear, $80 → expect average or good + fair price

---

## 6. Out of Scope

- Silk sub-types (momme weight, weave detection) — separate feature
- Improving wash cycle estimate grounding — separate feature
- Verdict sentence library rewrite — existing sentences still render in tertiary position; rewrite is a future pass
- Score banding disclaimer ("scores within ±5 are not meaningfully different") — can be added to methodology page first
- Spot-check validation dataset — separate exercise, recommended before next major engine change
