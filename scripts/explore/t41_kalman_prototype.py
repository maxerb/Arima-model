"""T4.1 exploration: first look at the collection-frequency state-space model on trousers (paper Chart 3).

Fits SARIMAX on log levels with NaN in non-collection months, mean-form drift via an exogenous time trend,
for a few AR orders, and prints parameters and fit time. Kept for reference (AGENTS.md rule 7).
"""

import time
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from arima_snb.config import FINAL, NO_COLLECTION_TOL

warnings.filterwarnings("ignore")

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
for item in ["i075", "i069", "i001"]:
    lp = panel[panel.item_id == item].set_index("date")["log_p"].asfreq("MS")
    collected = lp.diff().abs() >= NO_COLLECTION_TOL
    y = lp.where(collected)
    y.iloc[0] = lp.iloc[0]                      # first month anchors the level
    trend = pd.Series(np.arange(len(y), dtype=float), index=y.index, name="t")
    for p, seas in [(1, False), (2, True), (4, True), (12, False)]:
        t0 = time.time()
        mod = SARIMAX(y, exog=trend, order=(p, 1, 0),
                      seasonal_order=(1, 0, 0, 12) if seas else (0, 0, 0, 0),
                      simple_differencing=False, enforce_stationarity=True)
        res = mod.fit(disp=False, maxiter=200)
        print(item, p, seas, f"{time.time() - t0:5.2f}s", "llf", round(res.llf, 1),
              "nobs_eff", int(y.notna().sum()), dict(res.params.round(4)))
