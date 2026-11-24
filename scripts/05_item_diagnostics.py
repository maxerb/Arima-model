"""T2.1: item diagnostics (ADF/KPSS, seasonality, collection frequency) -> data/final/item_specs.csv.

Paper pp. 6-7; decisions D-09, D-10, D-31...D-34. Prints counts per method and vintage and draws example ACFs.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.graphics.tsaplots import plot_acf  # noqa: E402

from arima_snb.config import FIGURES, FINAL, SPEC_VINTAGES, TABLES  # noqa: E402
from arima_snb.diagnostics import cut, every_third, item_specs  # noqa: E402

panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
collection = pd.read_csv(FINAL / "collection.csv", parse_dates=["date"])
items = pd.read_csv(FINAL / "items.csv")
names = items.set_index("item_id").name_en

specs = item_specs(panel, collection, items, SPEC_VINTAGES)
specs.to_csv(FINAL / "item_specs.csv", index=False)

# --- sanity output ---------------------------------------------------------------
assert (specs.d == 1).all()
assert specs.groupby("vintage").item_id.nunique().max() <= 182
summary = pd.concat([pd.crosstab(specs.vintage, specs.method),
                     pd.crosstab(specs.vintage, specs.collection_freq),
                     specs.groupby("vintage")[["seasonal", "d_flag", "quarterly_lags"]].sum()], axis=1)
TABLES.mkdir(parents=True, exist_ok=True)
summary.to_csv(TABLES / "item_specs_summary.csv")
pd.set_option("display.width", 200)
print(summary)

trousers = names[names.str.contains("rousers")].index[0]
for v in (2003, 2007, 2008, 2011):
    s = specs[specs.vintage == v].set_index("item_id")
    print(f"vintage {v}: rice seasonal={s.loc['i001', 'seasonal']}; trousers freq={s.loc[trousers, 'collection_freq']},"
          f" seasonal={s.loc[trousers, 'seasonal']}")

# --- example ACF figure (vintage 2007): one seasonal, one quarterly, one monthly non-seasonal ---
s07 = specs[specs.vintage == 2007].set_index("item_id")
examples = {"seasonal": s07[s07.seasonal & (s07.method == "arima") & ~s07.quarterly_lags].acf12.idxmax(),
            "quarterly": s07[s07.quarterly_lags].acf12.abs().idxmin() if s07.quarterly_lags.any() else None,
            "monthly non-seasonal": "i001"}
wide = panel.pivot(index="date", columns="item_id", values="log_p")
fig, axes = plt.subplots(3, 2, figsize=(11, 8))
for ax, (kind, iid) in zip(axes, examples.items()):
    if iid is None:
        continue
    x = cut(wide[iid], 2007)
    ax[0].plot(x.index, x.values)
    ax[0].set_title(f"{kind}: {names[iid]} (log price)", fontsize=9)
    dx = (every_third(x).diff() if kind == "quarterly" else x.diff()).dropna()
    plot_acf(dx, ax=ax[1], lags=12 if kind == "quarterly" else 36,
             title=f"ACF of log changes ({'quarterly lags' if kind == 'quarterly' else 'months'})")
fig.tight_layout()
FIGURES.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGURES / "diag_examples.png", dpi=120)
print("examples:", {k: (v, names.get(v)) for k, v in examples.items()})
print("wrote", FINAL / "item_specs.csv", "and", FIGURES / "diag_examples.png")
