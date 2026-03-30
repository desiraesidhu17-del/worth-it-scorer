# Design: "Cold Data" Visual Redesign

**Date:** 2026-03-29
**Status:** Approved
**Scope:** `static/style.css`, `templates/index.html`, `static/app.js` (score rendering only)

---

## Direction

SSENSE editorial minimalism × Bloomberg terminal data density.
Cream background, Space Mono throughout, zero border-radius, bracket-style UI.
Reference: the EFFECTS menu screenshot — `[ ] STIPPLING`, `[ ] DOTS`, etc.

---

## Palette

| Token      | Value     | Usage                            |
|------------|-----------|----------------------------------|
| `--bg`     | `#f5f2eb` | Page background (warm cream)     |
| `--surface`| `#ede9df` | Section backgrounds if needed    |
| `--border` | `#ccc8be` | All 1px rules and dividers       |
| `--text`   | `#1a1a1a` | Primary text                     |
| `--muted`  | `#8a8070` | Labels, secondary text           |
| `--score`  | `#f5820a` | Score number only (Bloomberg orange) |
| `--green`  | `#2d6e3e` | High scores, good confidence     |
| `--yellow` | `#a07800` | Medium scores, medium confidence |
| `--red`    | `#c0392b` | Low scores, low confidence       |

---

## Typography

- **Font:** `Space Mono` (Google Fonts, 400 + 700 weights)
- **Fallback:** `"Courier New", Courier, monospace`
- **Base size:** 14px
- **Labels:** ALL CAPS, `letter-spacing: 0.08em`
- **No system UI font anywhere** — monospace only

---

## Layout & Structure Changes

### Header
```
worth it?    FIBER SCIENCE, NOT OPINION
─────────────────────────────────────────
```
- Logo: lowercase `worth it?` in mono, `font-weight: 700`
- Tagline: uppercase, muted, right-aligned or same line
- `1px solid --border` rule beneath

### Score Block (replaces SVG circle)
```
70              Solid natural fiber composition
──              with good predicted performance.
/100
                [MEDIUM CONFIDENCE]
                Fabric weight (GSM) not listed.
```
- `70` in `--score` orange, `font-size: 4rem`, `font-weight: 700`
- `──` thin rule, `/ 100` in `--muted`
- Verdict sentence in regular text to the right
- Confidence in brackets: `[HIGH CONFIDENCE]`, `[MEDIUM CONFIDENCE]`, `[LOW CONFIDENCE]`

### Section Headers
```
/MATERIAL ANALYSIS
──────────────────────────────────────────
```
- `/SECTION NAME` prefix, uppercase, `--muted` color for the slash
- Full-width `1px` rule beneath

### Stat Rows
```
DURABILITY.....................  70 / 100
PRICE PRESSURE.........  FAIRLY PRICED
COST PER WASH..........  $1.10 – $2.21
```
- Dotted leaders (`...`) between label and value
- Labels in `--muted`, values in `--text`
- Implemented with CSS `display: flex` + dotted border-bottom trick or JS-generated dots

### Property Bars
```
PILLING RESISTANCE    [██████░░░░]  59
TENSILE STRENGTH      [███████░░░]  65
COLORFASTNESS         [████████░░]  80
MOISTURE MANAGEMENT   [█████████░]  93
```
- `border-radius: 0` — square ends
- Bar track: `--border` fill
- Bar fill: color-coded (`--red` / `--yellow` / `--green`) per value
- Value number right-aligned

### Construction Section
```
/CONSTRUCTION                    6.0 / 10
──────────────────────────────────────────
[██████░░░░░░░░░░░░░░░░░░░░░░░░]

Premium construction expected at this price.

Madewell: Average construction — Flat-felled
seams on denim; consistent clean finishing.
```

### Buttons
```
[ DOWNLOAD CARD ]     [ SCORE ANOTHER ]
```
- Square, `1px solid --border`, no fill
- Hover: invert (black bg, white text)
- `font-family: monospace`, uppercase

### Input Form
- Tab labels: `URL` / `TEXT` / `MANUAL` — uppercase, underline active state
- Input fields: `border-radius: 0`, `1px solid --border`, cream background
- Submit button: `[ ANALYZE FIBER ]` bracket style

---

## Removed Elements

- SVG progress circle — replaced with plain number
- `border-radius` — removed everywhere (set to `0`)
- `box-shadow` — removed everywhere
- `-apple-system` / sans-serif fonts — replaced with Space Mono
- Dark background (`#0f0f0f`) — replaced with cream

---

## Files Changed

| File | Change |
|------|--------|
| `templates/index.html` | Add Space Mono Google Fonts link; update score block HTML (remove SVG, add `<div class="score-number-block">`); update button text to bracket style |
| `static/style.css` | Full palette swap; font swap; remove all border-radius; new section header styles; stat row dots; square bars; button invert hover |
| `static/app.js` | Remove `stroke-dashoffset` SVG animation; add plain number render for score; keep bar width animation |

---

## What Stays the Same

- All scoring logic (backend untouched)
- All data fields rendered (nothing removed from result card)
- Responsive breakpoint at 520px
- Color-coding semantics (red=bad, yellow=medium, green=good) — just darker shades for cream bg
- Download card functionality
