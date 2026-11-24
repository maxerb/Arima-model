"""T2.2 exploration: profile one slow CLS candidate fit (runtime check)."""
import cProfile
import pstats

import pandas as pd

from arima_snb.config import FINAL
from arima_snb.item_models import fit_cls

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
y = panel[panel.item_id == "i050"].set_index("date").log_p.loc["2000-05":"2011-02"].diff().dropna().to_numpy()
pr = cProfile.Profile()
pr.enable()
fit_cls(y, 11, 2, True, 12, 23)
pr.disable()
pstats.Stats(pr).sort_stats("tottime").print_stats(10)
