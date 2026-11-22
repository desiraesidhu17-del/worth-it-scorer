# Barefax / Discovery Studio — Experiment 01

This is a **standalone, dependency-free interactive prototype** for a different shopping experience: **Keep what you love. Change the rest.** It lives only on the `experiment/discovery-studio` branch and does not modify the production scoring engine, Chrome extension, Flask routes, or Railway deployment.

## Open it

From the repository's root:

```sh
python -m http.server 8765
```

Visit **http://localhost:8765/studio/** in a browser. You can also open `studio/index.html` directly. Nothing needs to be installed, and no API key or account is required.

The layout is responsive; try it on a narrow window too.

## Three-minute play test

1. Start with **The Everyday**. The matching engine initially preserves silhouette; turn on Neckline to narrow the options.
2. Turn off **Neckline** to widen the possibilities, or preserve **Material** to tighten the shortlist.
3. Switch **Close to my idea** / **Surprise me**. Both respect all preserved traits; the second favours more variation in other traits.
4. Click **Explore this direction** to adopt an alternative, then **Undo**.
5. Save two or three pieces with the heart buttons. Open **My finds** to compare and remove them.
6. Refresh. Saved pieces persist in this browser's local storage; the active exploration itself resets.

## What is real and what isn't

- **Real functionality:** responsive interface, hard-constraint attribute matching, exploration, undo, save/remove, local persistence, and side-by-side comparison.
- **Illustrative data:** twelve *fictional design exercises*, with original vector garments and demo attributes. These are **not retailer listings** or price/quality/fit claims. Nothing is for sale.
- **Not connected:** live product search, existing Worth It scorer, price tracking, accounts, factory provenance, merchant feeds, AI models, checkout, analytics, or paid APIs.

Do not use the sample materials to imply verified product composition or superiority. The matching is intentionally simple and transparent so that the user experience can be tested without fake "AI intelligence."

## Why isolated?

The canonical Worth It scorer is currently in `app.py`, `scoring/`, `templates/`, `static/`, and `extension/`. This experiment only adds `studio/`; **do not merge into main** until both its purpose and interactions have been reviewed.

The October 2026 unpushed documentation commit reported by Codex on another local checkout (`509e469`) is **not** part of this branch. Preserve it and reconcile separately if it contains useful notes.

## Questions for the next session

- Does selecting attributes feel playful or too questionnaire-like?
- Would you rather begin with a product link, an image, a saved board, or a broad idea?
- Are four alternatives useful, or would fewer, more distinct options be better?
- Which information should appear immediately and which belongs behind **Quality & evidence**?
- Does the comparison make it easier to *finish*, rather than just generating more browsing?

**Next small experiment:** replace a few demo entries with real, permitted product images and source links, preserving the ability to tell verified facts from inferred attributes. Only then investigate integrating the existing scoring API. Avoid a full rewrite or catalogue ingestion.

## Session handoff

- Built: first visual discovery screen; twelve sample garments; preserve/change matching; surprise mode; undo; saved comparisons.
- Verify: run the static server, interact with the controls, use browser devtools to check for errors.
- Next: collect concrete feedback from the working preview, then change one interaction at a time.
