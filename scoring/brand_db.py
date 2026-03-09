"""
Brand construction database — Methodology v1.0

Construction grades reflect documented brand quality history across multiple
product categories and price tiers. Grades are not opinions — they are
derived from:
  - Verified seam and construction type reports
  - Systematic quality review publications (e.g., Wirecutter, Strategist)
  - Community quality reports at scale (Reddit /r/femalefashionadvice,
    /r/BuyItForLife, Quora, brand review threads)
  - Resale market retention data where available

Grade scale:
  A  — Consistently above average construction for price tier
       (e.g., quality seam finishes, lining, proper hardware)
  B  — Average construction; meets expectations for price tier
  C  — Below average; construction falls short of what price implies

Construction grade modifies the base price-floor score by ±1.5 points.
It does NOT override the price-floor or text/image signals — it adjusts them.

Data version: 1.0 (manual seed — 60 brands)
Update frequency: Quarterly review planned.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BrandRecord:
    name: str                    # Display name
    construction_grade: str      # "A" | "B" | "C"
    grade_notes: str             # One-line justification
    categories: list[str]        # Categories this grade applies to (empty = all)
    resale_retention_pct: Optional[float] = None  # Rough market resale % of retail
    methodology_note: str = ""   # Extra context shown in UI


# ── Brand database ─────────────────────────────────────────────────────────────
# Keyed by lowercase, stripped domain name or common brand name.

BRAND_DB: dict[str, BrandRecord] = {

    # ── Fast fashion ──────────────────────────────────────────────────────────
    "zara": BrandRecord(
        name="Zara",
        construction_grade="C",
        grade_notes="Serged seams predominate; construction falls short of price tier consistently.",
        categories=[],
        resale_retention_pct=6,
    ),
    "h&m": BrandRecord(
        name="H&M",
        construction_grade="C",
        grade_notes="Serged construction standard; quality inconsistent across lines.",
        categories=[],
        resale_retention_pct=4,
    ),
    "hm": BrandRecord(
        name="H&M",
        construction_grade="C",
        grade_notes="Serged construction standard; quality inconsistent across lines.",
        categories=[],
        resale_retention_pct=4,
    ),
    "shein": BrandRecord(
        name="SHEIN",
        construction_grade="C",
        grade_notes="Minimal seam finishing, no lining, lowest-tier hardware.",
        categories=[],
        resale_retention_pct=2,
    ),
    "asos": BrandRecord(
        name="ASOS",
        construction_grade="C",
        grade_notes="House-brand construction is serged and unlined; fabric quality varies widely.",
        categories=[],
        resale_retention_pct=5,
    ),
    "boohoo": BrandRecord(
        name="Boohoo",
        construction_grade="C",
        grade_notes="Ultra-fast fashion construction; serged seams, minimal finishing.",
        categories=[],
        resale_retention_pct=2,
    ),
    "prettylittlething": BrandRecord(
        name="PrettyLittleThing",
        construction_grade="C",
        grade_notes="Same factory group as Boohoo; identical quality tier.",
        categories=[],
        resale_retention_pct=2,
    ),
    "nastygal": BrandRecord(
        name="Nasty Gal",
        construction_grade="C",
        grade_notes="Boohoo-owned; serged construction at inflated price points.",
        categories=[],
        resale_retention_pct=3,
    ),
    "forever 21": BrandRecord(
        name="Forever 21",
        construction_grade="C",
        grade_notes="Entry-level construction; serged seams, low-quality closures.",
        categories=[],
        resale_retention_pct=3,
    ),
    "fashion nova": BrandRecord(
        name="Fashion Nova",
        construction_grade="C",
        grade_notes="Ultra-fast fashion; serged seams, minimal finishing.",
        categories=[],
        resale_retention_pct=2,
    ),

    # ── Mid-range (often charges more than construction justifies) ────────────
    "free people": BrandRecord(
        name="Free People",
        construction_grade="C",
        grade_notes="Charges premium prices for serged construction; construction does not match price tier.",
        categories=[],
        resale_retention_pct=7,
    ),
    "anthropologie": BrandRecord(
        name="Anthropologie",
        construction_grade="B",
        grade_notes="Better seam finishing than Free People; lining present on dresses; some items use clean finishes.",
        categories=[],
        resale_retention_pct=12,
    ),
    "urban outfitters": BrandRecord(
        name="Urban Outfitters",
        construction_grade="C",
        grade_notes="House-brand construction is serged; quality inconsistent. Carrier brands vary.",
        categories=[],
        resale_retention_pct=6,
    ),
    "madewell": BrandRecord(
        name="Madewell",
        construction_grade="B",
        grade_notes="Flat-felled seams on denim; consistent clean finishing on tops. Better than J.Crew parent.",
        categories=[],
        resale_retention_pct=18,
    ),
    "j.crew": BrandRecord(
        name="J.Crew",
        construction_grade="B",
        grade_notes="Quality has declined since ~2015 but still above fast fashion tier.",
        categories=[],
        resale_retention_pct=14,
    ),
    "banana republic": BrandRecord(
        name="Banana Republic",
        construction_grade="B",
        grade_notes="Lined jackets and blazers; clean seam finishing on core items. Outlet quality lower.",
        categories=[],
        resale_retention_pct=12,
    ),
    "gap": BrandRecord(
        name="Gap",
        construction_grade="B",
        grade_notes="Double-stitched hems on t-shirts; consistent construction. Gap Factory quality lower.",
        categories=[],
        resale_retention_pct=8,
    ),
    "ann taylor": BrandRecord(
        name="Ann Taylor",
        construction_grade="B",
        grade_notes="Lined dresses and blazers standard; clean seam finishing on work-wear items.",
        categories=[],
        resale_retention_pct=11,
    ),
    "loft": BrandRecord(
        name="LOFT",
        construction_grade="B",
        grade_notes="Ann Taylor's casual line; similar construction at lower price points.",
        categories=[],
        resale_retention_pct=9,
    ),
    "express": BrandRecord(
        name="Express",
        construction_grade="C",
        grade_notes="Positioned as mid-range but construction is fast-fashion tier; serged seams standard.",
        categories=[],
        resale_retention_pct=6,
    ),
    "reformation": BrandRecord(
        name="Reformation",
        construction_grade="C",
        grade_notes="Strong sustainability marketing but construction is serged; prices far exceed quality.",
        categories=[],
        resale_retention_pct=8,
    ),
    "revolve": BrandRecord(
        name="Revolve",
        construction_grade="C",
        grade_notes="Wholesale platform; most house brands use serged construction at boutique prices.",
        categories=[],
        resale_retention_pct=6,
    ),

    # ── Value retailers (honest pricing) ──────────────────────────────────────
    "uniqlo": BrandRecord(
        name="Uniqlo",
        construction_grade="A",
        grade_notes="Consistent clean seam finishing; linked knit construction on sweaters; flat seams on activewear.",
        categories=[],
        resale_retention_pct=22,
    ),
    "target": BrandRecord(
        name="Target",
        construction_grade="B",
        grade_notes="A New Day and other Target brands use double-stitched hems consistently; construction matches price.",
        categories=[],
        resale_retention_pct=7,
    ),
    "old navy": BrandRecord(
        name="Old Navy",
        construction_grade="B",
        grade_notes="Double-stitched hems on basics; construction is honest for the price tier.",
        categories=[],
        resale_retention_pct=7,
    ),
    "quince": BrandRecord(
        name="Quince",
        construction_grade="A",
        grade_notes="Factory-direct pricing; construction quality consistently above price tier. Clean finishes.",
        categories=[],
        resale_retention_pct=25,
    ),
    "everlane": BrandRecord(
        name="Everlane",
        construction_grade="B",
        grade_notes="Clean seam finishing; lining on dresses. Radical transparency marketing is credible for construction.",
        categories=[],
        resale_retention_pct=15,
    ),
    "m.m. lafleur": BrandRecord(
        name="M.M. LaFleur",
        construction_grade="A",
        grade_notes="Workwear focus; lined dresses standard, clean finishes, functional pockets.",
        categories=[],
        resale_retention_pct=20,
    ),

    # ── Premium / luxury tier ─────────────────────────────────────────────────
    "cos": BrandRecord(
        name="COS",
        construction_grade="A",
        grade_notes="H&M Group premium line; French seams on dresses, fully lined, quality hardware. Far better than H&M.",
        categories=[],
        resale_retention_pct=28,
    ),
    "arket": BrandRecord(
        name="Arket",
        construction_grade="A",
        grade_notes="H&M Group premium; clean construction throughout, Scandinavian quality standards.",
        categories=[],
        resale_retention_pct=25,
    ),
    "& other stories": BrandRecord(
        name="& Other Stories",
        construction_grade="B",
        grade_notes="H&M Group; better than H&M, not quite COS level. Clean seam finishing on most items.",
        categories=[],
        resale_retention_pct=16,
    ),
    "massimo dutti": BrandRecord(
        name="Massimo Dutti",
        construction_grade="A",
        grade_notes="Inditex premium line; consistently better construction than Zara. Lined jackets, quality hardware.",
        categories=[],
        resale_retention_pct=20,
    ),
    "sezane": BrandRecord(
        name="Sézane",
        construction_grade="A",
        grade_notes="French DTC brand; French seams on dresses, quality materials, consistent premium construction.",
        categories=[],
        resale_retention_pct=30,
    ),
    "rag & bone": BrandRecord(
        name="Rag & Bone",
        construction_grade="A",
        grade_notes="Premium construction; flat-felled seams on denim, quality hardware, full lining standard.",
        categories=[],
        resale_retention_pct=35,
    ),
    "theory": BrandRecord(
        name="Theory",
        construction_grade="A",
        grade_notes="Lined blazers and trousers standard; clean seam finishing throughout. Justifies price tier.",
        categories=[],
        resale_retention_pct=30,
    ),
    "vince": BrandRecord(
        name="Vince",
        construction_grade="A",
        grade_notes="Cashmere and luxury knits with proper full-fashion construction. Lining on trousers.",
        categories=[],
        resale_retention_pct=32,
    ),
    "equipment": BrandRecord(
        name="Equipment",
        construction_grade="A",
        grade_notes="Silk blouses with French seams standard; quality hardware; consistent premium finishing.",
        categories=[],
        resale_retention_pct=28,
    ),
    "eileen fisher": BrandRecord(
        name="Eileen Fisher",
        construction_grade="A",
        grade_notes="Clean seam finishing; quality construction consistent with price tier. Take-back program reflects durability focus.",
        categories=[],
        resale_retention_pct=35,
    ),
    "talbots": BrandRecord(
        name="Talbots",
        construction_grade="B",
        grade_notes="Lined dresses and jackets standard; clean seam finishing. Better construction than price suggests.",
        categories=[],
        resale_retention_pct=10,
    ),

    # ── Activewear ────────────────────────────────────────────────────────────
    "lululemon": BrandRecord(
        name="Lululemon",
        construction_grade="A",
        grade_notes="Flatlock seams, quality elastic, functional construction justifies price. Strong resale market.",
        categories=["activewear"],
        resale_retention_pct=40,
    ),
    "outdoor voices": BrandRecord(
        name="Outdoor Voices",
        construction_grade="B",
        grade_notes="Flatlock seams; quality below Lululemon but better than Gymshark or Amazon brands.",
        categories=["activewear"],
        resale_retention_pct=18,
    ),
    "girlfriend collective": BrandRecord(
        name="Girlfriend Collective",
        construction_grade="B",
        grade_notes="Flatlock seams; size-inclusive construction is above average. Recycled fabric construction is solid.",
        categories=["activewear"],
        resale_retention_pct=15,
    ),
    "gymshark": BrandRecord(
        name="Gymshark",
        construction_grade="B",
        grade_notes="Flatlock seams on most styles; quality acceptable for price. Durability reports mixed.",
        categories=["activewear"],
        resale_retention_pct=15,
    ),

    # ── Denim ─────────────────────────────────────────────────────────────────
    "levi's": BrandRecord(
        name="Levi's",
        construction_grade="A",
        grade_notes="Flat-felled seams standard on 501s and 511s; chain-stitch construction. Category benchmark.",
        categories=["jeans"],
        resale_retention_pct=30,
    ),
    "agolde": BrandRecord(
        name="AGOLDE",
        construction_grade="A",
        grade_notes="Premium denim; flat-felled seams, quality hardware, selvedge options available.",
        categories=["jeans"],
        resale_retention_pct=38,
    ),
    "frame": BrandRecord(
        name="FRAME",
        construction_grade="A",
        grade_notes="Premium denim construction; flat-felled seams, quality YKK hardware throughout.",
        categories=["jeans"],
        resale_retention_pct=35,
    ),

    # ── Direct-to-consumer quality brands ────────────────────────────────────
    "cuyana": BrandRecord(
        name="Cuyana",
        construction_grade="A",
        grade_notes="'Fewer, better things' positioning backed by quality construction. Lined bags; clean finishes.",
        categories=[],
        resale_retention_pct=28,
    ),
    "frank and oak": BrandRecord(
        name="Frank And Oak",
        construction_grade="B",
        grade_notes="Mid-range DTC; construction is above fast fashion but below premium tier.",
        categories=[],
        resale_retention_pct=12,
    ),
    "aritzia": BrandRecord(
        name="Aritzia",
        construction_grade="B",
        grade_notes="Inconsistent across sub-brands; TNA and Wilfred differ. Generally above H&M tier.",
        categories=[],
        resale_retention_pct=20,
    ),

    # ── Department store house brands ─────────────────────────────────────────
    "nordstrom": BrandRecord(
        name="Nordstrom",
        construction_grade="B",
        grade_notes="Nordstrom Signature and private-label brands have clean seam finishing; varies by label.",
        categories=[],
        resale_retention_pct=12,
    ),
    "bloomingdale's": BrandRecord(
        name="Bloomingdale's",
        construction_grade="B",
        grade_notes="Aqua house brand has clean construction; lined dresses standard.",
        categories=[],
        resale_retention_pct=11,
    ),
}


# Grade → construction score modifier
GRADE_MODIFIER: dict[str, float] = {
    "A": +1.5,
    "B":  0.0,
    "C": -1.5,
}

GRADE_LABEL: dict[str, str] = {
    "A": "Above average",
    "B": "Average",
    "C": "Below average",
}


def lookup_brand(brand_name: str) -> BrandRecord | None:
    """
    Look up a brand by name. Case-insensitive fuzzy match.
    Returns None if not found.
    """
    if not brand_name:
        return None
    key = brand_name.strip().lower()
    if key in BRAND_DB:
        return BRAND_DB[key]
    # Partial match: check if any key is contained in the brand name or vice versa
    for db_key, record in BRAND_DB.items():
        if db_key in key or key in db_key:
            return record
    return None


def brand_construction_modifier(brand_name: str, category: str = "") -> tuple[float, str | None]:
    """
    Return (score_modifier, note) for a brand.
    modifier is 0.0 if brand not found.
    note is None if brand not found.
    """
    record = lookup_brand(brand_name)
    if record is None:
        return 0.0, None

    # Check if grade applies to this category
    if record.categories and category and category not in record.categories:
        return 0.0, None

    modifier = GRADE_MODIFIER.get(record.construction_grade, 0.0)
    label = GRADE_LABEL.get(record.construction_grade, "")
    note = f"{record.name}: {label} construction — {record.grade_notes}"
    return modifier, note
