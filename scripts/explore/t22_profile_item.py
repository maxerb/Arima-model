"""T2.2 exploration: profile the SIC grid search for one item at one origin (runtime check)."""
import cProfile
import pstats

import pandas as pd

from arima_snb.config import FINAL
from arima_snb.diagnostics import specs_for_origin
from arima_snb.item_models import forecast_item

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
specs = specs_for_origin(pd.read_csv(FINAL / "item_specs.csv"), "2011-02-01").set_index("item_id")
x = panel[panel.item_id == "i002"].set_index("date").log_p
spec = specs.loc["i002"].copy()
spec["item_id"] = "i002"
spec["seasonal"] = True
cProfile.run("print(forecast_item(x, spec, pd.Timestamp('2011-02-01'))[1])", "prof.out")
pstats.Stats("prof.out").sort_stats("cumtime").print_stats(12)
