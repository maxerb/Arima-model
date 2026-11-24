"""Explore (D-21): which special-grouping series (pos_no < 200, e.g. 118 Inland) each basket file contains,
read without dropping repeated numbers."""
import pandas as pd
from arima_snb import io
for b in ["LIK00B00", "LIK05B05", "LIK10B10"]:
    raw = pd.read_excel(io.find_raw(f"{b}_*"), header=None)
    pos = pd.to_numeric(raw[0], errors="coerce")
    sel = pos.notna() & (pos < 200) & (pos >= 100)
    names = raw.loc[sel, 1:8].bfill(axis=1).iloc[:, 0]
    print(b, len(raw)); print(pd.DataFrame({"row": raw.index[sel], "pos": pos[sel], "name": names}).to_string(index=False))
