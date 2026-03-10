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
    """Return the canonical lowercase fiber name for a raw fiber string.

    Rules:
    - "recycled" modifier is preserved in canonical name (distinct material for scoring)
    - Other modifiers (organic, regenerated, bio-based) are stripped — base fiber is canonical
    - Aliases are resolved (spandex → elastane, rayon → viscose, etc.)
    """
    cleaned = raw.lower().strip()
    # Strip known noise suffixes
    for noise in _NOISE_SUFFIXES:
        if cleaned.endswith(noise):
            cleaned = cleaned[: -len(noise)].strip(",. ").strip()
    # Check alias map first (handles multi-word like "tencel lyocell")
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    # Handle modifier + fiber
    for mod in _MODIFIERS:
        if cleaned.startswith(mod + " "):
            base = cleaned[len(mod) + 1:].strip()
            base = _ALIASES.get(base, base)
            if base in _KNOWN_FIBERS or base in _ALIASES.values():
                # "recycled" is a distinct material — keep modifier in canonical name
                # Other modifiers (organic, regenerated, bio-based) → strip to base fiber
                if mod == "recycled":
                    return f"recycled {base}"
                else:
                    return base
    # Check known fibers directly
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
    # Handle "recycled <fiber>" — strip "recycled" to check base
    if normalized.startswith("recycled "):
        base = normalized[len("recycled "):].strip()
        return base in _KNOWN_FIBERS
    return normalized in _KNOWN_FIBERS


def get_material_type(raw: str) -> str | None:
    """Return 'non-fiber' or 'fill' for special materials, None for normal fibers."""
    return _NON_FIBER.get(normalize_fiber(raw))
