"""Explore (T1.4): match paper Table 9 items to LIK2010 positions by 2010 weight (exact to 3 decimals)."""
import pandas as pd
from arima_snb import io
w = io.read_bfs_weights(io.find_raw("GEWICHTUNGEN_*"))
w10 = w[(w.basket=="LIK2005")&(w.year==2010)]
idx, pos = io.read_bfs_cpi_items(io.find_raw("LIK05B05_*"), "LIK05B05")
pos = pos.merge(w10[["pos_no","weight"]], on="pos_no", how="left")
t9 = pd.read_csv("data/meta/items_paper_table9.csv")
print("w10 rows", len(w10), "pos with w", pos.weight.notna().sum())
m = t9.merge(pos, left_on="weight_2010", right_on=pos.weight.round(3), how="left")
cnt = m.groupby("item_no").pos_no.count()
print("unique match", (cnt==1).sum(), "none", (cnt==0).sum(), "multi", (cnt>1).sum())
print(m[m.item_no.isin(cnt[cnt!=1].index)][["item_no","item_en","weight_2010","pos_no","level","name_de"]].to_string())

# Order-constrained: Table 9 follows the BFS position order, so take the first candidate after the previous match.
pos = pos.reset_index(drop=True); pos["row"] = pos.index
last = -1; res = []
for _, r in t9.iterrows():
    c = pos[(pos.weight.round(3) == r.weight_2010) & (pos.row > last)]
    if len(c): last = c.row.iloc[0]; res.append((r.item_no, r.item_en, c.pos_no.iloc[0], c.level.iloc[0], c.name_de.iloc[0]))
    else: res.append((r.item_no, r.item_en, None, None, None))
res = pd.DataFrame(res, columns=["item_no","item_en","pos_no","level","name_de"])
print("matched", res.pos_no.notna().sum()); print(res[res.pos_no.isna()].to_string())
print(res.level.value_counts())
idx, p10 = io.read_bfs_cpi_items(io.find_raw("LIK10B10_*"), "LIK10B10")
print("in LIK10B10 too:", res.pos_no.isin(p10.pos_no).sum())
