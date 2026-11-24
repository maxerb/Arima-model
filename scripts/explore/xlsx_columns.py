"""Explore (T1.4, D-21): non-date header columns and sheet names of the 2015+ BFS files (origin/type flags?)."""
import pandas as pd
from arima_snb import io
for b in ["LIK10B10","LIK15B15"]:
    x = pd.ExcelFile(io.find_raw(f"{b}_*")); print(b, x.sheet_names)
raw = pd.read_excel(io.find_raw("LIK15B15_*"), sheet_name="INDEX_m", header=None, nrows=6)
print([h for h in raw.iloc[3].tolist() if not hasattr(h, "year")][:30])
