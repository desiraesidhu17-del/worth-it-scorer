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
        "Expect pilling within one season. "
        "Not worth mid-range pricing."
    ),
    ("very_low", "cellulosic"): (
        "This blend is predicted to lose structure quickly. "
        "The material science doesn't support the price."
    ),
    ("very_low", "mixed"): (
        "Low predicted durability across the board. "
        "The fiber combination is associated with early wear."
    ),
    ("very_low", "natural"): (
        "Natural fibers, but a combination associated with poor durability. "
        "Short lifespan for the price."
    ),
    ("very_low", "premium"): (
        "Premium fiber, very low predicted durability. "
        "The fiber science does not support this price from a wear-resistance standpoint."
    ),

    # Low (26–45)
    ("low", "synthetic"): (
        "Will pill noticeably within the first season. "
        "Durability doesn't justify a mid-range price."
    ),
    ("low", "cellulosic"): (
        "Viscose and rayon lose structure faster than comparable naturals at this price. "
        "Handle with care."
    ),
    ("low", "mixed"): (
        "Mixed signals from the fiber composition. "
        "Some components hold up; others will show wear early."
    ),
    ("low", "natural"): (
        "Natural fiber content helps, but durability is still a concern. "
        "Best for light, occasional wear."
    ),
    ("low", "premium"): (
        "Lower predicted durability than the premium label suggests. "
        "The score reflects wear resistance — softness, drape, and feel are not captured here."
    ),

    # Mid (46–65)
    ("mid", "synthetic"): (
        "Decent predicted durability for synthetics. "
        "Reasonable quality for the category and price."
    ),
    ("mid", "cellulosic"): (
        "Moderate durability with good drape. "
        "Should hold up for regular rotation with proper care."
    ),
    ("mid", "mixed"): (
        "Balanced composition with middle-of-the-road predicted performance. "
        "No major red flags."
    ),
    ("mid", "natural"): (
        "Good natural fiber content with moderate durability. "
        "Care routine will drive actual lifespan."
    ),
    ("mid", "premium"): (
        "Premium fibers at a mid-range blend. "
        "Solid performance if priced accordingly."
    ),

    # Good (66–80)
    ("good", "synthetic"): (
        "Strong durability for a synthetic blend. "
        "Built to handle regular rotation."
    ),
    ("good", "cellulosic"): (
        "Above-average durability for a cellulosic blend. "
        "The fiber science backs up the price."
    ),
    ("good", "mixed"): (
        "Well-balanced composition with strong predicted durability. "
        "Worth the price at this level."
    ),
    ("good", "natural"): (
        "Solid natural fiber performance. "
        "This is the quality level where the fiber science earns its keep."
    ),
    ("good", "premium"): (
        "Premium fibers doing real work here. "
        "Durability is strong and the composition backs the investment."
    ),

    # Excellent (81–100)
    ("excellent", "synthetic"): (
        "Exceptional durability for this fiber class. "
        "Engineered for performance and longevity."
    ),
    ("excellent", "cellulosic"): (
        "Best-in-class durability for a cellulosic blend. "
        "This is what quality looks like at the fiber level."
    ),
    ("excellent", "mixed"): (
        "Genuinely good value — the fiber composition backs it up. "
        "Top-tier durability for the category."
    ),
    ("excellent", "natural"): (
        "Excellent natural fiber composition with top-tier predicted durability. "
        "Worth the investment."
    ),
    ("excellent", "premium"): (
        "Premium fibers, premium performance. "
        "The material science earns the price."
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


# ── Headline system ───────────────────────────────────────────────────────────
# Three-step architecture:
#   Step 1 (A): 2D matrix by (score_band, price_pressure_level) — consistency + control
#   Step 2 (B-lite): premium fiber override at low/very_low — swaps headline only
#   Step 3 (C): get_watch_for() below — controlled lookup, not generation

HEADLINE_MATRIX: dict[tuple[str, str], tuple[str, str]] = {
    # (score_band, price_pressure_level): (headline, sub_line)
    # Language rules: use "durability" not "material/fiber"; real-world outcome subs;
    # price criticism: "price runs ahead" not "doesn't justify".

    # very_low (0–25)
    ("very_low", "low"):      ("Weak durability, fair price",
                               "Durability is low — the price at least reflects it."),
    ("very_low", "moderate"): ("Weak durability, priced too high",
                               "Likely to show wear early relative to the price."),
    ("very_low", "high"):     ("Poor durability, high price",
                               "Expect visible wear sooner than this price suggests."),
    ("very_low", "extreme"):  ("Luxury price, budget fiber",
                               "You're paying for positioning, not performance."),
    ("very_low", "unknown"):  ("Very low durability",
                               "Likely to show visible wear early in regular use."),

    # low (26–45)
    ("low", "low"):      ("Below-average durability, fair price",
                          "Performance is below average — the price is honest about that."),
    ("low", "moderate"): ("Below-average durability, priced too high",
                          "Wear resistance doesn't match what the price suggests."),
    ("low", "high"):     ("Overpriced for durability",
                          "Wear resistance is below what this price suggests."),
    ("low", "extreme"):  ("Luxury price, low durability",
                          "You're paying for positioning, not how it holds up."),
    ("low", "unknown"):  ("Below-average durability",
                          "Expect earlier wear than most alternatives in this category."),

    # mid (46–65)
    ("mid", "low"):      ("Average durability, fair price",
                          "Nothing exceptional — but the price is honest about that."),
    ("mid", "moderate"): ("Average durability, slight premium",
                          "Solid for the category — with a modest premium on top."),
    ("mid", "high"):     ("Average durability, overpriced",
                          "Performance is average — the price runs ahead of it."),
    ("mid", "extreme"):  ("Average durability, luxury pricing",
                          "Performance is typical — the price goes far beyond what it warrants."),
    ("mid", "unknown"):  ("Average durability",
                          "Should hold up fine under normal rotation."),

    # good (66–80)
    ("good", "low"):      ("Strong durability, fair price",
                           "Performance backs up the price — this is what good value looks like."),
    ("good", "moderate"): ("Strong durability, slight premium",
                           "Good performance, with a modest brand premium on top."),
    ("good", "high"):     ("Good durability, overpriced",
                           "Performance is strong — but the price runs well ahead of it."),
    ("good", "extreme"):  ("Good durability, steep premium",
                           "Solid performance — but you're paying well beyond what it warrants."),
    ("good", "unknown"):  ("Above-average durability",
                           "Built to hold up over regular rotation."),

    # excellent (81–100)
    ("excellent", "low"):      ("Exceptional durability, great value",
                                "Top-tier performance at a price that reflects how it holds up."),
    ("excellent", "moderate"): ("Exceptional durability, modest premium",
                                "Top-tier performance — the slight premium is the cost of this quality level."),
    ("excellent", "high"):     ("Exceptional durability, steep price",
                                "Top-tier performance — but the price runs well ahead of it."),
    ("excellent", "extreme"):  ("Exceptional durability, extreme price",
                                "Performance is exceptional — but the price goes far beyond what even that justifies."),
    ("excellent", "unknown"):  ("Exceptional durability",
                                "Built for longevity — top-tier performance across the board."),
}

# Step 2 override: premium fiber (silk, cashmere, alpaca, merino) at low/very_low score.
# Replaces both headline and sub_line — the override provides its own specific sub.
_PREMIUM_OVERRIDE_BANDS: frozenset[str] = frozenset({"very_low", "low"})
_PREMIUM_OVERRIDE_HEADLINE = "Built for feel, not longevity"
_PREMIUM_OVERRIDE_SUB = "Fine fibers like silk prioritize softness and drape over durability."


def get_headline(
    score: float,
    price_pressure_level: str,
    composition: list[dict],
) -> tuple[str, str]:
    """
    Returns (headline, headline_sub) for the result card.

    Step 1 (A): 2D matrix keyed on (score_band, price_pressure_level).
    Step 2 (B-lite): premium fiber at low/very_low overrides the headline.

    composition: [{"canonical": str, "pct": float}] — known fibers only.
    price_pressure_level: "low" | "moderate" | "high" | "extreme" | "unknown"
    """
    band = get_score_band(score)

    # Step 2: B-lite override
    if band in _PREMIUM_OVERRIDE_BANDS:
        if get_dominant_fiber_class(composition) == "premium":
            return _PREMIUM_OVERRIDE_HEADLINE, _PREMIUM_OVERRIDE_SUB

    # Step 1: base matrix
    key = (band, price_pressure_level)
    if key in HEADLINE_MATRIX:
        return HEADLINE_MATRIX[key]

    # Fallback to unknown-price entry for the band
    return HEADLINE_MATRIX.get((band, "unknown"), ("", ""))


# ── Watch For system (Step 3 — Approach C, controlled) ────────────────────────
# Produces up to 3 specific, user-visible failure mode strings.
# Layer 1: property-based generic fallback.
# Layer 2: fiber-specific override replaces generic for that property slot.
# Layer 3: price flag when high price + low durability band.

# (property_name): (score_threshold, generic_watch_for_string)
_WATCH_PROPERTY_GENERIC: dict[str, tuple[float, str]] = {
    "pilling":       (50.0, "Surface pilling or fuzzing"),
    "tensile":       (50.0, "Seam stress, distortion over time"),
    "colorfastness": (65.0, "Color fading with repeated washing"),
    "moisture":      (30.0, "Traps heat, low breathability"),
}

# fiber_canonical: {property_name: (score_threshold, watch_for_string)}
# When dominant fiber matches AND property score < threshold,
# this string replaces the generic string for that property slot.
_WATCH_FIBER_SPECIFIC: dict[str, dict[str, tuple[float, str]]] = {
    "acrylic":  {"pilling":  (50.0, "Heavy pilling within 1–2 seasons")},
    "silk":     {"pilling":  (55.0, "Snagging, delicate handling required"),
                 "tensile":  (60.0, "Snagging, delicate handling required")},
    "viscose":  {"tensile":  (50.0, "Shrinks or distorts when wet")},
    "rayon":    {"tensile":  (50.0, "Shrinks or distorts when wet")},
    "cashmere": {"pilling":  (35.0, "Visible pilling after early wears")},
    "wool":     {"pilling":  (60.0, "Pilling under arms and at seams")},
    "cotton":   {"colorfastness": (75.0, "Fading after repeated washing")},
}

_WATCH_PRICE_FLAG = "High care cost relative to expected lifespan"
_WATCH_PRICE_FLAG_THRESHOLD = 100.0
_WATCH_PRICE_FLAG_BANDS: frozenset[str] = frozenset({"very_low", "low"})


def get_watch_for(
    composition: list[dict],
    property_scores: dict,
    price: float | None,
    score_band: str,
) -> list[str]:
    """
    Returns up to 3 user-visible failure modes for this composition.

    composition: [{"canonical": str, "pct": float}] — known fibers only.
    property_scores: {"pilling": float, "tensile": float, "colorfastness": float, "moisture": float}
    price: retail price in USD, or None.
    score_band: "very_low" | "low" | "mid" | "good" | "excellent"
    """
    # Dominant fiber = highest-percentage canonical fiber
    dominant_fiber = ""
    if composition:
        dominant_fiber = max(composition, key=lambda f: f.get("pct", 0)).get("canonical", "")

    fiber_overrides = _WATCH_FIBER_SPECIFIC.get(dominant_fiber, {})
    results: list[str] = []
    seen: set[str] = set()

    for prop, (generic_threshold, generic_str) in _WATCH_PROPERTY_GENERIC.items():
        score = property_scores.get(prop, 100.0)

        # Layer 2: fiber-specific override for this property slot
        if prop in fiber_overrides:
            override_threshold, override_str = fiber_overrides[prop]
            if score < override_threshold:
                if override_str not in seen:
                    seen.add(override_str)
                    results.append(override_str)
                continue  # Skip generic for this slot regardless

        # Layer 1: generic fallback
        if score < generic_threshold:
            if generic_str not in seen:
                seen.add(generic_str)
                results.append(generic_str)

    # Layer 3: price flag
    if (
        price is not None
        and price > _WATCH_PRICE_FLAG_THRESHOLD
        and score_band in _WATCH_PRICE_FLAG_BANDS
        and _WATCH_PRICE_FLAG not in seen
        and len(results) < 3
    ):
        results.append(_WATCH_PRICE_FLAG)

    return results[:3]
