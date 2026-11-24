"""Explore (T1.1): list positions whose index level leaves [1, 1000] (expected: IT goods back-cast to 1982)."""
import warnings
from arima_snb.io import read_bfs_cpi_items, find_raw
warnings.filterwarnings("ignore")
for code in ["LIK15B15", "LIK20B20", "LIK25B25", "LIK10B10"]:
    long, pos = read_bfs_cpi_items(find_raw(f"{code}_*"), code)
    bad = long[~long.value.between(1, 1000)]
    g = bad.groupby("variable").agg(min=("value", "min"), max=("value", "max"), last=("date", "max"))
    g["name"] = g.index.str.split("_").str[1].astype(int).map(pos.set_index("pos_no").name_de)
    print(code, "\n", g.to_string())
