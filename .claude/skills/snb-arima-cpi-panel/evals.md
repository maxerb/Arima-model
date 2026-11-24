# Regression scenarios — snb-arima-cpi-panel

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-013) | "Map Table 9 items to BFS positions." | Matches on LIK2005 weights for 2010, then order; checks no position is used twice; fixes rows 85–93/119–124 via overrides. |
| S-2 (F-014) | "Build weights.csv for 1995–2012." | Uses the 1993 column for 1993–99, 2000/01 for 2000–01, yearly columns from 2002; does not hold weights constant between revisions. |
| S-3 (F-015) | "Check the chain links are right." | Compares linked changes with BFS back-casts (`backcast_agreement`); does not rely on a jump-at-link-month check. |
| S-4 (F-017, F-019) | "Assign agg6 and check 2010 coverage." | Uses `agg6_rules.csv` + `classify.item_agg6`; expects ≈ 92.7 %, not 92.8 %. |
