"""
Scoring engine unit tests.

Run from /clothing_quality_backend/:
    python -m scoring.tests

Each test prints PASS or FAIL with a brief explanation.
"""

import sys
from .engine import score_item


def _run(name: str, fn):
    try:
        fn()
        print(f"  PASS  {name}")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False
    except Exception as e:
        print(f"  ERROR {name}: {type(e).__name__}: {e}")
        return False


# ── Individual tests ──────────────────────────────────────────────────────────

def test_acrylic_polyester_sweater():
    """
    Free People-type sweater: 52% acrylic, 48% polyester, $148.
    Should score LOW on material (acrylic pills badly), HIGH price pressure,
    and very low worth-it score.
    """
    result = score_item(
        composition=[{"fiber": "acrylic", "pct": 52}, {"fiber": "polyester", "pct": 48}],
        price=148.0,
        category="sweater",
    )
    # Polyester raises tensile/colorfastness; material score ~55-65 is correct.
    # The rip-off signal comes from price pressure, not material score alone.
    assert result.material_score < 70, (
        f"Acrylic/poly sweater should score below 70, got {result.material_score}"
    )
    assert result.price_pressure["level"] in ("high", "extreme"), (
        f"$148 acrylic sweater should have high/extreme price pressure, got {result.price_pressure['level']}"
    )
    assert result.worth_it_score < 50, (
        f"Worth-It Score should be below 50, got {result.worth_it_score}"
    )
    assert result.confidence == "high", (
        f"Full composition given — should be high confidence, got {result.confidence}"
    )


def test_merino_wool_sweater():
    """
    Uniqlo-type merino sweater: 100% merino, $80.
    Should score well — merino is genuinely durable and $80 is mid-range for quality merino.
    """
    result = score_item(
        composition=[{"fiber": "merino", "pct": 100}],
        price=80.0,
        category="sweater",
    )
    assert result.material_score >= 55, (
        f"Merino sweater should score 55+, got {result.material_score}"
    )
    assert result.price_pressure["level"] in ("low", "moderate"), (
        f"$80 merino should have low/moderate pressure, got {result.price_pressure['level']}"
    )
    assert result.worth_it_score > result.material_score - 10, (
        "Worth-It Score should stay close to material score for fairly-priced item"
    )


def test_cotton_tshirt_budget():
    """
    Basic cotton t-shirt: 100% cotton, $12.
    Should score mid on material (cotton is decent), low price pressure at $12.
    """
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=12.0,
        category="t-shirt",
    )
    assert 35 <= result.material_score <= 75, (
        f"Cotton t-shirt material score should be 35–75, got {result.material_score}"
    )
    assert result.price_pressure["level"] == "low", (
        f"$12 cotton tee should have low price pressure, got {result.price_pressure['level']}"
    )
    # GSM confidence note should fire for cotton t-shirt
    assert result.confidence in ("medium", "high"), (
        f"Expected medium or high confidence, got {result.confidence}"
    )


def test_reformation_viscose_dress():
    """
    Reformation-type dress: 100% viscose, $220.
    Viscose is weak (pilling, tensile) — $220 is extreme price pressure for this fiber.
    """
    result = score_item(
        composition=[{"fiber": "viscose", "pct": 100}],
        price=220.0,
        category="dress",
    )
    assert result.material_score < 55, (
        f"Pure viscose dress should score below 55, got {result.material_score}"
    )
    assert result.price_pressure["level"] in ("high", "extreme"), (
        f"$220 viscose dress should have high/extreme price pressure, got {result.price_pressure['level']}"
    )
    assert result.worth_it_score < 45, (
        f"Worth-It Score should be below 45, got {result.worth_it_score}"
    )


def test_lyocell_dress_fair_price():
    """
    Lyocell dress: 100% lyocell, $95.
    Lyocell is genuinely better than viscose. $95 mid-range dress should score fairly.
    """
    result = score_item(
        composition=[{"fiber": "lyocell", "pct": 100}],
        price=95.0,
        category="dress",
    )
    assert result.material_score > 50, (
        f"Lyocell dress should score above 50, got {result.material_score}"
    )
    assert result.price_pressure["level"] in ("low", "moderate"), (
        f"$95 lyocell dress should have low/moderate pressure, got {result.price_pressure['level']}"
    )
    # Lyocell should score noticeably better than viscose
    viscose_result = score_item(
        composition=[{"fiber": "viscose", "pct": 100}],
        price=95.0,
        category="dress",
    )
    assert result.material_score > viscose_result.material_score, (
        "Lyocell should outscore pure viscose"
    )


def test_polycotton_blend_interaction():
    """
    50/50 poly-cotton: blend interaction should give better pilling than pure cotton average.
    """
    poly_cotton = score_item(
        composition=[{"fiber": "polyester", "pct": 50}, {"fiber": "cotton", "pct": 50}],
        price=35.0,
        category="t-shirt",
    )
    pure_cotton = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=35.0,
        category="t-shirt",
    )
    # Poly-cotton pilling score should be higher than pure cotton due to blend interaction
    assert poly_cotton.property_scores["pilling"] > pure_cotton.property_scores["pilling"], (
        "Poly-cotton blend pilling score should exceed pure cotton due to blend interaction"
    )
    assert poly_cotton.blend_interactions_applied is True


def test_unknown_fiber_reduces_confidence():
    """
    Composition with an unknown fiber should reduce confidence.
    """
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 60}, {"fiber": "bambazite", "pct": 40}],
        price=50.0,
        category="t-shirt",
    )
    assert result.confidence in ("medium", "low"), (
        f"Unknown fiber should reduce confidence below 'high', got {result.confidence}"
    )
    assert "bambazite" in result.unknown_fibers


def test_no_composition_data():
    """
    Empty composition should return a zero score with low confidence.
    """
    result = score_item(
        composition=[],
        price=100.0,
        category="dress",
    )
    assert result.material_score == 0
    assert result.confidence == "low"
    assert result.worth_it_score == 0


def test_percentages_normalised():
    """
    Percentages that don't sum to 100 should be normalised gracefully.
    """
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 60}, {"fiber": "polyester", "pct": 60}],
        price=40.0,
        category="t-shirt",
    )
    # Should not crash; score should be valid
    assert 0 < result.material_score < 100
    assert result.worth_it_score >= 0


def test_alias_resolution():
    """
    Fiber aliases (spandex, rayon, tencel) should resolve correctly.
    """
    result_spandex = score_item(
        composition=[{"fiber": "cotton", "pct": 95}, {"fiber": "spandex", "pct": 5}],
        price=45.0,
        category="jeans",
    )
    result_elastane = score_item(
        composition=[{"fiber": "cotton", "pct": 95}, {"fiber": "elastane", "pct": 5}],
        price=45.0,
        category="jeans",
    )
    # spandex and elastane are the same fiber — scores must match exactly
    assert result_spandex.material_score == result_elastane.material_score, (
        "Spandex and elastane aliases should resolve to identical scores"
    )
    assert result_spandex.unknown_fibers == [], "Spandex should not be in unknown fibers"


def test_cost_per_wash_calculation():
    """
    Cost-per-wash should be mathematically consistent with price and score band.
    """
    result = score_item(
        composition=[{"fiber": "acrylic", "pct": 100}],
        price=100.0,
        category="sweater",
    )
    cpw = result.cost_per_wash
    assert cpw["wash_cycles_min"] > 0
    assert cpw["wash_cycles_max"] >= cpw["wash_cycles_min"]
    assert cpw["cost_per_wash_high"] >= cpw["cost_per_wash_low"]
    assert abs(cpw["cost_per_wash_high"] - 100 / cpw["wash_cycles_min"]) < 0.01


def test_category_normalisation():
    """
    Category aliases (cardigan, hoodie, coat) should map to parent categories.
    """
    cardigan = score_item(
        composition=[{"fiber": "wool", "pct": 100}],
        price=150.0,
        category="cardigan",
    )
    sweater = score_item(
        composition=[{"fiber": "wool", "pct": 100}],
        price=150.0,
        category="sweater",
    )
    assert cardigan.material_score == sweater.material_score, (
        "Cardigan should use sweater weights"
    )


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


def test_gsm_modifier_applied_true_at_baseline():
    """applied=True even when modifier is 0 (180–239gsm baseline range)."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=30.0,
        category="t-shirt",
        gsm=200.0,
    )
    assert result.gsm_modifier_applied is True
    assert result.gsm_modifier == 0


def test_acrylic_sweater_category_penalty():
    """
    Acrylic above 40% in sweater gets -5 category fit penalty.
    60% acrylic sweater should score lower than 30% acrylic sweater.
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
    assert high_acrylic.material_score < low_acrylic.material_score, (
        f"High acrylic sweater should score lower: {high_acrylic.material_score} vs {low_acrylic.material_score}"
    )


def test_cotton_activewear_penalty():
    """
    Cotton in activewear gets -4. 100% polyester activewear (>70%) gets +4.
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
    assert poly_active.material_score > cotton_active.material_score, (
        f"Polyester activewear should outscore cotton: {poly_active.material_score} vs {cotton_active.material_score}"
    )


def test_viscose_dress_category_penalty():
    """
    100% viscose in dress gets -3 category fit.
    Lyocell in dress has no penalty, so should score higher.
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
    Single-fiber (90%+) gets +2 dominance; 4-fiber blend gets -2.
    Using t-shirt avoids confounding with viscose-in-dress penalty.
    Net spread is 4 points from dominance alone.
    """
    single_fiber = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=80.0,
        category="t-shirt",
        gsm=200.0,  # baseline GSM: 0 modifier, no confidence penalty
    )
    four_fiber = score_item(
        composition=[
            {"fiber": "cotton", "pct": 40},
            {"fiber": "polyester", "pct": 30},
            {"fiber": "viscose", "pct": 20},
            {"fiber": "elastane", "pct": 10},
        ],
        price=80.0,
        category="t-shirt",
    )
    # single fiber: +2 dominance; 4-fiber: -2 dominance — directional check
    assert single_fiber.material_score > four_fiber.material_score, (
        f"Single fiber should outscore 4-fiber blend: "
        f"{single_fiber.material_score} vs {four_fiber.material_score}"
    )
    assert four_fiber.gsm_modifier_applied is False


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
    Delta should be 1.2.
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

    delta = result_med.worth_it_score - result_low.worth_it_score
    assert abs(delta - 1.2) < 0.15, (
        f"Expected delta ~1.2 between medium/low confidence, got {delta:.2f}"
    )


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all():
    tests = [
        ("Acrylic/polyester sweater at $148",   test_acrylic_polyester_sweater),
        ("Merino sweater at $80",                test_merino_wool_sweater),
        ("Cotton t-shirt at $12",                test_cotton_tshirt_budget),
        ("Viscose dress at $220",                test_reformation_viscose_dress),
        ("Lyocell dress at $95",                 test_lyocell_dress_fair_price),
        ("Poly-cotton blend interaction",        test_polycotton_blend_interaction),
        ("Unknown fiber reduces confidence",     test_unknown_fiber_reduces_confidence),
        ("No composition data",                  test_no_composition_data),
        ("Percentage normalisation",             test_percentages_normalised),
        ("Alias resolution (spandex/elastane)",  test_alias_resolution),
        ("Cost-per-wash calculation",            test_cost_per_wash_calculation),
        ("Category normalisation (cardigan)",    test_category_normalisation),
        ("GSM fields always exist on result",    test_gsm_modifier_fields_exist),
        ("GSM modifier -10 below 140gsm",        test_gsm_modifier_below_140),
        ("GSM modifier +6 above 240gsm",         test_gsm_modifier_above_240),
        ("GSM modifier skips non-cotton fiber",  test_gsm_modifier_not_applied_wrong_fiber),
        ("GSM modifier skips sweater category",  test_gsm_modifier_not_applied_wrong_category),
        ("GSM modifier applied=True at baseline 200gsm", test_gsm_modifier_applied_true_at_baseline),
        ("Acrylic >40% sweater category penalty",     test_acrylic_sweater_category_penalty),
        ("Cotton in activewear penalised",            test_cotton_activewear_penalty),
        ("Viscose in dress penalised",                test_viscose_dress_category_penalty),
        ("4-fiber blend no dominance bonus",          test_fiber_dominance_four_fiber_penalty),
        ("Construction score lifts worth_it_score",   test_construction_incorporated_in_worth_it_score),
        ("Low confidence uses half construction mod", test_construction_low_confidence_half_modifier),
    ]

    print("\nScoring Engine Tests\n" + "─" * 40)
    passed = sum(_run(name, fn) for name, fn in tests)
    total = len(tests)
    print("─" * 40)
    print(f"{passed}/{total} tests passed\n")
    return passed == total


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
