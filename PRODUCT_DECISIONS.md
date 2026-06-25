# Product Decisions — worth it?

> **The product logic and strategy layer.** Answers *what the product means and why* —
> not how it's coded (`CLAUDE.md`) and not what's next (`CURRENT_ROADMAP.md`).
>
> Sections marked **🟡 NEEDS INPUT** are strategic decisions from your ChatGPT discussions
> that aren't yet captured here. Fill these in — I left them as prompts rather than
> inventing strategy I can't verify from the code.

Last updated: 2026-06-19

---

## 1. What the card is supposed to communicate
The card answers one question: **"Will this hold up, and is the price fair for that?"**
It is a decision assistant, not a review. Outcome-first: the headline is the verdict, the
score is supporting evidence (deliberately demoted from hero in the headline redesign).

## 2. What the score means
- A **durability-vs-price** measure (0–100). "Is this built to last, and fairly priced for it?"
- Built from: weighted fiber properties (per category) → blend interactions → GSM/dominance/
  category-fit adjustments → construction contribution.

## 3. What the score does NOT mean
- **Not** comfort, feel, softness, drape, or style.
- **Not** "will you personally like it."
- This caveat is printed on the card so the number isn't over-read.

## 4. How we handle polyester / synthetics
- Polyester is **not auto-penalized** — it scores well where it fits the job
  (e.g. activewear: polyester >70% → +4; durability-favorable).
- Where it's a poor fit, it's flagged honestly rather than scored down silently:
  t-shirts weight **moisture/breathability** heavily (0.28), and polyester tees surface a
  **"Traps heat, low breathability"** watch-for.
- Principle: **fit-for-purpose over fiber snobbery.** Synthetic ≠ bad.

## 5. How we handle technical gear
- When membrane/performance signals appear (GORE-TEX, seam sealing, PrimaLoft, DWR, etc.,
  2+ categories → `is_technical`), a fiber-only durability score is **misleading**, so the
  card switches to the **technical override** state: shows "Fiber score" only, hides
  price-fit / cost-per-wear, and explains value comes from membrane tech + construction.
- Principle: **don't pretend to score what the score can't see.**

## 6. Brand / ownership context  🟡 NEEDS INPUT
> From your discussions: how (if at all) does brand ownership / parent-company context factor
> into the verdict or card? Capture the decision and rationale here.

## 7. "Shop" positioning  🟡 NEEDS INPUT
> Where does a Shop/discovery surface fit relative to the scorer? What is it for, and what is
> it explicitly NOT for? Capture the positioning decision here.

## 8. Discovery / sequencing  🟡 NEEDS INPUT
> The intended order users encounter features (ambient badge → card → ...). Capture the
> intended discovery sequence and why.

## 9. What we are deliberately NOT building (yet)
- **Compare feature (Plan B)** — frozen until ambient (Plan A) is validated in real use.
- Anything that turns the score into a comfort/style rating — that would dilute the one
  thing the score is trusted to mean (durability vs price).

---

## Open product tensions
- **Low score + "fairly priced"** can read as contradictory because material quality and
  price fairness are scored independently. Decision needed: reword, or visually separate the
  two axes so they don't appear to contradict. (Tracked in CURRENT_ROADMAP.md item #1.)
