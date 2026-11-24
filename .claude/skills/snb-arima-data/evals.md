# Regression scenarios — snb-arima-data

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-009) | "Get the SNB conditional inflation forecasts 2004–2011." | Loads SNB cube `snbiprogq` via `read_snb_cube`; does not plan to hand-collect from press releases. |
| S-2 (F-010) | "Download the mortgage rate for the rent model." | Uses SNB `zikrepro` `M_MV`; does not try to scrape the BWO page. |
| S-3 (F-011, F-012) | "Transcribe Table 9 and the collection calendars." | Uses PDF pp. 23–27 / 19–23; leaves `agg6` empty (D-21); renders calendar pages to PNG and cross-checks mark counts; skips page headers. |
