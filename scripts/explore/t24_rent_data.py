"""T2.4 exploration: rent index collection months and the SNB mortgage rate (M_MV).

Questions: (1) in which months does the rent item (i094) change, per year, since 1993?
(2) what does the mortgage-rate series look like quarterly, and how big are its changes?
Run: python scripts/explore/t24_rent_data.py
"""
import numpy as np
import pandas as pd

from arima_snb import io
from arima_snb.config import FINAL

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
rent = panel[panel.item_id == "i094"].set_index("date")["log_p"].sort_index()
d = rent.diff()
chg = d[d.abs() >= 1e-3]
print("Rent: months with a change, by year")
for y, g in chg.groupby(chg.index.year):
    print(y, sorted(g.index.month.tolist()))

m = io.read_snb_cube(io.find_raw("snb-data-zikrepro-*.csv"), "zikrepro")
print(m.variable.unique()[:20])
mv = m[m.variable == "zikrepro_M_MV"].set_index("date")["value"].sort_index()
print("M_MV", mv.index.min(), mv.index.max(), len(mv))
print(mv.loc["1999":"2012"].resample("QS").mean().round(3).to_string())
q = mv.resample("QS").mean().diff()
print("quarterly changes: share >0", (q > 0).mean().round(2), "share <0", (q < 0).mean().round(2))
print(q.describe())

# Quarterly rent changes (Feb/May/Aug/Nov) since 1993
rq = rent[rent.index.month.isin([2, 5, 8, 11])].diff()
print("Rent quarterly log changes (x100):")
print((rq.loc["1993":] * 100).round(2).to_string())
