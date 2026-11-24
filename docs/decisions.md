# Decision log

Every place where the paper is silent (gaps G1–G13 in `paper_spec.md`) or where we deviate from it gets an entry.
Reference the ID in code comments (`# D-03`). Status: `proposed` (default chosen by agent, not yet confirmed by the
user) · `confirmed` · `revised` (keep the old text, add the new one below).

| ID | Gap | Decision | Why | Alternatives / sensitivity | Status |
|---|---|---|---|---|---|
| D-01 | G1 | Item models include a constant (drift in log levels) | Mean item inflation ≠ 0; paper omits it only "to keep the exposition simple" (p. 6) | No constant; check effect on h ≥ 3 | proposed |
| D-02 | G2 | SIC grid p ∈ {0,…,12}, q ∈ {0,1,2} for monthly items; p ∈ {0,…,4} quarterly lags for quarterly items | Covers a year of dynamics, keeps search cheap | q ∈ {0,…,4}; report how often bounds bind | proposed |
| D-03 | G3 | Recursive (expanding) window from item start; re-estimate and re-select order at every quarterly origin | "lag order is selected every time the models are reestimated" (p. 7) | Rolling 10-year window | proposed |
| D-04 | G4 | Origins = Feb/May/Aug/Nov 2004 … Nov 2011 (32 origins); errors for h where actuals exist | Matches "2004–2011" and 2-months-known rule | Restrict all h to a common target window | proposed |
| D-05 | G5 | AR(1) benchmark on monthly Δlog headline CPI, iterated forward, same information set | Paper: "simple autoregressive forecast … same information set" (p. 8) | AR(1) on quarterly y-o-y inflation | proposed |
| D-06 | G12 | Replace Consensus Economics with KOF Consensus (KOF files to be copied into `data/raw/` in T0.0) | Consensus Economics is paywalled | Report separately, flag as non-identical | proposed |
| D-07 | — | No add-factors in pseudo-OOS (VAT, tobacco, electricity) | Paper ignores add-factors in pseudo-OOS (p. 12) | VAT-adjusted variant as robustness | proposed |
| D-08 | — | The repo is standalone; raw downloads live in `data/raw/` and are tracked in git when the licence allows and files are small (< 50 MB total), else gitignored and re-downloadable via `docs/data_sources.md` | User wants a self-contained repository; tracking raw files makes results reproducible even if sources change | Always gitignore raw data | proposed |
| D-09 | G7 | Items with fewer than 36 monthly (12 quarterly) observations get an ad-hoc rule instead of an ARIMA | Paper uses ad-hoc rules for items with too few observations (p. 7) but gives no number; 3 years is the minimum for a lag-12 seasonal term | 24 or 48 months | proposed |
