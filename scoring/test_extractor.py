"""Tests for the production extraction pipeline. Run with: pytest scoring/test_extractor.py -v"""
import pytest


# ── Task 1: Fiber vocabulary tests ────────────────────────────────────────────

def test_fiber_normalization_aliases():
    from scoring.fiber_vocab import normalize_fiber
    assert normalize_fiber("spandex") == "elastane"
    assert normalize_fiber("polyamide") == "nylon"
    assert normalize_fiber("tencel") == "lyocell"
    assert normalize_fiber("Tencel Lyocell") == "lyocell"
    assert normalize_fiber("merino wool") == "wool"
    assert normalize_fiber("organic cotton") == "cotton"

def test_fiber_normalization_modifiers():
    from scoring.fiber_vocab import normalize_fiber, get_modifier
    assert normalize_fiber("recycled polyester") == "recycled polyester"
    assert get_modifier("recycled polyester") == "recycled"
    assert get_modifier("organic cotton") == "organic"
    assert get_modifier("cotton") is None

def test_fiber_normalization_viscose():
    from scoring.fiber_vocab import normalize_fiber
    assert normalize_fiber("rayon") == "viscose"
    assert normalize_fiber("viscose") == "viscose"

def test_fiber_is_known():
    from scoring.fiber_vocab import is_known_fiber
    assert is_known_fiber("cotton") is True
    assert is_known_fiber("polyester") is True
    assert is_known_fiber("exclusive of trims") is False
    assert is_known_fiber("imported") is False
    assert is_known_fiber("recycled polyester") is True

def test_non_fiber_materials():
    from scoring.fiber_vocab import get_material_type
    assert get_material_type("leather") == "non-fiber"
    assert get_material_type("suede") == "non-fiber"
    assert get_material_type("down") == "fill"
    assert get_material_type("cotton") is None  # normal fiber


# ── Task 2: Contextual regex tests ────────────────────────────────────────────

def test_regex_finds_simple_composition():
    from scoring.extractor import extract_by_regex
    text = "75% cotton, 25% polyester"
    result = extract_by_regex(text)
    assert len(result) == 2
    assert {"fiber": "cotton", "pct": 75.0} in result
    assert {"fiber": "polyester", "pct": 25.0} in result

def test_regex_ignores_sale_percentages():
    from scoring.extractor import extract_by_regex
    text = "10% off today only. Machine wash. 75% cotton, 25% polyester."
    result = extract_by_regex(text)
    fibers = [r["fiber"] for r in result]
    assert "cotton" in fibers
    assert "polyester" in fibers
    # "off" is not a fiber - should not appear
    assert len(result) == 2

def test_regex_ignores_customer_ratings():
    from scoring.extractor import extract_by_regex
    text = "Rated 95% by customers. Material: 100% cotton."
    result = extract_by_regex(text)
    assert len(result) == 1
    assert result[0]["fiber"] == "cotton"

def test_regex_ignores_water_usage():
    from scoring.extractor import extract_by_regex
    text = "Made with 30% less water. Fabric: 80% cotton, 20% nylon."
    result = extract_by_regex(text)
    assert len(result) == 2
    fibers = [r["fiber"] for r in result]
    assert "cotton" in fibers
    assert "nylon" in fibers

def test_regex_normalizes_aliases():
    from scoring.extractor import extract_by_regex
    text = "Composition: 95% viscose, 5% spandex"
    result = extract_by_regex(text)
    fibers = [r["fiber"] for r in result]
    assert "elastane" in fibers  # spandex normalized
    assert "viscose" in fibers

def test_regex_handles_recycled_modifier():
    from scoring.extractor import extract_by_regex
    text = "Shell: 75% recycled polyester, 25% nylon"
    result = extract_by_regex(text)
    fibers = [r["fiber"] for r in result]
    assert "recycled polyester" in fibers
    assert "nylon" in fibers

def test_regex_returns_empty_for_no_composition():
    from scoring.extractor import extract_by_regex
    text = "Beautiful dress. Free shipping on orders over $50."
    result = extract_by_regex(text)
    assert result == []


# ── Task 3: JSON-LD + candidate block tests ───────────────────────────────────

def test_json_ld_extracts_composition():
    from scoring.extractor import _extract_json_ld
    blocks = [{
        "@type": "Product",
        "name": "Cotton T-Shirt",
        "offers": {"price": "29.99"},
        "description": "Made from 100% organic cotton. Machine wash cold.",
    }]
    result = _extract_json_ld(blocks)
    assert result.price == 29.99
    assert len(result.composition_blocks) == 1
    assert result.composition_blocks[0].fibers[0]["fiber"] == "cotton"
    assert result.extraction_method == "json_ld"

def test_json_ld_skips_non_product():
    from scoring.extractor import _extract_json_ld
    blocks = [{"@type": "Organization", "name": "Zara"}]
    result = _extract_json_ld(blocks)
    assert result.composition_blocks == []

def test_candidate_block_isolation_finds_materials():
    from scoring.extractor import isolate_candidate_blocks
    html = """
    <div>
      <h3>Materials</h3>
      <p>Shell: 75% cotton, 25% polyester. Lining: 100% viscose.</p>
    </div>
    <div><h3>Shipping</h3><p>Free shipping on orders over $50.</p></div>
    """
    blocks = isolate_candidate_blocks(html)
    assert len(blocks) >= 1
    assert any("cotton" in b.lower() for b in blocks)

def test_extract_from_text_basic():
    from scoring.extractor import extract_from_text
    result = extract_from_text("Composition: 80% cotton, 20% polyester. Care: machine wash.")
    assert result.main_composition is not None
    assert len(result.main_composition) == 2

def test_validation_confidence_full_sum():
    from scoring.extractor import _apply_validation, CompositionBlock, ExtractionResult
    block = CompositionBlock(part="unknown", fibers=[
        {"fiber": "cotton", "pct": 75},
        {"fiber": "polyester", "pct": 25},
    ], source="regex")
    result = ExtractionResult(composition_blocks=[block])
    result = _apply_validation(result)
    assert result.extraction_confidence == "high"
    assert result.warnings == []

def test_validation_confidence_partial_sum():
    from scoring.extractor import _apply_validation, CompositionBlock, ExtractionResult
    block = CompositionBlock(part="unknown", fibers=[
        {"fiber": "cotton", "pct": 70},
    ], source="regex")
    result = ExtractionResult(composition_blocks=[block])
    result = _apply_validation(result)
    assert result.extraction_confidence in ("medium", "low")
    assert len(result.warnings) >= 1


# ── Task 4: GPT fallback tests ────────────────────────────────────────────────

import json as _json
from unittest.mock import MagicMock, patch

def test_gpt_fallback_parses_response():
    from scoring.extractor import _call_gpt_resolver
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=_json.dumps({
            "product_name": "Silk Blouse",
            "price": 120.0,
            "brand": "COS",
            "composition_blocks": [
                {"part": "shell", "fibers": [{"fiber": "silk", "pct": 100}]}
            ],
            "main_composition": [{"fiber": "silk", "pct": 100}],
            "confidence": "high",
            "reasoning": "Single fiber 100% sum."
        })))]
    )
    result = _call_gpt_resolver("Silk blouse, COS, $120. 100% silk.", mock_client)
    assert result.main_composition is not None
    assert result.main_composition[0]["fiber"] == "silk"
    assert result.extraction_method == "gpt"

def test_gpt_fallback_handles_invalid_json():
    from scoring.extractor import _call_gpt_resolver
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="not valid json {{"))]
    )
    result = _call_gpt_resolver("some text", mock_client)
    assert result.composition_blocks == []


# ── Task 1: _parse_price currency handling ────────────────────────────────────

def test_parse_price_usd():
    from app import _parse_price
    assert _parse_price("$217.00") == 217.0

def test_parse_price_cad():
    from app import _parse_price
    assert _parse_price("CA$217.00") == 217.0

def test_parse_price_gbp():
    from app import _parse_price
    assert _parse_price("£89.99") == 89.99

def test_parse_price_eur():
    from app import _parse_price
    assert _parse_price("€120") == 120.0

def test_parse_price_aud():
    from app import _parse_price
    assert _parse_price("AU$145.00") == 145.0

def test_parse_price_thousands():
    from app import _parse_price
    assert _parse_price("$1,234.00") == 1234.0

def test_parse_price_none():
    from app import _parse_price
    assert _parse_price(None) is None

def test_parse_price_numeric():
    from app import _parse_price
    assert _parse_price(217) == 217.0

def test_parse_price_european_decimal_known_limitation():
    # European format "1.234,56" (meaning 1234.56) is a known limitation:
    # comma is stripped first, leaving "1.23456", which parses as 1.23456.
    # We intentionally do not fix this edge case; this test documents the behavior.
    from app import _parse_price
    assert _parse_price("1.234,56") == 1.23456

def test_parse_price_multiple_decimal_points():
    # "12.34.56" is malformed; float() raises ValueError, so we return None.
    # This is intentional — we drop silently rather than guess.
    from app import _parse_price
    assert _parse_price("12.34.56") is None
