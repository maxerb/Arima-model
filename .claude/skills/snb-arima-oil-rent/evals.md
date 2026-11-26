# Regression scenarios — snb-arima-oil-rent

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-039, F-040, F-041) | "Estimate the oil ECM at origin 2008-05." | Models i100 and i130 (items with special == oil); x_t = mean of the last 10 daily Brent×USDCHF before the 1st of month t (D-14 rev.); sample from 1993-05 (D-38); crude cut at `crude_info_cutoff(origin)`. |
| S-2 (F-042, F-049) | "Plug the special models into the item forecasts." | Passes `crude_chf_daily` / `mortgage_rate` to `forecast_item(s)`; None gives the plain ARIMA benchmark. |
| S-3 (F-047, F-048) | "Build the rent model's mortgage series." | Uses SNB zikrepro M_MV quarterly average (D-19, D-15 rev.), months ≤ origin only; rent collected Feb/May/Aug/Nov since 1993 (D-48); AR p = 0..4 by SIC. |
