"""Explore (T1.4): rows of the draft item mapping that are unmatched or matched by name only (2000-2020 baskets)."""
import pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
m = pd.read_csv("data/interim/item_mapping_draft.csv", dtype={"pos_nos": str})
t9 = pd.read_csv("data/meta/items_paper_table9.csv")
p05 = m[m.base=="LIK05B05"].set_index("item_no").name_de
r = m[m.base.isin(["LIK00B00","LIK10B10","LIK15B15","LIK20B20"]) & m.rule.isin(["name","unmatched"])]
r = r.assign(name05=r.item_no.map(p05), pos05=r.item_no.map(m[m.base=="LIK05B05"].set_index("item_no").pos_nos))
print(r[["item_no","pos05","name05","base","pos_nos","rule","name_de"]].to_string())
