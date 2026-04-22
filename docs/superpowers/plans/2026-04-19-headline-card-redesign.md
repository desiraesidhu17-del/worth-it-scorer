# Headline Card Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the score number as the card's headline with a three-step outcome label system (base matrix + fiber-class override + "Watch for" list), and differentiate evidence layers for construction, CPW, and property bars.

**Architecture:** New functions `get_headline()` and `get_watch_for()` added to `verdict_library.py` with TDD. Wired into `ScoreResult` via `engine.py`. Frontend restructures `card-top` to vertical stack with headline first; score demoted to compact inline line. Construction hides numeric score when only price-tier inference is available.

**Tech Stack:** Python 3.11, Flask, vanilla JS, Space Mono CSS (Cold Data theme). Pytest for new unit tests; existing custom runner (`python -m scoring.tests`) for engine integration tests.

---

## File Map

| File | Change |
|---|---|
| `scoring/test_verdict.py` | **New** — pytest unit tests for `get_headline()` and `get_watch_for()` |
| `scoring/verdict_library.py` | Add `HEADLINE_MATRIX`, `_PREMIUM_OVERRIDE_*`, `_WATCH_*` constants; add `get_headline()`, `get_watch_for()` |
| `scoring/engine.py` | Add `headline`, `headline_sub`, `watch_for` fields to `ScoreResult`; import and call new functions in `score_item()`; update `_no_data_result()` |
| `templates/index.html` | Restructure `card-top` to vertical stack; add property attribution line; add construction-not-assessed fallback element; rename CPW stat label |
| `static/app.js` | Update `renderResult()` for headline/sub/watch-for/score-line; rewrite `renderConstruction()` to hide score at price-floor only; update reset handler |
| `static/style.css` | Change `.card-top` to vertical flex; shrink `.score-number`; add headline/sub/watch-for/score-line/attribution/construction-fallback styles |

`app.py` — no changes needed. `ScoreResult.to_dict()` uses `asdict()` which picks up new fields automatically.

---

### Task 1: `get_headline()` — TDD

**Files:**
- Create: `scoring/test_verdict.py`
- Modify: `scoring/verdict_library.py`

- [ ] **Step 1.1: Create test file with failing tests**

Create `scoring/test_verdict.py`:

```python
"""
Unit tests for verdict_library headline and watch_for functions.

Run from project root:
    pytest scoring/test_verdict.py -v
"""
import pytest
from scoring.verdict_library import get_headline, get_watch_for


# ── get_headline ───────────────────────────────────────────────────────────────

def test_headline_premium_override_low():
    """100% silk at low band triggers B-override regardless of price pressure."""
    silk = [{"canonical": "silk", "pct": 100}]
    headline, sub = get_headline(score=35.0, price_pressure_level="high", composition=silk)
    assert headline == "Built for feel, not longevity"
    assert "softness" in sub.lower() or "drape" in sub.lower()


def test_headline_premium_override_very_low():
    """Cashmere at very_low also triggers B-override."""
    cashmere = [{"canonical": "cashmere", "pct": 100}]
    headline, sub = get_headline(score=15.0, price_pressure_level="extreme", composition=cashmere)
    assert headline == "Built for feel, not longevity"


def test_headline_premium_no_override_at_mid():
    """Premium fiber at mid band uses the normal matrix, not the B-override."""
    silk = [{"canonical": "silk", "pct": 100}]
    headline, sub = get_headline(score=55.0, price_pressure_level="low", composition=silk)
    assert headline != "Built for feel, not longevity"
    assert "average" in headline.lower() or "fair" in headline.lower()


def test_headline_matrix_low_high():
    """Low band + high price pressure → 'Overpriced for durability'."""
    acrylic = [{"canonical": "acrylic", "pct": 100}]
    headline, sub = get_headline(score=35.0, price_pressure_level="high", composition=acrylic)
    assert headline == "Overpriced for durability"
    assert "wear resistance" in sub.lower() or "price" in sub.lower()


def test_headline_matrix_excellent_low():
    """Excellent band + fair price → great value headline."""
    comp = [{"canonical": "nylon", "pct": 100}]
    headline, sub = get_headline(score=85.0, price_pressure_level="low", composition=comp)
    assert headline == "Exceptional durability, great value"


def test_headline_matrix_mid_moderate():
    """Mid band + slight premium → average + premium headline."""
    comp = [{"canonical": "cotton", "pct": 100}]
    headline, sub = get_headline(score=55.0, price_pressure_level="moderate", composition=comp)
    assert headline == "Average durability, slight premium"


def test_headline_unknown_price():
    """Unknown price pressure uses the material-only fallback."""
    comp = [{"canonical": "wool", "pct": 100}]
    headline, sub = get_headline(score=60.0, price_pressure_level="unknown", composition=comp)
    assert "average" in headline.lower()


def test_headline_very_low_extreme_non_premium():
    """Very low band + extreme pressure for a synthetic → 'Luxury price, budget fiber'."""
    comp = [{"canonical": "acrylic", "pct": 100}]
    headline, sub = get_headline(score=20.0, price_pressure_level="extreme", composition=comp)
    assert headline == "Luxury price, budget fiber"
    assert "positioning" in sub.lower()


# ── get_watch_for ──────────────────────────────────────────────────────────────

def test_watch_for_acrylic_pilling():
    """Acrylic pilling → fiber-specific string replaces generic."""
    comp = [{"canonical": "acrylic", "pct": 100}]
    props = {"pilling": 20, "tensile": 50, "colorfastness": 85, "moisture": 15}
    result = get_watch_for(comp, props, price=50.0, score_band="low")
    assert "Heavy pilling within 1–2 seasons" in result


def test_watch_for_silk_snagging_not_duplicated():
    """Silk triggers snagging string once even when multiple properties are weak."""
    comp = [{"canonical": "silk", "pct": 100}]
    props = {"pilling": 45, "tensile": 55, "colorfastness": 60, "moisture": 75}
    result = get_watch_for(comp, props, price=300.0, score_band="low")
    assert result.count("Snagging, delicate handling required") == 1
    assert len(result) <= 3


def test_watch_for_viscose_wet():
    """Viscose low tensile → shrinks or distorts when wet."""
    comp = [{"canonical": "viscose", "pct": 100}]
    props = {"pilling": 30, "tensile": 40, "colorfastness": 65, "moisture": 75}
    result = get_watch_for(comp, props, price=80.0, score_band="low")
    assert "Shrinks or distorts when wet" in result


def test_watch_for_price_flag_appended():
    """High price + low band → care cost flag appended."""
    comp = [{"canonical": "cashmere", "pct": 100}]
    props = {"pilling": 25, "tensile": 50, "colorfastness": 55, "moisture": 80}
    result = get_watch_for(comp, props, price=400.0, score_band="low")
    assert "High care cost relative to expected lifespan" in result


def test_watch_for_max_three():
    """Result is always capped at 3 items."""
    comp = [{"canonical": "acrylic", "pct": 100}]
    props = {"pilling": 10, "tensile": 10, "colorfastness": 10, "moisture": 10}
    result = get_watch_for(comp, props, price=500.0, score_band="very_low")
    assert len(result) <= 3


def test_watch_for_empty_when_all_high():
    """No watch-fors when all property scores are strong."""
    comp = [{"canonical": "polyester", "pct": 100}]
    props = {"pilling": 85, "tensile": 90, "colorfastness": 80, "moisture": 20}
    result = get_watch_for(comp, props, price=50.0, score_band="good")
    assert result == []


def test_watch_for_no_price_flag_at_mid_band():
    """Price flag only fires at very_low or low band."""
    comp = [{"canonical": "silk", "pct": 100}]
    props = {"pilling": 45, "tensile": 55, "colorfastness": 60, "moisture": 75}
    result = get_watch_for(comp, props, price=500.0, score_band="mid")
    assert "High care cost relative to expected lifespan" not in result
```

- [ ] **Step 1.2: Run tests to confirm they fail (functions not yet defined)**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_verdict.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name 'get_headline' from 'scoring.verdict_library'`

- [ ] **Step 1.3: Add headline constants and `get_headline()` to `verdict_library.py`**

Append to the bottom of `scoring/verdict_library.py` (after the closing brace of `get_cost_per_wash`):

```python
# ── Headline system ───────────────────────────────────────────────────────────
# Three-step architecture:
#   Step 1 (A): 2D matrix by (score_band, price_pressure_level) — consistency + control
#   Step 2 (B-lite): premium fiber override at low/very_low — swaps headline only
#   Step 3 (C): get_watch_for() below — controlled lookup, not generation

HEADLINE_MATRIX: dict[tuple[str, str], tuple[str, str]] = {
    # (score_band, price_pressure_level): (headline, sub_line)
    # Language rules: use "durability" not "material/fiber"; real-world outcome subs;
    # price criticism: "price runs ahead" not "doesn't justify".

    # very_low (0–25)
    ("very_low", "low"):      ("Weak durability, fair price",
                               "Durability is low — the price at least reflects it."),
    ("very_low", "moderate"): ("Weak durability, priced too high",
                               "Likely to show wear early relative to the price."),
    ("very_low", "high"):     ("Poor durability, high price",
                               "Expect visible wear sooner than this price suggests."),
    ("very_low", "extreme"):  ("Luxury price, budget fiber",
                               "You're paying for positioning, not performance."),
    ("very_low", "unknown"):  ("Very low durability",
                               "Likely to show visible wear early in regular use."),

    # low (26–45)
    ("low", "low"):      ("Below-average durability, fair price",
                          "Performance is below average — the price is honest about that."),
    ("low", "moderate"): ("Below-average durability, priced too high",
                          "Wear resistance doesn't match what the price suggests."),
    ("low", "high"):     ("Overpriced for durability",
                          "Wear resistance is below what this price suggests."),
    ("low", "extreme"):  ("Luxury price, low durability",
                          "You're paying for positioning, not how it holds up."),
    ("low", "unknown"):  ("Below-average durability",
                          "Expect earlier wear than most alternatives in this category."),

    # mid (46–65)
    ("mid", "low"):      ("Average durability, fair price",
                          "Nothing exceptional — but the price is honest about that."),
    ("mid", "moderate"): ("Average durability, slight premium",
                          "Solid for the category — with a modest premium on top."),
    ("mid", "high"):     ("Average durability, overpriced",
                          "Performance is average — the price runs ahead of it."),
    ("mid", "extreme"):  ("Average durability, luxury pricing",
                          "Performance is typical — the price goes far beyond what it warrants."),
    ("mid", "unknown"):  ("Average durability",
                          "Should hold up fine under normal rotation."),

    # good (66–80)
    ("good", "low"):      ("Strong durability, fair price",
                           "Performance backs up the price — this is what good value looks like."),
    ("good", "moderate"): ("Strong durability, slight premium",
                           "Good performance, with a modest brand premium on top."),
    ("good", "high"):     ("Good durability, overpriced",
                           "Performance is strong — but the price runs well ahead of it."),
    ("good", "extreme"):  ("Good durability, steep premium",
                           "Solid performance — but you're paying well beyond what it warrants."),
    ("good", "unknown"):  ("Above-average durability",
                           "Built to hold up over regular rotation."),

    # excellent (81–100)
    ("excellent", "low"):      ("Exceptional durability, great value",
                                "Top-tier performance at a price that reflects how it holds up."),
    ("excellent", "moderate"): ("Exceptional durability, modest premium",
                                "Top-tier performance — the slight premium is the cost of this quality level."),
    ("excellent", "high"):     ("Exceptional durability, steep price",
                                "Top-tier performance — but the price runs well ahead of it."),
    ("excellent", "extreme"):  ("Exceptional durability, extreme price",
                                "Performance is exceptional — but the price goes far beyond what even that justifies."),
    ("excellent", "unknown"):  ("Exceptional durability",
                                "Built for longevity — top-tier performance across the board."),
}

# Step 2 override: premium fiber (silk, cashmere, alpaca, merino) at low/very_low score.
# Swaps headline only — sub_line comes from the Step 1 matrix.
_PREMIUM_OVERRIDE_BANDS: frozenset[str] = frozenset({"very_low", "low"})
_PREMIUM_OVERRIDE_HEADLINE = "Built for feel, not longevity"
_PREMIUM_OVERRIDE_SUB = "Fine fibers like silk prioritize softness and drape over durability."


def get_headline(
    score: float,
    price_pressure_level: str,
    composition: list[dict],
) -> tuple[str, str]:
    """
    Returns (headline, headline_sub) for the result card.

    Step 1 (A): 2D matrix keyed on (score_band, price_pressure_level).
    Step 2 (B-lite): premium fiber at low/very_low overrides the headline.

    composition: [{"canonical": str, "pct": float}] — known fibers only.
    price_pressure_level: "low" | "moderate" | "high" | "extreme" | "unknown"
    """
    band = get_score_band(score)

    # Step 2: B-lite override
    if band in _PREMIUM_OVERRIDE_BANDS:
        if get_dominant_fiber_class(composition) == "premium":
            return _PREMIUM_OVERRIDE_HEADLINE, _PREMIUM_OVERRIDE_SUB

    # Step 1: base matrix
    key = (band, price_pressure_level)
    if key in HEADLINE_MATRIX:
        return HEADLINE_MATRIX[key]

    # Fallback to unknown-price entry for the band
    return HEADLINE_MATRIX.get((band, "unknown"), ("", ""))
```

- [ ] **Step 1.4: Run headline tests only**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_verdict.py -k "headline" -v
```

Expected: all 8 `test_headline_*` tests pass. `test_watch_for_*` tests still fail (ImportError).

- [ ] **Step 1.5: Commit**

```bash
git add scoring/verdict_library.py scoring/test_verdict.py
git commit -m "feat: add get_headline() with 25-entry matrix and premium fiber B-override"
```

---

### Task 2: `get_watch_for()` — tests already written, add implementation

**Files:**
- Modify: `scoring/verdict_library.py`

- [ ] **Step 2.1: Confirm watch_for tests are failing (function not yet defined)**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_verdict.py -k "watch_for" -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'get_watch_for'`

- [ ] **Step 2.2: Append watch_for constants and function to `verdict_library.py`**

Append to the bottom of `scoring/verdict_library.py` (after `get_headline`):

```python
# ── Watch For system (Step 3 — Approach C, controlled) ────────────────────────
# Produces 2–3 specific, user-visible failure mode strings.
# Layer 1: property-based generic fallback.
# Layer 2: fiber-specific override replaces generic for that property slot.
# Layer 3: price flag when high price + low durability band.

# (property_name): (score_threshold, generic_watch_for_string)
_WATCH_PROPERTY_GENERIC: dict[str, tuple[float, str]] = {
    "pilling":       (50.0, "Surface pilling or fuzzing"),
    "tensile":       (50.0, "Seam stress, distortion over time"),
    "colorfastness": (65.0, "Color fading with repeated washing"),
}

# fiber_canonical: {property_name: (score_threshold, watch_for_string)}
# When dominant fiber matches AND property score < threshold,
# this string replaces the generic string for that property slot.
_WATCH_FIBER_SPECIFIC: dict[str, dict[str, tuple[float, str]]] = {
    "acrylic":  {"pilling":  (50.0, "Heavy pilling within 1–2 seasons")},
    "silk":     {"pilling":  (55.0, "Snagging, delicate handling required"),
                 "tensile":  (60.0, "Snagging, delicate handling required")},
    "viscose":  {"tensile":  (50.0, "Shrinks or distorts when wet")},
    "rayon":    {"tensile":  (50.0, "Shrinks or distorts when wet")},
    "cashmere": {"pilling":  (35.0, "Visible pilling after early wears")},
    "wool":     {"pilling":  (60.0, "Pilling under arms and at seams")},
    "cotton":   {"colorfastness": (75.0, "Fading after repeated washing")},
}

_WATCH_PRICE_FLAG = "High care cost relative to expected lifespan"
_WATCH_PRICE_FLAG_THRESHOLD = 100.0
_WATCH_PRICE_FLAG_BANDS: frozenset[str] = frozenset({"very_low", "low"})


def get_watch_for(
    composition: list[dict],
    property_scores: dict,
    price: float | None,
    score_band: str,
) -> list[str]:
    """
    Returns up to 3 user-visible failure modes for this composition.

    composition: [{"canonical": str, "pct": float}] — known fibers only.
    property_scores: {"pilling": float, "tensile": float, "colorfastness": float, "moisture": float}
    price: retail price in USD, or None.
    score_band: "very_low" | "low" | "mid" | "good" | "excellent"
    """
    # Dominant fiber = highest-percentage canonical fiber
    dominant_fiber = ""
    if composition:
        dominant_fiber = max(composition, key=lambda f: f.get("pct", 0)).get("canonical", "")

    fiber_overrides = _WATCH_FIBER_SPECIFIC.get(dominant_fiber, {})
    results: list[str] = []
    seen: set[str] = set()

    for prop, (generic_threshold, generic_str) in _WATCH_PROPERTY_GENERIC.items():
        score = property_scores.get(prop, 100.0)

        # Layer 2: fiber-specific override for this property slot
        if prop in fiber_overrides:
            override_threshold, override_str = fiber_overrides[prop]
            if score < override_threshold:
                if override_str not in seen:
                    seen.add(override_str)
                    results.append(override_str)
                continue  # Skip generic for this slot regardless

        # Layer 1: generic fallback
        if score < generic_threshold:
            if generic_str not in seen:
                seen.add(generic_str)
                results.append(generic_str)

    # Layer 3: price flag
    if (
        price is not None
        and price > _WATCH_PRICE_FLAG_THRESHOLD
        and score_band in _WATCH_PRICE_FLAG_BANDS
        and _WATCH_PRICE_FLAG not in seen
        and len(results) < 3
    ):
        results.append(_WATCH_PRICE_FLAG)

    return results[:3]
```

- [ ] **Step 2.3: Run all verdict tests**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_verdict.py -v
```

Expected: all 15 tests pass (8 headline + 7 watch_for).

- [ ] **Step 2.4: Confirm no regression in extractor tests**

```bash
pytest scoring/test_extractor.py -v 2>&1 | tail -5
```

Expected: `33 passed`.

- [ ] **Step 2.5: Commit**

```bash
git add scoring/verdict_library.py
git commit -m "feat: add get_watch_for() with property/fiber/price-flag layers"
```

---

### Task 3: Wire new fields into `engine.py`

**Files:**
- Modify: `scoring/engine.py`

- [ ] **Step 3.1: Update import block in `engine.py`**

Find the existing import from `.verdict_library` (lines 28–33):

```python
from .verdict_library import (
    get_verdict_sentence,
    get_cost_per_wash,
    get_score_band,
    CONFIDENCE_NOTES,
)
```

Replace with:

```python
from .verdict_library import (
    get_verdict_sentence,
    get_cost_per_wash,
    get_score_band,
    CONFIDENCE_NOTES,
    get_headline,
    get_watch_for,
)
```

- [ ] **Step 3.2: Add three new fields to `ScoreResult` dataclass**

In `ScoreResult`, find the `construction` field and the `# Metadata` block (lines 77–81):

```python
    # Construction sub-score (optional — populated when text or image is available)
    construction: Optional[ConstructionResult] = None

    # Metadata
    methodology_version: str = METHODOLOGY_VERSION
    unknown_fibers: list[str] = field(default_factory=list)
```

Replace with:

```python
    # Construction sub-score (optional — populated when text or image is available)
    construction: Optional[ConstructionResult] = None

    # Headline (three-step system — see verdict_library.get_headline / get_watch_for)
    headline: str = ""
    headline_sub: str = ""
    watch_for: list[str] = field(default_factory=list)

    # Metadata
    methodology_version: str = METHODOLOGY_VERSION
    unknown_fibers: list[str] = field(default_factory=list)
```

- [ ] **Step 3.3: Call new functions in `score_item()`**

Find the `# ── 10. Human-readable outputs` block (around line 198). After computing `verdict` and `band`, add the two new calls:

```python
    # ── 10. Human-readable outputs ────────────────────────────────────────────────
    comp_dicts = [{"canonical": e.canonical, "pct": e.pct} for e in known_entries]
    verdict = get_verdict_sentence(worth_it_score, comp_dicts)
    band = get_score_band(worth_it_score)

    headline, headline_sub = get_headline(
        worth_it_score,
        price_pressure["level"],
        comp_dicts,
    )
    watch_for = get_watch_for(
        comp_dicts,
        {k: round(v, 1) for k, v in adjusted.items()},
        price,
        band,
    )
```

Then add the three new fields to the `return ScoreResult(...)` call. The full return statement becomes:

```python
    return ScoreResult(
        composition=entries,
        price=price,
        category=category,
        material_score=material_score,
        property_scores={k: round(v, 1) for k, v in adjusted.items()},
        blend_interactions_applied=blend_interactions_applied,
        price_pressure=price_pressure,
        cost_per_wash=cost_per_wash,
        worth_it_score=worth_it_score,
        confidence=confidence,
        confidence_notes=confidence_notes,
        verdict_sentence=verdict,
        score_band=band,
        unknown_fibers=unknown_fibers,
        construction=construction,
        headline=headline,
        headline_sub=headline_sub,
        watch_for=watch_for,
    )
```

- [ ] **Step 3.4: Update `_no_data_result()` with explicit fallback headline**

Find `_no_data_result()` (around line 303). Add `headline`, `headline_sub`, `watch_for` to its `ScoreResult(...)` call. The full updated return is:

```python
    return ScoreResult(
        composition=entries,
        price=price,
        category=category,
        material_score=0,
        property_scores={},
        blend_interactions_applied=False,
        price_pressure={"level": "unknown", "label": "Unknown", "benchmark": None, "detail": ""},
        cost_per_wash={},
        worth_it_score=0,
        confidence="low",
        confidence_notes=[CONFIDENCE_NOTES["low_no_composition"]],
        verdict_sentence="No fiber composition data available — score cannot be calculated.",
        score_band="very_low",
        unknown_fibers=unknown_fibers,
        headline="No composition data",
        headline_sub="Score cannot be calculated without fiber composition information.",
        watch_for=[],
    )
```

- [ ] **Step 3.5: Run all tests**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_verdict.py scoring/test_extractor.py -v 2>&1 | tail -8
python -m scoring.tests
```

Expected:
- pytest: all 48 tests pass (15 new + 33 extractor)
- `python -m scoring.tests`: `12/12 tests passed`

- [ ] **Step 3.6: Commit**

```bash
git add scoring/engine.py
git commit -m "feat: add headline/headline_sub/watch_for to ScoreResult; wire into score_item()"
```

---

### Task 4: HTML restructure

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 4.1: Replace `card-top` with vertical headline-first structure**

Find the entire `<div class="card-top">` block (lines 147–161) and replace it:

Old block:
```html
        <div class="card-top">
          <div class="score-block">
            <span id="score-number" class="score-number">—</span>
            <div class="score-rule"></div>
            <span class="score-denom">/ 100</span>
          </div>

          <div class="card-top-right">
            <p id="verdict-sentence" class="verdict-sentence"></p>
            <div class="confidence-badge">
              <span id="confidence-label"></span>
              <span id="confidence-note" class="confidence-note"></span>
            </div>
          </div>
        </div>
```

New block:
```html
        <div class="card-top">
          <p id="card-headline" class="card-headline"></p>
          <p id="card-headline-sub" class="card-headline-sub"></p>

          <div id="watch-for-row" class="watch-for-row" hidden>
            <span class="watch-for-label">Watch for:</span>
            <span id="watch-for-items"></span>
          </div>

          <div class="score-line">
            <span id="score-number" class="score-number">—</span>
            <span class="score-sep"> / 100  ·  </span>
            <span id="score-band-label" class="score-band-label"></span>
          </div>

          <div class="confidence-badge">
            <span id="confidence-label"></span>
            <span id="confidence-note" class="confidence-note"></span>
          </div>

          <p id="verdict-sentence" class="verdict-sentence"></p>
        </div>
```

- [ ] **Step 4.2: Add property bars attribution line**

Find:
```html
        <div class="section-header">/PROPERTIES</div>
```

Replace with:
```html
        <div class="section-header">/PROPERTIES</div>
        <p class="properties-attribution">Fiber class averages — ASTM D4970/D5034</p>
```

- [ ] **Step 4.3: Add construction-not-assessed fallback element**

Find:
```html
        <div id="construction-row" class="construction-row" hidden>
```

Insert this block immediately before it:
```html
        <div id="construction-not-assessed" class="construction-not-assessed" hidden>
          <span class="construction-na-label">Construction not assessed</span>
          <p id="construction-floor-note-na" class="construction-floor-note"></p>
        </div>
```

- [ ] **Step 4.4: Rename CPW stat label**

Find:
```html
              <span class="stat-label">Cost per wash</span>
```

Replace with:
```html
              <span class="stat-label">Est. cost per wear</span>
```

- [ ] **Step 4.5: Commit**

```bash
git add templates/index.html
git commit -m "feat: restructure card-top to headline-first; add property attribution and construction fallback HTML"
```

---

### Task 5: JavaScript updates

**Files:**
- Modify: `static/app.js`

- [ ] **Step 5.1: Replace `renderResult()` opening section**

Find `function renderResult(r) {` (line 149). Replace everything from the function opening through the confidence badge block — stopping before `document.getElementById("stat-material")` — with:

```javascript
function renderResult(r) {
  hideAll();
  document.getElementById("result-card").hidden = false;

  const score = Math.round(r.worth_it_score || 0);
  const material = Math.round(r.material_score || 0);
  const props = r.property_scores || {};
  const pp = r.price_pressure || {};
  const cpw = r.cost_per_wash || {};

  // Headline
  document.getElementById("card-headline").textContent = r.headline || "";
  document.getElementById("card-headline-sub").textContent = r.headline_sub || "";

  // Watch for
  const watchItems = r.watch_for || [];
  const watchRow = document.getElementById("watch-for-row");
  if (watchItems.length > 0) {
    document.getElementById("watch-for-items").textContent = watchItems.join("  ·  ");
    watchRow.hidden = false;
  } else {
    watchRow.hidden = true;
  }

  // Score line
  document.getElementById("score-number").textContent = score;
  document.getElementById("score-number").style.color = scoreColor(score);

  const bandLabels = {
    very_low:  "VERY LOW DURABILITY",
    low:       "LOW DURABILITY",
    mid:       "AVERAGE DURABILITY",
    good:      "ABOVE AVERAGE DURABILITY",
    excellent: "STRONG DURABILITY",
  };
  document.getElementById("score-band-label").textContent = bandLabels[r.score_band] || "";

  // Confidence
  const conf = r.confidence || "low";
  const confLabel = document.getElementById("confidence-label");
  confLabel.textContent = `[${conf.toUpperCase()} CONFIDENCE]`;
  confLabel.style.color = conf === "high" ? "var(--green)" : conf === "medium" ? "var(--yellow)" : "var(--red)";
  const notes = r.confidence_notes || [];
  document.getElementById("confidence-note").textContent = notes[notes.length - 1] || "";

  // Verdict sentence (tertiary)
  document.getElementById("verdict-sentence").textContent = r.verdict_sentence || "";
```

Leave the rest of `renderResult()` (stat-material through renderConstruction) unchanged.

- [ ] **Step 5.2: Replace `renderConstruction()` to hide score at price-floor only**

Find `function renderConstruction(c) {` (line 202) and replace the entire function:

```javascript
function renderConstruction(c) {
  const row = document.getElementById("construction-row");
  const notAssessed = document.getElementById("construction-not-assessed");
  const constrHeader = document.querySelector(".section-header-construction");

  if (!c) {
    row.hidden = true;
    notAssessed.hidden = true;
    if (constrHeader) constrHeader.hidden = true;
    return;
  }

  if (constrHeader) constrHeader.hidden = false;

  // Hide numeric score when only price-floor inference — no real signals
  const isPriceFloorOnly =
    c.source === "price_floor" && (!c.signals_found || c.signals_found.length === 0);

  if (isPriceFloorOnly) {
    row.hidden = true;
    notAssessed.hidden = false;
    const noteEl = document.getElementById("construction-floor-note-na");
    if (noteEl && c.price_floor_note) {
      noteEl.textContent = c.price_floor_note;
      noteEl.hidden = false;
    }
    return;
  }

  // Real signals found — show full construction row
  row.hidden = false;
  notAssessed.hidden = true;

  const scoreVal = c.score || 0;
  const scoreEl = document.getElementById("construction-score");
  scoreEl.textContent = `${scoreVal.toFixed(1)} / 10`;
  scoreEl.style.color = scoreColor(scoreVal * 10);

  const bar = document.getElementById("bar-construction");
  bar.style.width = `${scoreVal * 10}%`;
  bar.style.background = scoreColor(scoreVal * 10);

  const noteEl = document.getElementById("construction-floor-note");
  if (c.price_floor_note) {
    noteEl.textContent = c.price_floor_note;
    noteEl.hidden = false;
  } else {
    noteEl.hidden = true;
  }

  const sigList = document.getElementById("construction-signals");
  sigList.innerHTML = "";
  (c.signals_found || []).forEach(sig => {
    const li = document.createElement("li");
    li.textContent = sig;
    sigList.appendChild(li);
  });
}
```

- [ ] **Step 5.3: Add reset cleanup for new elements**

Find `document.getElementById("btn-reset").addEventListener("click", () => {` (line 304). Inside the callback, after the existing `.forEach(id => { ... })` block, add:

```javascript
  document.getElementById("card-headline").textContent = "";
  document.getElementById("card-headline-sub").textContent = "";
  document.getElementById("watch-for-items").textContent = "";
  document.getElementById("watch-for-row").hidden = true;
  document.getElementById("score-number").textContent = "—";
  document.getElementById("score-number").style.color = "";
  document.getElementById("score-band-label").textContent = "";
  document.getElementById("construction-not-assessed").hidden = true;
```

- [ ] **Step 5.4: Commit**

```bash
git add static/app.js
git commit -m "feat: update renderResult() for headline/watch-for; construction hides score at price-floor only"
```

---

### Task 6: CSS additions

**Files:**
- Modify: `static/style.css`

- [ ] **Step 6.1: Update `.card-top` to vertical flex stack**

Find `.card-top {` (around line 278):

```css
.card-top {
  display: flex;
  gap: 24px;
  align-items: center;
  padding: 28px 24px;
  border-bottom: 1px solid var(--border);
}
```

Replace with:

```css
.card-top {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 28px 24px;
  border-bottom: 1px solid var(--border);
}
```

- [ ] **Step 6.2: Shrink `.score-number` from 4rem to 1.6rem**

Find `.score-number {` (around line 294):

```css
.score-number {
  font-size: 4rem;
  font-weight: 700;
  line-height: 1;
  color: var(--score);
  font-variant-numeric: tabular-nums;
}
```

Replace with:

```css
.score-number {
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1;
  color: var(--score);
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 6.3: Update `.verdict-sentence` to tertiary muted style**

Find `.verdict-sentence {` (around line 317):

```css
.verdict-sentence {
  font-size: 1rem;
  line-height: 1.5;
  margin-bottom: 6px;
}
```

Replace with:

```css
.verdict-sentence {
  font-size: 0.8rem;
  color: var(--muted);
  line-height: 1.5;
  margin-top: 10px;
  margin-bottom: 0;
}
```

- [ ] **Step 6.4: Add new styles for headline system and layer differentiation**

After the `.confidence-note` rule (around line 340), insert:

```css
/* ── Headline system ─────────────────────────────────────────────────────── */
.card-headline {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.2;
  color: var(--text);
  margin-bottom: 6px;
}

.card-headline-sub {
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.5;
  margin-bottom: 16px;
}

.watch-for-row {
  margin-bottom: 14px;
  font-size: 0.78rem;
  line-height: 1.5;
}

.watch-for-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-weight: 700;
  margin-right: 4px;
}

.score-line {
  display: flex;
  align-items: baseline;
  gap: 0;
  margin-bottom: 10px;
}

.score-sep {
  font-size: 0.82rem;
  color: var(--muted);
}

.score-band-label {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}

/* ── Property bars attribution ────────────────────────────────────────────── */
.properties-attribution {
  padding: 4px 24px 10px;
  font-size: 0.65rem;
  color: var(--muted);
  font-style: italic;
  letter-spacing: 0.02em;
}

/* ── Construction not assessed ───────────────────────────────────────────── */
.construction-not-assessed {
  padding: 12px 24px;
  border-top: 1px solid var(--border);
}

.construction-na-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  font-style: italic;
}
```

- [ ] **Step 6.5: Run tests and commit**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_verdict.py scoring/test_extractor.py -v 2>&1 | tail -5
```

Expected: all tests pass.

```bash
git add static/style.css
git commit -m "feat: add headline card CSS — vertical stack, demoted score, watch-for, attribution, construction fallback"
```

---

### Task 7: End-to-end verification

**Files:** None modified.

- [ ] **Step 7.1: Run all automated tests**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_verdict.py scoring/test_extractor.py -v 2>&1 | tail -8
python -m scoring.tests
```

Expected:
- pytest: 48 tests pass (15 new + 33 extractor)
- `python -m scoring.tests`: `12/12 tests passed`

- [ ] **Step 7.2: Start server**

```bash
python app.py
```

Navigate to `http://localhost:5000`.

- [ ] **Step 7.3: Spot-check — 100% silk dress at $340**

Use the "Enter manually" tab:
- Composition: `100% silk`
- Price: `340`
- Category: `Dress / skirt`

Expected:
- Headline: `Built for feel, not longevity`
- Sub-line: `Fine fibers like silk prioritize softness and drape over durability.`
- Watch for: includes `Snagging, delicate handling required` and `High care cost relative to expected lifespan`
- Score line: `{score} / 100  ·  LOW DURABILITY` (score number is orange, rest muted)
- `/CONSTRUCTION` section: shows "Construction not assessed" + price floor note (no numeric score)
- CPW stat label reads `Est. cost per wear`
- Property bars: `Fiber class averages — ASTM D4970/D5034` appears below `/PROPERTIES`

- [ ] **Step 7.4: Spot-check — 100% acrylic sweater at $50**

- Composition: `100% acrylic`
- Price: `50`
- Category: `Sweater / knitwear`

Expected:
- Headline: `Weak durability, fair price` or `Below-average durability, fair price` (low band + low pressure)
- Watch for: includes `Heavy pilling within 1–2 seasons`
- Score line: `{score} / 100  ·  LOW DURABILITY` or `VERY LOW DURABILITY`
- No premium override fires

- [ ] **Step 7.5: Spot-check — 80% polyester / 20% elastane activewear at $85**

- Composition: `80% polyester, 20% elastane`
- Price: `85`
- Category: `Activewear`

Expected:
- Headline from mid or good band (polyester is strong)
- Watch for: empty or minimal (no weak properties for polyester)
- No premium override
- CPW label: `Est. cost per wear`
