"""
Detect technical fabric and construction signals in product page text.

Each of 6 categories contributes at most one signal to the count.
is_technical fires when 2+ categories match — single hits are too common
in marketing copy to be reliable.
"""
import re


# Category 1: Waterproof membrane brands
# Display label includes the matched term.
_MEMBRANE_BRANDS = [
    "GORE-TEX PRO",
    "GORE-TEX ACTIVE",
    "GORE-TEX PACLITE",
    "GORE-TEX",
    "ePE",
    "NeoShell",
    "eVent fabric",
    "eVent",
    "Pertex Shield",
    "Pertex",
    "Dermizax",
    "H2No",
    "HyVent",
    "Omni-Tech",
    "FutureLight",
]

# Category 2: DWR treatment phrases
_DWR_PHRASES = [
    "durable water repellent",
    "water-repellent finish",
    "DWR",
]

# Category 3: Seam sealing phrases
_SEAM_PHRASES = [
    "seam-sealed",
    "fully taped",
    "critically seamed",
    "taped seams",
]

# Category 4: Technical shell terms
_SHELL_TERMS = [
    "waterproof-breathable",
    "hardshell",
    "softshell",
    "3-layer",
    "2.5-layer",
]

# Category 5: Performance ratings — regex patterns
_PERFORMANCE_PATTERNS = [
    r"\d{4,5}\s*mm",          # e.g. "20000mm" or "20,000 mm"
    r"waterproof rating",
    r"MVTR",
    r"CFM breathability",
]

# Category 6: Technical insulation brands and terms
_INSULATION_TERMS = [
    "PrimaLoft",
    "Thermolite",
    "Polartec",
    "800 fill",
    "900 fill",
    "down fill power",
    "RDS-certified",
    "RDS certified",
]


def _match_first(text_lower: str, terms: list[str], case_sensitive: bool = False) -> str | None:
    """Return the first matching term, or None."""
    for term in terms:
        needle = term if case_sensitive else term.lower()
        haystack = text_lower if not case_sensitive else text_lower
        if needle in haystack:
            return term
    return None


def _match_first_regex(text: str, patterns: list[str]) -> str | None:
    """Return the first regex match text, or None."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def _find_membrane(text: str, text_lower: str) -> str | None:
    """
    Find the most specific membrane brand match (longer variants first).
    Returns the original brand name as found (preserving case for display),
    or None if no match.
    """
    for brand in _MEMBRANE_BRANDS:  # ordered: specific before generic
        if brand.lower() in text_lower:
            # Grab the actual text at that position to preserve product casing
            m = re.search(re.escape(brand), text, re.IGNORECASE)
            return m.group(0) if m else brand
    return None


def detect_technical_signals(text: str) -> dict:
    """
    Scan product page text for technical fabric and construction signals.

    Returns:
        {
            "is_technical": bool,       # True when 2+ categories match
            "signals_found": list[str], # human-readable display labels
            "signal_count": int,        # number of categories matched
        }

    Each of the 6 detection categories contributes at most one signal.
    """
    text_lower = text.lower()
    signals: list[str] = []

    # Category 1: Waterproof membrane
    membrane = _find_membrane(text, text_lower)
    if membrane:
        signals.append(f"Waterproof membrane ({membrane})")

    # Category 2: DWR treatment
    for phrase in _DWR_PHRASES:
        if phrase.lower() in text_lower:
            signals.append("DWR (durable water repellent) treatment")
            break

    # Category 3: Seam sealing
    for phrase in _SEAM_PHRASES:
        if phrase.lower() in text_lower:
            signals.append("Seam sealing")
            break

    # Category 4: Technical shell
    for term in _SHELL_TERMS:
        if term.lower() in text_lower:
            signals.append(f"Technical shell ({term})")
            break

    # Category 5: Performance ratings
    match = _match_first_regex(text, _PERFORMANCE_PATTERNS)
    if match:
        signals.append(f"Performance rating ({match})")

    # Category 6: Technical insulation
    for term in _INSULATION_TERMS:
        if term.lower() in text_lower:
            signals.append(f"Technical insulation ({term})")
            break

    count = len(signals)
    return {
        "is_technical": count >= 2,
        "signals_found": signals,
        "signal_count": count,
    }
