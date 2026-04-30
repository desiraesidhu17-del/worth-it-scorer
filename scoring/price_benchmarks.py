"""
Price benchmarks by category and material quality tier (US market, 2025–2026).

Sources:
- CNBC Fashion Industry Price Analysis (Oct 2025)
- JINFENG Apparel US market benchmarks
- Manual survey of major US retailers (Zara, Uniqlo, Everlane, Reformation,
  Free People, Madewell, Banana Republic, J.Crew, Target, H&M, ASOS)

Tiers are defined by the material durability score from the scoring engine:
- Budget tier: material durability score 0–40
- Mid tier:    material durability score 41–65
- Quality tier: material durability score 66–100

Price ranges represent the typical retail window for each tier.
A garment priced above its tier's max is considered "overpriced for quality."
A garment priced below its tier's min is either a genuine deal or unverifiable.
"""

from dataclasses import dataclass


@dataclass
class PriceBenchmark:
    category: str
    tier: str          # "budget" | "mid" | "quality"
    score_min: int     # minimum material durability score for this tier
    score_max: int     # maximum material durability score for this tier
    price_min: float   # typical low-end retail price (USD)
    price_max: float   # typical high-end retail price (USD)


PRICE_BENCHMARKS: list[PriceBenchmark] = [

    # Ranges reflect fair value for the fiber quality tier, anchored to value
    # retailers (Uniqlo, Target, Everlane basics) — not what premium brands
    # charge for the same fibers. Paying above the range max for a given tier
    # means you're paying a brand premium, not a quality premium.

    # ── T-shirt ───────────────────────────────────────────────────────────────
    PriceBenchmark("t-shirt", "budget",  0,  40,   6,  18),
    PriceBenchmark("t-shirt", "mid",    41,  65,  15,  40),
    PriceBenchmark("t-shirt", "quality",66, 100,  35,  80),

    # ── Sweater ───────────────────────────────────────────────────────────────
    PriceBenchmark("sweater", "budget",  0,  40,  15,  50),
    PriceBenchmark("sweater", "mid",    41,  65,  40,  90),
    PriceBenchmark("sweater", "quality",66, 100,  75, 260),

    # ── Dress ─────────────────────────────────────────────────────────────────
    PriceBenchmark("dress", "budget",  0,  40,  12,  55),
    PriceBenchmark("dress", "mid",    41,  65,  45, 110),
    PriceBenchmark("dress", "quality",66, 100,  95, 350),

    # ── Jeans ─────────────────────────────────────────────────────────────────
    PriceBenchmark("jeans", "budget",  0,  40,  18,  40),
    PriceBenchmark("jeans", "mid",    41,  65,  38,  80),
    PriceBenchmark("jeans", "quality",66, 100,  70, 220),

    # ── Outerwear / jackets / coats ───────────────────────────────────────────
    PriceBenchmark("outerwear", "budget",  0,  40,  35,  95),
    PriceBenchmark("outerwear", "mid",    41,  65,  80, 190),
    PriceBenchmark("outerwear", "quality",66, 100, 160, 550),

    # ── Activewear ────────────────────────────────────────────────────────────
    PriceBenchmark("activewear", "budget",  0,  40,  10,  30),
    PriceBenchmark("activewear", "mid",    41,  65,  25,  70),
    PriceBenchmark("activewear", "quality",66, 100,  55, 160),

    # ── Other (catch-all) ─────────────────────────────────────────────────────
    PriceBenchmark("other", "budget",  0,  40,   8,  45),
    PriceBenchmark("other", "mid",    41,  65,  35, 100),
    PriceBenchmark("other", "quality",66, 100,  80, 300),
]

# Construction quality floors by price tier
# At certain price points, certain constructions are economically impossible.
# These are used to flag when a brand charges a premium price but delivers
# budget-tier construction.
CONSTRUCTION_FLOORS: dict[str, dict] = {
    "under_25": {
        "label": "Under $25",
        "expected": "serged seams, no lining, minimal finishing",
        "score_floor": 0,
    },
    "25_to_75": {
        "label": "$25–$75",
        "expected": "may have partial lining, clean finishes on visible seams",
        "score_floor": 4,
    },
    "75_to_150": {
        "label": "$75–$150",
        "expected": "should have lining, clean finishes throughout, quality closures",
        "score_floor": 6,
    },
    "over_150": {
        "label": "Over $150",
        "expected": "should have French or flat-felled seams, full lining, natural hardware",
        "score_floor": 8,
    },
}


def get_benchmark(category: str, material_score: float) -> PriceBenchmark | None:
    """Return the price benchmark for a given category and material durability score."""
    cat = category.lower().strip()
    # Fall back to "other" if category not found
    available_cats = {b.category for b in PRICE_BENCHMARKS}
    if cat not in available_cats:
        cat = "other"

    for benchmark in PRICE_BENCHMARKS:
        if benchmark.category == cat and benchmark.score_min <= material_score <= benchmark.score_max:
            return benchmark
    return None


def get_construction_floor(price: float) -> dict:
    """Return the construction quality floor for a given retail price."""
    if price < 25:
        return CONSTRUCTION_FLOORS["under_25"]
    elif price < 75:
        return CONSTRUCTION_FLOORS["25_to_75"]
    elif price < 150:
        return CONSTRUCTION_FLOORS["75_to_150"]
    else:
        return CONSTRUCTION_FLOORS["over_150"]


_CATEGORY_PLURAL = {
    "dress":      "dresses",
    "jeans":      "jeans",
    "outerwear":  "outerwear",
    "activewear": "activewear",
    "other":      "items",
}


def _pluralize(category: str) -> str:
    return _CATEGORY_PLURAL.get(category, category + "s")


def evaluate_price_pressure(
    price: float,
    category: str,
    material_score: float,
) -> dict:
    """
    Returns a price pressure assessment dict:
    {
        "level":    "low" | "moderate" | "high" | "extreme",
        "label":    human-readable label,
        "benchmark": PriceBenchmark (or None),
        "detail":   sentence explaining the pressure level,
    }
    """
    benchmark = get_benchmark(category, material_score)
    if benchmark is None or price is None:
        return {
            "level": "unknown",
            "label": "Price pressure unknown",
            "benchmark": None,
            "detail": "Price or category data missing — cannot assess value.",
        }

    low, high = benchmark.price_min, benchmark.price_max

    # How far above the expected range is the price?
    if price <= high:
        ratio = 0.0
    else:
        ratio = (price - high) / high  # 0.5 = 50% above the top of range

    if ratio <= 0:
        level = "low"
        label = "Fairly priced"
        detail = (
            f"At ${price:.0f}, this is within the typical range (${low:.0f}–${high:.0f}) "
            f"for {benchmark.tier}-tier {_pluralize(category)}. The price is consistent with the material quality."
        )
    elif ratio <= 0.5:
        level = "moderate"
        label = "Slightly overpriced"
        detail = (
            f"At ${price:.0f}, this is above the typical range (${low:.0f}–${high:.0f}) "
            f"for {benchmark.tier}-tier {_pluralize(category)}. You are paying a modest premium for this material quality."
        )
    elif ratio <= 1.5:
        level = "high"
        label = "Overpriced for quality"
        detail = (
            f"At ${price:.0f}, this is significantly above the typical range (${low:.0f}–${high:.0f}) "
            f"for this material durability score. You are paying a {benchmark.tier}-tier price "
            f"for {'budget' if benchmark.tier == 'mid' else 'budget-to-mid'}-tier material quality."
        )
    else:
        level = "extreme"
        label = "Luxury price, budget-tier material"
        detail = (
            f"At ${price:.0f}, you are paying more than double the expected range "
            f"(${low:.0f}–${high:.0f}) for this material durability score. "
            f"The fiber composition does not support this price point."
        )

    return {
        "level": level,
        "label": label,
        "benchmark": benchmark,
        "detail": detail,
    }
