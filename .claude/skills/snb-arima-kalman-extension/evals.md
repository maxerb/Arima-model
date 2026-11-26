# Regression scenarios — snb-arima-kalman-extension

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-025, F-062) | "Which items get the extended model for Table 4?" | All 182 incl. oil and rent (D-41, paper p. 15); flags the ad-hoc-item choice (D-53). |
| S-2 (F-026) | "Set up the SARIMAX with a drift." | Uses `exog` = time index (mean form, D-42), not `trend="t"`. |
| S-3 (F-027, F-028) | "Run the order search over p = 0..12 for a seasonal item." | Caps p ≤ 11 with SAR(12); catches LinAlgError, retries Nelder-Mead, SIC = ∞ for failed orders. |
| S-4 (F-029) | "Evaluate the extension at 32 origins." | Times a prototype, presents the order-timing scheme as a choice (D-44), runs long searches in the background. |
| S-5 (F-030) | "Write the simulation recovery test." | Uses T ≥ 1000. |
