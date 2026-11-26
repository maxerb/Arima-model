# Regression scenarios — snb-arima-evaluation

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-051, F-052, F-074) | "Run the pseudo-OOS for 2004–2011." | Calls `run_pseudo_oos(inputs, origins, ...)`; produces `arima182` and `arima182_special` from one fit; reuses the per-origin item cache; long run in background. |
| S-2 (F-063, F-064) | "Add the AR(1) and ARIMA(14) benchmarks." | AR(1) with month intercepts (D-05 rev.); groups specified like items, collected if any member is (D-55). |
| S-3 (F-065) | "Add the SNB and consensus benchmarks." | SNB from cube snbiprogq, T = 31 (D-20); KOF survey of the origin quarter (D-56), annual target (D-57). |
| S-4 (F-060, F-066) | "Compute DMW tests for Table 1 panel B (annual)." | Reuses `evaluate.dmw_hln` / `comparison_table`; kernel lag 3 for current year, 0 for next year (D-58). |
| S-5 (F-067, F-061) | "Table 4 does not show the paper's gain — build the table anyway." | Unreplicable cells '–' with note; diagnoses the miss by sub-aggregate then items from cached forecasts before refitting. |
| S-6 (F-053) | "Test the engine." | Flat-items construction → flat aggregate → h = 1 computed by hand. |
