"""Explore (T1.4): leaf positions per base and their first/last observation."""
import pandas as pd
from arima_snb import io
for b in ["LIK10B10","LIK15B15","LIK25B25"]:
    idx, pos = io.read_bfs_cpi_items(io.find_raw(f"{b}_*"), b)
    pos["var"] = b+"_"+pos.pos_no.astype(str)
    rng = idx.groupby("variable").date.agg(["min","max"])
    pos = pos.join(rng, on="var")
    # leaf = next row not deeper
    pos["leaf"] = pos.level.shift(-1).fillna(0) <= pos.level
    lv = pos[pos.leaf]
    print(b, "leaves", len(lv)); print(lv["min"].value_counts().head(8)); print(lv["max"].value_counts().head(5))
raw = pd.read_excel(io.find_raw("LIK10B10_*"), header=None, nrows=12); print(raw.iloc[:12,:12].to_string())
raw = pd.read_excel(io.find_raw("LIK25B25_*"), sheet_name="INDEX_m", header=None, nrows=8); print(raw.iloc[:8,:10].to_string())
