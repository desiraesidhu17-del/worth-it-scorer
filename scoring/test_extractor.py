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
