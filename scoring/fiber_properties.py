"""
Fiber property scores sourced from:
- ASTM D4970/D4970M-22 (pilling resistance)
- ASTM D5034 (tensile strength)
- ASTM D4838 (colorfastness to light)
- Textile Exchange Fiber Reports
- Lenzing AG technical data sheets

Each property is scored 0–100 where 100 = best performance.
Scores represent typical performance for the fiber class.
Individual garment performance varies with construction, GSM, and care.
"""

FIBER_PROPERTIES = {
    # ── Synthetic fibers ──────────────────────────────────────────────────────
    "polyester": {
        "pilling":   85,  # Low pill tendency due to high tenacity
        "tensile":   90,  # High tensile strength, excellent recovery
        "colorfastness": 80,  # Good with disperse dyes; heat-setting required
        "moisture":  20,  # Hydrophobic; poor absorbency
        "notes": "Durable and colourfast but traps heat. Moisture-wicking versions score higher on moisture."
    },
    "nylon": {
        "pilling":   80,
        "tensile":   95,  # Highest tensile strength of common fibers
        "colorfastness": 75,
        "moisture":  30,
        "notes": "Extremely strong and abrasion-resistant. Common in activewear and hosiery."
    },
    "acrylic": {
        "pilling":   20,  # Severe pilling is the defining weakness
        "tensile":   50,
        "colorfastness": 85,  # Excellent colour retention
        "moisture":  15,
        "notes": "Worst pilling resistance of common fibers. Often used as cheap wool substitute."
    },
    "elastane": {  # Also sold as Spandex, Lycra
        "pilling":   70,
        "tensile":   40,  # Low tensile but extreme stretch recovery
        "colorfastness": 70,
        "moisture":  20,
        "notes": "Always blended. Adds stretch; degrades with chlorine and heat over time."
    },
    "polypropylene": {
        "pilling":   75,
        "tensile":   80,
        "colorfastness": 60,  # Difficult to dye
        "moisture":  5,   # Near-zero absorbency
        "notes": "Lightweight; excellent moisture-wicking when engineered. Rare in fashion."
    },

    # ── Natural plant fibers ──────────────────────────────────────────────────
    "cotton": {
        "pilling":   50,  # Moderate pilling; cotton pills gradually (soft, not hard pills)
        "tensile":   60,
        "colorfastness": 75,  # Good with reactive dyes; fades faster than poly
        "moisture":  90,  # Excellent absorbency
        "notes": "Comfort and breathability are high. Durability depends heavily on GSM and weave."
    },
    "linen": {
        "pilling":   55,
        "tensile":   80,  # Stronger wet than dry
        "colorfastness": 70,
        "moisture":  90,
        "notes": "Gets stronger and softer with washing. Prone to wrinkling."
    },
    "hemp": {
        "pilling":   60,
        "tensile":   85,
        "colorfastness": 65,
        "moisture":  85,
        "notes": "One of the most durable natural fibers. Softens with washing. Rare in mainstream fashion."
    },

    # ── Natural protein fibers ────────────────────────────────────────────────
    "wool": {
        "pilling":   55,  # Fine wool pills more than coarser grades
        "tensile":   65,
        "colorfastness": 60,  # Acid dyes; can fade with UV and washing
        "moisture":  90,  # Absorbs up to 30% of weight without feeling wet
        "notes": "Natural crimp provides insulation. Felts with heat/agitation. Quality varies by grade."
    },
    "merino": {
        "pilling":   60,  # Finer fibres pill somewhat less
        "tensile":   65,
        "colorfastness": 62,
        "moisture":  92,
        "notes": "Premium fine wool. Softer than standard wool. Odour-resistant."
    },
    "cashmere": {
        "pilling":   25,  # Extremely fine fibres pill heavily
        "tensile":   50,
        "colorfastness": 55,
        "moisture":  80,
        "notes": "Exceptional softness but lowest durability of luxury fibers. Pills rapidly without anti-pill treatment."
    },
    "alpaca": {
        "pilling":   50,
        "tensile":   60,
        "colorfastness": 58,
        "moisture":  85,
        "notes": "Warmer than wool, hypoallergenic. Less prone to felting."
    },
    "silk": {
        "pilling":   45,
        "tensile":   55,
        "colorfastness": 60,  # Sensitive to light; degrades with prolonged UV
        "moisture":  75,
        "notes": "Luxurious drape and sheen. Weakens when wet. Dry-clean preferred."
    },

    # ── Semi-synthetic / regenerated cellulose ────────────────────────────────
    "viscose": {      # Also sold as Rayon
        "pilling":   30,
        "tensile":   40,  # Significantly weaker when wet
        "colorfastness": 65,
        "moisture":  75,
        "notes": "Drapes well but weakest when wet. Prone to shrinking. Widely used as cheap luxury substitute."
    },
    "rayon": {        # Alias for viscose
        "pilling":   30,
        "tensile":   40,
        "colorfastness": 65,
        "moisture":  75,
        "notes": "See viscose."
    },
    "modal": {
        "pilling":   55,  # Better than viscose due to higher wet strength
        "tensile":   55,
        "colorfastness": 70,
        "moisture":  80,
        "notes": "Softer and more durable than standard viscose. Resists shrinking better."
    },
    "lyocell": {      # Brand name: Tencel (Lenzing)
        "pilling":   60,
        "tensile":   60,
        "colorfastness": 75,
        "moisture":  85,
        "notes": "Best durability of the regenerated cellulose family. Smooth surface inhibits pilling."
    },
    "tencel": {       # Brand alias for lyocell
        "pilling":   60,
        "tensile":   60,
        "colorfastness": 75,
        "moisture":  85,
        "notes": "See lyocell."
    },
    "bamboo": {
        "pilling":   40,
        "tensile":   50,
        "colorfastness": 65,
        "moisture":  80,
        "notes": "Usually processed as bamboo viscose; properties mirror viscose unless otherwise specified."
    },
    "cupro": {
        "pilling":   45,
        "tensile":   50,
        "colorfastness": 68,
        "moisture":  78,
        "notes": "Silk-like hand feel. More durable than viscose."
    },
}

# Category-specific scoring weights
# Each category emphasises the properties that consumers actually notice
CATEGORY_WEIGHTS = {
    "sweater": {
        "pilling": 0.45,
        "tensile": 0.25,
        "colorfastness": 0.20,
        "moisture": 0.10,
    },
    "t-shirt": {
        "pilling": 0.25,
        "tensile": 0.25,   # tensile matters less in a casual tee
        "colorfastness": 0.22,
        "moisture": 0.28,  # breathability is core to t-shirt quality
    },
    "dress": {
        "pilling": 0.30,
        "tensile": 0.25,
        "colorfastness": 0.30,
        "moisture": 0.15,
    },
    "jeans": {
        "pilling": 0.15,
        "tensile": 0.45,
        "colorfastness": 0.30,
        "moisture": 0.10,
    },
    "outerwear": {
        "pilling": 0.25,
        "tensile": 0.35,
        "colorfastness": 0.25,
        "moisture": 0.15,
    },
    "activewear": {
        "pilling": 0.20,
        "tensile": 0.30,
        "colorfastness": 0.20,
        "moisture": 0.30,
    },
    "other": {
        "pilling": 0.35,
        "tensile": 0.30,
        "colorfastness": 0.20,
        "moisture": 0.15,
    },
}

# Canonical fiber names — maps common alternate names to the key used above
FIBER_ALIASES = {
    "polyester": "polyester",
    "poly": "polyester",
    "pes": "polyester",
    "recycled polyester": "polyester",
    "recycled nylon": "nylon",
    "recycled cotton": "cotton",
    "recycled wool": "wool",
    "nylon": "nylon",
    "polyamide": "nylon",
    "pa": "nylon",
    "acrylic": "acrylic",
    "acrylique": "acrylic",
    "elastane": "elastane",
    "spandex": "elastane",
    "lycra": "elastane",
    "stretch": "elastane",
    "cotton": "cotton",
    "coton": "cotton",
    "co": "cotton",
    "organic cotton": "cotton",
    "linen": "linen",
    "flax": "linen",
    "li": "linen",
    "hemp": "hemp",
    "wool": "wool",
    "laine": "wool",
    "wo": "wool",
    "merino": "merino",
    "merino wool": "merino",
    "cashmere": "cashmere",
    "kashmir": "cashmere",
    "alpaca": "alpaca",
    "silk": "silk",
    "soie": "silk",
    "se": "silk",
    "viscose": "viscose",
    "rayon": "rayon",
    "modal": "modal",
    "lyocell": "lyocell",
    "tencel": "tencel",
    "tencel lyocell": "lyocell",
    "bamboo": "bamboo",
    "bamboo viscose": "bamboo",
    "cupro": "cupro",
    "bemberg": "cupro",
}


def resolve_fiber(name: str) -> str | None:
    """Normalise a fiber name to its canonical key. Returns None if unknown."""
    key = name.strip().lower()
    return FIBER_ALIASES.get(key)


def get_fiber(name: str) -> dict | None:
    """Return property dict for a fiber name (handles aliases). Returns None if unknown."""
    canonical = resolve_fiber(name)
    if canonical is None:
        return None
    return FIBER_PROPERTIES.get(canonical)
