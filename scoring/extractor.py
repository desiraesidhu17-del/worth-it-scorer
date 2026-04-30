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


def _parse_price_raw(value) -> float | None:
    """Strip currency symbols/codes and return float, or None on failure.
    Handles: $217, CA$217, £89.99, €120, AU$145, 1,234.56, plain 217
    """
    if value is None:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


# ── Material context keywords — regex must find these near a % match ──────────
_MATERIAL_CONTEXT_RE = re.compile(
    r"\b(material|fabric|shell|lining|body|composition|trim|care|content|"
    r"fibre|fiber|outer|inside|fill|filling|made of|made from|made with)\b",
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

# ── DOM labels that indicate product detail sections ──────────────────────────
_DETAIL_LABELS = frozenset([
    "materials", "material", "fabric", "composition", "care", "details",
    "shell", "lining", "body", "trim", "content", "construction",
    "product details", "fabric & care", "material & care",
    "fiber content", "fibre content",
])

# Context window (chars around a % match to check for material keywords).
# 300 chars covers Madewell-style blocks where "The fabric:" label appears
# ~255 chars before the actual fiber percentages in the same candidate block.
_CONTEXT_WINDOW = 300

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
    gsm: Optional[float] = None

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
            "gsm": self.gsm,
        }


# ── Public entry points ────────────────────────────────────────────────────────

def extract_from_text(text: str) -> ExtractionResult:
    """Extract composition from plain text (paste-text path)."""
    result = ExtractionResult()
    result.gsm = _extract_gsm(text)
    fibers = extract_by_regex(text)
    if fibers:
        block = CompositionBlock(part="unknown", fibers=fibers, source="regex")
        result.composition_blocks = [block]
        result.extraction_method = "regex"
        result = _apply_validation(result)
        _select_main_composition(result)
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

    # Extract GSM from candidate text if not already found
    if result.gsm is None:
        all_candidate = " ".join(payload.get("candidate_blocks") or [])
        result.gsm = _extract_gsm(all_candidate)

    # Step 5+6: Normalize and validate
    if result.composition_blocks:
        result = _apply_normalization(result)
        result = _apply_validation(result)
        _select_main_composition(result)

    # Use payload price (extension already picks the right one via JSON-LD first)
    if payload.get("price"):
        result.price = _parse_price_raw(payload["price"])

    if payload.get("category"):
        result.category = payload["category"]
    else:
        # Infer category from URL + og:title — extension never sends this field
        infer_text = " ".join(filter(None, [
            payload.get("url", ""),
            (payload.get("meta") or {}).get("og:title", ""),
        ]))
        result.category = _infer_category(infer_text) or result.category

    return result


_CATEGORY_PATTERNS = [
    ("dress",      r"\b(dress(?:es)?|skirt|slip)\b"),
    ("sweater",    r"\b(sweater|knitwear|cardigan|pullover|crewneck|turtleneck|knit)\b"),
    ("t-shirt",    r"\b(t-shirt|tee|tank\s*top|crop\s*top)\b"),
    ("jeans",      r"\b(jeans?|denim|trousers?|pants?|chinos?|slacks)\b"),
    ("outerwear",  r"\b(jacket|coat|parka|puffer|anorak|windbreaker|outerwear|blazer)\b"),
    ("activewear", r"\b(leggings?|activewear|sports?\s*bra|shorts?|gym|yoga|athletic)\b"),
]


def _infer_category(text: str) -> Optional[str]:
    """Return a category string inferred from URL or product title, or None."""
    lowered = text.lower()
    for category, pattern in _CATEGORY_PATTERNS:
        if re.search(pattern, lowered):
            return category
    return None


# ── Step 3: Contextual regex ────────────────────────────────────────────────

def extract_by_regex(text: str) -> list[dict]:
    """
    Find fiber/percentage pairs in text using contextual filtering.
    Returns list of {"fiber": str, "pct": float} dicts.

    For short texts (≤300 chars, e.g. isolated candidate blocks or paste input),
    skip the context-keyword check and rely on is_known_fiber as the primary filter.
    For long texts (full product pages), require a material keyword nearby to avoid
    false positives from sale percentages, ratings, etc.
    """
    results: list[dict] = []
    seen_fibers: set[str] = set()
    is_short_text = len(text) <= 300

    for match in _PCT_FIBER_RE.finditer(text):
        pct_str, fiber_raw = match.group(1), match.group(2).strip()

        # Context check: only for long texts (full-page scans)
        if not is_short_text:
            start = max(0, match.start() - _CONTEXT_WINDOW)
            end = min(len(text), match.end() + _CONTEXT_WINDOW)
            context = text[start:end]
            if not _MATERIAL_CONTEXT_RE.search(context):
                # No material keyword nearby — skip unless we already have fibers
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
            result.price = _parse_price_raw(price_raw)

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
                parsed = _parse_price_raw(meta[key])
                if parsed:
                    result.price = parsed
                    break
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
