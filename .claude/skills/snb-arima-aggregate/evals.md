# Regression scenarios — snb-arima-aggregate

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-020) | "Aggregate the item panel to total CPI." | Passes wide index levels (not log prices) to `aggregate_index`; passes `items` to `build_subaggregate_series`. |
| S-2 (F-021) | "Re-aggregate CPI for 1999–2002." | Uses basket periods May 1993→May 2000 (incl. May 2000) and May 2000→Dec 2001, then December chaining (D-29). |
| S-3 (F-043) | "Check the ARIMA(14) sub-aggregates." | Re-aggregates the groups with summed weights and compares with the item total (incl. groups starting after 1993, e.g. Education). |
| S-4 (F-044, F-045) | "Build ARIMA(1) and the forecast aggregates." | ARIMA(1) on official CPI (D-47); uses `weights_known_at`, `splice_forecast`, `forecast_aggregates`; selects with `df["aggregate"]`. |
