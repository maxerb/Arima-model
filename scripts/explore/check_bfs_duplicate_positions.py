"""Explore (T1.1): which position numbers occur twice in a BFS LIK file, and where (row index)."""
import warnings
from arima_snb.io import read_bfs_cpi_items, find_raw
warnings.filterwarnings("ignore")
for code in ["LIK93B93", "LIK10B10", "LIK20B20"]:
    _, pos = read_bfs_cpi_items(find_raw(f"{code}_*"), code)
    d = pos[pos.pos_no.duplicated(keep=False)]
    print(code, len(d), "dup rows; first index of dups:", d.index.min(), "of", len(pos))
    print(d.head(6).to_string())
