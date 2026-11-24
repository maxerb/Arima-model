"""T2.5 exploration: where do the ARIMA(14) sub-aggregates fail to add up to the item aggregate?"""
import pandas as pd
from arima_snb import aggregate
from arima_snb.config import FINAL

long = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
weights = pd.read_csv(FINAL / "weights.csv")
items = pd.read_csv(FINAL / "items.csv")
wide = long.pivot(index="date", columns="item_id", values="index").asfreq("MS")
total = aggregate.aggregate_index(wide, weights)
g = aggregate.build_subaggregate_series(wide, weights, items, "agg14")
w = aggregate.subaggregate_weights(weights, items, "agg14").rename(columns={"group": "item_id"})
back = aggregate.aggregate_index(g, w)
gap = (back / total.reindex(back.index) - 1)
print(gap[gap.abs() > 1e-9].head(20))
print(gap.abs().groupby(gap.index.year).max())
print(g.loc["1993-05":"2001-01"].isna().sum())

# Which items are missing inside a weight period although they have a weight? (D-30 renormalises those months)
wk = weights.pivot(index="year", columns="item_id", values="weight")
for y in (2000, 2005, 2012, 2020):
    m = wide.loc[f"{y}-01":f"{y}-12"]
    has_w = wk.loc[y].dropna().index
    miss = m[has_w].isna().sum()
    print(y, miss[miss > 0].to_dict())
print("yoy gap (pp), max abs:", (aggregate.monthly_yoy(back) - aggregate.monthly_yoy(total)).abs().max())

# Items with a weight in a period but no index in its link month: counted in the group weight, dropped by D-30.
per = aggregate.weight_periods(wide.index.min(), wide.index.max())
for p in per.itertuples():
    if p.weight_year not in wk.index:
        continue
    has_w = wk.loc[p.weight_year].dropna().index
    nolink = [i for i in has_w if pd.isna(wide.loc[p.link, i]) if p.link in wide.index]
    if nolink:
        print(p.weight_year, p.link.date(), nolink, wk.loc[p.weight_year, nolink].round(3).to_dict())

# Items present in the link month but missing in some later month of the period
for p in per.itertuples():
    if p.weight_year not in wk.index or p.link not in wide.index:
        continue
    has_w = wk.loc[p.weight_year].dropna().index
    m = wide.loc[p.start:p.end, has_w]
    holes = m.isna().sum()
    holes = holes[holes > 0]
    if len(holes):
        print("holes", p.weight_year, holes.to_dict())
# Duplicated group labels / items without group?
print(items.agg14.isna().sum(), items.agg14.nunique())
# groups: is weight-normalisation identical? compare group-weight-sum vs items in wide
print(set(weights.item_id) - set(wide.columns), set(weights.item_id) - set(items.item_id))

# Per group: does group(t)/group(link) equal the weighted item relative of that group? (link May 2000, t Jun 2000)
L, t = pd.Timestamp("2000-05-01"), pd.Timestamp("2000-06-01")
w00 = wk.loc[2000]
for name, ids in items.groupby("agg14")["item_id"]:
    ids = [i for i in ids if i in w00.dropna().index]
    rel = (wide.loc[t, ids] / wide.loc[L, ids])
    direct = (rel * w00[ids]).sum() / w00[ids].sum()
    print(f"{name[:30]:30s} {g.loc[t, name] / g.loc[L, name]:.6f} {direct:.6f} n={len(ids)} nan_rel={rel.isna().sum()}")
