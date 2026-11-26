# Regression scenarios — snb-arima-item-models

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-032, F-037) | "Fit all 182 item models at origin 2006-05." | Uses CLS (`fit_cls`) with SIC eq. (3) on a common sample, optimiser capped at 100 evaluations, `ProcessPoolExecutor` with a `__main__` guard; not SARIMAX ML, not joblib. |
| S-2 (F-033, F-034) | "Seasonal item with 21 obs in the common sample at 2004-02." | Caps p ≤ 11 with the seasonal AR(12); shrinks the grid / drops the seasonal term until ≥ 24 obs remain (D-37). |
| S-3 (F-035) | "Item forecast implies +40 % in 12 months." | Checks the [1st, 99th] percentile of the item's own 12-month changes (D-11), switches to `adhoc_avg_yoy`, logs it. |
| S-4 (F-036) | "Forecast a quarterly-collected item." | Fits on the quarterly-sampled series (D-36), forecasts at collection months, carries the level forward in between. |
| S-5 (F-038) | "Write the SIC order-recovery test." | Simulates an AR(2) not mimicked by MA(1), e.g. φ = (0.3, 0.4). |
