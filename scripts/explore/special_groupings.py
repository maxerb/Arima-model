"""Explore (T1.4, D-21): special groupings (Sondergliederungen) at the end of the 2005/2010 basket files."""
import pandas as pd
from arima_snb import io
for b in ["LIK05B05", "LIK10B10"]:
    raw = pd.read_excel(io.find_raw(f"{b}_*"), header=None)
    pos = pd.to_numeric(raw[0], errors="coerce")
    dup = pos.duplicated(keep="first") & pos.notna()
    first = dup.idxmax()
    print(b, "special groupings start at row", first)
    print(raw.iloc[first-3:first+60, :9].to_string())
