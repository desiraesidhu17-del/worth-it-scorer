"""
Pre-written verdict sentences mapped to score ranges and dominant fiber types.

These are authored, not AI-generated.
All sentences are framed as predictions based on fiber composition ("associated with",
"predicted to", "typical for") — NOT factual claims about manufacturing.

Legal framing: these represent consumer value guidance derived from published
fiber science, not claims about any specific garment's manufacturing process.
"""

# ── Worth-It Score verdict sentences ─────────────────────────────────────────
# Keyed by (score_band, dominant_fiber_class)
# score_band: "very_low" (0-25), "low" (26-45), "mid" (46-65),
#             "good" (66-80), "excellent" (81-100)
# dominant_fiber_class: "synthetic", "natural", "cellulosic", "mixed", "premium"

WORTH_IT_VERDICTS: dict[tuple[str, str], str] = {

    # Very low (0–25)
    ("very_low", "synthetic"): (
        "The fiber composition here is associated with fast-fashion quality. "
        "Expect visible pilling and shape loss within a few months of regular wear."
    ),
    ("very_low", "cellulosic"): (
        "This blend of regenerated fibers is predicted to lose shape and surface quality quickly. "
        "The material science does not support the price."
    ),
    ("very_low", "mixed"): (
        "This composition sits at the low end of predicted durability. "
        "The combination of fibers is associated with early pilling and reduced colorfastness."
    ),
    ("very_low", "natural"): (
        "While natural fibers, this specific blend is associated with significant durability concerns. "
        "The predicted lifespan is short for the price."
    ),
    ("very_low", "premium"): (
        "Despite premium fiber branding, this composition is associated with poor durability. "
        "Price does not reflect the likely wear experience."
    ),

    # Low (26–45)
    ("low", "synthetic"): (
        "This synthetic blend is predicted to pill noticeably within the first season. "
        "The durability score does not justify a mid-range price."
    ),
    ("low", "cellulosic"): (
        "Viscose and rayon-dominant fabrics are predicted to lose structure and surface quality "
        "faster than comparable natural fibers at this price. Handle with care."
    ),
    ("low", "mixed"): (
        "The fiber mix here pulls the durability score down. "
        "Some components are predicted to perform well; others will likely show wear early."
    ),
    ("low", "natural"): (
        "Natural fiber content helps, but this specific composition is associated with "
        "moderate durability concerns. Worth considering if you plan to wear it lightly."
    ),
    ("low", "premium"): (
        "The premium fiber name does not guarantee durability at this blend ratio. "
        "Predicted performance is below what the price typically signals."
    ),

    # Mid (46–65)
    ("mid", "synthetic"): (
        "A solid synthetic blend with decent predicted durability. "
        "Not exceptional, but reasonable quality for the category."
    ),
    ("mid", "cellulosic"): (
        "This regenerated cellulose blend offers moderate durability and good drape. "
        "With proper care, it should hold up for regular rotation."
    ),
    ("mid", "mixed"): (
        "A mixed composition with balanced predicted performance. "
        "Not a standout, but the fiber science is consistent with mid-range expectations."
    ),
    ("mid", "natural"): (
        "Good natural fiber content with moderate predicted durability. "
        "Care behavior will have a significant impact on actual lifespan."
    ),
    ("mid", "premium"): (
        "Premium fiber content with solid predicted performance. "
        "Worth the investment if priced within the mid range for this category."
    ),

    # Good (66–80)
    ("good", "synthetic"): (
        "Strong predicted durability for a synthetic blend. "
        "The fiber composition is consistent with a garment that holds up well over time."
    ),
    ("good", "cellulosic"): (
        "Above-average predicted durability for a cellulosic blend. "
        "The fiber science backs up the price at this level."
    ),
    ("good", "mixed"): (
        "Well-balanced fiber composition with strong predicted durability. "
        "The material score supports the price point."
    ),
    ("good", "natural"): (
        "Solid natural fiber composition with good predicted performance. "
        "This is the quality level where the fiber science earns its keep."
    ),
    ("good", "premium"): (
        "The premium fibers here are doing real work. "
        "Predicted durability is strong and the composition backs up the investment."
    ),

    # Excellent (81–100)
    ("excellent", "synthetic"): (
        "Exceptional predicted durability for this fiber class. "
        "The composition is engineered for performance and longevity."
    ),
    ("excellent", "cellulosic"): (
        "Best-in-class predicted durability for a cellulosic blend. "
        "This is what quality looks like at the fiber level."
    ),
    ("excellent", "mixed"): (
        "This is genuinely good value — the fiber composition backs it up. "
        "Predicted durability is in the top tier for this category."
    ),
    ("excellent", "natural"): (
        "Excellent natural fiber composition with top-tier predicted durability. "
        "The material science supports the price and then some."
    ),
    ("excellent", "premium"): (
        "Premium fibers used correctly. "
        "This composition is associated with exceptional longevity and is worth the investment."
    ),
}

# ── Pilling-specific sentences ────────────────────────────────────────────────
# Used when pilling is the dominant risk factor (score < 40 and category = sweater/knitwear)
PILLING_WARNINGS: dict[str, str] = {
    "acrylic": (
        "Acrylic is the fiber most associated with rapid, heavy pilling. "
        "Expect significant surface fuzz within 2–3 months of regular wear."
    ),
    "cashmere": (
        "Cashmere's fine fibers are inherently prone to pilling, especially in blends. "
        "This is a known trade-off for softness at this price tier."
    ),
    "viscose": (
        "Viscose and rayon pill faster than most natural fibers. "
        "Surface quality is likely to decline noticeably with regular use."
    ),
    "wool_acrylic_blend": (
        "Adding acrylic to wool significantly increases pilling risk. "
        "This blend is associated with early surface degradation despite the wool content."
    ),
}

# ── Confidence note templates ─────────────────────────────────────────────────
CONFIDENCE_NOTES: dict[str, str] = {
    "high": "Full fiber composition listed — score confidence is high.",
    "medium_gsm": (
        "Fabric weight (GSM) is not listed. For this fiber type, weight significantly affects "
        "durability. The score may be optimistic for lightweight versions."
    ),
    "medium_blend": (
        "This blend combination is not in our tested-blend database. "
        "Score is based on weighted fiber averages, which may not reflect interaction effects."
    ),
    "medium_partial": (
        "Composition percentages are partially listed. "
        "Score is calculated from available data; unlisted fibers could affect performance."
    ),
    "low_no_composition": (
        "No fiber composition data found for this item. "
        "Score cannot be calculated from material science — brand history used as proxy only."
    ),
    "low_unknown_fibers": (
        "One or more fibers in this composition are not in our database. "
        "Score excludes these components and may be inaccurate."
    ),
}

# ── Cost-per-wash lifespan estimates by material score band ──────────────────
# Expressed in estimated number of wash cycles before noticeable quality decline.
# Based on WRAP/Textile 2030 durability framework and consumer testing data.
WASH_CYCLE_ESTIMATES: dict[str, tuple[int, int]] = {
    "very_low":  (15, 25),    # 15–25 washes
    "low":       (25, 50),    # 25–50 washes
    "mid":       (50, 100),   # 50–100 washes
    "good":      (100, 200),  # 100–200 washes
    "excellent": (200, 400),  # 200–400 washes
}


def get_score_band(score: float) -> str:
    if score <= 25:
        return "very_low"
    elif score <= 45:
        return "low"
    elif score <= 65:
        return "mid"
    elif score <= 80:
        return "good"
    else:
        return "excellent"


def get_dominant_fiber_class(composition: list[dict]) -> str:
    """
    Classify the dominant fiber class of a composition.
    composition: [{"canonical": str, "pct": float}]
    """
    premium_fibers = {"cashmere", "silk", "alpaca", "merino"}
    natural_fibers = {"cotton", "linen", "hemp", "wool"}
    cellulosic_fibers = {"viscose", "rayon", "modal", "lyocell", "tencel", "bamboo", "cupro"}
    synthetic_fibers = {"polyester", "nylon", "acrylic", "elastane", "polypropylene"}

    totals: dict[str, float] = {
        "premium": 0, "natural": 0, "cellulosic": 0, "synthetic": 0
    }

    for fiber in composition:
        canonical = fiber.get("canonical", "")
        pct = fiber.get("pct", 0)
        if canonical in premium_fibers:
            totals["premium"] += pct
        elif canonical in natural_fibers:
            totals["natural"] += pct
        elif canonical in cellulosic_fibers:
            totals["cellulosic"] += pct
        elif canonical in synthetic_fibers:
            totals["synthetic"] += pct

    return max(totals, key=lambda k: totals[k])


def get_verdict_sentence(score: float, composition: list[dict]) -> str:
    band = get_score_band(score)
    fiber_class = get_dominant_fiber_class(composition)
    key = (band, fiber_class)
    return WORTH_IT_VERDICTS.get(key, WORTH_IT_VERDICTS.get((band, "mixed"), ""))


def get_wash_cycle_estimate(score: float) -> tuple[int, int]:
    band = get_score_band(score)
    return WASH_CYCLE_ESTIMATES[band]


def get_cost_per_wash(price: float, score: float) -> dict:
    """Returns cost-per-wash range given retail price and material score."""
    low_cycles, high_cycles = get_wash_cycle_estimate(score)
    if price and price > 0:
        cost_high = round(price / low_cycles, 2)
        cost_low = round(price / high_cycles, 2)
    else:
        cost_low = cost_high = None
    return {
        "wash_cycles_min": low_cycles,
        "wash_cycles_max": high_cycles,
        "cost_per_wash_low": cost_low,
        "cost_per_wash_high": cost_high,
        "note": (
            f"Estimated lifespan: {low_cycles}–{high_cycles} wash cycles before noticeable quality decline. "
            + (f"At ${price:.0f}, that is ${cost_low:.2f}–${cost_high:.2f} per wash." if price else "")
        ),
    }
