"""Explore (T1.4): draft item mapping, list rows needing review (unmatched or name-only matches)."""
import pandas as pd
from arima_snb import panel
pd.set_option("display.width", 250)
t9, m = panel.build_mapping()
m.to_csv("data/interim/item_mapping_draft.csv", index=False)
print(m.groupby(["base","rule"]).size().unstack(fill_value=0))
rev = m[(m.rule.isin(["unmatched","name"])) | ((m.rule=="same_no") & (m.similarity<0.8))]
rev = rev.merge(t9[["item_no","item_en","pos05"]], on="item_no")
print(rev[rev.base.isin(["LIK00B00","LIK05B05","LIK10B10"])][["item_no","item_en","pos05","base","pos_nos","rule","similarity","name_de"]].to_string())
print("=== later/earlier baskets ===")
print(rev[~rev.base.isin(["LIK05B05"])][["item_no","item_en","pos05","base","pos_nos","rule","similarity","name_de"]].to_string())
