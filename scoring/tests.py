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
