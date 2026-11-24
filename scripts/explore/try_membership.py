"""Explore (D-21): estimate origin/type membership from BFS aggregates and check the rebuilt series."""
import pandas as pd
from arima_snb import classify
keys = classify.leaf_keys()
print("leaves:", keys.groupby("base").size().to_dict(), "unique keys:", keys.key.nunique())
for cl in ["origin", "type"]:
    s = classify.estimate_membership(cl, keys)
    print(cl, "share of keys with max membership > 0.9:", round((s.max_share > 0.9).mean(), 3))
    print(s.label.value_counts().to_string())
    print(classify.rebuild_check(cl, keys, s.label).to_string(index=False))
