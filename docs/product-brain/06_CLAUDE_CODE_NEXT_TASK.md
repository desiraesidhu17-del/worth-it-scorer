# 06 · Claude Code — Next Task

> Fill this in before handing a task to Claude Code. One task at a time. Keep it specific.

## Objective
<!-- One sentence: what should be true when this task is done? -->

## Context
<!-- Why now? Link relevant product-brain sections (card spec, decisions, open questions). -->

## Files likely affected
<!-- Best guess at the files to touch. -->

## Tasks
<!-- Ordered, concrete steps. -->
- [ ]

## Tests to run
<!-- e.g. pytest scoring/test_extractor.py scoring/test_verdict.py ; python -m scoring.tests -->

## Do not change
<!-- Explicit guardrails — files/behavior that must stay untouched. -->


# 06 · Claude Code — Next Task

## Objective
Prices in non-USD currencies (CAD first) are scored against USD benchmarks,
so a $498 CAD item is judged as if it were $498 USD and called "fairly priced."
Make price scoring currency-aware.

## Context
Found from real-retailer testing. Reigning Champ GORE-TEX Rival, $498 CAD,
scored against the USD benchmark range and displayed roughly "$501, fairly
priced." $498 CAD is about $365 USD. Affects every Canadian-priced page, which
is most of my own test set. This is the app-wide version of the currency bug
previously noted in the Option B swimwear work.

## Files likely affected
scoring/price_benchmarks.py (evaluate_price_pressure), the extractor where
price/currency is parsed, possibly engine.py where price flows in.

## Open questions before scoping
- Where does currency get detected? Is it captured at extraction today or lost?
- Convert to USD at scan time, or store benchmarks per currency?
- Static conversion rate or a live source? (Static is fine for v1.)

## Tests to run
python -m scoring.tests

## Do not change
Not yet scoped. This needs its own session before handing to Claude Code.