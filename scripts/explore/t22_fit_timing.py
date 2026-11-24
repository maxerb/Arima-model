"""T2.2 exploration: how long does one SARIMAX item fit take? Motivates the estimation-method decision (D-35)."""
import time
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from arima_snb.config import FINAL

warnings.simplefilter("ignore")
panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
y = panel[panel.item_id == "i002"].set_index("date").log_p.loc["2000-05":"2011-02"].diff().dropna()
y.index.freq = "MS"
for p, q, s in [(1, 0, False), (6, 0, False), (12, 2, False), (6, 1, True), (12, 2, True)]:
    t = time.perf_counter()
    SARIMAX(y.values, order=(p, 0, q), seasonal_order=(1, 0, 0, 12) if s else (0, 0, 0, 0), trend="c").fit(disp=False)
    print(f"p={p} q={q} seasonal={s}: {time.perf_counter() - t:.2f}s")
