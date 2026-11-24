---
name: snb-arima-decision-research
description: Research best practice for one modelling decision of the SNB disaggregate-ARIMA replication - a gap G1–G13 where Huwiler & Kaufmann (2013) are silent, or a D-xx entry in docs/decisions.md - by checking the paper itself, central-bank and statistical-office practice (SNB, ECB, Fed, BFS, IMF CPI manual), the forecasting literature and software docs, then writing a sourced research note and updating the decision row. Use when the user asks "what is best practice for D-11", "how do others handle X", "research gap G8", "is our default for D-xx defensible", or before confirming a proposed decision.
---

# SNB ARIMA — research best practice for one decision

Goal: turn a decision we made by default into one we can **defend in the thesis** with sources, in one short research note.
One invocation = one decision (D-xx or G-x). Do not change code here; if the research changes the decision, the change
is done later in the task that owns the code.

## Inputs
- The decision ID (`D-11`) or gap ID (`G7`). If the user gives only a topic ("implausible forecasts"), find the matching
  row in `docs/decisions.md`; if none exists, create a new `D-xx` row with status `proposed` first.
- Read: the row in `docs/decisions.md`, the gap text and the relevant section of `docs/paper_spec.md`, and the skill
  that will implement it (e.g. `snb-arima-item-models` for D-02) so the research answers the question the code needs.

## Procedure
1. **Frame the question** in one sentence the literature could answer, plus the candidate options (our default + 1–3
   alternatives). Example: "When selecting ARIMA orders by BIC for monthly CPI components, what maximum p and q are used?"
   Write down *what would change our mind* (e.g. "if most studies allow q up to 4 and find it is selected often").
2. **Check the paper first.** Re-read the passage cited in `paper_spec.md`; if the paper does answer it (footnote,
   appendix, table note), say so — the gap is closed and the research note can be short.
3. **Search, in this order of authority** (use WebSearch, `standard` mode first; read pages with the `web-fetch` agent):
   1. Same institution / same model: other SNB Economic Studies and Working Papers on inflation forecasting, SNB Quarterly
      Bulletin boxes, later papers citing Huwiler & Kaufmann (2013).
   2. Official statistics methodology: BFS/SFSO LIK methodology documents (basket revisions, collection, chaining), IMF/ILO
      *Consumer Price Index Manual*, Eurostat HICP methodology — authoritative for data questions (G8, G9, collection).
   3. Peer literature on disaggregate inflation forecasting, e.g. Hubrich (2005), Hendry & Hubrich (2011), Bermingham &
      D'Agostino (2014), Faust & Wright (2013, *Handbook of Economic Forecasting*), Stock & Watson — for model questions.
   4. Textbooks and software docs: Hyndman & Athanasopoulos *FPP*, Hamilton, Lütkepohl, Durbin & Koopman (state space),
      `statsmodels` docs — for estimation mechanics (G1, G3, G6, G13).
   These names are starting points, not facts: **only cite a source you actually opened**, with the page/section where
   the claim is. Never cite from memory; if a page cannot be fetched, say so and do not use it.
4. **Extract evidence** into a table: source, what they do / recommend, context (country, frequency, horizon), how close
   it is to our setting. Note disagreements explicitly — a split literature is a reason for a sensitivity check.
5. **Optional quick empirical check.** If the data exist and the question is empirical (e.g. "how often does q = 2 bind?"),
   write a small script in `scripts/explore/research_D-xx_<topic>.py` (AGENTS.md rule 7) and report its output. Respect
   no-look-ahead even in explorations. Skip this if the data are not built yet; say which task would enable it.
6. **Recommend.** Keep, change or refine the default. Give the reason in 2–3 plain sentences a Bachelor student can put in
   the thesis, and name the sensitivity check (alternative to run in T5.1) if sources disagree or the choice could move RMSFE.
7. **Write the note** `docs/decision_research/D-xx.md` with the template below.
8. **Update the row** in `docs/decisions.md`: sharpen "Why" (cite the 1–2 strongest sources, short form `Author (year, p.)`),
   update "Alternatives / sensitivity", add `see decision_research/D-xx.md`. **Keep status `proposed`** — only the user
   confirms. If the recommendation changes the decision, keep the old text and mark it `revised` per the log's rules.
9. **Ask the user** to confirm: recommendation + main alternative in two sentences, buttons "Confirm" / "Use alternative".
   On confirmation set status `confirmed`.
10. **Close**: micro retro with `skill-feedback-loop` (log in `docs/skill_feedback.md`), commit
    `D-xx: research best practice for <topic>` with the attribution line, `git push origin main`.

## Research note template (`docs/decision_research/D-xx.md`)
```markdown
# D-xx (G-y): <topic>
Date: YYYY-MM-DD · Status of decision after research: proposed / confirmed

## Question
<one sentence> — options considered: A (current default), B, C.

## What the paper says
<quote ≤ 15 words or paraphrase, with page> — or "silent".

## Evidence
| Source (opened) | What they do / recommend | Setting | Relevance |
|---|---|---|---|

## Empirical check (optional)
<script path, result, or "not yet possible: needs T2.1">

## Recommendation
<keep/change/refine + 2–3 sentences of reasoning for the thesis>

## Sensitivity check
<alternative to run in T5.1, or "none needed because …">

## Sources
- Full reference with URL / DOI, accessed YYYY-MM-DD.
```

## Rules
- Evidence beats convenience: if good sources contradict our default, say so plainly even if the change costs work.
- Prefer sources close to our setting (Swiss/euro-area CPI, monthly item level, short horizons) over generic advice.
- Quote at most one short passage per source (< 15 words); otherwise paraphrase.
- Never write numbers into the note that no source or script produced.
- Several decisions at once: do them one after another (one note each), not merged.

## Checks (definition of done)
- `docs/decision_research/D-xx.md` exists, every row of the evidence table has an opened source in "Sources".
- The `docs/decisions.md` row references the note; `pytest tests/test_decisions.py` still passes.
- Any exploration script runs from the repo root without errors.
