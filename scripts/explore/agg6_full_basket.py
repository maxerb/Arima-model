"""Explore (D-21): ARIMA(6) group weights on the FULL 2010 basket (2011 weights) from estimated memberships,
fractional vs rounded, compared with paper Table 9 (2010 weights, full basket = 100)."""
import pandas as pd
from arima_snb import classify, panel
keys = classify.leaf_keys()
so = classify.estimate_membership("origin", keys); st = classify.estimate_membership("type", keys)
_, pos = panel.load_basket("LIK10B10"); k = keys[keys.base == "LIK10B10"].set_index("pos_no")
w = panel.load_weights(); w11 = w[(w.basket == "LIK2010") & (w.year == 2011)].drop_duplicates("pos_no").set_index("pos_no").weight
d = k.join(w11.rename("w")); d["dom"] = d.key.map(so.domestic)
for c in st.columns[:5]: d[c] = d.key.map(st[c])
d["goods"] = d[["non-durable goods", "semi-durable goods", "durable goods"]].sum(axis=1)
oil = set(classify.descendants(pos, 4090)) | set(classify.descendants(pos, 7083) if 7083 in pos.index else [])
oil_names = pos[pos.name_de.str.contains("Heizöl|Benzin|Diesel|Treibstoff", na=False)].index
oil |= {l for o in oil_names for l in classify.descendants(pos, o)}
rent = set(classify.descendants(pos, 4002))
print("oil leaves:", pos.loc[sorted(oil), "name_de"].tolist(), "rent:", pos.loc[sorted(rent), "name_de"].tolist())
for frac in [True, False]:
    x = d.copy()
    if not frac:
        x["dom"] = (x.dom > 0.5).astype(float)
        lab = x[["goods", "private services", "public services"]].idxmax(axis=1)
        for c in ["goods", "private services", "public services"]: x[c] = (lab == c).astype(float)
    sp = x.index.isin(oil) | x.index.isin(rent)
    r = {"Domestic goods": (x.w * x.dom * x.goods)[~sp].sum(),
         "Domestic private services excl. rents": (x.w * x.dom * x["private services"])[~sp].sum(),
         "Rents": x.w[x.index.isin(rent)].sum(), "Public services": (x.w * x.dom * x["public services"])[~sp].sum(),
         "Imported excl. oil": (x.w * (1 - x.dom))[~sp].sum(), "Oil": x.w[x.index.isin(oil)].sum()}
    print("fractional" if frac else "rounded", {a: round(b, 2) for a, b in r.items()}, "sum", round(sum(r.values()), 2),
          "domestic total", round((x.w * x.dom).sum(), 2), "(BFS 2011: 73.419)")
print("paper 2010: 16.875 / 27.818 / 19.499 / 8.711 / 23.447 / 3.650")
