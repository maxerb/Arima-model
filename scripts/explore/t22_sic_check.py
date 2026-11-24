"""T2.2 exploration: which orders does SIC pick on simulated AR(2) data, and with which SIC values?"""
import sys

import numpy as np

sys.path.insert(0, "tests")
from test_item_models import _ar_sim  # noqa: E402

from arima_snb.item_models import fit_cls, select_order  # noqa: E402

for seed in range(3):
    y = _ar_sim([0.5, -0.3], 240, seed=seed)
    sel = select_order(y, seasonal=False, quarterly=False)
    b = sel["fit"]
    print(seed, (b["p"], b["q"]), round(b["sic"], 4), "failed", sel["n_failed"])
    for p, q in [(2, 0), (1, 1), (2, 1), (3, 0)]:
        f = fit_cls(y, p, q, False, 12, 12)
        print("   ", (p, q), None if f is None else (round(f["sic"], 4), round(f["sse"], 6), f["k"]))
