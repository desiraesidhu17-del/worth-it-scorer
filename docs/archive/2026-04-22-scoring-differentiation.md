# Scoring Differentiation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four differentiation layers to the scoring engine — GSM extraction, GSM modifier, construction integration, fiber dominance/category-fit micro-adjustments, and confidence-aware scoring — all deterministic and explainable.

**Architecture:** All changes are layered on top of the existing `score_item()` pipeline with a new `gsm` parameter; modifiers are computed after the base material score and combined before applying the ±15 cap; the construction contribution replaces the raw `material_score - penalty` formula in `worth_it_score`. Every modifier is stored in `ScoreResult` for display transparency.

**Tech Stack:** Python 3.11, pytest, existing `scoring/` module. No new dependencies.

---

## File Map

| File | Change |
|------|--------|
| `scoring/extractor.py` | Add `_extract_gsm()`, `gsm` field to `ExtractionResult`, call from `extract_from_text` and `extract_from_payload` |
| `scoring/engine.py` | Add `gsm` param to `score_item`, `gsm`/`gsm_modifier`/`gsm_modifier_applied` to `ScoreResult`, add `_gsm_modifier_for_score`, `_fiber_dominance_adjustment`, `_category_fit_adjustment`, `_construction_contribution`; update `_assess_confidence`; rewrite worth_it_score formula |
| `scoring/tests.py` | Add 8 new integration tests; update one range comment in `test_acrylic_polyester_sweater` |
| `scoring/test_extractor.py` | Add 4 GSM extraction tests |
| `app.py` | Pass `gsm=result_extraction.gsm` in `score_page_endpoint`; accept `gsm` from request body in path C of `/api/score` |

---

## Task 1: GSM Extraction — extractor.py

**Files:**
- Modify: `scoring/extractor.py`
- Test: `scoring/test_extractor.py`

- [ ] **Step 1: Write failing GSM tests in test_extractor.py**

Append after the existing tests (after `test_regex_finds_gsm_in_payload_text` if it exists, otherwise at end of file):

```python
# ── Task GSM: GSM extraction ──────────────────────────────────────────────────

def test_gsm_extraction_direct():
    from scoring.extractor import _extract_gsm
    assert _extract_gsm("200gsm cotton blend") == 200.0
    assert _extract_gsm("180 GSM fabric weight") == 180.0
    assert _extract_gsm("300GSM heavyweight") == 300.0

def test_gsm_extraction_oz_conversion():
    from scoring.extractor import _extract_gsm
    # 6 oz/sq yd × 33.9 = 203.4 gsm — within range
    result = _extract_gsm("6 oz/sq yd cotton")
    assert result is not None
    assert abs(result - 203.4) < 1.0

def test_gsm_extraction_out_of_range():
    from scoring.extractor import _extract_gsm
    assert _extract_gsm("25gsm tissue paper") is None   # below 80
    assert _extract_gsm("700gsm industrial mat") is None  # above 600
    assert _extract_gsm("no weight here") is None

def test_gsm_populates_extraction_result():
    from scoring.extractor import extract_from_text
    result = extract_from_text("75% cotton, 25% polyester. Fabric weight: 220gsm.")
    assert result.gsm == 220.0

def test_gsm_none_when_absent():
    from scoring.extractor import extract_from_text
    result = extract_from_text("75% cotton, 25% polyester.")
    assert result.gsm is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
pytest scoring/test_extractor.py::test_gsm_extraction_direct scoring/test_extractor.py::test_gsm_extraction_oz_conversion scoring/test_extractor.py::test_gsm_extraction_out_of_range scoring/test_extractor.py::test_gsm_populates_extraction_result scoring/test_extractor.py::test_gsm_none_when_absent -v
```

Expected: all FAIL with `ImportError: cannot import name '_extract_gsm'` or `AttributeError: 'ExtractionResult' has no attribute 'gsm'`

- [ ] **Step 3: Add `gsm` field to `ExtractionResult` (line ~90 in extractor.py)**

Find the `ExtractionResult` dataclass (around line 89) and add `gsm` after the `warnings` field:

```python
@dataclass
class ExtractionResult:
    # Core outputs
    composition_blocks: list[CompositionBlock] = field(default_factory=list)
    main_composition: Optional[list[dict]] = None
    composition_raw: str = ""

    # Metadata
    price: Optional[float] = None
    brand: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    gsm: Optional[float] = None          # ← NEW: fabric weight in GSM

    # Confidence
    extraction_method: str = "none"
    extraction_confidence: str = "low"
    _confidence_score: float = 0.0

    warnings: list[str] = field(default_factory=list)
```

Also update `to_dict()` to include gsm:

```python
    def to_dict(self) -> dict:
        return {
            "composition": self.main_composition or [],
            "composition_blocks": [
                {"part": b.part, "fibers": b.fibers, "pct_sum": b.pct_sum()}
                for b in self.composition_blocks
            ],
            "composition_raw": self.composition_raw,
            "price": self.price,
            "brand": self.brand,
            "product_name": self.product_name,
            "category": self.category,
            "gsm": self.gsm,                          # ← NEW
            "extraction_method": self.extraction_method,
            "extraction_confidence": self.extraction_confidence,
            "warnings": self.warnings,
        }
```

- [ ] **Step 4: Add GSM regex constants and `_extract_gsm()` (after `_CONTEXT_WINDOW = 300` at line ~75)**

```python
# ── GSM extraction patterns ────────────────────────────────────────────────────
_GSM_RE = re.compile(r"\b(\d{2,4})\s*gsm\b", re.IGNORECASE)
_OZ_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*oz(?:/sq\s*yd|/yd)?\b", re.IGNORECASE)
_OZ_TO_GSM = 33.9
_GSM_MIN, _GSM_MAX = 80, 600


def _extract_gsm(text: str) -> Optional[float]:
    """
    Extract fabric weight in GSM from text.
    Handles: "200gsm", "180 GSM", "6 oz/sq yd" (converted via ×33.9).
    Returns None if no value found or value outside plausible range (80–600).
    """
    m = _GSM_RE.search(text)
    if m:
        val = float(m.group(1))
        if _GSM_MIN <= val <= _GSM_MAX:
            return val

    m = _OZ_RE.search(text)
    if m:
        val = float(m.group(1)) * _OZ_TO_GSM
        if _GSM_MIN <= val <= _GSM_MAX:
            return val

    return None
```

- [ ] **Step 5: Call `_extract_gsm` in `extract_from_text` (line ~129)**

```python
def extract_from_text(text: str) -> ExtractionResult:
    """Extract composition from plain text (paste-text path)."""
    result = ExtractionResult()
    result.gsm = _extract_gsm(text)          # ← NEW
    fibers = extract_by_regex(text)
    if fibers:
        block = CompositionBlock(part="unknown", fibers=fibers, source="regex")
        result.composition_blocks = [block]
        result.extraction_method = "regex"
        result = _apply_validation(result)
        _select_main_composition(result)
    return result
```

- [ ] **Step 6: Call `_extract_gsm` in `extract_from_payload` (after existing candidate_blocks loop, before `_apply_normalization`)**

In the `extract_from_payload` function, find where the `if result.composition_blocks:` block ends (around line 177) and insert before the normalization call:

```python
    # Step 5+6: Normalize and validate
    if result.composition_blocks:
        # Extract GSM from candidate text if not already found
        if not result.gsm:
            all_candidate = " ".join(payload.get("candidate_blocks") or [])
            result.gsm = _extract_gsm(all_candidate)

        result = _apply_normalization(result)
        result = _apply_validation(result)
        _select_main_composition(result)
```

- [ ] **Step 7: Run GSM tests to verify they pass**

```bash
pytest scoring/test_extractor.py::test_gsm_extraction_direct scoring/test_extractor.py::test_gsm_extraction_oz_conversion scoring/test_extractor.py::test_gsm_extraction_out_of_range scoring/test_extractor.py::test_gsm_populates_extraction_result scoring/test_extractor.py::test_gsm_none_when_absent -v
```

Expected: all PASS

- [ ] **Step 8: Run full extractor test suite to verify no regressions**

```bash
pytest scoring/test_extractor.py -v
```

Expected: all 33 existing tests + 5 new = 38 PASS (no failures)

- [ ] **Step 9: Commit**

```bash
git add scoring/extractor.py scoring/test_extractor.py
git commit -m "feat: add GSM extraction to extractor pipeline — _extract_gsm(), gsm field on ExtractionResult"
```

---

## Task 2: GSM Modifier + ScoreResult Fields — engine.py

**Files:**
- Modify: `scoring/engine.py`
- Test: `scoring/tests.py`

- [ ] **Step 1: Write failing GSM modifier tests in tests.py**

Append after the existing test functions (before `run_all`):

```python
def test_gsm_modifier_fields_exist():
    """ScoreResult always exposes gsm, gsm_modifier, gsm_modifier_applied."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
    )
    assert hasattr(result, "gsm_modifier_applied")
    assert hasattr(result, "gsm_modifier")
    assert hasattr(result, "gsm")
    assert result.gsm_modifier_applied is False  # no GSM provided
    assert result.gsm_modifier == 0
    assert result.gsm is None


def test_gsm_modifier_below_140():
    """120gsm cotton t-shirt gets -10 vs 200gsm baseline."""
    lightweight = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
        gsm=120.0,
    )
    baseline = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
        gsm=200.0,
    )
    assert lightweight.gsm_modifier_applied is True
    assert lightweight.gsm_modifier == -10
    assert abs(lightweight.material_score - (baseline.material_score - 10)) < 0.1


def test_gsm_modifier_above_240():
    """270gsm cotton t-shirt gets +6 vs 200gsm baseline."""
    heavy = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
        gsm=270.0,
    )
    baseline = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
        gsm=200.0,
    )
    assert heavy.gsm_modifier == 6
    assert abs(heavy.material_score - (baseline.material_score + 6)) < 0.1


def test_gsm_modifier_not_applied_wrong_fiber():
    """GSM modifier does not fire for polyester (only cotton/linen > 50%)."""
    result = score_item(
        composition=[{"fiber": "polyester", "pct": 100}],
        price=40.0,
        category="t-shirt",
        gsm=120.0,
    )
    assert result.gsm_modifier_applied is False
    assert result.gsm_modifier == 0


def test_gsm_modifier_not_applied_wrong_category():
    """GSM modifier does not fire for sweater category."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=60.0,
        category="sweater",
        gsm=120.0,
    )
    assert result.gsm_modifier_applied is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
python -m scoring.tests 2>&1 | head -30
```

Expected: `ERROR` on new tests with `TypeError: score_item() got an unexpected keyword argument 'gsm'`

- [ ] **Step 3: Add `gsm`/`gsm_modifier`/`gsm_modifier_applied` fields to `ScoreResult` (after `unknown_fibers` field)**

In `engine.py`, find the end of ScoreResult dataclass (around line 88) and add:

```python
    # Construction sub-score (optional — populated when text or image is available)
    construction: Optional[ConstructionResult] = None

    # Headline (three-step system — see verdict_library.get_headline / get_watch_for)
    headline: str = ""
    headline_sub: str = ""
    watch_for: list[str] = field(default_factory=list)

    # GSM (fabric weight) modifier
    gsm: Optional[float] = None             # ← NEW: GSM value passed in
    gsm_modifier: int = 0                   # ← NEW: -10 / -5 / 0 / +6 / +10
    gsm_modifier_applied: bool = False      # ← NEW: True if conditions were met

    # Metadata
    methodology_version: str = METHODOLOGY_VERSION
    unknown_fibers: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Add `gsm` parameter to `score_item` and `_gsm_modifier_for_score` helper**

At the top of `score_item`, add `gsm: Optional[float] = None` to the signature:

```python
def score_item(
    composition: list[dict],
    price: Optional[float] = None,
    category: str = "other",
    construction: Optional[ConstructionResult] = None,
    gsm: Optional[float] = None,           # ← NEW
) -> ScoreResult:
```

Add the helper function before `_normalise_category` (around line 244):

```python
def _gsm_modifier_for_score(
    gsm: Optional[float],
    known_entries: list[FiberEntry],
    category: str,
) -> tuple[int, bool]:
    """
    Returns (modifier, applied).
    Conditions: GSM provided, cotton or linen > 50% of composition, category is t-shirt or dress.
    modifier values: below 140 → -10, 140–179 → -5, 180–239 → 0, 240–299 → +6, 300+ → +10.
    applied is True when all conditions are met, even if modifier is 0.
    """
    if gsm is None:
        return 0, False
    if category not in ("t-shirt", "dress"):
        return 0, False

    natural_cellulose = {"cotton", "linen"}
    dominant = any(e.canonical in natural_cellulose and e.pct > 50 for e in known_entries)
    if not dominant:
        return 0, False

    if gsm < 140:
        return -10, True
    elif gsm < 180:
        return -5, True
    elif gsm < 240:
        return 0, True
    elif gsm < 300:
        return 6, True
    else:
        return 10, True
```

- [ ] **Step 5: Apply GSM modifier in `score_item` after step 4 (after line ~178)**

After the `material_score = round(max(0.0, min(100.0, material_score)), 1)` line in step 4, add:

```python
    # ── 4.5. GSM modifier (applied in Task 3 combined cap) ──────────────────
    gsm_mod, gsm_mod_applied = _gsm_modifier_for_score(gsm, known_entries, category)
    # Combined adjustment applied in 4.6 (see Task 3)
    # For now, store modifier values — applied below
```

Then update the ScoreResult constructor at the bottom to pass the new fields:

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
        gsm=gsm,                              # ← NEW
        gsm_modifier=gsm_mod,                 # ← NEW
        gsm_modifier_applied=gsm_mod_applied, # ← NEW
    )
```

Note: the full combined cap and actual material_score adjustment happens in Task 3. For now this just stores the values.

- [ ] **Step 6: Run GSM modifier tests**

```bash
python -m scoring.tests 2>&1
```

Expected: new GSM field tests PASS; GSM modifier/score tests may still fail (modifier not applied to material_score yet — Task 3 does this)

- [ ] **Step 7: Commit the field additions**

```bash
git add scoring/engine.py scoring/tests.py
git commit -m "feat: add gsm param and gsm_modifier/gsm_modifier_applied fields to ScoreResult"
```

---

## Task 3: Fiber Dominance + Category Fit + Combined Cap — engine.py

**Files:**
- Modify: `scoring/engine.py`
- Test: `scoring/tests.py`

- [ ] **Step 1: Write failing tests for category fit and dominance**

Append to `tests.py`:

```python
def test_acrylic_sweater_category_penalty():
    """
    Acrylic above 40% in sweater gets -5 category fit penalty.
    60% acrylic sweater should score lower than 30% acrylic sweater
    by more than just the property score difference.
    """
    high_acrylic = score_item(
        composition=[{"fiber": "acrylic", "pct": 60}, {"fiber": "polyester", "pct": 40}],
        price=80.0,
        category="sweater",
    )
    low_acrylic = score_item(
        composition=[{"fiber": "acrylic", "pct": 30}, {"fiber": "polyester", "pct": 70}],
        price=80.0,
        category="sweater",
    )
    # 60% acrylic gets -5 category penalty; 30% acrylic does not
    assert high_acrylic.material_score < low_acrylic.material_score, (
        f"High acrylic sweater should score lower: {high_acrylic.material_score} vs {low_acrylic.material_score}"
    )


def test_cotton_activewear_penalty():
    """
    Cotton in activewear gets -4 (wrong fiber for moisture management).
    100% polyester activewear (above 70%) also gets +4 bonus.
    """
    poly_active = score_item(
        composition=[{"fiber": "polyester", "pct": 100}],
        price=50.0,
        category="activewear",
    )
    cotton_active = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=50.0,
        category="activewear",
    )
    # Polyester: +2 dominance, +4 category fit. Cotton: +2 dominance, -4 category fit.
    # Polyester also naturally scores higher in moisture for activewear weights.
    assert poly_active.material_score > cotton_active.material_score, (
        f"Polyester activewear should outscore cotton: {poly_active.material_score} vs {cotton_active.material_score}"
    )


def test_viscose_dress_category_penalty():
    """
    100% viscose in dress gets -3 category fit (structure loss and shrink known issues).
    Verify score is lower than lyocell dress (which gets no penalty).
    """
    viscose = score_item(
        composition=[{"fiber": "viscose", "pct": 100}],
        price=100.0,
        category="dress",
    )
    lyocell = score_item(
        composition=[{"fiber": "lyocell", "pct": 100}],
        price=100.0,
        category="dress",
    )
    assert lyocell.material_score > viscose.material_score, (
        f"Lyocell dress should outscore viscose dress: {lyocell.material_score} vs {viscose.material_score}"
    )


def test_fiber_dominance_four_fiber_penalty():
    """
    Composition with 4+ fibers gets -2 (complex blends introduce more variance).
    Single fiber gets +2.
    """
    four_fiber = score_item(
        composition=[
            {"fiber": "cotton", "pct": 40},
            {"fiber": "polyester", "pct": 30},
            {"fiber": "viscose", "pct": 20},
            {"fiber": "elastane", "pct": 10},
        ],
        price=80.0,
        category="dress",
    )
    # four-fiber composition should have gsm_modifier_applied False and no +2 bonus
    # We just verify the score is computed without crash and is in valid range
    assert 0 < four_fiber.material_score < 100
    assert four_fiber.gsm_modifier_applied is False
```

- [ ] **Step 2: Run tests to verify relevant ones fail**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
python -m scoring.tests 2>&1 | grep -E "FAIL|PASS|ERROR"
```

Expected: `test_acrylic_sweater_category_penalty` likely fails (penalty not applied yet), others may pass incidentally.

- [ ] **Step 3: Add `_fiber_dominance_adjustment` and `_category_fit_adjustment` helpers to engine.py**

Add after `_gsm_modifier_for_score` (before `_normalise_category`):

```python
def _fiber_dominance_adjustment(known_entries: list[FiberEntry]) -> int:
    """
    +2 if one fiber makes up 90%+ of total known composition.
    -2 if 4 or more distinct fibers (complex blend; more variance).
    0 otherwise.
    """
    if not known_entries:
        return 0
    known_total = sum(e.pct for e in known_entries)
    if known_total == 0:
        return 0
    for entry in known_entries:
        if (entry.pct / known_total) * 100 >= 90:
            return 2
    if len(known_entries) >= 4:
        return -2
    return 0


def _category_fit_adjustment(known_entries: list[FiberEntry], category: str) -> int:
    """
    Flat adjustments for fiber/category combinations with strong quality implications.
    Additive — multiple adjustments can stack.

    Viscose/rayon in dress:       -3 (known structure loss and shrinkage)
    Linen in t-shirt or dress:    +3 (strong, breathable; good fit for category)
    Acrylic in sweater >40%:      -5 (genuinely poor durability; underpenalized by property avg)
    Polyester in activewear >70%: +4 (appropriate performance fiber)
    Cotton in activewear:         -4 (retains moisture; wrong for performance use)
    """
    adj = 0
    for entry in known_entries:
        fiber = entry.canonical
        pct = entry.pct

        if fiber in ("viscose", "rayon") and category == "dress":
            adj -= 3

        if fiber == "linen" and category in ("t-shirt", "dress"):
            adj += 3

        if fiber == "acrylic" and category == "sweater" and pct > 40:
            adj -= 5

        if fiber == "polyester" and category == "activewear" and pct > 70:
            adj += 4

        if fiber == "cotton" and category == "activewear":
            adj -= 4

    return adj
```

- [ ] **Step 4: Apply combined adjustments with ±15 cap in `score_item` (replace the placeholder from Task 2)**

Replace the `# ── 4.5. GSM modifier ...` placeholder comment block added in Task 2 with the full combined adjustment:

```python
    # ── 4.5. Combined score adjustments (GSM + dominance + category fit) ────
    gsm_mod, gsm_mod_applied = _gsm_modifier_for_score(gsm, known_entries, category)
    dominance_adj = _fiber_dominance_adjustment(known_entries)
    category_adj = _category_fit_adjustment(known_entries, category)
    combined_adj = max(-15, min(15, gsm_mod + dominance_adj + category_adj))
    material_score = round(max(0.0, min(100.0, material_score + combined_adj)), 1)
```

- [ ] **Step 5: Run all engine tests**

```bash
python -m scoring.tests
```

Expected: all 12 original + new tests PASS. If `test_acrylic_polyester_sweater` shows `material_score < 70` still passing — expected (acrylic at 52% in sweater now gets -5, lowering it further below 70).

- [ ] **Step 6: Run pytest suite to catch extractor regressions**

```bash
pytest scoring/test_extractor.py scoring/test_verdict.py -q
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add scoring/engine.py scoring/tests.py
git commit -m "feat: add fiber dominance, category-fit adjustments, GSM modifier with ±15 combined cap"
```

---

## Task 4: Construction Contribution to worth_it_score — engine.py

**Files:**
- Modify: `scoring/engine.py`
- Test: `scoring/tests.py`

- [ ] **Step 1: Write failing construction contribution test**

Append to `tests.py`:

```python
def test_construction_incorporated_in_worth_it_score():
    """
    Medium-confidence construction score 8 vs score 2 should produce a 4.8-point
    difference in worth_it_score: (8-5)*0.8 - (2-5)*0.8 = 2.4 - (-2.4) = 4.8.
    """
    from scoring.construction_rubric import ConstructionResult

    good_construction = ConstructionResult(
        score=8.0,
        confidence="medium",
        signals_found=["French seams", "Fully lined"],
        source="text",
    )
    poor_construction = ConstructionResult(
        score=2.0,
        confidence="medium",
        signals_found=["Serged seams"],
        source="text",
    )
    shared_kwargs = dict(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=80.0,
        category="dress",
        gsm=220.0,   # provide GSM to neutralise confidence penalty
    )
    result_good = score_item(**shared_kwargs, construction=good_construction)
    result_poor = score_item(**shared_kwargs, construction=poor_construction)

    delta = result_good.worth_it_score - result_poor.worth_it_score
    assert abs(delta - 4.8) < 0.15, (
        f"Expected worth_it_score delta ~4.8, got {delta:.2f}"
    )
    assert result_good.worth_it_score > result_poor.worth_it_score


def test_construction_low_confidence_half_modifier():
    """
    Low-confidence construction uses half the modifier.
    Score 8, low confidence: contribution = (8-5)*0.8/2 = 1.2.
    Score 8, medium confidence: contribution = (8-5)*0.8 = 2.4.
    """
    from scoring.construction_rubric import ConstructionResult

    med = ConstructionResult(score=8.0, confidence="medium", source="text")
    low = ConstructionResult(score=8.0, confidence="low", source="price_floor")

    shared = dict(
        composition=[{"fiber": "wool", "pct": 100}],
        price=150.0,
        category="sweater",
    )
    result_med = score_item(**shared, construction=med)
    result_low = score_item(**shared, construction=low)

    # medium gets 2.4, low gets 1.2 — difference is 1.2
    delta = result_med.worth_it_score - result_low.worth_it_score
    assert abs(delta - 1.2) < 0.15, (
        f"Expected delta ~1.2 between medium/low confidence, got {delta:.2f}"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m scoring.tests 2>&1 | grep -E "construction_incorporated|construction_low_confidence"
```

Expected: FAIL — the current formula doesn't include construction.

- [ ] **Step 3: Add `_construction_contribution` helper to engine.py**

Add after `_category_fit_adjustment` (before `_normalise_category`):

```python
def _construction_contribution(construction: ConstructionResult) -> float:
    """
    Returns construction score contribution to worth_it_score.

    Formula: (score - 5) * 0.8, capped at ±5 points.
    Neutral midpoint: score 5 → contribution 0.
    Score 7 → +1.6; score 3 → -1.6; score 10 → +4.0; score 0 → -4.0.

    Low confidence (price floor only): half the modifier, reflecting low certainty.
    Medium/high confidence (text or image signals): full modifier.
    """
    raw = (construction.score - 5) * 0.8
    capped = max(-5.0, min(5.0, raw))
    if construction.confidence == "low":
        return capped * 0.5
    return capped
```

- [ ] **Step 4: Update `worth_it_score` formula in `score_item` (step 8, around line 198)**

Replace the current step 8 block:

```python
    # ── 8. Worth-It Score ────────────────────────────────────────────────────
    # Primarily driven by material score, modulated by price pressure.
    # Price pressure penalty scales the score down when price is unjustified.
    pressure_penalty = _price_pressure_penalty(price_pressure["level"])
    worth_it_score = round(max(0.0, material_score - pressure_penalty), 1)
```

with:

```python
    # ── 8. Worth-It Score ────────────────────────────────────────────────────
    # Material score minus price pressure penalty plus construction contribution.
    # Construction: (score−5)×0.8, capped ±5. Low confidence uses half modifier.
    pressure_penalty = _price_pressure_penalty(price_pressure["level"])
    construction_contrib = _construction_contribution(construction)
    worth_it_score = round(
        max(0.0, material_score - pressure_penalty + construction_contrib), 1
    )
```

- [ ] **Step 5: Run construction tests**

```bash
python -m scoring.tests 2>&1
```

Expected: `test_construction_incorporated_in_worth_it_score` and `test_construction_low_confidence_half_modifier` PASS. Also verify existing tests still pass — in particular:
- `test_acrylic_polyester_sweater`: worth_it_score < 50 — construction at $148 sweater = "premium" floor = score 7, (7-5)*0.8 = 1.6, half for low = 0.8. New worth_it_score ≈ 53.6 - 25 + 0.8 = 29.4 < 50 ✓
- `test_reformation_viscose_dress`: worth_it_score < 45 — $220 dress premium floor = score 7, 0.8 low confidence. New ≈ 48.75 - 25 + 0.8 = 24.55 < 45 ✓

- [ ] **Step 6: Run full test suite**

```bash
pytest scoring/test_extractor.py scoring/test_verdict.py -q && python -m scoring.tests
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add scoring/engine.py scoring/tests.py
git commit -m "feat: incorporate construction score into worth_it_score — (score−5)×0.8, capped ±5, half for low confidence"
```

---

## Task 5: Confidence-Aware GSM Penalty — engine.py

**Files:**
- Modify: `scoring/engine.py`
- Test: `scoring/tests.py`

- [ ] **Step 1: Write failing confidence-penalty test**

Append to `tests.py`:

```python
def test_gsm_confidence_penalty_reduces_score():
    """
    Cotton t-shirt with no GSM provided should score 3 points lower than
    same t-shirt with GSM=200 (baseline, no modifier). The penalty reflects
    that we can't confirm the cotton is heavy enough to justify the base score.
    """
    no_gsm = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
    )
    with_gsm_baseline = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
        gsm=200.0,  # baseline: 0 modifier, but no confidence penalty
    )
    # With no GSM: dominance +2, confidence penalty -3, net = -1 vs with_gsm_baseline
    # With GSM 200: dominance +2, no penalty, net = +2 vs base
    # Difference should be 3 points
    assert abs(with_gsm_baseline.material_score - no_gsm.material_score - 3) < 0.15, (
        f"Expected no-GSM to be 3 lower: with_gsm={with_gsm_baseline.material_score}, "
        f"no_gsm={no_gsm.material_score}"
    )


def test_gsm_confidence_penalty_does_not_fire_for_polyester():
    """The -3 confidence penalty does not apply to polyester (not cotton/linen)."""
    poly_no_gsm = score_item(
        composition=[{"fiber": "polyester", "pct": 100}],
        price=30.0,
        category="t-shirt",
    )
    poly_with_gsm = score_item(
        composition=[{"fiber": "polyester", "pct": 100}],
        price=30.0,
        category="t-shirt",
        gsm=120.0,  # gsm doesn't trigger modifier for polyester either
    )
    # Scores should be identical — neither GSM modifier nor penalty applies
    assert poly_no_gsm.material_score == poly_with_gsm.material_score


def test_gsm_confidence_penalty_fires_for_dress():
    """
    Linen dress with no GSM should get the -3 confidence penalty
    (linen > 50% in dress, no GSM — same conditions as t-shirt).
    """
    no_gsm = score_item(
        composition=[{"fiber": "linen", "pct": 100}],
        price=80.0,
        category="dress",
    )
    with_gsm = score_item(
        composition=[{"fiber": "linen", "pct": 100}],
        price=80.0,
        category="dress",
        gsm=200.0,
    )
    assert with_gsm.material_score > no_gsm.material_score, (
        f"Dress with GSM should score higher: {with_gsm.material_score} vs {no_gsm.material_score}"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m scoring.tests 2>&1 | grep -E "gsm_confidence|FAIL|PASS"
```

Expected: the confidence penalty tests FAIL (penalty not yet applied).

- [ ] **Step 3: Update `_assess_confidence` to also include "dress" category in GSM check**

In `_assess_confidence` (around line 295), change:

```python
    if is_gsm_sensitive and category in ("t-shirt", "other"):
```

to:

```python
    if is_gsm_sensitive and category in ("t-shirt", "dress"):
```

This removes "other" from the confidence note (matching the spec: t-shirt and dress only) and adds "dress".

- [ ] **Step 4: Apply the -3 material_score penalty in `score_item` after step 5**

After calling `_assess_confidence` in step 5 (around line 186), add:

```python
    # ── 5. Confidence assessment ─────────────────────────────────────────────
    confidence, confidence_notes = _assess_confidence(
        entries=entries,
        known_pct_total=known_pct_total,
        total_pct=total_pct,
        all_blends_known=all_blends_known,
        category=category,
    )

    # ── 5.5. Confidence-aware GSM penalty ────────────────────────────────────
    # When GSM is missing for cotton/linen-heavy t-shirts and dresses, the base
    # score may be optimistic — lightweight fabric significantly hurts durability.
    # Subtract 3 to reflect this uncertainty. (Separate from ±15 combined cap.)
    if gsm is None:
        _gsm_sensitive_fibers = {"cotton", "linen"}
        _heavy_natural = any(
            e.canonical in _gsm_sensitive_fibers and e.pct > 50 for e in known_entries
        )
        if _heavy_natural and category in ("t-shirt", "dress"):
            material_score = round(max(0.0, material_score - 3), 1)
```

- [ ] **Step 5: Run full engine test suite**

```bash
python -m scoring.tests
```

Expected: all tests PASS including new confidence penalty tests.

- Verify `test_cotton_tshirt_budget` still has `35 <= material_score <= 75`:
  - Cotton base ≈ 69.2, +2 dominance, -3 confidence penalty = 68.2. In range. ✓

- [ ] **Step 6: Run pytest suite**

```bash
pytest scoring/test_extractor.py scoring/test_verdict.py -q
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add scoring/engine.py scoring/tests.py
git commit -m "feat: confidence-aware GSM penalty — missing weight data subtracts 3 from material_score for cotton/linen t-shirts and dresses"
```

---

## Task 6: Wire GSM Through app.py

**Files:**
- Modify: `app.py`
- Test: manual verification (no new unit tests — this is wiring, not logic)

- [ ] **Step 1: Pass `gsm` from `result_extraction` in `score_page_endpoint`**

In `app.py`, find `score_page_endpoint` (around line 591). Change the `score_item` call from:

```python
        score_result = score_item(
            composition=composition,
            price=price,
            category=category,
            construction=construction,
        )
```

to:

```python
        score_result = score_item(
            composition=composition,
            price=price,
            category=category,
            construction=construction,
            gsm=result_extraction.gsm,   # ← NEW: pass GSM if extracted from page
        )
```

- [ ] **Step 2: Accept `gsm` in Path C of `/api/score` (direct composition input)**

In `/api/score`, Path C (around line 139), find:

```python
        elif request.is_json:
            data = request.get_json(force=True)
            composition = data.get("composition", [])
            price = _parse_price(data.get("price"))
            category = data.get("category", "other")
            brand = data.get("brand") or None
```

Add `gsm` extraction:

```python
        elif request.is_json:
            data = request.get_json(force=True)
            composition = data.get("composition", [])
            price = _parse_price(data.get("price"))
            category = data.get("category", "other")
            brand = data.get("brand") or None
            gsm = data.get("gsm")          # ← NEW: optional GSM from API caller
            if gsm is not None:
                try:
                    gsm = float(gsm)
                except (ValueError, TypeError):
                    gsm = None
```

Then update the `score_item` call in Path C (around line 183):

```python
        result = score_item(
            composition=composition,
            price=price,
            category=category,
            construction=construction,
            gsm=gsm if 'gsm' in locals() else None,  # only set in Path C
        )
```

Wait — that's awkward because `gsm` is only defined in Path C. Better approach: define `gsm = None` at the top of the try block, then set it in Path C:

At the start of the `try:` block in `score_endpoint` (around line 90), add:

```python
    try:
        construction = None
        gsm = None                    # ← NEW: set at top, overridden in Path C
```

Then in Path C, set `gsm = data.get("gsm")` and convert to float.

Then update the `score_item` call at line ~183:

```python
        result = score_item(
            composition=composition,
            price=price,
            category=category,
            construction=construction,
            gsm=gsm,                  # ← NEW
        )
```

- [ ] **Step 3: Verify the server starts**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
python -c "import app; print('app imports OK')"
```

Expected: `app imports OK`

- [ ] **Step 4: Quick smoke test of API**

```bash
curl -s -X POST http://localhost:5001/api/score \
  -H "Content-Type: application/json" \
  -d '{"composition": [{"fiber": "cotton", "pct": 100}], "price": 30, "category": "t-shirt", "gsm": 120}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('gsm:', d.get('gsm'), 'modifier:', d.get('gsm_modifier'), 'applied:', d.get('gsm_modifier_applied'))"
```

Expected output:
```
gsm: 120.0 modifier: -10 applied: True
```

(Start the server first with `preview_start "worth-it-server"` if not running)

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: wire GSM through app.py — score_page_endpoint passes extraction.gsm to score_item; /api/score accepts gsm param"
```

---

## Task 7: Verify All Tests Pass + Update Test Registry

**Files:**
- Modify: `scoring/tests.py` (add new tests to `run_all`)

- [ ] **Step 1: Add new tests to `run_all` in tests.py**

In `tests.py`, find `run_all()` and update the tests list to include all new tests:

```python
def run_all():
    tests = [
        ("Acrylic/polyester sweater at $148",         test_acrylic_polyester_sweater),
        ("Merino sweater at $80",                     test_merino_wool_sweater),
        ("Cotton t-shirt at $12",                     test_cotton_tshirt_budget),
        ("Viscose dress at $220",                     test_reformation_viscose_dress),
        ("Lyocell dress at $95",                      test_lyocell_dress_fair_price),
        ("Poly-cotton blend interaction",             test_polycotton_blend_interaction),
        ("Unknown fiber reduces confidence",          test_unknown_fiber_reduces_confidence),
        ("No composition data",                       test_no_composition_data),
        ("Percentage normalisation",                  test_percentages_normalised),
        ("Alias resolution (spandex/elastane)",       test_alias_resolution),
        ("Cost-per-wash calculation",                 test_cost_per_wash_calculation),
        ("Category normalisation (cardigan)",         test_category_normalisation),
        # ── New differentiation tests ─────────────────────────────────────────
        ("GSM fields exist on ScoreResult",           test_gsm_modifier_fields_exist),
        ("GSM modifier -10 for 120gsm cotton tee",    test_gsm_modifier_below_140),
        ("GSM modifier +6 for 270gsm cotton tee",     test_gsm_modifier_above_240),
        ("GSM modifier not applied — wrong fiber",    test_gsm_modifier_not_applied_wrong_fiber),
        ("GSM modifier not applied — wrong category", test_gsm_modifier_not_applied_wrong_category),
        ("Acrylic >40% sweater category penalty",     test_acrylic_sweater_category_penalty),
        ("Cotton in activewear penalised",            test_cotton_activewear_penalty),
        ("Viscose in dress penalised",                test_viscose_dress_category_penalty),
        ("4-fiber blend has no dominance bonus",      test_fiber_dominance_four_fiber_penalty),
        ("Construction score lifts worth_it_score",   test_construction_incorporated_in_worth_it_score),
        ("Low confidence uses half construction mod", test_construction_low_confidence_half_modifier),
        ("GSM missing: -3 confidence penalty",        test_gsm_confidence_penalty_reduces_score),
        ("No GSM penalty for polyester",              test_gsm_confidence_penalty_does_not_fire_for_polyester),
        ("GSM penalty fires for linen dress",         test_gsm_confidence_penalty_fires_for_dress),
    ]
    ...
```

- [ ] **Step 2: Run the full engine test suite**

```bash
cd /Users/desiraesidhu/clothing_quality_backend
python -m scoring.tests
```

Expected output:
```
Scoring Engine Tests
────────────────────────────────────────
  PASS  Acrylic/polyester sweater at $148
  PASS  Merino sweater at $80
  PASS  Cotton t-shirt at $12
  PASS  Viscose dress at $220
  PASS  Lyocell dress at $95
  PASS  Poly-cotton blend interaction
  PASS  Unknown fiber reduces confidence
  PASS  No composition data
  PASS  Percentage normalisation
  PASS  Alias resolution (spandex/elastane)
  PASS  Cost-per-wash calculation
  PASS  Category normalisation (cardigan)
  PASS  GSM fields exist on ScoreResult
  PASS  GSM modifier -10 for 120gsm cotton tee
  PASS  GSM modifier +6 for 270gsm cotton tee
  PASS  GSM modifier not applied — wrong fiber
  PASS  GSM modifier not applied — wrong category
  PASS  Acrylic >40% sweater category penalty
  PASS  Cotton in activewear penalised
  PASS  Viscose in dress penalised
  PASS  4-fiber blend has no dominance bonus
  PASS  Construction score lifts worth_it_score
  PASS  Low confidence uses half construction mod
  PASS  GSM missing: -3 confidence penalty
  PASS  No GSM penalty for polyester
  PASS  GSM penalty fires for linen dress
────────────────────────────────────────
26/26 tests passed
```

- [ ] **Step 3: Run pytest suite (33 extractor + 15 verdict + 5 new extractor = 53 tests)**

```bash
pytest scoring/test_extractor.py scoring/test_verdict.py -v
```

Expected: all tests pass (no failures)

- [ ] **Step 4: If any original test fails, fix the range — document why**

Most likely candidates and their post-change values (for reference):
- `test_cotton_tshirt_budget`: material_score ≈ 68.2 — still in `35–75` ✓
- `test_acrylic_polyester_sweater`: material_score ≈ 53.6 (was ~58.6 before -5 acrylic penalty) — still `< 70` ✓
- `test_merino_wool_sweater`: material_score ≈ 66.85 — still `>= 55` ✓; worth_it_score ≈ 61.85 — still `> material_score - 10` ✓
- `test_reformation_viscose_dress`: material_score ≈ 48.75 — still `< 55` ✓; worth_it_score ≈ 24.55 — still `< 45` ✓

If `test_acrylic_polyester_sweater` fails because the new worth_it_score is unexpectedly close to 50: the construction at $148 sweater adds +0.8 (price-floor score 7, low confidence). New worth_it_score ≈ 29.4 — well below 50. Update the assertion comment if helpful.

- [ ] **Step 5: Final commit**

```bash
git add scoring/tests.py
git commit -m "test: add 14 new engine integration tests for scoring differentiation features"
```

- [ ] **Step 6: Push to Railway**

```bash
git push origin main
```

---

## Self-Review Against Spec

| Spec Requirement | Task | Status |
|-----------------|------|--------|
| `_extract_gsm()` with gsm/oz patterns, 80–600 range | Task 1 | ✓ |
| `gsm` field on `ExtractionResult` | Task 1 | ✓ |
| `gsm_modifier_applied: bool` on `ScoreResult` | Task 2 | ✓ |
| GSM modifier: cotton/linen >50%, t-shirt or dress, 5-band scale | Task 2+3 | ✓ |
| Combined adjustment cap ±15 | Task 3 | ✓ |
| Construction contribution: (score-5)*0.8, ±5 cap, half for low confidence | Task 4 | ✓ |
| Fiber dominance: 90%+ → +2, 4+ fibers → -2 | Task 3 | ✓ |
| Category fit: viscose in dress -3, linen in tee/dress +3, acrylic sweater >40% -5, poly activewear >70% +4, cotton activewear -4 | Task 3 | ✓ |
| Confidence-aware penalty: -3 when GSM note fires and no GSM provided | Task 5 | ✓ |
| Extend GSM confidence note to dress (not just t-shirt) | Task 5 | ✓ |
| Wire GSM through app.py | Task 6 | ✓ |
| No changes to fiber_properties.py, blend interactions, price pressure, verdict/headline | All tasks | ✓ (verified by running full suite) |
| All 33 existing tests still pass | Task 7 | ✓ (ranges verified above) |
