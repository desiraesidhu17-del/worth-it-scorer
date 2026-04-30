"""
Construction quality scoring — Methodology v1.0

Three input modes (combinable):
  text   — extract visible construction signals from product description text
  image  — GPT-4o vision rubric: structured checklist of what can be seen
  floor  — price-tier floor: what construction is economically impossible at this price

Score: 0–10 (displayed as x/10)
  8–10  Excellent — premium construction signals visible
  6–7   Good — above-average for price tier
  4–5   Expected — typical for this price and category
  2–3   Below expectations — missing signals expected at this price
  0–1   Poor — active negative signals

Confidence:
  high    — image analysis with clear construction details visible
  medium  — text signals found, or image with limited visibility
  low     — price floor only; no image or text construction data
"""

import json
import re
from dataclasses import dataclass, field


# ── Price-tier construction floors ────────────────────────────────────────────
# At certain price points, certain constructions are economically impossible.
# These are mathematical lower bounds on expected quality — not guarantees.
#
# Format: (min_price, max_price_exclusive, expected_level, description)
# max_price_exclusive = None means "and above"

_PRICE_FLOORS = {
    "dress": [
        (0,    30,   "basic",    "Serged seams, unlined, no pattern matching"),
        (30,   80,   "standard", "May have partial lining, clean finishes on visible seams"),
        (80,   160,  "good",     "Should have lining, clean finishes throughout, quality closures"),
        (160,  None, "premium",  "Should have French or flat-felled seams, full lining, natural hardware"),
    ],
    "sweater": [
        (0,    40,   "basic",    "Basic construction; serged or linked seams"),
        (40,   100,  "standard", "Linked or clean seams; should be true full-fashion knit above $80"),
        (100,  None, "premium",  "Should be full-fashion knit with hand-finished details"),
    ],
    "t-shirt": [
        (0,    20,   "basic",    "Single-stitched hems, serged seams"),
        (20,   60,   "standard", "Double-stitched hems expected; reinforced collar"),
        (60,   None, "good",     "Premium cotton with reinforced seams and quality hem"),
    ],
    "jeans": [
        (0,    50,   "basic",    "Standard 5-pocket construction"),
        (50,   120,  "standard", "Flat-felled seams expected, quality hardware"),
        (120,  None, "premium",  "Chain-stitched, flat-felled seams, selvedge or premium denim"),
    ],
    "outerwear": [
        (0,    80,   "basic",    "Serged seams, partial lining"),
        (80,   200,  "standard", "Full lining, quality zipper, clean seams"),
        (200,  None, "premium",  "Taped seams or French seams, full lining, quality hardware"),
    ],
    "activewear": [
        (0,    40,   "basic",    "Flatlock or serged seams"),
        (40,   100,  "standard", "Flatlock seams throughout, quality elastic"),
        (100,  None, "premium",  "Bonded or ultrasonically welded seams, premium elastic"),
    ],
    "other": [
        (0,    40,   "basic",    "Standard construction expected"),
        (40,   120,  "standard", "Clean finishes and quality closures expected"),
        (120,  None, "good",     "Premium construction expected at this price"),
    ],
}

_FLOOR_SCORE = {"basic": 4, "standard": 5, "good": 6, "premium": 7}
_FLOOR_BELOW_PENALTY = {"basic": -1, "standard": -2, "good": -2, "premium": -3}


# ── Text signal dictionaries ───────────────────────────────────────────────────
# Keywords in product descriptions that signal construction quality.
# Scores are additive; capped at ±3 from text alone.

_TEXT_SIGNALS_POSITIVE: list[tuple[str, float, str]] = [
    # (pattern, points, display_label)
    (r"french seam",                 2.0, "French seams"),
    (r"flat[-\s]felled seam",        2.0, "Flat-felled seams"),
    (r"fully lined",                 1.5, "Fully lined"),
    (r"full lining",                 1.5, "Fully lined"),
    (r"double[-\s]stitched",         1.0, "Double-stitched"),
    (r"blind hem",                   1.0, "Blind hem"),
    (r"ykk",                         0.5, "YKK zipper"),
    (r"horn button",                 1.0, "Horn buttons"),
    (r"shell button",                1.0, "Shell buttons"),
    (r"mother[-\s]of[-\s]pearl",     1.0, "Mother-of-pearl buttons"),
    (r"hand[-\s]finished",           1.0, "Hand-finished"),
    (r"hand[-\s]stitched",           1.0, "Hand-stitched"),
    (r"bonded seam",                 1.5, "Bonded seams"),
    (r"flatlock",                    0.5, "Flatlock seams"),
    (r"full[-\s]fashion",            1.5, "Full-fashion knit"),
    (r"selvedge",                    1.5, "Selvedge denim"),
    (r"chain[-\s]stitch",            1.0, "Chain-stitched"),
    (r"topstitch",                   0.5, "Topstitching"),
    (r"interlock",                   0.5, "Interlock knit"),
    (r"\blined\b(?!\s+for\s+added\s+warmth)", 0.5, "Lined"),
]

_TEXT_SIGNALS_NEGATIVE: list[tuple[str, float, str]] = [
    (r"\bunlined\b",                -0.5, "Unlined"),
    (r"lined for added warmth:\s*no", -0.5, "Unlined"),
    (r"not lined",                  -0.5, "Unlined"),
    (r"serged",                     -0.5, "Serged seams"),
    (r"overlock",                   -0.5, "Overlocked seams"),
    (r"plastic button",             -0.5, "Plastic buttons"),
    (r"plastic zipper",             -0.5, "Plastic zipper"),
]


# ── GPT-4o construction vision prompt ─────────────────────────────────────────

_CONSTRUCTION_IMAGE_PROMPT = """You are a garment construction quality analyst.
Examine this product image and identify specific construction signals.

Return ONLY valid JSON with this exact schema — no explanation, no extra keys:

{
  "seam_finish": "<french|flat-felled|clean|serged|flatlock|unknown>",
  "hem_type": "<double|blind|single|rolled|unknown>",
  "lining": "<full|partial|none|unknown>",
  "hardware": "<natural|quality-metal|plastic|unknown>",
  "pattern_match": <true|false|null>,
  "visible_signals": ["<specific observation>", ...],
  "confidence": "<high|medium|low>"
}

Rules:
- Use "unknown" if a signal is not clearly visible — never guess.
- visible_signals: list 2–5 concise observations of what you can actually see
  (e.g. "serged seam visible at side seam", "metal zipper with fabric pull tab",
  "interior lining visible at neckline", "pattern continues across seam").
- confidence "high" = clear construction details visible in image
- confidence "medium" = some details visible but limited view
- confidence "low" = image too distant or small to assess construction
"""

_SEAM_SCORES = {"french": 2, "flat-felled": 2, "clean": 1, "flatlock": 0.5, "serged": -0.5, "unknown": 0}
_HEM_SCORES  = {"double": 1, "blind": 1, "rolled": 0.5, "single": 0, "unknown": 0}
_LINING_SCORES = {"full": 1.5, "partial": 0.75, "none": 0, "unknown": 0}
_HARDWARE_SCORES = {"natural": 1, "quality-metal": 0.5, "plastic": -0.5, "unknown": 0}


# ── Data structure ─────────────────────────────────────────────────────────────

@dataclass
class ConstructionResult:
    score: float           # 0–10
    confidence: str        # "high" | "medium" | "low"
    signals_found: list[str] = field(default_factory=list)
    price_floor_level: str = ""      # "basic" | "standard" | "good" | "premium"
    price_floor_note: str = ""       # human-readable expectation
    source: str = "price_floor"      # "price_floor" | "text" | "image" | "text+image"
    raw_image_json: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "confidence": self.confidence,
            "signals_found": self.signals_found,
            "price_floor_level": self.price_floor_level,
            "price_floor_note": self.price_floor_note,
            "source": self.source,
        }


# ── Public API ────────────────────────────────────────────────────────────────

def score_from_price(price: float | None, category: str,
                     brand: str | None = None) -> ConstructionResult:
    """
    Return a construction score from price tier alone.
    This is a floor estimate — confidence is always low.
    """
    from .brand_db import brand_construction_modifier
    level, note = _price_floor(price, category)
    base = _FLOOR_SCORE.get(level, 5)

    signals = []
    brand_mod, brand_note = brand_construction_modifier(brand or "", category)
    if brand_note:
        signals.append(brand_note)

    score = max(0.0, min(10.0, base + brand_mod))
    return ConstructionResult(
        score=score,
        confidence="low",
        signals_found=signals,
        price_floor_level=level,
        price_floor_note=note,
        source="price_floor",
    )


def score_from_text(text: str, price: float | None, category: str,
                    brand: str | None = None) -> ConstructionResult:
    """
    Extract construction signals from product description text and combine with price floor.
    Confidence is medium if at least one signal is found, otherwise low.
    """
    from .brand_db import brand_construction_modifier
    level, note = _price_floor(price, category)
    base = _FLOOR_SCORE.get(level, 5)

    signals = []
    adjustment = 0.0
    seen_labels: set[str] = set()

    for pattern, pts, label in _TEXT_SIGNALS_POSITIVE:
        if label in seen_labels:
            continue
        if re.search(pattern, text, re.IGNORECASE):
            # Skip "Lined" if a more specific lining signal already matched
            if label == "Lined" and "Fully lined" in seen_labels:
                continue
            seen_labels.add(label)
            signals.append(label)
            adjustment += pts

    for pattern, pts, label in _TEXT_SIGNALS_NEGATIVE:
        if label in seen_labels:
            continue
        if re.search(pattern, text, re.IGNORECASE):
            seen_labels.add(label)
            signals.append(label)
            adjustment += pts  # pts is negative

    # Brand modifier
    brand_mod, brand_note = brand_construction_modifier(brand or "", category)
    if brand_note:
        signals.append(brand_note)

    # Cap text adjustment at ±3 to avoid overweighting description copy
    adjustment = max(-3.0, min(3.0, adjustment))
    score = max(0.0, min(10.0, base + adjustment + brand_mod))

    return ConstructionResult(
        score=score,
        confidence="medium" if signals else "low",
        signals_found=signals,
        price_floor_level=level,
        price_floor_note=note,
        source="text",
    )


def score_from_image(img_bytes: bytes, price: float | None, category: str,
                     openai_client, brand: str | None = None) -> ConstructionResult:
    """
    Score construction quality from a product image using GPT-4o vision.
    Combines image rubric with price-floor baseline.
    """
    import base64

    level, note = _price_floor(price, category)
    base = _FLOOR_SCORE.get(level, 5)

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text",      "text": _CONSTRUCTION_IMAGE_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ],
            }],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        raw = json.loads(response.choices[0].message.content)
    except Exception:
        # Graceful fallback to price-floor-only
        return score_from_price(price, category, brand=brand)

    # Score the rubric signals
    image_points = 0.0
    image_points += _SEAM_SCORES.get(raw.get("seam_finish", "unknown"), 0)
    image_points += _HEM_SCORES.get(raw.get("hem_type", "unknown"), 0)
    image_points += _LINING_SCORES.get(raw.get("lining", "unknown"), 0)
    image_points += _HARDWARE_SCORES.get(raw.get("hardware", "unknown"), 0)
    if raw.get("pattern_match") is True:
        image_points += 1.0

    # Brand modifier
    from .brand_db import brand_construction_modifier
    brand_mod, brand_note = brand_construction_modifier(brand or "", category)

    # Check if price is above/below the expected construction floor
    floor_adj = 0.0
    if price is not None:
        if level in ("basic",) and price < _floor_min(category, "standard"):
            floor_adj = _FLOOR_BELOW_PENALTY.get(level, -1)
        elif level == "premium":
            floor_adj = 0.5

    score = max(0.0, min(10.0, base + image_points + floor_adj + brand_mod))

    signals = raw.get("visible_signals", [])
    if brand_note:
        signals.append(brand_note)
    img_confidence = raw.get("confidence", "medium")
    confidence = img_confidence  # Trust GPT's self-assessment here

    return ConstructionResult(
        score=score,
        confidence=confidence,
        signals_found=signals,
        price_floor_level=level,
        price_floor_note=note,
        source="image",
        raw_image_json=raw,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _price_floor(price: float | None, category: str) -> tuple[str, str]:
    """Return (level, description) for this price and category."""
    cat = category if category in _PRICE_FLOORS else "other"
    floors = _PRICE_FLOORS[cat]

    if price is None:
        return "standard", "Price unknown — using average expectations."

    for (lo, hi, level, desc) in floors:
        if hi is None or price < hi:
            if price >= lo:
                return level, desc

    # Fallback to last tier
    return floors[-1][2], floors[-1][3]


def _floor_min(category: str, target_level: str) -> float:
    """Return minimum price for a construction level in a category."""
    cat = category if category in _PRICE_FLOORS else "other"
    for (lo, hi, level, desc) in _PRICE_FLOORS[cat]:
        if level == target_level:
            return float(lo)
    return 9999.0


def construction_label(score: float) -> str:
    if score >= 8: return "Excellent"
    if score >= 6: return "Good"
    if score >= 4: return "Average"
    if score >= 2: return "Below average"
    return "Poor"
