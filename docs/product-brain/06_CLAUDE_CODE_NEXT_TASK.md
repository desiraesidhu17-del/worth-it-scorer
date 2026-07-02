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

## Task: price currency preservation (detection only, no scoring change)

Problem:
_parse_price strips everything but digits, so CA$150, US$150, £150 and €150 all
collapse to 150 and score against the US benchmark table. The GPT prompts also
tell the model to return price with no currency symbol, throwing currency away
even when the page has it.

Goal:
Preserve original amount, currency, and raw price string. Do not change any
scoring behavior yet. This commit is plumbing only.

Scope:
1. Parser returns amount, currency, and raw_price string. Detect currency from
   explicit markers in the string only: CAD / CA$ / C$, USD / US$, AUD / AU$,
   GBP / £, EUR / €.
2. Also capture currency from structured metadata already being read (JSON-LD
   priceCurrency, meta price:currency / og:price:currency), at the same point the
   extractor already reads meta price. This is nearly free since that path exists.
3. Update the text and image GPT prompts to ask for "currency":
   "USD|CAD|AUD|GBP|EUR|null" alongside price. Remove the "no currency symbol"
   instruction that forces the model to discard it.
4. Preserve amount / currency / raw_price in result_dict for debugging and future UI.
5. Do not change which numeric price is passed into scoring. score_item still gets
   the bare amount. Scores for any given item must be identical to before this commit.
6. Plain "$150" with no symbol and no structured currency source parses to
   amount 150, currency null. Do not default to USD.
7. Do not infer currency from domain (.ca), locale, or Shopify settings in this
   task. That resolution layer belongs to the benchmark-policy task.

Tests:
- CA$150 -> amount 150, currency CAD
- US$150 -> amount 150, currency USD
- £150   -> amount 150, currency GBP
- €150   -> amount 150, currency EUR
- AU$150 -> amount 150, currency AUD
- plain "$150" -> amount 150, currency null
- one known item scores identically to before (metadata added, score unchanged)

Do not:
- convert currencies or add live FX
- create CAD benchmark ranges
- build domain / locale currency inference
- change price pressure, construction floors, cost-per-wash, verdicts, or card copy