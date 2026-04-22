import os, re, base64, hashlib, json, time
import uuid as _uuid_module
import requests as http_requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from openai import OpenAI, OpenAIError

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

from scoring import score_item
from scoring.construction_rubric import score_from_text, score_from_image, score_from_price

load_dotenv(override=True)
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

openai_client = OpenAI(api_key=API_KEY)

# In-memory extraction cache: hash → parsed extraction dict
_extraction_cache: dict[str, dict] = {}

# Result store for extension flow: uuid → { result, expires_at }
_result_store: dict[str, dict] = {}
_RESULT_TTL_SECONDS = 300  # 5 minutes

# Known retailers that block automated access (Akamai/Cloudflare Enterprise CDN)
# For these we skip the slow Playwright attempt and go straight to a clear error with
# brand-specific paste instructions.
_BLOCKED_DOMAINS = {
    "zara.com":          "On the Zara product page, scroll down to 'Composition and care' — copy those lines and paste them here.",
    "asos.com":          "On the ASOS product page, scroll to 'Product details' and copy the 'Composition' line.",
    "freepeople.com":    "On the Free People page, scroll to 'CONTENT + CARE' — copy those lines and paste them here.",
    "anthropologie.com": "On the Anthropologie page, scroll to 'Content + Care' — copy that section and paste it here.",
    "madewell.com":      "On the Madewell page, scroll to the 'Details' panel — copy the fabric content line and paste it here.",
    "urbanoutfitters.com": "On the Urban Outfitters page, scroll to 'Content + Care' — copy those lines and paste them here.",
    "nastygal.com":      "On the Nasty Gal page, scroll to 'Details' — copy the composition line and paste it here.",
    "hm.com":            "On the H&M page, scroll to 'Composition' — copy those lines and paste them here.",
    "shein.com":         "On the SHEIN page, click 'See all' under description, copy the composition lines, and paste them here.",
    "prettylittlething.com": "On the PrettyLittleThing page, scroll to 'Product Details' — copy the composition line and paste it here.",
    "boohoo.com":        "On the Boohoo page, scroll to 'Product details' — copy the composition line and paste it here.",
    "nordstrom.com":     "On the Nordstrom page, scroll to 'Details & Care' — copy those lines and paste them here.",
    "bloomingdales.com": "On the Bloomingdale's page, scroll to 'Details' — copy the fabric content lines and paste them here.",
}

# Browser-like headers for URL fetching
_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/methodology")
def methodology():
    return render_template("methodology.html")


@app.route("/api/score", methods=["POST"])
def score_endpoint():
    """
    Four input paths, all returning the same score object:

    A) JSON with "url"         → fetch page, GPT extracts composition
    B) JSON with "raw_text"    → GPT extracts composition from pasted text
    C) JSON with "composition" → score directly, no GPT needed
    D) Multipart with "image"  → GPT-4o vision extracts composition
    """
    try:
        construction = None  # populated below when source text/image is available

        # ── Path A: URL scan ──────────────────────────────────────────────────
        if request.is_json and request.get_json(force=True, silent=True) and \
                "url" in (request.get_json(force=True, silent=True) or {}):
            data = request.get_json(force=True)
            url = data.get("url", "").strip()
            price = _parse_price(data.get("price"))
            category = data.get("category", "other")

            extraction = _extract_from_url(url)
            if "error" in extraction:
                return jsonify(extraction), 422

            composition = extraction.get("composition", [])
            brand = extraction.get("brand") or None
            if price is None:
                price = _parse_price(extraction.get("price"))
            if category == "other" and extraction.get("category"):
                category = extraction["category"]
            # Construction: extract signals from page text + brand grade
            page_text = extraction.get("_page_text", "")
            if page_text:
                construction = score_from_text(page_text, price, category, brand=brand)

        # ── Path B: Raw text paste ────────────────────────────────────────────
        elif request.is_json and "raw_text" in (request.get_json(force=True, silent=True) or {}):
            data = request.get_json(force=True)
            raw_text = data.get("raw_text", "").strip()
            price = _parse_price(data.get("price"))
            category = data.get("category", "other")

            if not raw_text:
                return jsonify({"error": "raw_text is required"}), 400

            extraction = _extract_from_text(raw_text)
            if "error" in extraction:
                return jsonify(extraction), 422

            composition = extraction.get("composition", [])
            brand = extraction.get("brand") or None
            if price is None:
                price = _parse_price(extraction.get("price"))
            if category == "other" and extraction.get("category"):
                category = extraction["category"]
            # Construction: scan the raw user-pasted text for signals + brand grade
            construction = score_from_text(raw_text, price, category, brand=brand)

        # ── Path C: Direct composition (manual form) ──────────────────────────
        elif request.is_json:
            data = request.get_json(force=True)
            composition = data.get("composition", [])
            price = _parse_price(data.get("price"))
            category = data.get("category", "other")
            brand = data.get("brand") or None

            if not composition:
                return jsonify({"error": "composition is required"}), 400
            # Construction: price-floor + brand grade (no text/image available)
            from scoring.construction_rubric import score_from_price as _sfp
            construction = _sfp(price, category, brand=brand)

        # ── Path D: Image upload ──────────────────────────────────────────────
        elif "image" in request.files:
            file = request.files["image"]
            price = _parse_price(request.form.get("price"))
            category = request.form.get("category", "other")
            brand = request.form.get("brand") or None

            img_bytes = file.read()
            extraction = _extract_from_image(img_bytes)
            if "error" in extraction:
                return jsonify(extraction), 422

            composition = extraction.get("composition", [])
            if not brand:
                brand = extraction.get("brand") or None
            if price is None:
                price = _parse_price(extraction.get("price"))
            if category == "other" and extraction.get("category"):
                category = extraction["category"]
            # Construction: full GPT-4o vision rubric on the same image + brand grade
            construction = score_from_image(img_bytes, price, category, openai_client, brand=brand)

        else:
            return jsonify({"error": "Provide a URL, product text, composition, or image"}), 400

        if not composition:
            return jsonify({
                "error": "No fiber composition found. The page may not list materials, or the site blocks external access.",
                "error_type": "empty",
            }), 422

        result = score_item(
            composition=composition,
            price=price,
            category=category,
            construction=construction,
        )
        return jsonify(result.to_dict())

    except OpenAIError as e:
        code = getattr(e, "code", "")
        if code == "insufficient_quota":
            return jsonify({"error": "OpenAI quota exceeded — please check your plan."}), 429
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── URL extraction ─────────────────────────────────────────────────────────────

def _extract_from_url(url: str) -> dict:
    """Fetch a product page URL and extract composition via GPT text extraction.

    Strategy:
    1. Check known-blocked retailers first — skip fetch, return specific instructions immediately.
    2. Try a fast requests.get() — works for server-rendered sites (Uniqlo, etc.)
    3. If blocked or insufficient text, fall back to Playwright headless Chromium.
    4. Only surface the 'Paste text' error if both paths fail.
    """
    if not url.startswith(("http://", "https://")):
        return {"error": "Please enter a full URL starting with https://", "error_type": "network"}

    cache_key = "url:" + hashlib.sha256(url.encode()).hexdigest()
    if cache_key in _extraction_cache:
        return _extraction_cache[cache_key]

    # ── Step 0: Known-blocked retailer fast-path ──────────────────────────────
    domain_hint = _blocked_domain_hint(url)
    if domain_hint:
        return {
            "error": f"This site blocks automated access. Switch to the 'Paste text' tab — {domain_hint}",
            "error_type": "blocked",
        }

    page_text = None
    raw_html = None  # Raw HTML for candidate block isolation and JSON-LD extraction
    needs_js = False

    # ── Step 1: Fast HTTP fetch ───────────────────────────────────────────────
    try:
        response = http_requests.get(url, headers=_FETCH_HEADERS, timeout=8, allow_redirects=True)

        if response.status_code in (403, 401, 429):
            needs_js = True  # Site blocks bots — try headless browser
        elif response.status_code >= 400:
            return {
                "error": f"This page returned an error ({response.status_code}). Check the link and try again.",
                "error_type": "network",
            }
        else:
            raw_html = response.text  # Capture raw HTML before stripping tags
            soup = BeautifulSoup(raw_html, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer", "iframe", "noscript"]):
                tag.decompose()
            candidate = soup.get_text(separator=" ", strip=True)
            if len(candidate.strip()) < 200:
                needs_js = True  # JS-rendered — content not in static HTML
            else:
                page_text = candidate

    except http_requests.exceptions.Timeout:
        needs_js = True  # Slow server — try headless with longer timeout
    except http_requests.exceptions.RequestException:
        return {
            "error": "Couldn't reach this URL. Check the link and try again.",
            "error_type": "network",
        }

    # ── Step 2: Playwright headless fallback ──────────────────────────────────
    if needs_js and page_text is None:
        page_text = _fetch_with_playwright(url)

    # ── Step 3: Still nothing? Surface actionable error ───────────────────────
    if not page_text:
        return {
            "error": (
                "This site requires a browser to load its content. "
                "Switch to the 'Paste text' tab: open the product page, copy the description and materials section, and paste it there."
            ),
            "error_type": "blocked",
        }

    # ── Production pipeline ────────────────────────────────────────────────────
    from scoring.extractor import (
        isolate_candidate_blocks, extract_from_payload, _call_gpt_resolver
    )

    # Step 0: candidate block isolation from fetched HTML
    html_source = raw_html or page_text or ""
    candidate_blocks = isolate_candidate_blocks(html_source) if html_source else []

    # Build payload for extract_from_payload
    payload = {
        "url": url,
        "json_ld": _extract_json_ld_from_html(html_source),
        "meta": _extract_meta_from_html(html_source),
        "candidate_blocks": candidate_blocks or ([page_text[:3000]] if page_text else []),
    }

    extraction = extract_from_payload(payload)

    # GPT fallback if needed
    if not extraction.composition_blocks:
        fallback_text = " ".join(candidate_blocks[:3]) if candidate_blocks else page_text[:2000]
        extraction = _call_gpt_resolver(fallback_text, openai_client)

    result = extraction.to_dict()
    result["_page_text"] = " ".join(candidate_blocks) if candidate_blocks else page_text[:3000]
    _extraction_cache[cache_key] = result
    return result


def _blocked_domain_hint(url: str) -> str | None:
    """Return a paste-text hint string if the URL matches a known-blocked retailer, else None."""
    try:
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or ""
        # Strip www. prefix for matching
        hostname = hostname.removeprefix("www.")
        for domain, hint in _BLOCKED_DOMAINS.items():
            if hostname == domain or hostname.endswith("." + domain):
                return hint
    except Exception:
        pass
    return None


def _extract_json_ld_from_html(html_or_text: str) -> list:
    """Extract JSON-LD blocks from raw HTML."""
    if not html_or_text:
        return []
    try:
        soup = BeautifulSoup(html_or_text, "lxml")
        blocks = []
        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string or ""
            try:
                blocks.append(json.loads(raw))
            except (json.JSONDecodeError, ValueError):
                blocks.append(raw)  # send raw for fallback
        return blocks
    except Exception:
        return []


def _extract_meta_from_html(html_or_text: str) -> dict:
    """Extract key meta tags from raw HTML."""
    meta = {}
    if not html_or_text:
        return meta
    try:
        soup = BeautifulSoup(html_or_text, "lxml")
        for tag in soup.find_all("meta"):
            name = tag.get("property") or tag.get("name") or ""
            content = tag.get("content") or ""
            if name and content:
                meta[name] = content
    except Exception:
        pass
    return meta


def _fetch_with_playwright(url: str) -> str | None:
    """Render a page with headless Chromium and return its visible text.

    Returns None if Playwright is unavailable or the fetch fails.
    """
    if not _PLAYWRIGHT_AVAILABLE:
        return None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=_FETCH_HEADERS["User-Agent"],
                locale="en-US",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Block images, fonts, media — we only need text
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "media", "font", "stylesheet")
                else route.continue_(),
            )

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                # Give JS a moment to inject product content
                page.wait_for_timeout(2500)
            except PlaywrightTimeout:
                browser.close()
                return None

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer", "iframe", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text if len(text.strip()) >= 200 else None

    except Exception:
        return None


# ── Text extraction ────────────────────────────────────────────────────────────

def _extract_from_text(raw_text: str) -> dict:
    """Extract composition from user-pasted product description text."""
    cache_key = "text:" + hashlib.sha256(raw_text.encode()).hexdigest()
    if cache_key in _extraction_cache:
        return _extraction_cache[cache_key]

    result = _call_gpt_text_extraction(raw_text[:6000])
    _extraction_cache[cache_key] = result
    return result


# ── Shared GPT text extraction ─────────────────────────────────────────────────

_TEXT_EXTRACTION_PROMPT = """You are a product data extractor for clothing items.
Extract ONLY the following fields from this product page text. Return valid JSON only. No explanation.

{
  "composition": [{"fiber": "<fiber name>", "pct": <number 0-100>}],
  "price": <number or null>,
  "category": "<sweater|t-shirt|dress|jeans|outerwear|activewear|other>",
  "brand": "<brand name or null>"
}

Rules:
- composition must be a list of fibers found in the text. Only include fibers with listed percentages.
- price must be a number (no currency symbol). Use the sale price if discounted. null if not found.
- fiber names must be lowercase (e.g. "polyester", "cotton", "viscose", "elastane").
- Percentages should sum to approximately 100.
- If a field is not found in the text, return null. Do not guess or invent data.
"""


def _call_gpt_text_extraction(text: str) -> dict:
    """Send text to gpt-4o-mini for structured composition extraction."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _TEXT_EXTRACTION_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            max_tokens=300,
        )
    except OpenAIError:
        raise  # Re-raise so the route handler catches and formats it

    raw = response.choices[0].message.content
    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Could not parse the product data. Try the manual entry tab.", "error_type": "parse"}

    # Normalise composition: lowercase fiber names, filter nulls
    composition = []
    for item in extracted.get("composition") or []:
        if isinstance(item, dict) and item.get("fiber") and item.get("pct") is not None:
            composition.append({
                "fiber": str(item["fiber"]).lower().strip(),
                "pct": float(item["pct"]),
            })

    extracted["composition"] = composition
    return extracted


# ── Image extraction (unchanged) ──────────────────────────────────────────────

_IMAGE_EXTRACTION_PROMPT = """You are a product data extractor for clothing items.
Extract ONLY the following fields from this product page image. Return valid JSON only. No explanation.

{
  "composition": [{"fiber": "<fiber name>", "pct": <number 0-100>}],
  "price": <number or null>,
  "category": "<sweater|t-shirt|dress|jeans|outerwear|activewear|other>",
  "brand": "<brand name or null>"
}

Rules:
- composition must be a list. If percentages are not listed, still list the fibers with pct set to null.
- price must be a number (no currency symbol). null if not visible.
- If a field is not visible or not available, use null. Do not guess or invent data.
- fiber names should be lowercase (e.g. "polyester", "cotton", "viscose").
- Percentages should sum to approximately 100. If they clearly don't, adjust proportionally.
"""


def _extract_from_image(img_bytes: bytes) -> dict:
    """Send image to GPT-4o for structured composition extraction. Caches by image hash."""
    img_hash = hashlib.sha256(img_bytes).hexdigest()
    if img_hash in _extraction_cache:
        return _extraction_cache[img_hash]

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": _IMAGE_EXTRACTION_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            ],
        }],
        response_format={"type": "json_object"},
        max_tokens=400,
    )

    raw = response.choices[0].message.content
    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Could not parse composition from image. Try pasting the details manually.", "error_type": "parse"}

    composition = []
    for item in extracted.get("composition") or []:
        if isinstance(item, dict) and item.get("fiber"):
            pct = item.get("pct")
            if pct is not None:
                composition.append({"fiber": str(item["fiber"]).lower(), "pct": float(pct)})

    extracted["composition"] = composition
    _extraction_cache[img_hash] = extracted
    return extracted


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_price(value) -> float | None:
    if value is None:
        return None
    try:
        # Strip all non-numeric characters except decimal point.
        # Handles: $217, CA$217, £89.99, €120, AU$145, 1,234.56
        cleaned = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


# ── Extension API endpoints ────────────────────────────────────────────────────

@app.route("/api/score-page", methods=["POST", "OPTIONS"])
def score_page_endpoint():
    """
    Extension endpoint. Receives pre-extracted page data from content.js.
    Runs the production extraction pipeline, stores result, returns { result_id }.
    """
    if request.method == "OPTIONS":
        return _cors_preflight()

    try:
        data = request.get_json(force=True, silent=True) or {}
        price = _parse_price(data.get("price"))
        category = data.get("category", "other")

        # Run production extraction pipeline
        from scoring.extractor import extract_from_payload, _call_gpt_resolver
        result_extraction = extract_from_payload(data)

        # GPT fallback if still no composition
        if not result_extraction.composition_blocks:
            candidate_text = " ".join(data.get("candidate_blocks") or [])
            if candidate_text:
                result_extraction = _call_gpt_resolver(candidate_text, openai_client)

        if not result_extraction.composition_blocks:
            return jsonify({
                "error": "No fiber composition found on this page.",
                "error_type": "empty"
            }), 422

        composition = result_extraction.main_composition or (
            result_extraction.composition_blocks[0].fibers
            if result_extraction.composition_blocks else []
        )
        if price is None:
            price = result_extraction.price
        if category == "other" and result_extraction.category:
            category = result_extraction.category

        brand = result_extraction.brand
        candidate_text = " ".join(data.get("candidate_blocks") or [])
        construction = score_from_text(
            candidate_text, price, category, brand=brand
        ) if candidate_text else None

        score_result = score_item(
            composition=composition,
            price=price,
            category=category,
            construction=construction,
        )
        result_dict = score_result.to_dict()
        result_dict.update(result_extraction.to_dict())

        # Technical signal detection (extension path only — candidate_blocks present)
        if candidate_text:
            from scoring.technical_signals import detect_technical_signals
            tech = detect_technical_signals(candidate_text)
            if tech["is_technical"]:
                result_dict["technical_override"] = tech["signals_found"]

        # Store with TTL
        result_id = str(_uuid_module.uuid4())
        _result_store[result_id] = {
            "result": result_dict,
            "expires_at": time.time() + _RESULT_TTL_SECONDS,
        }
        _cleanup_result_store()

        return jsonify({"result_id": result_id})

    except OpenAIError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/result/<result_id>", methods=["GET", "OPTIONS"])
def get_result_endpoint(result_id: str):
    """Fetch a previously scored result by UUID (used by web app after extension opens it)."""
    if request.method == "OPTIONS":
        return _cors_preflight()

    entry = _result_store.get(result_id)
    if not entry:
        return jsonify({"error": "Result not found or expired", "error_type": "expired"}), 404
    if time.time() > entry["expires_at"]:
        del _result_store[result_id]
        return jsonify({"error": "Result expired", "error_type": "expired"}), 404

    return jsonify(entry["result"])


def _cleanup_result_store():
    """Evict expired entries. Call periodically to prevent memory growth."""
    now = time.time()
    expired = [k for k, v in _result_store.items() if now > v["expires_at"]]
    for k in expired:
        del _result_store[k]


def _cors_preflight():
    """Return CORS preflight response for extension requests."""
    resp = jsonify({})
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp, 204


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to extension API endpoints."""
    if request.path.startswith("/api/score-page") or request.path.startswith("/api/result/"):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(port=port, debug=True)
