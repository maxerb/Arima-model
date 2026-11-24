"""Explore (T1.4): date range per base file and weight years per basket."""
from arima_snb import io
for b in ["LIK93B93","LIK00B00","LIK05B05"]:
    idx, pos = io.read_bfs_cpi_items(io.find_raw(f"{b}_*"), b)
    t = idx[idx.variable==f"{b}_100"]; print(b, t.date.min(), t.date.max(), t.value.iloc[:2].tolist())
w = io.read_bfs_weights(io.find_raw("GEWICHTUNGEN_*"))
print(w.groupby("basket").year.unique())
