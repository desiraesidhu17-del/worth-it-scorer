# Production Extraction Pipeline + Chrome Extension Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace GPT-first extraction with a 6-step deterministic pipeline and add a Chrome extension that reads any retailer page and opens the web app pre-scored.

**Architecture:** New `scoring/extractor.py` runs JSON-LD → meta → contextual regex → GPT fallback → normalization → validation. Two new Flask endpoints (`/api/score-page`, `/api/result/<uuid>`) serve the extension. Extension is 4 files (Manifest V3) that extract DOM data, POST to the API, and open the web app with `?result=<uuid>`.

**Tech Stack:** Python/Flask (backend), BeautifulSoup (HTML parsing), GPT-4o-mini (fallback resolver only), Vanilla JS (extension, no frameworks), Chrome Manifest V3.

**Design doc:** `docs/plans/2026-03-09-production-extraction-extension-design.md`

---

## Task 1: Fiber vocabulary + normalization

**Files:**
- Create: `scoring/fiber_vocab.py`
- Test: `scoring/test_extractor.py`

**Step 1: Create test file with normalization tests**

```python
# scoring/test_extractor.py
"""Tests for the production extraction pipeline. Run with: pytest scoring/test_extractor.py -v"""
import pytest

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
```

**Step 2: Run to verify tests fail**
```bash
cd /Users/desiraesidhu/clothing_quality_backend
python -m pytest scoring/test_extractor.py::test_fiber_normalization_aliases -v
```
Expected: `ModuleNotFoundError` or `ImportError`

**Step 3: Implement `scoring/fiber_vocab.py`**

```python
"""
Fiber vocabulary, canonical names, aliases, and modifiers.
Used by the extraction pipeline for normalization.
"""

# Maps alias → canonical fiber name
# Keys are lowercase. Handles modifiers separately.
_ALIASES: dict[str, str] = {
    "spandex": "elastane",
    "polyamide": "nylon",
    "tencel": "lyocell",
    "tencel lyocell": "lyocell",
    "lyocell (tencel)": "lyocell",
    "rayon": "viscose",
    "merino": "wool",
    "merino wool": "wool",
    "flax": "linen",
    "pu": "polyurethane",
    "elastomultiester": "polyester",
}

# Known base fibers (canonical, lowercase)
_KNOWN_FIBERS: frozenset[str] = frozenset([
    "cotton", "polyester", "nylon", "viscose", "wool", "linen", "silk",
    "elastane", "lyocell", "acrylic", "cashmere", "mohair", "hemp",
    "bamboo", "modal", "cupro", "acetate", "leather", "suede", "down",
    "polyurethane", "polypropylene",
])

# Modifiers that prefix a fiber name
_MODIFIERS: tuple[str, ...] = ("recycled", "organic", "regenerated", "bio-based")

# Non-fiber / fill materials
_NON_FIBER: dict[str, str] = {
    "leather": "non-fiber",
    "suede": "non-fiber",
    "nubuck": "non-fiber",
    "down": "fill",
    "feather": "fill",
    "fiberfill": "fill",
}

# Noise strings to strip from regex captures
_NOISE_SUFFIXES: tuple[str, ...] = (
    "exclusive of trims", "exclusive of decoration",
    "imported", "body", "shell", "lining", "trim",
    "except", "excl",
)


def normalize_fiber(raw: str) -> str:
    """Return the canonical lowercase fiber name for a raw fiber string."""
    cleaned = raw.lower().strip()
    # Strip known noise suffixes
    for noise in _NOISE_SUFFIXES:
        if cleaned.endswith(noise):
            cleaned = cleaned[: -len(noise)].strip(",. ").strip()
    # Check alias map first (handles multi-word like "tencel lyocell")
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    # Handle modifier + fiber: "recycled polyester" stays as "recycled polyester"
    for mod in _MODIFIERS:
        if cleaned.startswith(mod + " "):
            base = cleaned[len(mod) + 1:].strip()
            base = _ALIASES.get(base, base)
            if base in _KNOWN_FIBERS or base in _ALIASES.values():
                return f"{mod} {base}"
    # Alias map without modifier prefix
    if cleaned in _KNOWN_FIBERS:
        return cleaned
    return cleaned  # Return as-is; caller uses is_known_fiber() to validate


def get_modifier(raw: str) -> str | None:
    """Return the modifier prefix ('recycled', 'organic', etc.) or None."""
    cleaned = raw.lower().strip()
    for mod in _MODIFIERS:
        if cleaned.startswith(mod + " "):
            return mod
    return None


def is_known_fiber(raw: str) -> bool:
    """Return True if this string resolves to a known fiber (after normalization)."""
    normalized = normalize_fiber(raw)
    # Strip modifier if present to check base fiber
    for mod in _MODIFIERS:
        if normalized.startswith(mod + " "):
            base = normalized[len(mod) + 1:].strip()
            return base in _KNOWN_FIBERS
    return normalized in _KNOWN_FIBERS


def get_material_type(raw: str) -> str | None:
    """Return 'non-fiber' or 'fill' for special materials, None for normal fibers."""
    return _NON_FIBER.get(normalize_fiber(raw))
```

**Step 4: Run tests**
```bash
python -m pytest scoring/test_extractor.py -k "fiber" -v
```
Expected: All fiber tests PASS

**Step 5: Commit**
```bash
git add scoring/fiber_vocab.py scoring/test_extractor.py
git commit -m "feat: fiber vocabulary, normalization, alias map"
```

---

## Task 2: Contextual regex composition extraction (Step 3)

**Files:**
- Create: `scoring/extractor.py` (skeleton + regex step)
- Modify: `scoring/test_extractor.py`

**Step 1: Add regex extraction tests**

```python
# Add to scoring/test_extractor.py

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
```

**Step 2: Run to verify tests fail**
```bash
python -m pytest scoring/test_extractor.py -k "regex" -v
```
Expected: `ImportError` — `extractor` module doesn't exist yet

**Step 3: Create `scoring/extractor.py` with regex extraction**

```python
"""
Production extraction pipeline for clothing product pages.

Steps:
  0 - Candidate block isolation (HTML)
  1 - JSON-LD candidate extraction
  2 - Meta tag extraction (price/brand)
  3 - Contextual regex composition extraction
  4 - GPT-4o-mini resolver (fallback only)
  5 - Normalization
  6 - Validation + reconciliation

Entry points:
  extract_from_html(html: str, url: str) -> ExtractionResult
  extract_from_payload(payload: dict) -> ExtractionResult  (for extension)
  extract_from_text(text: str) -> ExtractionResult
"""

from __future__ import annotations
import re
import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup
from .fiber_vocab import normalize_fiber, is_known_fiber, get_material_type

log = logging.getLogger(__name__)

# ── Material context keywords — regex must find these near a % match ──────────
_MATERIAL_CONTEXT_RE = re.compile(
    r"\b(material|fabric|shell|lining|body|composition|trim|care|content|"
    r"fibre|fiber|outer|inside|fill|filling|made of|made from)\b",
    re.IGNORECASE,
)

# ── Core % + fiber pattern ─────────────────────────────────────────────────────
_PCT_FIBER_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*([a-zA-Z][a-zA-Z\s]{2,30})",
)

# ── Multi-block label prefixes ─────────────────────────────────────────────────
_BLOCK_PREFIX_RE = re.compile(
    r"^(shell|outer|body|lining|trim|fill|filling|inside|exterior|interior)\s*[:\-]\s*",
    re.IGNORECASE,
)

# ── DOM labels that indicate product detail sections ─────────────────────────
_DETAIL_LABELS = frozenset([
    "materials", "material", "fabric", "composition", "care", "details",
    "shell", "lining", "body", "trim", "content", "construction",
    "product details", "fabric & care", "material & care",
    "fiber content", "fibre content",
])

# Context window (chars around a % match to check for material keywords)
_CONTEXT_WINDOW = 80


@dataclass
class CompositionBlock:
    part: str  # "shell", "lining", "body", "unknown"
    fibers: list[dict]  # [{"fiber": str, "pct": float}]
    confidence_weight: float = 0.5
    source: str = "unknown"  # "json_ld", "regex", "gpt"

    def pct_sum(self) -> float:
        return sum(f["pct"] for f in self.fibers)


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

    # Confidence
    extraction_method: str = "none"   # json_ld | regex | gpt | none
    extraction_confidence: str = "low"  # high | medium | low
    _confidence_score: float = 0.0

    warnings: list[str] = field(default_factory=list)

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
            "extraction_method": self.extraction_method,
            "extraction_confidence": self.extraction_confidence,
            "warnings": self.warnings,
        }


# ── Public entry points ────────────────────────────────────────────────────────

def extract_from_text(text: str) -> ExtractionResult:
    """Extract composition from plain text (paste-text path)."""
    result = ExtractionResult()
    fibers = extract_by_regex(text)
    if fibers:
        block = CompositionBlock(part="unknown", fibers=fibers, source="regex")
        result.composition_blocks = [block]
        result.extraction_method = "regex"
        result = _apply_validation(result)
    return result


def extract_from_payload(payload: dict) -> ExtractionResult:
    """
    Extract from extension payload.
    Payload keys: url, json_ld[], meta{}, candidate_blocks[], price?, category?
    Starts at Step 1 (JSON-LD) since Step 0 already ran in the browser.
    """
    result = ExtractionResult()

    # Step 1: JSON-LD candidates
    json_ld_blocks = payload.get("json_ld") or []
    json_ld_result = _extract_json_ld(json_ld_blocks)
    if json_ld_result.composition_blocks:
        result = json_ld_result

    # Step 2: Meta tags (price/brand supplement)
    meta = payload.get("meta") or {}
    _apply_meta(result, meta)

    # Step 3: Contextual regex on candidate blocks
    if not result.composition_blocks:
        candidate_texts = payload.get("candidate_blocks") or []
        for text in candidate_texts:
            fibers = extract_by_regex(text)
            if fibers:
                part = _detect_block_part(text)
                result.composition_blocks.append(
                    CompositionBlock(part=part, fibers=fibers, source="regex")
                )
                result.composition_raw += text + " | "

        if result.composition_blocks:
            result.extraction_method = "regex"

    # Step 4: GPT fallback handled by caller (needs openai_client)
    # Step 5+6: Normalize and validate
    if result.composition_blocks:
        result = _apply_normalization(result)
        result = _apply_validation(result)
        _select_main_composition(result)

    # Override price/category from payload if provided
    if payload.get("price"):
        try:
            result.price = float(str(payload["price"]).replace("$", "").strip())
        except (ValueError, TypeError):
            pass
    if payload.get("category"):
        result.category = payload["category"]

    return result


# ── Step 3: Contextual regex ────────────────────────────────────────────────

def extract_by_regex(text: str) -> list[dict]:
    """
    Find fiber/percentage pairs in text using contextual filtering.
    Returns list of {"fiber": str, "pct": float} dicts.
    Only returns matches where nearby text contains material context keywords.
    """
    results: list[dict] = []
    seen_fibers: set[str] = set()

    for match in _PCT_FIBER_RE.finditer(text):
        pct_str, fiber_raw = match.group(1), match.group(2).strip()

        # Check material context window
        start = max(0, match.start() - _CONTEXT_WINDOW)
        end = min(len(text), match.end() + _CONTEXT_WINDOW)
        context = text[start:end]
        if not _MATERIAL_CONTEXT_RE.search(context):
            # No material keyword nearby — skip
            # But allow if we already have fibers (continuation of composition list)
            if not results:
                continue

        normalized = normalize_fiber(fiber_raw)

        # Skip if not a known fiber
        if not is_known_fiber(normalized):
            continue

        # Skip non-fiber materials (leather, down, etc.) from % composition
        if get_material_type(normalized):
            continue

        if normalized in seen_fibers:
            continue

        try:
            pct = float(pct_str)
        except ValueError:
            continue

        if pct <= 0 or pct > 100:
            continue

        seen_fibers.add(normalized)
        results.append({"fiber": normalized, "pct": pct})

    return results


# ── Step 0: Candidate block isolation ─────────────────────────────────────────

def isolate_candidate_blocks(html: str) -> list[str]:
    """
    From raw HTML, find text blocks near product-detail labels.
    Returns list of candidate text strings, deduped.
    """
    soup = BeautifulSoup(html, "lxml")
    candidates: list[str] = []
    seen_hashes: set[str] = set()

    # Find labeled nodes
    for tag in soup.find_all(True):
        tag_text = tag.get_text(separator=" ", strip=True)
        if not tag_text:
            continue
        if tag_text.lower() in _DETAIL_LABELS:
            # Collect this node + siblings/children (bounded)
            block_parts = [tag_text]
            # Next sibling text
            for sibling in tag.next_siblings:
                if hasattr(sibling, "get_text"):
                    sib_text = sibling.get_text(separator=" ", strip=True)
                    if sib_text and len(sib_text) < 500:
                        block_parts.append(sib_text)
                    if len(" ".join(block_parts)) > 600:
                        break
            # Parent container text
            if tag.parent:
                parent_text = tag.parent.get_text(separator=" ", strip=True)
                if len(parent_text) < 800:
                    block_parts.append(parent_text)

            block = " ".join(block_parts).strip()
            text_hash = hashlib.md5(block.encode()).hexdigest()
            if text_hash not in seen_hashes and block:
                seen_hashes.add(text_hash)
                candidates.append(block)

    return candidates


# ── Step 1: JSON-LD extraction ─────────────────────────────────────────────────

def _extract_json_ld(json_ld_blocks: list) -> ExtractionResult:
    result = ExtractionResult()
    for block in json_ld_blocks:
        if isinstance(block, str):
            try:
                block = json.loads(block)
            except (json.JSONDecodeError, ValueError):
                continue
        if not isinstance(block, dict):
            continue
        if block.get("@type") != "Product":
            continue

        # Try to get price
        offers = block.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price_raw = offers.get("price") or block.get("price")
        if price_raw:
            try:
                result.price = float(str(price_raw).replace("$", "").strip())
            except (ValueError, TypeError):
                pass

        result.brand = (
            (block.get("brand") or {}).get("name")
            if isinstance(block.get("brand"), dict)
            else block.get("brand")
        )
        result.product_name = block.get("name")

        # Try to extract composition from description
        desc = block.get("description") or ""
        if desc:
            fibers = extract_by_regex(desc)
            if fibers:
                result.composition_blocks.append(
                    CompositionBlock(
                        part="unknown",
                        fibers=fibers,
                        confidence_weight=0.8,
                        source="json_ld",
                    )
                )
                result.composition_raw = desc[:200]
                result.extraction_method = "json_ld"

    return result


# ── Step 2: Meta tag supplement ────────────────────────────────────────────────

def _apply_meta(result: ExtractionResult, meta: dict) -> None:
    if not result.price:
        for key in ("product:price:amount", "og:price:amount", "price"):
            if meta.get(key):
                try:
                    result.price = float(str(meta[key]).replace("$", "").strip())
                    break
                except (ValueError, TypeError):
                    pass
    if not result.brand and meta.get("og:site_name"):
        result.brand = meta["og:site_name"]
    if not result.product_name and meta.get("og:title"):
        result.product_name = meta["og:title"]


# ── Step 5: Normalization ──────────────────────────────────────────────────────

def _apply_normalization(result: ExtractionResult) -> ExtractionResult:
    for block in result.composition_blocks:
        normalized = []
        seen = set()
        for fiber_entry in block.fibers:
            canon = normalize_fiber(fiber_entry["fiber"])
            if canon not in seen:
                seen.add(canon)
                normalized.append({"fiber": canon, "pct": fiber_entry["pct"]})
        block.fibers = normalized
    return result


# ── Step 6: Validation + reconciliation ───────────────────────────────────────

def _apply_validation(result: ExtractionResult) -> ExtractionResult:
    total_confidence = 0.0
    count = 0

    for block in result.composition_blocks:
        pct_sum = block.pct_sum()
        if 95 <= pct_sum <= 105:
            block.confidence_weight = max(block.confidence_weight, 0.9)
        elif 60 <= pct_sum < 95:
            block.confidence_weight = min(block.confidence_weight, 0.6)
            result.warnings.append(f"Partial composition ({pct_sum:.0f}% — may be incomplete)")
        else:
            block.confidence_weight = min(block.confidence_weight, 0.3)
            result.warnings.append(f"Unusual percentage total ({pct_sum:.0f}%)")

        total_confidence += block.confidence_weight
        count += 1

    if count > 0:
        avg = total_confidence / count
        result._confidence_score = avg
        if avg >= 0.75:
            result.extraction_confidence = "high"
        elif avg >= 0.5:
            result.extraction_confidence = "medium"
        else:
            result.extraction_confidence = "low"

    return result


def _select_main_composition(result: ExtractionResult) -> None:
    """Choose main_composition from blocks. Prefer shell/body; else single block; else null."""
    if not result.composition_blocks:
        result.main_composition = None
        return

    # Priority 1: explicitly labeled shell or body
    for part in ("shell", "body", "outer"):
        for block in result.composition_blocks:
            if block.part == part:
                result.main_composition = block.fibers
                return

    # Priority 2: single unambiguous block
    if len(result.composition_blocks) == 1:
        result.main_composition = result.composition_blocks[0].fibers
        return

    # Priority 3: null — let UI explain
    result.main_composition = None


def _detect_block_part(text: str) -> str:
    """Detect if text has a multi-block prefix like 'Shell:' or 'Lining:'."""
    m = _BLOCK_PREFIX_RE.match(text.strip())
    if m:
        return m.group(1).lower()
    return "unknown"
```

**Step 4: Run regex tests**
```bash
python -m pytest scoring/test_extractor.py -k "regex" -v
```
Expected: All PASS

**Step 5: Commit**
```bash
git add scoring/extractor.py scoring/test_extractor.py
git commit -m "feat: contextual regex extraction with fiber vocab"
```

---

## Task 3: JSON-LD + candidate block extraction tests

**Files:**
- Modify: `scoring/test_extractor.py`

**Step 1: Add tests for JSON-LD and candidate block isolation**

```python
# Add to scoring/test_extractor.py

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
    # Shipping block should not dominate
    assert not any("free shipping" in b.lower() and "cotton" not in b.lower() for b in blocks)

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
```

**Step 2: Run tests**
```bash
python -m pytest scoring/test_extractor.py -v
```
Expected: All PASS

**Step 3: Commit**
```bash
git add scoring/test_extractor.py
git commit -m "test: JSON-LD, candidate block isolation, validation tests"
```

---

## Task 4: GPT fallback resolver (Step 4)

**Files:**
- Modify: `scoring/extractor.py`
- Modify: `scoring/test_extractor.py`

**Step 1: Add GPT fallback test (mocked)**

```python
# Add to scoring/test_extractor.py
from unittest.mock import MagicMock, patch

def test_gpt_fallback_parses_response():
    from scoring.extractor import _call_gpt_resolver
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps({
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
    import json
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
```

**Step 2: Run to verify fail**
```bash
python -m pytest scoring/test_extractor.py -k "gpt" -v
```
Expected: `ImportError` — `_call_gpt_resolver` not yet defined

**Step 3: Add `_call_gpt_resolver` to `scoring/extractor.py`**

Add at the end of `scoring/extractor.py`:

```python
# ── Step 4: GPT resolver ───────────────────────────────────────────────────────

_GPT_RESOLVER_PROMPT = """You are a clothing product data extractor. Extract ONLY what is explicitly stated.
Return valid JSON only. No explanation outside the JSON.

Schema:
{
  "product_name": "string or null",
  "price": "number or null",
  "brand": "string or null",
  "composition_blocks": [
    {"part": "shell|lining|trim|body|unknown",
     "fibers": [{"fiber": "lowercase fiber name", "pct": number}]}
  ],
  "main_composition": [{"fiber": "string", "pct": number}] or null,
  "confidence": "high|medium|low",
  "reasoning": "one sentence"
}

Rules:
- Only include fibers with explicit percentages in the source text.
- main_composition = shell/body block if labeled; else single block; else null.
- fiber names must be lowercase canonical names (cotton, polyester, elastane, etc.).
- Do NOT guess or invent percentages.
"""


def _call_gpt_resolver(text: str, openai_client) -> ExtractionResult:
    """Call GPT-4o-mini to resolve composition from candidate text (fallback only)."""
    result = ExtractionResult()
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _GPT_RESOLVER_PROMPT},
                {"role": "user", "content": text[:1500]},  # hard cap
            ],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError, Exception) as e:
        log.warning("GPT resolver failed: %s", e)
        return result

    result.product_name = data.get("product_name")
    result.brand = data.get("brand")
    if data.get("price"):
        try:
            result.price = float(data["price"])
        except (ValueError, TypeError):
            pass

    for block_data in data.get("composition_blocks") or []:
        fibers = [
            {"fiber": normalize_fiber(f["fiber"]), "pct": float(f["pct"])}
            for f in (block_data.get("fibers") or [])
            if f.get("fiber") and f.get("pct") is not None
            and is_known_fiber(normalize_fiber(f["fiber"]))
        ]
        if fibers:
            result.composition_blocks.append(
                CompositionBlock(
                    part=block_data.get("part", "unknown"),
                    fibers=fibers,
                    confidence_weight=0.6,
                    source="gpt",
                )
            )

    raw_main = data.get("main_composition") or []
    if raw_main:
        result.main_composition = [
            {"fiber": normalize_fiber(f["fiber"]), "pct": float(f["pct"])}
            for f in raw_main
            if f.get("fiber") and f.get("pct") is not None
        ]

    result.extraction_method = "gpt"
    result._confidence_score = {"high": 0.7, "medium": 0.5, "low": 0.3}.get(
        data.get("confidence", "low"), 0.3
    )
    result.extraction_confidence = data.get("confidence", "low")
    return result
```

**Step 4: Run all extractor tests**
```bash
python -m pytest scoring/test_extractor.py -v
```
Expected: All PASS

**Step 5: Commit**
```bash
git add scoring/extractor.py scoring/test_extractor.py
git commit -m "feat: GPT-4o-mini fallback resolver with mocked tests"
```

---

## Task 5: New backend endpoints + result store

**Files:**
- Modify: `app.py`

**Step 1: Add result store + `/api/score-page` + `/api/result/<uuid>` to `app.py`**

Add after the `_extraction_cache` line near the top of `app.py`:

```python
import uuid as _uuid_module
import time

# Result store for extension flow: uuid → { result, expires_at }
_result_store: dict[str, dict] = {}
_RESULT_TTL_SECONDS = 300  # 5 minutes
```

Add two new routes after the existing `@app.route("/methodology")` route:

```python
@app.route("/api/score-page", methods=["POST", "OPTIONS"])
def score_page_endpoint():
    """
    Extension endpoint. Receives pre-extracted page data from content.js.
    Runs the production extraction pipeline, stores result, returns { result_id }.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()

    try:
        data = request.get_json(force=True, silent=True) or {}
        price = _parse_price(data.get("price"))
        category = data.get("category", "other")

        # Run production extraction pipeline
        from scoring.extractor import extract_from_payload, _call_gpt_resolver
        result_extraction = extract_from_payload(data)

        # GPT fallback if still no composition
        if not result_extraction.composition_blocks:
            candidate_text = " ".join(data.get("candidate_blocks") or [])
            if candidate_text:
                result_extraction = _call_gpt_resolver(candidate_text, openai_client)

        if not result_extraction.composition_blocks:
            return jsonify({
                "error": "No fiber composition found on this page.",
                "error_type": "empty"
            }), 422

        composition = result_extraction.main_composition or (
            result_extraction.composition_blocks[0].fibers
            if result_extraction.composition_blocks else []
        )
        if price is None:
            price = result_extraction.price
        if category == "other" and result_extraction.category:
            category = result_extraction.category

        brand = result_extraction.brand
        construction = score_from_text(
            " ".join(data.get("candidate_blocks") or []),
            price, category, brand=brand
        )

        score_result = score_item(
            composition=composition,
            price=price,
            category=category,
            construction=construction,
        )
        result_dict = score_result.to_dict()
        result_dict.update(result_extraction.to_dict())

        # Store with TTL
        result_id = str(_uuid_module.uuid4())
        _result_store[result_id] = {
            "result": result_dict,
            "expires_at": time.time() + _RESULT_TTL_SECONDS,
        }
        _cleanup_result_store()

        return jsonify({"result_id": result_id})

    except OpenAIError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/result/<result_id>", methods=["GET", "OPTIONS"])
def get_result_endpoint(result_id: str):
    """Fetch a previously scored result by UUID (used by web app after extension opens it)."""
    if request.method == "OPTIONS":
        return _cors_preflight()

    entry = _result_store.get(result_id)
    if not entry:
        return jsonify({"error": "Result not found or expired", "error_type": "expired"}), 404
    if time.time() > entry["expires_at"]:
        del _result_store[result_id]
        return jsonify({"error": "Result expired", "error_type": "expired"}), 404

    return jsonify(entry["result"])


def _cleanup_result_store():
    """Evict expired entries. Call periodically to prevent memory growth."""
    now = time.time()
    expired = [k for k, v in _result_store.items() if now > v["expires_at"]]
    for k in expired:
        del _result_store[k]


def _cors_preflight():
    """Return CORS preflight response for extension requests."""
    resp = jsonify({})
    resp.headers["Access-Control-Allow-Origin"] = "*"  # tighten to extension ID in production
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp, 204


# Add CORS headers to extension endpoints after each response
@app.after_request
def add_cors_headers(response):
    # Only add CORS for the extension API endpoints
    if request.path.startswith("/api/score-page") or request.path.startswith("/api/result/"):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
```

**Step 2: Verify app starts**
```bash
cd /Users/desiraesidhu/clothing_quality_backend
python -c "from app import app; print('OK')"
```
Expected: `OK`

**Step 3: Smoke test new endpoints locally**
```bash
# Start server
python app.py &
sleep 2

# Test score-page with minimal payload
curl -s -X POST http://localhost:5001/api/score-page \
  -H "Content-Type: application/json" \
  -d '{"candidate_blocks": ["Material: 100% cotton"], "price": 40, "category": "t-shirt"}' | python -m json.tool

# Kill server
kill %1
```
Expected: JSON with `result_id` field

**Step 4: Commit**
```bash
git add app.py
git commit -m "feat: /api/score-page and /api/result/<uuid> endpoints with TTL store"
```

---

## Task 6: Update existing URL extraction path to use new pipeline

**Files:**
- Modify: `app.py`

**Step 1: Update `_extract_from_url` to use new extractor for Steps 0–3**

In `app.py`, find the `_extract_from_url` function. Replace the section after `page_text` is fetched (starting at `# Truncate to ~8000 chars`) with:

```python
    # ── New production pipeline ────────────────────────────────────────────
    from scoring.extractor import (
        isolate_candidate_blocks, extract_from_payload, _call_gpt_resolver
    )

    # Step 0: candidate block isolation from fetched HTML
    candidate_blocks = []
    if hasattr(response, 'text'):  # requests response available
        candidate_blocks = isolate_candidate_blocks(response.text)

    # Build payload for extract_from_payload
    payload = {
        "url": url,
        "json_ld": _extract_json_ld_from_html(page_text),
        "meta": _extract_meta_from_html(page_text),
        "candidate_blocks": candidate_blocks or [page_text[:3000]],
    }

    extraction = extract_from_payload(payload)

    # GPT fallback if needed
    if not extraction.composition_blocks:
        fallback_text = " ".join(candidate_blocks[:3]) if candidate_blocks else page_text[:2000]
        extraction = _call_gpt_resolver(fallback_text, openai_client)

    result = extraction.to_dict()
    result["_page_text"] = " ".join(candidate_blocks) if candidate_blocks else page_text[:3000]
    _extraction_cache[cache_key] = result
    return result
```

Add two helper functions to `app.py` (after `_blocked_domain_hint`):

```python
def _extract_json_ld_from_html(html_or_text: str) -> list:
    """Extract JSON-LD blocks from raw HTML."""
    try:
        soup = BeautifulSoup(html_or_text, "lxml")
        blocks = []
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string or ""
            try:
                blocks.append(json.loads(raw))
            except (json.JSONDecodeError, ValueError):
                blocks.append(raw)  # send raw for fallback
        return blocks
    except Exception:
        return []


def _extract_meta_from_html(html_or_text: str) -> dict:
    """Extract key meta tags from raw HTML."""
    meta = {}
    try:
        soup = BeautifulSoup(html_or_text, "lxml")
        for tag in soup.find_all("meta"):
            name = tag.get("property") or tag.get("name") or ""
            content = tag.get("content") or ""
            if name and content:
                meta[name] = content
    except Exception:
        pass
    return meta
```

**Step 2: Verify app still starts**
```bash
python -c "from app import app; print('OK')"
```

**Step 3: Commit**
```bash
git add app.py
git commit -m "feat: URL extraction path uses new production pipeline"
```

---

## Task 7: Web app — render result from UUID on load

**Files:**
- Modify: `static/app.js`

**Step 1: Add result-from-UUID rendering to `static/app.js`**

Find the `DOMContentLoaded` event listener (or the top of `app.js`). Add at the very beginning:

```javascript
// ── Extension result: render score if ?result=UUID is in URL ─────────────
(function checkExtensionResult() {
  const params = new URLSearchParams(window.location.search);
  const resultId = params.get('result');
  if (!resultId) return;

  // Show loading state, hide input form
  const inputSection = document.querySelector('.input-section') ||
                       document.querySelector('form') ||
                       document.getElementById('input-area');
  if (inputSection) inputSection.hidden = true;

  const status = document.getElementById('status') ||
                 document.createElement('p');
  status.textContent = 'Loading score…';
  document.body.prepend(status);

  fetch(`/api/result/${resultId}`)
    .then(r => {
      if (r.status === 404) throw new Error('expired');
      if (!r.ok) throw new Error('fetch_failed');
      return r.json();
    })
    .then(data => {
      status.remove();
      if (inputSection) inputSection.hidden = false;
      renderResult(data);  // existing function
    })
    .catch(err => {
      status.textContent = err.message === 'expired'
        ? 'Score expired — please re-scan the page.'
        : 'Could not load score. Please try again.';
      if (inputSection) inputSection.hidden = false;
    });
})();
```

**Step 2: Verify no JS errors by running locally**
```bash
python app.py &
sleep 1
# Open browser to http://localhost:5001/?result=nonexistent
# Should show "Score expired" message, not crash
kill %1
```

**Step 3: Commit**
```bash
git add static/app.js
git commit -m "feat: render extension result from ?result=UUID on page load"
```

---

## Task 8: Chrome extension — manifest + content script

**Files:**
- Create: `extension/manifest.json`
- Create: `extension/content.js`
- Create: `extension/icons/` (placeholder)

**Step 1: Create extension directory and icons placeholder**
```bash
mkdir -p /Users/desiraesidhu/clothing_quality_backend/extension/icons
# Create placeholder 48x48 icon (replace with real icon later)
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (48, 48), color=(20, 20, 20))
d = ImageDraw.Draw(img)
d.text((8, 16), 'w?', fill=(255, 200, 0))
img.save('extension/icons/icon48.png')
img.save('extension/icons/icon128.png')
img.save('extension/icons/icon16.png')
" 2>/dev/null || \
python3 -c "
# Fallback: create minimal valid PNG bytes
import struct, zlib
def make_png(size):
    def png_chunk(name, data):
        c = zlib.crc32(name + data) & 0xffffffff
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', c)
    w = h = size
    raw = b'\\x00' + b'\\x14\\x14\\x14' * w
    idat = zlib.compress(raw * h)
    return (b'\\x89PNG\\r\\n\\x1a\\n' +
            png_chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
            png_chunk(b'IDAT', idat) + png_chunk(b'IEND', b''))
for s in [16, 48, 128]:
    open(f'extension/icons/icon{s}.png', 'wb').write(make_png(s))
print('Icons created')
"
```

**Step 2: Create `extension/manifest.json`**

```json
{
  "manifest_version": 3,
  "name": "worth it? — fiber science scorer",
  "version": "0.1.0",
  "description": "Score any clothing item's quality using fiber science. Works on Zara, ASOS, and all major retailers.",
  "permissions": ["activeTab", "scripting"],
  "host_permissions": [
    "https://web-production-adff3.up.railway.app/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

**Step 3: Create `extension/content.js`**

```javascript
/**
 * content.js — runs against the live rendered DOM in the active tab (isolated world).
 * Extracts product data and returns it to popup.js via chrome.runtime.sendMessage.
 *
 * Triggered on-demand by popup.js via chrome.scripting.executeScript.
 */

(function extractProductData() {
  const result = {
    url: window.location.href,
    json_ld: [],
    json_ld_raw: [],
    meta: {},
    candidate_blocks: [],
  };

  // ── JSON-LD blocks ─────────────────────────────────────────────────────────
  document.querySelectorAll('script[type="application/ld+json"]').forEach(script => {
    const raw = (script.textContent || '').trim();
    if (!raw) return;
    try {
      result.json_ld.push(JSON.parse(raw));
    } catch {
      result.json_ld_raw.push(raw);  // malformed — preserve for backend fallback
    }
  });

  // ── Meta tags ──────────────────────────────────────────────────────────────
  const WANTED_META = new Set([
    'og:title', 'og:description', 'og:price:amount',
    'product:price:amount', 'og:site_name', 'og:brand',
  ]);
  document.querySelectorAll('meta[property], meta[name]').forEach(tag => {
    const key = tag.getAttribute('property') || tag.getAttribute('name') || '';
    const val = tag.getAttribute('content') || '';
    if (WANTED_META.has(key) && val) result.meta[key] = val;
  });

  // ── Candidate block isolation (Step 0, runs in live DOM) ──────────────────
  const DETAIL_LABELS = new Set([
    'materials', 'material', 'fabric', 'composition', 'care', 'details',
    'shell', 'lining', 'body', 'trim', 'content', 'construction',
    'product details', 'fabric & care', 'material & care',
    'fiber content', 'fibre content', 'fabric content',
  ]);

  const seenHashes = new Set();

  function textHash(s) {
    let h = 0;
    for (let i = 0; i < Math.min(s.length, 200); i++) {
      h = (h * 31 + s.charCodeAt(i)) >>> 0;
    }
    return h;
  }

  function addCandidate(text) {
    if (!text || text.length < 10 || text.length > 800) return;
    const h = textHash(text.trim());
    if (seenHashes.has(h)) return;
    seenHashes.add(h);
    result.candidate_blocks.push(text.trim());
  }

  // Walk all nodes looking for label matches
  const allNodes = document.querySelectorAll(
    'h1,h2,h3,h4,h5,h6,button,label,summary,dt,th,span,div,p'
  );

  allNodes.forEach(node => {
    const labelText = (node.textContent || '').trim().toLowerCase();
    if (labelText.length > 60) return;  // too long to be a label
    if (!DETAIL_LABELS.has(labelText)) return;

    // Collect this node + nearby siblings + parent container
    const parts = [];

    // Next siblings (bounded)
    let sibling = node.nextElementSibling;
    let charCount = 0;
    while (sibling && charCount < 500) {
      const t = sibling.textContent.trim();
      if (t) { parts.push(t); charCount += t.length; }
      sibling = sibling.nextElementSibling;
    }

    // Parent container
    if (node.parentElement) {
      const parentText = node.parentElement.textContent.trim();
      if (parentText.length < 700) parts.push(parentText);
    }

    if (parts.length > 0) addCandidate(parts.join(' '));
  });

  // Fallback: grab <details>/<summary> contents (accordions)
  document.querySelectorAll('details').forEach(details => {
    const summaryText = (details.querySelector('summary') || {}).textContent || '';
    if (DETAIL_LABELS.has(summaryText.trim().toLowerCase())) {
      addCandidate(details.textContent.trim().slice(0, 600));
    }
  });

  return result;
})();
```

**Step 4: Commit**
```bash
git add extension/
git commit -m "feat: Chrome extension — manifest.json + content.js"
```

---

## Task 9: Chrome extension — popup UI

**Files:**
- Create: `extension/popup.html`
- Create: `extension/popup.js`

**Step 1: Create `extension/popup.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>worth it?</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      width: 280px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #111;
      color: #eee;
      padding: 20px;
    }
    .logo {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: -0.5px;
      margin-bottom: 4px;
    }
    .tagline {
      font-size: 10px;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 20px;
    }
    #score-btn {
      width: 100%;
      padding: 12px;
      background: #f0c040;
      color: #111;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.15s;
    }
    #score-btn:disabled { opacity: 0.5; cursor: default; }
    #score-btn:hover:not(:disabled) { opacity: 0.85; }
    #status {
      margin-top: 14px;
      font-size: 12px;
      color: #aaa;
      line-height: 1.5;
      min-height: 18px;
    }
    #status.error { color: #e07070; }
  </style>
</head>
<body>
  <div class="logo">worth it?</div>
  <div class="tagline">Fiber science, not opinion</div>
  <button id="score-btn">Score this page</button>
  <div id="status"></div>
  <script src="popup.js"></script>
</body>
</html>
```

**Step 2: Create `extension/popup.js`**

```javascript
/**
 * popup.js — orchestrates the extension flow:
 * 1. Inject content.js into current tab
 * 2. Receive extracted payload
 * 3. POST to /api/score-page
 * 4. Open web app with ?result=UUID
 */

const API_BASE = "https://web-production-adff3.up.railway.app";
const btn = document.getElementById("score-btn");
const status = document.getElementById("status");

function setStatus(msg, isError = false) {
  status.textContent = msg;
  status.className = isError ? "error" : "";
}

btn.addEventListener("click", async () => {
  btn.disabled = true;
  setStatus("Scanning page…");

  try {
    // Step 1: Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("no_tab");

    // Step 2: Inject content.js and get extracted data
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });

    // executeScript with a file runs the IIFE and returns its value
    // For content.js that returns a value, use func injection:
    const [{ result: payload }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        // Re-run extraction inline (content.js IIFE result)
        const r = {
          url: window.location.href,
          json_ld: [],
          json_ld_raw: [],
          meta: {},
          candidate_blocks: [],
        };
        document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
          try { r.json_ld.push(JSON.parse(s.textContent)); }
          catch { r.json_ld_raw.push(s.textContent || ""); }
        });
        const WANTED = new Set(["og:title","og:description","og:price:amount","product:price:amount","og:site_name"]);
        document.querySelectorAll("meta[property],meta[name]").forEach(t => {
          const k = t.getAttribute("property") || t.getAttribute("name") || "";
          const v = t.getAttribute("content") || "";
          if (WANTED.has(k) && v) r.meta[k] = v;
        });
        const LABELS = new Set(["materials","material","fabric","composition","care","details","shell","lining","body","trim","content","construction","product details","fabric & care","material & care","fiber content","fibre content"]);
        const seen = new Set();
        document.querySelectorAll("h1,h2,h3,h4,h5,h6,button,label,summary,dt,th,span,div,p").forEach(node => {
          const lbl = (node.textContent || "").trim().toLowerCase();
          if (lbl.length > 60 || !LABELS.has(lbl)) return;
          const parts = [];
          let sib = node.nextElementSibling, cc = 0;
          while (sib && cc < 500) { const t = sib.textContent.trim(); if (t) { parts.push(t); cc += t.length; } sib = sib.nextElementSibling; }
          if (node.parentElement) { const pt = node.parentElement.textContent.trim(); if (pt.length < 700) parts.push(pt); }
          if (parts.length) { const block = parts.join(" ").trim(); const h = block.slice(0,100); if (!seen.has(h) && block.length > 10) { seen.add(h); r.candidate_blocks.push(block.slice(0,600)); } }
        });
        return r;
      },
    });

    if (!payload) throw new Error("no_data");
    if (!payload.candidate_blocks.length && !payload.json_ld.length) {
      throw new Error("no_product");
    }

    setStatus("Scoring…");

    // Step 3: POST to /api/score-page
    const response = await fetch(`${API_BASE}/api/score-page`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      if (err.error_type === "empty") throw new Error("no_composition");
      throw new Error("api_error");
    }

    const { result_id } = await response.json();
    if (!result_id) throw new Error("api_error");

    // Step 4: Open web app with result
    await chrome.tabs.create({ url: `${API_BASE}?result=${result_id}` });
    window.close();

  } catch (err) {
    const messages = {
      no_tab: "Could not access the current tab.",
      no_data: "Could not read this page.",
      no_product: "No product info found — try the paste text tab on the web app.",
      no_composition: "No material composition found on this page.",
      api_error: "Scoring failed — try again.",
      default: "Something went wrong. Try again.",
    };
    setStatus(messages[err.message] || messages.default, true);
    btn.disabled = false;
  }
});
```

**Step 3: Commit**
```bash
git add extension/popup.html extension/popup.js
git commit -m "feat: Chrome extension popup UI and orchestration"
```

---

## Task 10: Load extension locally and smoke test

**Step 1: Open Chrome extension management**
```
Navigate to: chrome://extensions/
Toggle on "Developer mode" (top right)
Click "Load unpacked"
Select: /Users/desiraesidhu/clothing_quality_backend/extension/
```
Extension should appear with "worth it?" name.

**Step 2: Test on a non-blocked site**
1. Navigate to a Uniqlo or Everlane product page
2. Click the "worth it?" extension icon
3. Click "Score this page"
4. Expected: new tab opens at `web-production-adff3.up.railway.app?result=<uuid>` with score

**Step 3: Test on Zara**
1. Navigate to any Zara product page (e.g., the blocked sweater URL)
2. Click extension icon → "Score this page"
3. Expected: score loads in new tab (Zara's DOM is readable even though server-side scraping is blocked)

**Step 4: Test error states**
1. Go to a non-product page (e.g., google.com)
2. Click extension → expected: "No product info found" error
3. Close extension popup

---

## Task 11: Push to GitHub, verify Railway redeploy

**Step 1: Push all backend changes**
```bash
cd /Users/desiraesidhu/clothing_quality_backend
git push origin main
```

**Step 2: Watch Railway build**
Go to `railway.com` → `determined-flow` project → watch Activity panel for "Deployment successful"

**Step 3: Re-test extension against live Railway URL**
1. Reload extension at `chrome://extensions/`
2. Test on Zara product page
3. Verify score loads at `web-production-adff3.up.railway.app?result=<uuid>`

**Step 4: Update extension if Railway URL changes**
If Railway generates a new URL, update `API_BASE` in `extension/popup.js` and reload.

---

## Notes for Implementer

- **Tests location:** `scoring/test_extractor.py` — run with `pytest scoring/test_extractor.py -v`
- **No new pip packages needed** — uses existing `beautifulsoup4`, `openai`, `flask`
- **Extension not submitted to Chrome Web Store** — load unpacked for personal use; submission is a manual step
- **Result store is in-memory** — Railway restarts clear it; acceptable for MVP. Upgrade to Redis later.
- **CORS `*` wildcard** — acceptable for MVP; tighten to specific extension ID before public launch
- **content.js is duplicated** in `content.js` file and inlined in `popup.js` `func:` injection — this is intentional for MV3 compatibility; the file is kept for reference/maintenance
