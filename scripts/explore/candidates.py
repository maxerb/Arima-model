"""Explore (T1.4): for each item needing review, list nearby positions (by number) in the target basket."""
import sys
import pandas as pd
from arima_snb import panel
m = pd.read_csv("data/interim/item_mapping_draft.csv", dtype={"pos_nos": str})
bases = sys.argv[1].split(",")
r = m[m.base.isin(bases) & m.rule.isin(["name","unmatched"])]
p05 = m[m.base=="LIK05B05"].set_index("item_no")
sheet = {c: s for c, s, _ in panel.BASKETS}
for base, g in r.groupby("base"):
    _, pos = panel.load_basket(base)
    pos = pos.join(panel.basket_weight(sheet[base], base > "LIK05B05").rename("w"))
    for _, x in g.iterrows():
        n = int(p05.loc[x.item_no, "pos_nos"])
        print(f"## item {x.item_no} {p05.loc[x.item_no,'name_de']} ({n}) -> {base}")
        near = pos[(pos.index >= n - 30) & (pos.index <= n + 30)]
        print(near[["level", "name_de", "w"]].to_string(header=False))
