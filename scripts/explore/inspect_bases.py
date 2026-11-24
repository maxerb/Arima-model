"""Explore the BFS item files per base (T1.4): positions, levels, date ranges."""
from arima_snb import io
for b in ["LIK93B93","LIK00B00","LIK05B05","LIK10B10","LIK15B15","LIK20B20","LIK25B25"]:
    idx, meta = io.read_bfs_cpi_items(io.find_raw(f"{b}_*"), b)
    print(b, meta.shape, idx.shape); print(meta.head(3).to_string()); print(idx.head(3).to_string()); print(idx["date"].min(), idx["date"].max())
