"""
Scoring engine unit tests.

Run from /clothing_quality_backend/:
    python -m scoring.tests

Each test prints PASS or FAIL with a brief explanation.
"""

import sys
from .engine import score_item
from .technical_signals import detect_technical_signals


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
    Should score mid on material (cotton is decent).
    $12 is well below 50% of the quality-tier floor ($35), so price pressure = "undercut".
    """
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=12.0,
        category="t-shirt",
    )
    assert 35 <= result.material_score <= 75, (
        f"Cotton t-shirt material score should be 35–75, got {result.material_score}"
    )
    assert result.price_pressure["level"] == "undercut", (
        f"$12 cotton tee is far below floor — expected undercut, got {result.price_pressure['level']}"
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
        gsm=220.0,   # baseline GSM: 0 modifier, same for both items — isolates construction delta
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


def test_gsm_confidence_penalty_reduces_score():
    """
    Cotton t-shirt with no GSM should score 3 points lower than
    same t-shirt with GSM=200 (baseline, 0 modifier). Missing GSM
    means we can't confirm weight — nudge down slightly.
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
        gsm=200.0,  # baseline: 0 GSM modifier, no confidence penalty
    )
    # Expected: with_gsm_baseline is 3 points higher than no_gsm
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
        gsm=120.0,
    )
    # Neither GSM modifier nor penalty applies — scores should be identical
    assert poly_no_gsm.material_score == poly_with_gsm.material_score


def test_gsm_confidence_penalty_fires_for_dress():
    """
    Linen dress with no GSM should get the -3 confidence penalty.
    With GSM=200 (0 modifier) it should score 3 higher.
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
    delta = with_gsm.material_score - no_gsm.material_score
    assert abs(delta - 3) < 0.15, (
        f"Cotton dress without GSM should score 3 points lower; got delta={delta:.2f}"
    )


def test_verdict_bucket_worth_it():
    """Merino sweater at fair price → worth_it."""
    result = score_item(
        composition=[{"fiber": "merino", "pct": 100}],
        price=80.0,
        category="sweater",
    )
    assert result.verdict_bucket == "worth_it", (
        f"Merino at fair price should be worth_it, got {result.verdict_bucket} "
        f"(score={result.worth_it_score}, level={result.price_pressure['level']})"
    )


def test_verdict_bucket_overpriced_extreme():
    """Cotton t-shirt at $300 → overpriced (extreme price pressure)."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=300.0,
        category="t-shirt",
    )
    assert result.verdict_bucket == "overpriced", (
        f"Cotton t-shirt at $300 should be overpriced, got {result.verdict_bucket} "
        f"(score={result.worth_it_score}, level={result.price_pressure['level']})"
    )


def test_verdict_bucket_mixed_low_score_fair_price():
    """Acrylic tee at fair price → mixed (not overpriced — price is fair)."""
    result = score_item(
        composition=[{"fiber": "acrylic", "pct": 100}],
        price=25.0,
        category="t-shirt",
    )
    assert result.verdict_bucket == "mixed", (
        f"Acrylic tee at fair price should be mixed, got {result.verdict_bucket} "
        f"(score={result.worth_it_score}, level={result.price_pressure['level']})"
    )


def test_verdict_bucket_not_enough_info_low_confidence():
    """Unknown fiber → low confidence → not_enough_info."""
    result = score_item(
        composition=[{"fiber": "unknown_fiber_xyz", "pct": 100}],
        price=50.0,
        category="t-shirt",
    )
    assert result.verdict_bucket == "not_enough_info", (
        f"Unknown fiber should give not_enough_info, got {result.verdict_bucket}"
    )


def test_verdict_bucket_not_enough_info_no_price():
    """No price → unknown pressure level → not_enough_info."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=None,
        category="t-shirt",
    )
    assert result.verdict_bucket == "not_enough_info", (
        f"No price should give not_enough_info, got {result.verdict_bucket}"
    )


def test_verdict_bucket_overpriced_high_pressure():
    """Polyester tee at $200 → high/extreme pressure → overpriced."""
    result = score_item(
        composition=[{"fiber": "polyester", "pct": 100}],
        price=200.0,
        category="t-shirt",
    )
    assert result.price_pressure["level"] in ("high", "extreme"), (
        f"Poly tee at $200 should have high/extreme pressure, got {result.price_pressure['level']}"
    )
    assert result.verdict_bucket == "overpriced", (
        f"Should be overpriced, got {result.verdict_bucket}"
    )


def test_verdict_bucket_undercut_is_mixed():
    """Cotton t-shirt at $12 (undercut) → mixed, not worth_it."""
    result = score_item(
        composition=[{"fiber": "cotton", "pct": 100}],
        price=12.0,
        category="t-shirt",
    )
    assert result.price_pressure["level"] == "undercut", (
        f"$12 cotton tee should be undercut, got {result.price_pressure['level']}"
    )
    assert result.verdict_bucket == "mixed", (
        f"Undercut price should give mixed (not worth_it), got {result.verdict_bucket}"
    )


def test_verdict_bucket_field_always_present():
    """verdict_bucket is always one of the four valid values."""
    result = score_item(
        composition=[{"fiber": "silk", "pct": 100}],
        price=180.0,
        category="dress",
    )
    assert result.verdict_bucket in ("worth_it", "mixed", "overpriced", "not_enough_info"), (
        f"verdict_bucket must be one of four values, got {result.verdict_bucket!r}"
    )


# ── Technical signal extraction (Commit 1) ────────────────────────────────────

def test_tech_goretex_taped_is_waterproof_shell():
    """GORE-TEX + fully taped seams → technical, type waterproof_shell."""
    r = detect_technical_signals("GORE-TEX shell with fully taped seams.")
    assert r["is_technical"] is True, r
    assert r["technical_type"] == "waterproof_shell", (
        f"Expected waterproof_shell, got {r['technical_type']!r}"
    )


def test_tech_dwr_alone_not_technical():
    """DWR mentioned alone (one category) → is_technical False (threshold unchanged)."""
    r = detect_technical_signals("Treated with a durable water repellent finish.")
    assert r["is_technical"] is False, (
        f"DWR alone should not be technical, got {r}"
    )
    assert r["signal_count"] == 1, (
        f"DWR alone is one signal category, got {r['signal_count']}"
    )


def test_tech_waterproof_rating_spec_extracted():
    """'20,000 mm' → waterproof_rating spec with correct value + matched_text."""
    r = detect_technical_signals("GORE-TEX shell rated to 20,000 mm waterproof.")
    wp = [s for s in r["specs"] if s["label"] == "Waterproof rating"]
    assert wp, f"Expected a Waterproof rating spec, got {r['specs']}"
    assert "20,000" in wp[0]["value"] and "mm" in wp[0]["value"], wp[0]
    assert "20,000 mm" in wp[0]["matched_text"], wp[0]


def test_tech_fill_power_and_insulation_specs():
    """'800-fill down' → fill power spec (800) + insulation spec (down)."""
    r = detect_technical_signals("Insulated with 800-fill down for warmth.")
    by_label = {s["label"]: s for s in r["specs"]}
    assert "Fill power" in by_label, f"Expected Fill power spec, got {r['specs']}"
    assert by_label["Fill power"]["value"] == "800", by_label["Fill power"]
    assert "Insulation" in by_label, f"Expected Insulation spec, got {r['specs']}"
    assert by_label["Insulation"]["value"] == "down", by_label["Insulation"]


def test_tech_shell_layer_and_face_fabric_specs():
    """'3-layer ripstop' → shell construction spec + face fabric spec."""
    r = detect_technical_signals("3-layer ripstop construction.")
    by_label = {s["label"]: s for s in r["specs"]}
    assert "Shell construction" in by_label, f"Expected Shell construction, got {r['specs']}"
    assert by_label["Shell construction"]["value"] == "3-layer", by_label["Shell construction"]
    assert "Face fabric" in by_label, f"Expected Face fabric, got {r['specs']}"
    assert by_label["Face fabric"]["value"] == "ripstop", by_label["Face fabric"]


def test_tech_breathability_spec_extracted():
    """'15,000 g/m²/24h' → breathability spec, value traces to matched_text."""
    r = detect_technical_signals("Breathable membrane rated 15,000 g/m²/24h.")
    br = [s for s in r["specs"] if s["label"] == "Breathability"]
    assert br, f"Expected a Breathability spec, got {r['specs']}"
    assert "15,000" in br[0]["value"], br[0]
    assert "g/m" in br[0]["matched_text"], br[0]


def test_tech_fashion_puffer_not_technical_no_invented_specs():
    """Fashion puffer with no real technical signal → not technical, no specs."""
    r = detect_technical_signals(
        "Cozy puffer jacket, 100% polyester fill. Machine washable."
    )
    assert r["is_technical"] is False, f"Fashion puffer should not be technical, got {r}"
    assert r["specs"] == [], f"Must not invent specs for a fashion puffer, got {r['specs']}"


def test_tech_ambiguous_is_general_with_generic_compare():
    """Ambiguous technical item → technical_general + generic compare_on fallback."""
    r = detect_technical_signals(
        "Engineered with DWR treatment and a tested MVTR for moisture transport."
    )
    assert r["is_technical"] is True, f"DWR + MVTR is two categories → technical, got {r}"
    assert r["technical_type"] == "technical_general", (
        f"Ambiguous item should be technical_general, got {r['technical_type']!r}"
    )
    assert r["compare_on"] == [
        "Technical specs", "Construction", "Fabric durability", "Intended use"
    ], f"Expected generic fallback compare_on, got {r['compare_on']}"


def test_tech_data_shape_when_technical():
    """When technical: specs and compare_on are lists; every spec has the 3 keys."""
    r = detect_technical_signals(
        "GORE-TEX 3-layer shell, 20,000 mm, fully taped seams, "
        "800-fill down, ripstop face, YKK AquaGuard zips."
    )
    assert r["is_technical"] is True, r
    assert isinstance(r["specs"], list) and len(r["specs"]) >= 1, r["specs"]
    assert isinstance(r["compare_on"], list) and len(r["compare_on"]) >= 1, r["compare_on"]
    for s in r["specs"]:
        assert set(s.keys()) == {"label", "value", "matched_text"}, s
        assert isinstance(s["label"], str) and s["label"], s
        assert isinstance(s["value"], str) and s["value"], s
        assert isinstance(s["matched_text"], str) and s["matched_text"], s


def test_tech_fill_power_plus_dwr_is_technical():
    """Fill power + DWR = two categories → technical (detector counts fill power)."""
    r = detect_technical_signals("800-fill down with DWR finish")
    assert r["is_technical"] is True, (
        f"800-fill down + DWR should be two categories, got {r}"
    )


def test_tech_fill_power_alone_not_technical():
    """800-fill down alone extracts the spec but is one category → not technical."""
    r = detect_technical_signals("800-fill down")
    by_label = {s["label"]: s for s in r["specs"]}
    assert by_label.get("Fill power", {}).get("value") == "800", r["specs"]
    assert r["is_technical"] is False, (
        f"Fill power alone is one signal, must not be technical, got {r}"
    )
    assert r["signal_count"] == 1, r


def test_tech_generic_fill_language_not_technical_no_specs():
    """Generic 'polyester fill puffer' → no fill-power figure, not technical, no specs."""
    r = detect_technical_signals("polyester fill puffer jacket")
    assert r["is_technical"] is False, f"Generic fill language must not be technical, got {r}"
    assert r["specs"] == [], f"Must not invent specs for generic fill language, got {r['specs']}"


def test_tech_insulated_jacket_type():
    """Fill power + shell membrane + DWR → technical, type insulated_jacket."""
    r = detect_technical_signals("650-fill down, Pertex Quantum shell, DWR")
    assert r["is_technical"] is True, r
    assert r["technical_type"] == "insulated_jacket", (
        f"Expected insulated_jacket, got {r['technical_type']!r}"
    )


def _dwr_spec(text: str) -> dict:
    r = detect_technical_signals(text)
    dwr = [s for s in r["specs"] if s["label"] == "Water-repellent finish"]
    assert dwr, f"Expected a Water-repellent finish spec, got {r['specs']}"
    return dwr[0]


def test_tech_dwr_display_bare_dwr():
    """'DWR' alone → label 'Water-repellent finish', value 'DWR'."""
    spec = _dwr_spec("Jacket treated with DWR.")
    assert spec["value"] == "DWR", spec
    assert spec["matched_text"] == "DWR", spec


def test_tech_dwr_display_durable_water_repellent():
    """'durable water repellent' → normalized to value 'DWR'."""
    spec = _dwr_spec("Treated with a durable water repellent finish.")
    assert spec["value"] == "DWR", spec
    assert spec["matched_text"] == "durable water repellent", spec


def test_tech_dwr_display_water_repellent_finish():
    """'water-repellent finish' → normalized to value 'DWR'."""
    spec = _dwr_spec("Coated with a water-repellent finish for light rain.")
    assert spec["value"] == "DWR", spec
    assert spec["matched_text"] == "water-repellent finish", spec


def test_tech_dwr_display_pfas_free():
    """'PFAS-free DWR' → value stays 'PFAS-free DWR', matched_text is exact."""
    spec = _dwr_spec("Finished with PFAS-free DWR for reduced environmental impact.")
    assert spec["value"] == "PFAS-free DWR", spec
    assert spec["matched_text"] == "PFAS-free DWR", spec


def test_tech_dwr_display_pfc_free():
    """'PFC-free DWR' → value stays 'PFC-free DWR', matched_text is exact."""
    spec = _dwr_spec("Finished with PFC-free DWR for reduced environmental impact.")
    assert spec["value"] == "PFC-free DWR", spec
    assert spec["matched_text"] == "PFC-free DWR", spec


def test_tech_dwr_display_pfc_free_long_form():
    """'PFC-free durable water repellent' → value 'PFC-free DWR', exact matched_text."""
    spec = _dwr_spec("Finished with PFC-free durable water repellent treatment.")
    assert spec["value"] == "PFC-free DWR", spec
    assert spec["matched_text"] == "PFC-free durable water repellent", spec


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
        ("GSM missing: -3 confidence penalty",        test_gsm_confidence_penalty_reduces_score),
        ("No GSM penalty for polyester",              test_gsm_confidence_penalty_does_not_fire_for_polyester),
        ("GSM penalty fires for linen dress",         test_gsm_confidence_penalty_fires_for_dress),
        ("Verdict bucket: worth_it",                   test_verdict_bucket_worth_it),
        ("Verdict bucket: overpriced extreme",         test_verdict_bucket_overpriced_extreme),
        ("Verdict bucket: mixed low score fair price", test_verdict_bucket_mixed_low_score_fair_price),
        ("Verdict bucket: not_enough_info low conf",  test_verdict_bucket_not_enough_info_low_confidence),
        ("Verdict bucket: not_enough_info no price",  test_verdict_bucket_not_enough_info_no_price),
        ("Verdict bucket: overpriced high pressure",  test_verdict_bucket_overpriced_high_pressure),
        ("Verdict bucket: undercut is mixed",          test_verdict_bucket_undercut_is_mixed),
        ("Verdict bucket: field always present",       test_verdict_bucket_field_always_present),
        ("Tech: GORE-TEX + taped → waterproof_shell",  test_tech_goretex_taped_is_waterproof_shell),
        ("Tech: DWR alone not technical",              test_tech_dwr_alone_not_technical),
        ("Tech: waterproof rating spec",               test_tech_waterproof_rating_spec_extracted),
        ("Tech: fill power + insulation specs",        test_tech_fill_power_and_insulation_specs),
        ("Tech: shell layer + face fabric specs",      test_tech_shell_layer_and_face_fabric_specs),
        ("Tech: breathability spec",                   test_tech_breathability_spec_extracted),
        ("Tech: fashion puffer no invented specs",     test_tech_fashion_puffer_not_technical_no_invented_specs),
        ("Tech: ambiguous → general + generic compare", test_tech_ambiguous_is_general_with_generic_compare),
        ("Tech: data shape when technical",            test_tech_data_shape_when_technical),
        ("Tech: fill power + DWR is technical",         test_tech_fill_power_plus_dwr_is_technical),
        ("Tech: fill power alone not technical",        test_tech_fill_power_alone_not_technical),
        ("Tech: generic fill language not technical",   test_tech_generic_fill_language_not_technical_no_specs),
        ("Tech: insulated jacket type",                 test_tech_insulated_jacket_type),
        ("Tech: DWR display bare DWR",                  test_tech_dwr_display_bare_dwr),
        ("Tech: DWR display durable water repellent",   test_tech_dwr_display_durable_water_repellent),
        ("Tech: DWR display water-repellent finish",    test_tech_dwr_display_water_repellent_finish),
        ("Tech: DWR display PFAS-free",                 test_tech_dwr_display_pfas_free),
        ("Tech: DWR display PFC-free",                  test_tech_dwr_display_pfc_free),
        ("Tech: DWR display PFC-free long form",        test_tech_dwr_display_pfc_free_long_form),
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
