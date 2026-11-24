"""Explore (D-21 rev.): agg6 from rules + regression; rebuild check vs BFS series and totals."""
import pandas as pd
from arima_snb import classify
items = pd.read_csv("data/final/items.csv"); m = pd.read_csv("data/interim/item_mapping.csv", dtype={"pos_nos": str})
rules = pd.read_csv("data/meta/agg6_rules.csv")
keys = classify.leaf_keys()
d, leaf = classify.item_agg6(m, items, rules, keys)
d = d.merge(items[["item_id", "name_en", "weight_2010"]], on="item_id")
print(d.groupby("agg6").weight_2010.sum().round(3).to_string())
print(d[d.origin_rule == "data"][["item_id", "name_en", "weight_2010", "domestic_share", "agg6"]].to_string(index=False))
for cl in ["origin", "type"]:
    print(classify.rebuild_check(cl, keys, leaf[cl]).to_string(index=False))
