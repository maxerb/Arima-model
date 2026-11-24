"""Explore (D-21): agg6 weights of the 182 items (Table 9 weights) from estimated memberships vs paper Table 9."""
import pandas as pd
from arima_snb import classify, panel
keys = classify.leaf_keys()
so = classify.estimate_membership("origin", keys); st = classify.estimate_membership("type", keys)
items = pd.read_csv("data/final/items.csv"); m = pd.read_csv("data/interim/item_mapping.csv", dtype={"pos_nos": str})
_, pos10 = panel.load_basket("LIK10B10"); k10 = keys[keys.base == "LIK10B10"].set_index("pos_no").key
w = panel.load_weights(); w11 = w[(w.basket == "LIK2010") & (w.year == 2011)].drop_duplicates("pos_no").set_index("pos_no").weight
rows = []
for _, it in items.iterrows():
    p = m[(m.item_id == it.item_id) & (m.base == "LIK10B10")].pos_nos.iloc[0]
    lv = [l for x in p.split(";") for l in classify.descendants(pos10, int(x))]
    if not lv: print("no leaves:", it.item_id, it.name_en, p, pos10.loc[int(p.split(";")[0])].to_dict()); continue
    ww = w11.reindex(lv).fillna(0); ww = ww / ww.sum() if ww.sum() > 0 else ww * 0 + 1 / len(lv)
    dom = sum(ww[l] * so.loc[k10[l], "domestic"] for l in lv)
    ty = {c: sum(ww[l] * st.loc[k10[l], c] for l in lv) for c in st.columns[:5]}
    rows.append({"item_id": it.item_id, "name": it.name_en, "w": it.weight_2010, "special": it.special, "dom": dom, **ty})
d = pd.DataFrame(rows).fillna({"special": ""})
d["goods"] = d[["non-durable goods", "semi-durable goods", "durable goods"]].sum(axis=1)
def agg6(r, frac):
    if r.special == "oil": return {"Oil products": 1}
    if r.special == "rent": return {"Rents": 1}
    dom = r.dom if frac else float(r.dom > 0.5)
    g, pr, pu = r.goods, r["private services"], r["public services"]
    if not frac:
        lab = max([("g", g), ("pr", pr), ("pu", pu)], key=lambda x: x[1])[0]; g, pr, pu = lab == "g", lab == "pr", lab == "pu"
    return {"Domestic goods": dom * g, "Domestic private services": dom * pr, "Public services": dom * pu,
            "Imported excl. oil": 1 - dom}
for frac in [False, True]:
    tot = {}
    for _, r in d.iterrows():
        for k, v in agg6(r, frac).items(): tot[k] = tot.get(k, 0) + v * r.w
    print("fractional" if frac else "rounded", {k: round(v, 3) for k, v in tot.items()})
print("paper: Domestic durable goods 16.875, Domestic private services 27.818, Rents 19.499, Public services 8.711, Imported 23.447, Oil 3.650")
print(d[(d.dom > 0.1) & (d.dom < 0.9)][["item_id", "name", "w", "dom"]].round(2).to_string(index=False))
d.to_csv("data/interim/agg6_membership_explore.csv", index=False)
