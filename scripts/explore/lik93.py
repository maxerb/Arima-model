"""Explore (T1.4): structure of the 1993 basket file."""
from arima_snb import io
idx, pos = io.read_bfs_cpi_items(io.find_raw("LIK93B93_*"), "LIK93B93")
print(pos.head(8).to_string()); print(idx.groupby("variable").date.agg(["min","max"]).value_counts().head())
