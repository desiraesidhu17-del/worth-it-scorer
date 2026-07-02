# 03 · Product Decisions

> Accepted product decisions. These are settled unless explicitly revisited in 05_OPEN_QUESTIONS.

## Accepted decisions
- **The score should not imply total desirability.** It is a durability/value read, not an
  overall "should you want this" rating.
- **Polyester should not be glamorized just because it is durable.** Synthetic tradeoffs
  (heat, breathability, microplastics-adjacent feel) should be surfaced in watch-for language.
- **Natural fibers should not be automatically boosted.** Describe the real tradeoffs instead
  of rewarding a fiber for being "natural."
- **Technical outerwear triggers a technical context override**, not a normal price/value
  judgment — value there comes from membrane tech + construction, not fiber score.
- **PFAS is not included in v1 scoring.**
- **Brand ownership context does not affect the score.** If shown at all, it belongs under
  build confidence as a context note, never as a score input.
- **Discovery is not built now.** Scorer first, discovery later.


Two real decisions came out of this work that aren't written down:

- **Never invent a spec value.** Only show specs actually found on the page (value-anchored).
- **The comparison frame must match the garment.** A rain shell is never told to compare on insulation; unknown types fall back to a generic prompt. This is a stated correctness guarantee now.

The "low material score + 'fairly priced' reads contradictory" tension appears in **four** places (dashboard, roadmap, card spec, and CLAUDE.md known issues) but has never been decided. It's your oldest unresolved product question. Either promote it to an active task with a target resolution, or make a decision about how the two labels should coexist.

## Brand lookup: exact match, not substring (accepted)
lookup_brand now normalizes then requires exact equality, no substring or
word-boundary partial matching. Deliberate, because "gap", "cos", "equipment"
are real English words that a partial match misfires on. Tradeoff accepted:
a decorated brand field like "Gap Official Store" now returns no note rather
than a possibly-wrong one. No-note is the safe failure for a trust tool.

## Three-bug sequence from real-retailer testing (accepted)
DWR display normalization (done, commit b2830f6 area), brand lookup false
positives (done), CAD/USD currency (next, own session). Fixed as three
separate commits, not bundled.

## Bug 3: price currency handling
Decided 2026-07-02.

Bug 3 is not a shopper currency-conversion feature. It is a benchmark
market-alignment bug. The app currently strips currency off every price, so
CA$150, US$150, £150 and €150 all score against the same US benchmark table.

Rules:
- Prices stay as listed. The app does not convert the shopper-facing price into
  another currency, and does not assume the shopper wants a home-currency conversion.
- Currency is captured and used internally only, to pick the right benchmark basis.
- Do not FX-normalize a foreign price into the US table. Converting CA$150 to
  ~US$106 and grading it against US benchmarks just swaps one bias for another and
  hides a guess inside a number that looks precise. That breaks the receipts pitch.
- If no benchmark basis matches the detected currency, lower price-fit confidence
  instead of pretending the comparison is as strong as US price on US benchmark.
- CAD is the first non-US market to get real benchmarks, but the ranges get sourced
  the same way the US ranges were. Claude Code does not invent CAD ranges.