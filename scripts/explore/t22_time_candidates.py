"""T2.2 exploration: time individual CLS candidate fits (runtime check)."""
import time

import numpy as np
import pandas as pd

from arima_snb.config import FINAL
from arima_snb.item_models import fit_cls

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
y = panel[panel.item_id == "i002"].set_index("date").log_p.loc["2000-05":"2011-02"].diff().dropna().to_numpy()
for p, q, s in [(1, 0, False), (6, 0, False), (12, 2, False), (6, 1, True), (11, 2, True)]:
    t = time.perf_counter()
    f = fit_cls(y, p, q, s, 12, 23)
    print(p, q, s, f"{time.perf_counter() - t:.3f}s", None if f is None else round(f["sic"], 3), flush=True)
