"""
Blend interaction adjustments for common fiber combinations.

Research source:
- Eltahan (2019): "Relationship between Strength and Polyester Content Percentage
  of Cotton-Polyester Blended Woven Fabrics", SAPUB Journal of Clothing.
- Özdil et al. (2012): "Moisture Absorption and Release of Profiled Polyester
  and Cotton Composite Knitted Fabrics", Textile Research Journal.
- ASTM D4970/D4970M-22: Pilling resistance via Martindale tester.
- Industry standard: 65/35 and 50/50 poly-cotton blends achieve Grade 4 pilling
  (slight surface fuzzing, not Grade 1 severe).

Format: (fiber_a, fiber_b) → {property: delta}
Delta is added to the weighted-average score for that property.
Positive = better than weighted average predicts.
Negative = worse than weighted average predicts.

Only the top-20 most common commercial blends are included.
Unknown blends fall back to weighted average with a confidence penalty.
"""

from typing import Optional

# Keys are frozensets so order of fiber names doesn't matter
BLEND_ADJUSTMENTS: dict[frozenset, dict[str, float]] = {

    # ── Polyester + Cotton ────────────────────────────────────────────────────
    # Poly-cotton is the best-studied blend. Interaction effects are well-documented.
    frozenset({"polyester", "cotton"}): {
        "pilling":       +8,   # Poly raises cotton pilling resistance materially
        "tensile":       +5,   # Synergistic strength improvement
        "colorfastness": -5,   # Mixed dye requirements create shadow-fading risk
        "moisture":       0,   # Linear interpolation holds reasonably well
    },

    # ── Polyester + Viscose ───────────────────────────────────────────────────
    frozenset({"polyester", "viscose"}): {
        "pilling":       +5,   # Poly partially compensates viscose's weak surface
        "tensile":      +10,   # Poly significantly boosts viscose's low wet strength
        "colorfastness": -3,   # Dye compatibility issues
        "moisture":      +3,
    },
    frozenset({"polyester", "rayon"}): {  # Rayon = viscose alias
        "pilling":       +5,
        "tensile":      +10,
        "colorfastness": -3,
        "moisture":      +3,
    },

    # ── Polyester + Elastane ──────────────────────────────────────────────────
    frozenset({"polyester", "elastane"}): {
        "pilling":       -2,   # Elastane loops can catch and pill
        "tensile":       +3,
        "colorfastness":  0,
        "moisture":       0,
    },

    # ── Cotton + Elastane ─────────────────────────────────────────────────────
    frozenset({"cotton", "elastane"}): {
        "pilling":       -3,
        "tensile":       -2,   # Elastane reduces density of cotton structure
        "colorfastness": -2,
        "moisture":      -5,   # Elastane resists moisture slightly
    },

    # ── Cotton + Modal ────────────────────────────────────────────────────────
    frozenset({"cotton", "modal"}): {
        "pilling":       +5,   # Modal's smooth surface helps cotton
        "tensile":       +3,
        "colorfastness": +3,
        "moisture":      +5,   # Both highly absorbent; synergistic
    },

    # ── Cotton + Lyocell / Tencel ─────────────────────────────────────────────
    frozenset({"cotton", "lyocell"}): {
        "pilling":       +8,   # Lyocell's smooth surface significantly reduces pilling
        "tensile":       +5,
        "colorfastness": +5,
        "moisture":      +5,
    },
    frozenset({"cotton", "tencel"}): {
        "pilling":       +8,
        "tensile":       +5,
        "colorfastness": +5,
        "moisture":      +5,
    },

    # ── Wool + Acrylic ────────────────────────────────────────────────────────
    # Very common in budget knitwear. Acrylic dilutes wool's properties.
    frozenset({"wool", "acrylic"}): {
        "pilling":      -10,   # Acrylic drags wool's pill resistance down sharply
        "tensile":       -5,
        "colorfastness": +5,   # Acrylic's colorfastness compensates for wool's weaker retention
        "moisture":     -10,   # Acrylic significantly reduces moisture absorption
    },

    # ── Wool + Nylon ──────────────────────────────────────────────────────────
    frozenset({"wool", "nylon"}): {
        "pilling":       +5,   # Nylon improves wool's abrasion resistance
        "tensile":      +10,
        "colorfastness": -3,
        "moisture":      -5,
    },

    # ── Wool + Polyester ──────────────────────────────────────────────────────
    frozenset({"wool", "polyester"}): {
        "pilling":       +3,
        "tensile":       +8,
        "colorfastness": -3,
        "moisture":      -8,
    },

    # ── Merino + Elastane ─────────────────────────────────────────────────────
    frozenset({"merino", "elastane"}): {
        "pilling":       -5,
        "tensile":       -2,
        "colorfastness": -2,
        "moisture":      -3,
    },

    # ── Viscose + Elastane ────────────────────────────────────────────────────
    frozenset({"viscose", "elastane"}): {
        "pilling":       -5,
        "tensile":       -5,   # Elastane does not compensate viscose's wet weakness
        "colorfastness": -3,
        "moisture":       0,
    },

    # ── Viscose + Linen ───────────────────────────────────────────────────────
    frozenset({"viscose", "linen"}): {
        "pilling":       +5,
        "tensile":      +10,   # Linen substantially boosts viscose strength
        "colorfastness": +3,
        "moisture":      +5,
    },

    # ── Nylon + Elastane ──────────────────────────────────────────────────────
    frozenset({"nylon", "elastane"}): {
        "pilling":       -2,
        "tensile":       +3,
        "colorfastness": -2,
        "moisture":       0,
    },

    # ── Cotton + Linen ────────────────────────────────────────────────────────
    frozenset({"cotton", "linen"}): {
        "pilling":       +5,
        "tensile":      +10,
        "colorfastness":  0,
        "moisture":      +3,
    },

    # ── Silk + Elastane ───────────────────────────────────────────────────────
    frozenset({"silk", "elastane"}): {
        "pilling":       -5,
        "tensile":       -5,
        "colorfastness": -5,   # Elastane can bleed or resist dye differently
        "moisture":      -8,
    },

    # ── Lyocell + Elastane ────────────────────────────────────────────────────
    frozenset({"lyocell", "elastane"}): {
        "pilling":       -5,
        "tensile":       -3,
        "colorfastness": -2,
        "moisture":      -3,
    },
    frozenset({"tencel", "elastane"}): {
        "pilling":       -5,
        "tensile":       -3,
        "colorfastness": -2,
        "moisture":      -3,
    },

    # ── Acrylic + Polyester ───────────────────────────────────────────────────
    # Cheap knitwear blend. Neither compensates the other's weaknesses meaningfully.
    frozenset({"acrylic", "polyester"}): {
        "pilling":       -3,   # Polyester slightly worsens perceived pilling (diff. pile heights)
        "tensile":       +8,   # Polyester substantially boosts tensile
        "colorfastness": +3,
        "moisture":       0,
    },
}


def get_blend_adjustment(fiber_a: str, fiber_b: str) -> Optional[dict[str, float]]:
    """
    Return the interaction adjustment dict for a two-fiber blend, or None
    if the pair is not in the known-blend table.
    """
    key = frozenset({fiber_a.lower(), fiber_b.lower()})
    return BLEND_ADJUSTMENTS.get(key)


def apply_blend_adjustments(
    base_scores: dict[str, float],
    composition: list[dict],  # [{"fiber": str, "canonical": str, "pct": float}]
) -> tuple[dict[str, float], bool]:
    """
    Apply pairwise blend interaction adjustments to base weighted-average scores.

    Returns:
        adjusted_scores: property scores after applying blend interactions
        all_known: True if all pairwise interactions were in the table
                   (used to set confidence level)
    """
    adjusted = dict(base_scores)
    all_known = True
    seen_pairs: set[frozenset] = set()

    canonical_names = [f["canonical"] for f in composition if f.get("canonical")]

    for i, fiber_a in enumerate(canonical_names):
        for fiber_b in canonical_names[i + 1 :]:
            pair = frozenset({fiber_a, fiber_b})
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            adjustment = get_blend_adjustment(fiber_a, fiber_b)
            if adjustment is None:
                all_known = False
                continue

            # Scale the adjustment by the combined percentage of the two fibers
            combined_pct = sum(
                f["pct"] for f in composition if f.get("canonical") in (fiber_a, fiber_b)
            )
            scale = min(combined_pct / 100.0, 1.0)

            for prop, delta in adjustment.items():
                if prop in adjusted:
                    adjusted[prop] = max(0.0, min(100.0, adjusted[prop] + delta * scale))

    return adjusted, all_known
