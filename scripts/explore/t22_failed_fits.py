"""T2.2 exploration: which CLS candidates fail, and would a larger optimiser budget rescue them?

For a sample of monthly items at origin 2011-02, fit every (p, q) candidate with the default budget and with a
10x budget, and tabulate failures by q, and whether the rescued fits would have won the SIC comparison.
"""
import numpy as np
import pandas as pd

import arima_snb.item_models as im
from arima_snb.config import FINAL

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
wide = panel.pivot(index="date", columns="item_id", values="log_p").loc["2000-05":"2011-02"]
rows = []
for iid in ["i002", "i010", "i020", "i030", "i050", "i110", "i140", "i160"]:
    y = wide[iid].dropna().diff().dropna().to_numpy()
    for budget in (im.CLS_MAX_NFEV, 10 * im.CLS_MAX_NFEV):
        old = im.CLS_MAX_NFEV
        im.CLS_MAX_NFEV = budget
        for p in range(0, 13, 3):
            for q in range(3):
                f = im.fit_cls(y, p, q, False, 12, 12)
                rows.append({"item": iid, "budget": budget, "p": p, "q": q,
                             "failed": f is None, "sic": np.nan if f is None else f["sic"]})
        im.CLS_MAX_NFEV = old
r = pd.DataFrame(rows)
print(r.pivot_table(index="q", columns="budget", values="failed", aggfunc="mean"))
best = r.groupby(["item", "budget"]).sic.min().unstack()
print("best SIC per item, default vs 10x budget:\n", best.round(4))
