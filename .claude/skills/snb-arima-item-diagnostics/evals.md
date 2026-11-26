# Regression scenarios — snb-arima-item-diagnostics

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-069) | "Specify the item models for the 2004–2011 origins." | Presents the vintage scheme as a choice; with yearly vintages (D-31) vintage Y uses data to Dec Y for origins in Y+1; no data after the vintage date. |
| S-2 (F-070) | "Classify trousers' collection frequency in 2008." | Counts collections per year with the D-34 thresholds and takes max(inferred, calendar); does not rely on inferred flags alone. |
| S-3 (F-071) | "20 % of items fail the I(1) tests — fix d?" | Keeps d = 1 for all items, records `d_flag`; notes 13–26 % is expected here. |
