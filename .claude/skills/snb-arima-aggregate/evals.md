# Regression scenarios — snb-arima-aggregate

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-020) | "Aggregate the item panel to total CPI." | Passes wide index levels (not log prices) to `aggregate_index`; passes `items` to `build_subaggregate_series`. |
| S-2 (F-021) | "Re-aggregate CPI for 1999–2002." | Uses basket periods May 1993→May 2000 (incl. May 2000) and May 2000→Dec 2001, then December chaining (D-29). |
