"""Explore (T1.1): run the BFS CPI loaders on every raw file and print coverage per base (skill checks)."""
import warnings
import pandas as pd
from arima_snb.config import RAW
from arima_snb.io import read_bfs_cpi_items, read_bfs_weights, find_raw
warnings.filterwarnings("ignore")
for code in ["LIK93B93", "LIK00B00", "LIK05B05", "LIK10B10", "LIK15B15", "LIK20B20", "LIK25B25"]:
    long, pos = read_bfs_cpi_items(find_raw(f"{code}_*"), code)
    print(code, "positions", len(pos), "levels", pos.level.value_counts().sort_index().to_dict(),
          "dates", long.date.min().date(), long.date.max().date(), "dups", long.duplicated(["date", "variable"]).sum())
    print("   ", pos.head(4).name_de.tolist())
w = read_bfs_weights(find_raw("GEWICHTUNGEN_*"))
print(w.groupby(["basket", "year"]).size().unstack(0).fillna(0).astype(int))
print("totals (pos 100/10):", w[w.pos_no.isin([100, 10])].groupby("year").weight.first().to_dict())

# Spot check (skill snb-arima-data): headline y-o-y of the quarterly average, 2008Q3 should be about 3 % (paper Chart 2)
long, _ = read_bfs_cpi_items(find_raw("LIK10B10_*"), "LIK10B10")
total = long[long.variable == "LIK10B10_100"].set_index("date")["value"]
q = total.resample("QS").mean()
yoy = 100 * (q / q.shift(4) - 1)
print("headline y-o-y 2008Q3:", round(yoy.loc["2008-07-01"], 2))
assert 2.5 < yoy.loc["2008-07-01"] < 3.5
