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
    assert sub == "Fine fibers like silk prioritize softness and drape over durability."


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
