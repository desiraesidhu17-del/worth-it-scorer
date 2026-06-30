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

# Category 6: Technical insulation — branded insulations only.
# An explicit fill-power figure also counts (via _find_fill_power, shared with the
# spec extractor). Generic language ("puffer", "polyester fill", "down jacket",
# "RDS-certified" with no fill figure) deliberately does NOT count — too common in
# fashion copy to be a reliable technical signal.
_INSULATION_BRANDS = [
    "PrimaLoft",
    "Thermolite",
    "Polartec",
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

    Matches on word boundaries so short brand tokens (e.g. "ePE", "eVent")
    don't false-positive inside ordinary words like "repellent" or
    "prevention".
    """
    for brand in _MEMBRANE_BRANDS:  # ordered: specific before generic
        # \b around the escaped brand keeps "ePE" from matching "rePEllent"
        m = re.search(rf"\b{re.escape(brand)}\b", text, re.IGNORECASE)
        if m:
            return m.group(0)  # preserve product casing for display
    return None


# ── Structured spec extraction (Commit 1) ─────────────────────────────────────
# Each extractor below is VALUE-ANCHORED: it emits a spec only when an explicit
# value is present in the text. Never infer or default a spec value — a card that
# invents "20,000 mm" is worse than one that shows nothing.

# Shell layer construction, e.g. "3-layer", "2.5L"
_SHELL_LAYER_PATTERNS = [
    r"\b(2\.5|3|2)\s*-?\s*layer\b",
    r"\b(2\.5|3|2)\s*L\b",
]

# Seam sealing — ordered longest/most-specific first so matched_text is precise.
_SEAM_SPEC_PHRASES = [
    "fully taped seams",
    "critically taped seams",
    "critically seamed",
    "fully taped",
    "critically taped",
    "seam-sealed",
    "seam sealed",
    "taped seams",
]

# DWR finish — includes PFAS/PFC-free variants, ordered specific first.
_DWR_SPEC_PHRASES = [
    "PFAS-free DWR",
    "PFC-free DWR",
    "PFAS-free durable water repellent",
    "durable water repellent",
    "water-repellent finish",
    "DWR",
]

# Waterproof hydrostatic head, e.g. "20,000 mm" or "20000mm".
_WATERPROOF_MM_PATTERN = r"\b(?:\d{1,2},\d{3}|\d{4,6})\s*mm\b"

# Breathability — every pattern requires a number so a bare "MVTR" emits no spec.
_BREATHABILITY_PATTERNS = [
    r"\b(?:\d{1,2},\d{3}|\d{3,6})\s*g\s*/\s*m[²2]\s*/?\s*24\s*h?\b",
    r"\b(?:\d{1,2},\d{3}|\d{3,6})\s*g\s*/\s*m[²2]\b",
    r"\bMVTR\s*(?:of\s*)?\d[\d,]*\b",
    r"\b\d[\d,]*\s*MVTR\b",
    r"\bRET\s*(?:of\s*)?\d+(?:\.\d+)?\b",
    r"\b\d[\d,]*\s*(?:CFM|cfm)\b",
]

# Insulation type — (canonical display value, pattern).
_INSULATION_SPEC_TERMS = [
    ("PrimaLoft", r"\bprimaloft\b"),
    ("Thermolite", r"\bthermolite\b"),
    ("Polartec", r"\bpolartec\b"),
    ("synthetic insulation", r"\bsynthetic\s+insulation\b"),
    ("down", r"\bdown\b"),
]

# Fill power, e.g. "800-fill", "fill power of 850". Shared by the spec extractor
# AND the technical-insulation detector so detection and extraction can't drift.
_FILL_POWER_PATTERNS = [
    r"\b(\d{3})\s*-?\s*fill(?:\s*power)?\b",
    r"\bfill\s*power\s*(?:of\s*)?(\d{3})\b",
]


def _find_fill_power(text: str) -> re.Match | None:
    """First explicit fill-power match (group(1) = the figure), or None."""
    for pat in _FILL_POWER_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m
    return None

# Face fabric — (canonical display value, pattern).
_FACE_FABRIC_TERMS = [
    ("ripstop", r"\bripstop\b"),
    ("Cordura", r"\bcordura\b"),
    ("ballistic nylon", r"\bballistic\s+nylon\b"),
]

# Denier — case-sensitive so a lone lowercase "d" in prose doesn't false-match.
_DENIER_PATTERN = r"\b(\d{2,3})\s*-?\s*(?:[dD]enier\b|D\b)"

# Technical zippers — (canonical display value, pattern), specific first.
_ZIPPER_TERMS = [
    ("YKK AquaGuard", r"\bYKK\s+AquaGuard\b"),
    ("AquaGuard", r"\bAquaGuard\b"),
    ("waterproof zipper", r"\bwaterproof\s+zip(?:per)?s?\b"),
    ("YKK", r"\bYKK\b"),
]

# Hood / venting features — (canonical display value, pattern).
_HOOD_VENT_TERMS = [
    ("helmet-compatible hood", r"\bhelmet[-\s]compatible\s+hood\b"),
    ("storm hood", r"\bstorm\s+hood\b"),
    ("adjustable hood", r"\badjustable\s+hood\b"),
    ("pit zips", r"\bpit\s+zips?\b"),
]

# compare_on prompt lists — short, retailer-agnostic attribute names.
_WEATHER_COMPARE = [
    "Membrane / waterproofing",
    "Seam sealing",
    "Waterproof rating (mm)",
    "Breathability",
    "Face fabric durability",
]
_INSULATION_COMPARE = [
    "Fill power / insulation type",
    "Fill weight",
    "Shell fabric",
    "Warmth-to-weight",
    "DWR finish",
]
_GENERIC_COMPARE = [
    "Technical specs",
    "Construction",
    "Fabric durability",
    "Intended use",
]


def _spec(label: str, value: str, matched_text: str) -> dict:
    return {"label": label, "value": value, "matched_text": matched_text}


def _first_term_spec(label: str, text: str, terms: list[tuple[str, str]]) -> dict | None:
    """First (canonical, pattern) hit → spec with the canonical display value."""
    for canonical, pattern in terms:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return _spec(label, canonical, m.group(0))
    return None


def _extract_specs(text: str, text_lower: str) -> list[dict]:
    """Value-anchored spec extraction. Emits a spec only when its value appears."""
    specs: list[dict] = []

    # Membrane brand (word-boundary matched in _find_membrane)
    membrane = _find_membrane(text, text_lower)
    if membrane:
        specs.append(_spec("Membrane", membrane, membrane))

    # Shell layer construction → value normalised to "N-layer"
    for pat in _SHELL_LAYER_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            specs.append(_spec("Shell construction", f"{m.group(1)}-layer", m.group(0)))
            break

    # Seam sealing
    for phrase in _SEAM_SPEC_PHRASES:
        m = re.search(re.escape(phrase), text, re.IGNORECASE)
        if m:
            specs.append(_spec("Seam sealing", phrase, m.group(0)))
            break

    # DWR finish
    for phrase in _DWR_SPEC_PHRASES:
        m = re.search(re.escape(phrase), text, re.IGNORECASE)
        if m:
            specs.append(_spec("DWR finish", phrase, m.group(0)))
            break

    # Waterproof rating (mm)
    m = re.search(_WATERPROOF_MM_PATTERN, text, re.IGNORECASE)
    if m:
        specs.append(_spec("Waterproof rating", m.group(0), m.group(0)))

    # Breathability rating
    for pat in _BREATHABILITY_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            specs.append(_spec("Breathability", m.group(0), m.group(0)))
            break

    # Insulation type
    insulation = _first_term_spec("Insulation", text, _INSULATION_SPEC_TERMS)
    if insulation:
        specs.append(insulation)

    # Fill power (shared matcher with the detector)
    m = _find_fill_power(text)
    if m:
        specs.append(_spec("Fill power", m.group(1), m.group(0)))

    # Face fabric
    face = _first_term_spec("Face fabric", text, _FACE_FABRIC_TERMS)
    if face:
        specs.append(face)

    # Denier (case-sensitive match)
    m = re.search(_DENIER_PATTERN, text)
    if m:
        specs.append(_spec("Denier", f"{m.group(1)}D", m.group(0)))

    # Technical zipper
    zipper = _first_term_spec("Zipper", text, _ZIPPER_TERMS)
    if zipper:
        specs.append(zipper)

    # Hood / venting features
    hood = _first_term_spec("Hood / venting", text, _HOOD_VENT_TERMS)
    if hood:
        specs.append(hood)

    return specs


def _classify_type(text_lower: str, spec_labels: set[str]) -> str:
    """
    Light steer for comparison prompts, NOT an authoritative classification.
    Ambiguous input returns "technical_general" rather than forcing a type.
    """
    if "softshell" in text_lower:
        return "softshell"

    # Insulation dominates a bare shell membrane: an insulated jacket still has a
    # shell, so fill power / branded insulation classifies it as insulated even
    # when a membrane spec is also present.
    insulation_labels = {"Fill power", "Insulation"}
    if spec_labels & insulation_labels:
        if any(t in text_lower for t in ("polartec", "fleece", "midlayer", "mid-layer")):
            return "technical_midlayer"
        return "insulated_jacket"

    weather_labels = {"Membrane", "Seam sealing", "Waterproof rating", "Shell construction"}
    if (spec_labels & weather_labels
            or "waterproof-breathable" in text_lower
            or "hardshell" in text_lower):
        return "waterproof_shell"

    return "technical_general"


def _compare_on(technical_type: str, spec_labels: set[str]) -> list[str]:
    """
    Built primarily from which specs were actually found, lightly informed by
    technical_type, with a generic fallback. A correct compare_on does NOT depend
    on a correct technical_type for the spec-driven cases.
    """
    if spec_labels & {"Membrane", "Seam sealing", "Waterproof rating"}:
        return list(_WEATHER_COMPARE)
    if spec_labels & {"Fill power", "Insulation"}:
        return list(_INSULATION_COMPARE)
    if technical_type in ("waterproof_shell", "softshell"):
        return list(_WEATHER_COMPARE)
    if technical_type in ("insulated_jacket", "technical_midlayer"):
        return list(_INSULATION_COMPARE)
    return list(_GENERIC_COMPARE)


def detect_technical_signals(text: str) -> dict:
    """
    Scan product page text for technical fabric and construction signals.

    Returns:
        {
            "is_technical": bool,       # True when 2+ categories match
            "signals_found": list[str], # human-readable display labels
            "signal_count": int,        # number of categories matched
            "technical_type": str|None, # waterproof_shell | insulated_jacket |
                                        # softshell | technical_midlayer |
                                        # technical_general; None when not technical
            "specs": list[dict],        # value-anchored {label, value, matched_text}
            "compare_on": list[str],    # comparison-prompt attributes; [] when not technical
        }

    Each of the 6 detection categories contributes at most one signal.
    specs are always extracted (value-anchored, even for sub-threshold text);
    technical_type and compare_on are only populated when is_technical is True.
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

    # Category 6: Technical insulation — branded insulation OR an explicit
    # fill-power figure (same matcher the spec extractor uses, so they stay in
    # sync). Generic puffer/down/"polyester fill" language does not count.
    for brand in _INSULATION_BRANDS:
        if brand.lower() in text_lower:
            signals.append(f"Technical insulation ({brand})")
            break
    else:
        fill = _find_fill_power(text)
        if fill:
            signals.append(f"Technical insulation ({fill.group(0)})")

    count = len(signals)
    is_technical = count >= 2

    # specs are value-anchored and always extracted (even sub-threshold text).
    specs = _extract_specs(text, text_lower)
    spec_labels = {s["label"] for s in specs}

    # technical_type / compare_on only steer comparison once an item is technical.
    if is_technical:
        technical_type = _classify_type(text_lower, spec_labels)
        compare_on = _compare_on(technical_type, spec_labels)
    else:
        technical_type = None
        compare_on = []

    return {
        "is_technical": is_technical,
        "signals_found": signals,
        "signal_count": count,
        "technical_type": technical_type,
        "specs": specs,
        "compare_on": compare_on,
    }
