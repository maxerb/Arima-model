"""Explore (T1.4): unmatched Table 9 items and stability of position numbers/names across baskets."""
import pandas as pd
from arima_snb import io
w = io.read_bfs_weights(io.find_raw("GEWICHTUNGEN_*"))
P = {}
for b in ["LIK93B93","LIK00B00","LIK05B05","LIK10B10","LIK15B15","LIK20B20","LIK25B25"]:
    P[b] = io.read_bfs_cpi_items(io.find_raw(f"{b}_*"), b)[1].set_index("pos_no")
p05 = P["LIK05B05"].join(w[(w.basket=="LIK2005")&(w.year==2010)].set_index("pos_no").weight)
for b in P:
    if b=="LIK05B05": continue
    common = p05.index.intersection(P[b].index)
    same = (p05.loc[common].name_de.str.lower()==P[b].loc[common].name_de.str.lower()).sum()
    print(b, "common pos", len(common), "same name", same)
for b in ["LIK00B00","LIK10B10","LIK15B15"]:
    common = p05.index.intersection(P[b].index)
    d = pd.DataFrame({"n05": p05.loc[common].name_de, "nb": P[b].loc[common].name_de})
    print(b); print(d[d.n05.str.lower()!=d.nb.str.lower()].head(15).to_string())
