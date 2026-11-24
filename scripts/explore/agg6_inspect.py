"""Explore (D-21): items by agg6 label with their estimated shares."""
import pandas as pd
pd.set_option("display.width", 250)
m = pd.read_csv("data/interim/item_membership.csv"); it = pd.read_csv("data/final/items.csv")
d = it[["item_id", "name_en", "weight_2010"]].merge(m, on="item_id")
for g in ["Public services", "Domestic durable goods"]:
    print(g); print(d[d.agg6 == g][["item_id", "name_en", "weight_2010", "domestic", "goods", "private services", "public services"]].round(2).to_string(index=False))
