"""
Core scoring engine.

Takes a fiber composition, price, and category — returns a full score object.
No AI, no external calls. Pure deterministic logic.

Input example:
    score_item(
        composition=[{"fiber": "acrylic", "pct": 52}, {"fiber": "polyester", "pct": 48}],
        price=148.0,
        category="sweater",
    )

Output: ScoreResult dataclass (also serialisable to dict via .to_dict())
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

from .fiber_properties import (
    FIBER_PROPERTIES,
    CATEGORY_WEIGHTS,
    get_fiber,
    resolve_fiber,
)
from .blend_interactions import apply_blend_adjustments
from .price_benchmarks import evaluate_price_pressure
from .verdict_library import (
    get_verdict_sentence,
    get_cost_per_wash,
    get_score_band,
    CONFIDENCE_NOTES,
    get_headline,
    get_watch_for,
)
from .construction_rubric import ConstructionResult, score_from_price

METHODOLOGY_VERSION = "1.0"


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class FiberEntry:
    raw: str          # As supplied by the user / extraction
    canonical: str    # Resolved canonical name (or "unknown")
    pct: float        # Percentage (0–100)
    known: bool       # Whether we have property data for this fiber


@dataclass
class ScoreResult:
    # Input echo
    composition: list[FiberEntry]
    price: Optional[float]
    category: str

    # Material durability sub-score
    material_score: float          # 0–100
    property_scores: dict          # {"pilling": x, "tensile": x, ...}
    blend_interactions_applied: bool

    # Price / value
    price_pressure: dict           # from evaluate_price_pressure()
    cost_per_wash: dict            # from get_cost_per_wash()

    # Overall worth-it score
    worth_it_score: float          # 0–100

    # Confidence
    confidence: str                # "high" | "medium" | "low"
    confidence_notes: list[str]    # Plain-language explanations

    # Human-readable outputs
    verdict_sentence: str
    score_band: str                # "very_low" | "low" | "mid" | "good" | "excellent"

    # Construction sub-score (optional — populated when text or image is available)
    construction: Optional[ConstructionResult] = None

    # Headline (three-step system — see verdict_library.get_headline / get_watch_for)
    headline: str = ""
    headline_sub: str = ""
    watch_for: list[str] = field(default_factory=list)

    # GSM (fabric weight) modifier
    gsm: Optional[float] = None             # GSM value passed in
    gsm_modifier: int = 0                   # -10 / -5 / 0 / +6 / +10
    gsm_modifier_applied: bool = False      # True if conditions were met

    # Metadata
    methodology_version: str = METHODOLOGY_VERSION
    unknown_fibers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert FiberEntry list to plain dicts
        d["composition"] = [
            {"raw": f.raw, "canonical": f.canonical, "pct": f.pct, "known": f.known}
            for f in self.composition
        ]
        # PriceBenchmark is not serialisable; replace with plain dict
        if d["price_pressure"].get("benchmark"):
            bm = d["price_pressure"]["benchmark"]
            if hasattr(bm, "__dict__"):
                d["price_pressure"]["benchmark"] = bm.__dict__
        # Construction result
        if self.construction is not None:
            d["construction"] = self.construction.to_dict()
        else:
            d["construction"] = None
        return d


# ── Main scoring function ─────────────────────────────────────────────────────

def score_item(
    composition: list[dict],   # [{"fiber": str, "pct": float | int}, ...]
    price: Optional[float] = None,
    category: str = "other",
    construction: Optional[ConstructionResult] = None,
    gsm: Optional[float] = None,
) -> ScoreResult:
    """
    Score a garment from its fiber composition, retail price, and category.

    composition: list of dicts with keys "fiber" (str) and "pct" (number 0–100).
                 Percentages should sum to ~100; the engine normalises them if not.
    price:       retail price in USD, or None if unknown.
    category:    one of "sweater", "t-shirt", "dress", "jeans", "outerwear",
                 "activewear", "other".
    """
    category = _normalise_category(category)
    weights = CATEGORY_WEIGHTS.get(category, CATEGORY_WEIGHTS["other"])

    # ── 1. Resolve fibers ────────────────────────────────────────────────────
    entries: list[FiberEntry] = []
    unknown_fibers: list[str] = []
    total_pct = sum(float(f.get("pct", 0)) for f in composition)

    for raw_fiber in composition:
        raw_name = str(raw_fiber.get("fiber", "")).strip()
        pct = float(raw_fiber.get("pct", 0))
        # Normalise percentage if totals don't sum to 100
        if total_pct > 0 and abs(total_pct - 100) > 5:
            pct = (pct / total_pct) * 100

        canonical = resolve_fiber(raw_name)
        known = canonical is not None and canonical in FIBER_PROPERTIES

        if not known and raw_name:
            unknown_fibers.append(raw_name)

        entries.append(FiberEntry(
            raw=raw_name,
            canonical=canonical or "unknown",
            pct=pct,
            known=known,
        ))

    # Filter to known fibers for scoring; unknown fibers reduce confidence
    known_entries = [e for e in entries if e.known]
    known_pct_total = sum(e.pct for e in known_entries)

    if known_pct_total == 0:
        # Nothing to score
        return _no_data_result(entries, price, category, unknown_fibers)

    # ── 2. Weighted-average base property scores ─────────────────────────────
    base: dict[str, float] = {"pilling": 0, "tensile": 0, "colorfastness": 0, "moisture": 0}
    for entry in known_entries:
        props = get_fiber(entry.raw)
        weight = entry.pct / known_pct_total
        for prop in base:
            base[prop] += props[prop] * weight

    # ── 3. Apply blend interaction adjustments ───────────────────────────────
    comp_for_blend = [{"canonical": e.canonical, "pct": e.pct} for e in known_entries]
    adjusted, all_blends_known = apply_blend_adjustments(base, comp_for_blend)
    blend_interactions_applied = len(known_entries) > 1

    # ── 4. Weighted property score → material score ──────────────────────────
    material_score = sum(adjusted[prop] * weights[prop] for prop in weights)
    material_score = round(max(0.0, min(100.0, material_score)), 1)

    # ── 4.5. Combined score adjustments (GSM + dominance + category fit, cap ±15) ──
    gsm_mod, gsm_mod_applied = _gsm_modifier_for_score(gsm, known_entries, category)
    dominance_adj = _fiber_dominance_adjustment(known_entries)
    category_adj = _category_fit_adjustment(known_entries, category)
    combined_adj = max(-15, min(15, gsm_mod + dominance_adj + category_adj))
    material_score = round(max(0.0, min(100.0, material_score + combined_adj)), 1)

    # ── 5. Confidence assessment ─────────────────────────────────────────────
    confidence, confidence_notes = _assess_confidence(
        entries=entries,
        known_pct_total=known_pct_total,
        total_pct=total_pct,
        all_blends_known=all_blends_known,
        category=category,
    )

    # ── 6. Price pressure ────────────────────────────────────────────────────
    price_pressure = evaluate_price_pressure(price, category, material_score)

    # ── 7. Cost per wash ─────────────────────────────────────────────────────
    cost_per_wash = get_cost_per_wash(price or 0, material_score)

    # ── 9. Construction score ─────────────────────────────────────────────────
    if construction is None:
        construction = score_from_price(price, category)

    # ── 8. Worth-It Score ────────────────────────────────────────────────────
    # Material score minus price pressure penalty plus construction contribution.
    # Construction: (score−5)×0.8, capped ±5. Low confidence uses half modifier.
    pressure_penalty = _price_pressure_penalty(price_pressure["level"])
    construction_contrib = _construction_contribution(construction)
    worth_it_score = round(
        max(0.0, material_score - pressure_penalty + construction_contrib), 1
    )

    # ── 10. Human-readable outputs ────────────────────────────────────────────
    comp_dicts = [{"canonical": e.canonical, "pct": e.pct} for e in known_entries]
    verdict = get_verdict_sentence(worth_it_score, comp_dicts)
    band = get_score_band(worth_it_score)
    headline, headline_sub = get_headline(
        worth_it_score,
        price_pressure["level"],
        comp_dicts,
    )
    watch_for = get_watch_for(
        comp_dicts,
        {k: round(v, 1) for k, v in adjusted.items()},
        price,
        band,
    )

    return ScoreResult(
        composition=entries,
        price=price,
        category=category,
        material_score=material_score,
        property_scores={k: round(v, 1) for k, v in adjusted.items()},
        blend_interactions_applied=blend_interactions_applied,
        price_pressure=price_pressure,
        cost_per_wash=cost_per_wash,
        worth_it_score=worth_it_score,
        confidence=confidence,
        confidence_notes=confidence_notes,
        verdict_sentence=verdict,
        score_band=band,
        unknown_fibers=unknown_fibers,
        construction=construction,
        headline=headline,
        headline_sub=headline_sub,
        watch_for=watch_for,
        gsm=gsm,
        gsm_modifier=gsm_mod,
        gsm_modifier_applied=gsm_mod_applied,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gsm_modifier_for_score(
    gsm: Optional[float],
    known_entries: list[FiberEntry],
    category: str,
) -> tuple[int, bool]:
    """
    Returns (modifier, applied).
    Conditions: GSM provided, cotton or linen > 50% of composition, category is t-shirt or dress.
    modifier values: below 140 → -10, 140–179 → -5, 180–239 → 0, 240–299 → +6, 300+ → +10.
    applied is True when all conditions are met, even if modifier is 0 (baseline range).
    """
    if gsm is None:
        return 0, False
    if category not in ("t-shirt", "dress"):
        return 0, False

    natural_cellulose = {"cotton", "linen"}
    dominant = any(e.canonical in natural_cellulose and e.pct > 50 for e in known_entries)
    if not dominant:
        return 0, False

    if gsm < 140:
        return -10, True
    elif gsm < 180:
        return -5, True
    elif gsm < 240:
        return 0, True
    elif gsm < 300:
        return 6, True
    else:
        return 10, True


def _fiber_dominance_adjustment(known_entries: list[FiberEntry]) -> int:
    """
    +2 if one fiber makes up 90%+ of total known composition.
    -2 if 4 or more distinct fibers (complex blend; more variance).
    0 otherwise.
    """
    if not known_entries:
        return 0
    known_total = sum(e.pct for e in known_entries)
    if known_total == 0:
        return 0
    for entry in known_entries:
        if (entry.pct / known_total) * 100 >= 90:
            return 2
    if len(known_entries) >= 4:
        return -2
    return 0


def _category_fit_adjustment(known_entries: list[FiberEntry], category: str) -> int:
    """
    Flat adjustments for fiber/category combinations with strong quality implications.
    Additive — multiple adjustments can stack.

    Viscose/rayon in dress:       -3 (known structure loss and shrinkage)
    Linen in t-shirt or dress:    +3 (strong, breathable; good fit for category)
    Acrylic in sweater >40%:      -5 (genuinely poor durability; underpenalized by property avg)
    Polyester in activewear >70%: +4 (appropriate performance fiber)
    Cotton in activewear:         -4 (retains moisture; wrong for performance use)
    # Note: viscose and rayon are tracked as separate canonical fibers.
    # A label listing both would apply the -3 twice — rare in practice.
    """
    adj = 0
    for entry in known_entries:
        fiber = entry.canonical
        pct = entry.pct

        if fiber in ("viscose", "rayon") and category == "dress":
            adj -= 3

        if fiber == "linen" and category in ("t-shirt", "dress"):
            adj += 3

        if fiber == "acrylic" and category == "sweater" and pct > 40:
            adj -= 5

        if fiber == "polyester" and category == "activewear" and pct > 70:
            adj += 4

        if fiber == "cotton" and category == "activewear":
            adj -= 4

    return adj


def _construction_contribution(construction: ConstructionResult) -> float:
    """
    Returns construction score contribution to worth_it_score.

    Formula: (score - 5) * 0.8, capped at ±5 points.
    Neutral midpoint: score 5 → contribution 0.
    Score 7 → +1.6; score 3 → -1.6; score 10 → +4.0; score 0 → -4.0.

    Low confidence (price floor only): half the modifier, reflecting low certainty.
    Medium/high confidence (text or image signals): full modifier.
    """
    raw = (construction.score - 5) * 0.8
    capped = max(-5.0, min(5.0, raw))
    if construction.confidence == "low":
        return capped * 0.5
    return capped


def _normalise_category(category: str) -> str:
    cat = category.lower().strip()
    aliases = {
        "top": "t-shirt",
        "tee": "t-shirt",
        "shirt": "t-shirt",
        "blouse": "dress",
        "skirt": "dress",
        "pants": "jeans",
        "trousers": "jeans",
        "coat": "outerwear",
        "jacket": "outerwear",
        "cardigan": "sweater",
        "knit": "sweater",
        "knitwear": "sweater",
        "hoodie": "sweater",
        "sweatshirt": "sweater",
        "leggings": "activewear",
        "sports bra": "activewear",
    }
    return aliases.get(cat, cat if cat in CATEGORY_WEIGHTS else "other")


def _assess_confidence(
    entries: list[FiberEntry],
    known_pct_total: float,
    total_pct: float,
    all_blends_known: bool,
    category: str,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    issues: list[str] = []

    unknown_pct = 100 - known_pct_total
    has_unknown = any(not e.known for e in entries)

    if has_unknown and unknown_pct > 20:
        issues.append("major_unknown")
        notes.append(CONFIDENCE_NOTES["low_unknown_fibers"])
    elif has_unknown:
        issues.append("minor_unknown")
        notes.append(CONFIDENCE_NOTES["medium_partial"])

    if not all_blends_known and len(entries) > 1:
        issues.append("blend_unknown")
        notes.append(CONFIDENCE_NOTES["medium_blend"])

    # GSM matters most for cotton-heavy and linen garments in t-shirt category
    gsm_sensitive_fibers = {"cotton", "linen", "hemp"}
    is_gsm_sensitive = any(
        e.canonical in gsm_sensitive_fibers and e.pct > 40 for e in entries if e.known
    )
    if is_gsm_sensitive and category in ("t-shirt", "other"):
        issues.append("gsm_unknown")
        notes.append(CONFIDENCE_NOTES["medium_gsm"])

    if not issues:
        notes.append(CONFIDENCE_NOTES["high"])
        return "high", notes
    elif "major_unknown" in issues:
        return "low", notes
    else:
        return "medium", notes


def _price_pressure_penalty(level: str) -> float:
    """
    Translate price pressure level into a Worth-It Score deduction.
    The penalty makes the Worth-It Score lower than material score when price is unjustified.
    """
    return {
        "low": 0,
        "moderate": 5,
        "high": 15,
        "extreme": 25,
        "unknown": 0,
    }.get(level, 0)


def _no_data_result(
    entries: list[FiberEntry],
    price: Optional[float],
    category: str,
    unknown_fibers: list[str],
) -> ScoreResult:
    return ScoreResult(
        composition=entries,
        price=price,
        category=category,
        material_score=0,
        property_scores={},
        blend_interactions_applied=False,
        price_pressure={"level": "unknown", "label": "Unknown", "benchmark": None, "detail": ""},
        cost_per_wash={},
        worth_it_score=0,
        confidence="low",
        confidence_notes=[CONFIDENCE_NOTES["low_no_composition"]],
        verdict_sentence="No fiber composition data available — score cannot be calculated.",
        score_band="very_low",
        unknown_fibers=unknown_fibers,
        headline="No composition data",
        headline_sub="Score cannot be calculated without fiber composition information.",
        watch_for=[],
    )
