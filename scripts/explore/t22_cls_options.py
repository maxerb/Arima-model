"""T2.2 exploration: speed and success of the CLS fit on MA-heavy candidates (runtime check)."""
import time

import pandas as pd

from arima_snb.config import FINAL
from arima_snb.item_models import fit_cls

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
for item in ["i002", "i010", "i050"]:
    y = panel[panel.item_id == item].set_index("date").log_p.loc["2000-05":"2011-02"].diff().dropna().to_numpy()
    for p, q, s in [(12, 2, False), (11, 2, True), (3, 2, False), (2, 0, False)]:
        t = time.perf_counter()
        f = fit_cls(y, p, q, s, 12, 23)
        print(item, p, q, s, f"{time.perf_counter() - t:.2f}s", None if f is None else round(f["sic"], 3), flush=True)
