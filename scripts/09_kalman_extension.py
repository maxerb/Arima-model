"""T4.1: collection-frequency state-space model (paper section 5, App. C) for all 182 items.

    python scripts/09_kalman_extension.py            # resume: only (vintage, item) pairs not yet in the orders file
    python scripts/09_kalman_extension.py --force    # rebuild the orders file from scratch

Steps
1. AR order by SIC (p = 0..12, seasonal flag from item_specs) per item and annual vintage -> data/final/kalman_orders.csv
   (D-41 all items, D-44 yearly SIC). This is the slow part (~1 h on 6 cores); results are appended per vintage.
2. Sanity forecast for all items at origin Nov 2011 (last Table 4 origin) -> outputs/forecasts/kalman_t41_2011-11.csv,
   item-level errors for 2012 vs a no-change forecast.
3. Paper Chart 3 replica (women's trousers): smoother interpolation 1993-2009 and forecast from Nov 2009
   -> outputs/figures/chart3_trousers.png.
"""

import sys
import time
from concurrent.futures import ProcessPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from arima_snb.config import FIGURES, FINAL, FORECASTS, KALMAN_N_JOBS, KALMAN_VINTAGES  # noqa: E402
from arima_snb.kalman_ext import (fit_with_fallback, forecast_item_kalman, observed_levels,  # noqa: E402
                                  order_for_vintage, orders_for_origin, smoothed_levels)
from arima_snb.panel import collection_pattern  # noqa: E402

ORDERS = FINAL / "kalman_orders.csv"
SANITY_ORIGIN = pd.Timestamp("2011-11-01")
CHART3_ITEM, CHART3_ORIGIN = "i075", pd.Timestamp("2009-11-01")   # women's trousers, paper Chart 3
STEPS = 13                                   # origin = 2nd month of quarter -> end of h = 5 quarter is 13 months ahead


def _search(args):
    """Worker: order search for one (vintage, item)."""
    vintage, item_id, log_p, seasonal = args
    t0 = time.time()
    row = order_for_vintage(log_p, vintage, seasonal)
    return {"vintage": vintage, "item_id": item_id, **row, "seconds": round(time.time() - t0, 1)}


def build_orders(series: dict, specs: pd.DataFrame, force: bool) -> pd.DataFrame:
    done = pd.read_csv(ORDERS) if ORDERS.exists() and not force else pd.DataFrame(columns=["vintage", "item_id"])
    have = set(zip(done.vintage, done.item_id))
    for vintage in KALMAN_VINTAGES:
        sv = specs[specs.vintage == vintage].set_index("item_id")
        todo = [(vintage, i, series[i], bool(sv.loc[i, "seasonal"]) if i in sv.index else False)
                for i in sorted(series) if (vintage, i) not in have]
        if not todo:
            continue
        t0 = time.time()
        with ProcessPoolExecutor(KALMAN_N_JOBS) as pool:
            rows = list(pool.map(_search, todo, chunksize=1))
        done = pd.concat([done, pd.DataFrame(rows)], ignore_index=True)
        done.sort_values(["vintage", "item_id"]).to_csv(ORDERS, index=False)   # save after every vintage
        print(f"vintage {vintage}: {len(rows)} items in {time.time() - t0:.0f}s", flush=True)
    return done.sort_values(["vintage", "item_id"]).reset_index(drop=True)


def sanity_forecasts(series: dict, orders: pd.DataFrame, collection: pd.DataFrame) -> pd.DataFrame:
    """All items at one origin; compare 2012 item errors with a no-change forecast."""
    o = orders_for_origin(orders, SANITY_ORIGIN).set_index("item_id")
    out = []
    for item_id, log_p in series.items():
        if item_id not in o.index or log_p[:SANITY_ORIGIN].dropna().empty:
            continue
        months = collection_pattern(collection, item_id, SANITY_ORIGIN)
        f = forecast_item_kalman(log_p, SANITY_ORIGIN, STEPS, int(o.loc[item_id, "p"]),
                                 bool(o.loc[item_id, "seasonal"]), months)
        out.append(f.assign(item_id=item_id, model="kalman"))
    fc = pd.concat(out, ignore_index=True)
    FORECASTS.mkdir(parents=True, exist_ok=True)
    fc.to_csv(FORECASTS / f"kalman_t41_{SANITY_ORIGIN:%Y-%m}.csv", index=False)

    actual = pd.DataFrame({i: s for i, s in series.items()}).stack().rename("log_p").rename_axis(["target", "item_id"])
    fc = fc.join(actual, on=["target", "item_id"])
    last = {i: s[:SANITY_ORIGIN].dropna().iloc[-1] for i, s in series.items() if not s[:SANITY_ORIGIN].dropna().empty}
    fc["no_change"] = fc.item_id.map(last)
    err = pd.DataFrame({k: (fc[k] - fc.log_p) for k in ["log_p_hat", "log_p_latent", "no_change"]})
    err["h_month"] = (fc.target.dt.year - SANITY_ORIGIN.year) * 12 + fc.target.dt.month - SANITY_ORIGIN.month
    rmse = (err.groupby("h_month")[["log_p_hat", "log_p_latent", "no_change"]]
            .apply(lambda e: np.sqrt((e ** 2).mean())) * 100)
    print(f"\nItem-level RMSE (log points x100) of forecasts from {SANITY_ORIGIN:%Y-%m}, mean over items:")
    print(rmse.round(2).to_string())
    assert fc.log_p_hat.notna().all() and np.isfinite(fc.log_p_hat).all()
    return fc


def chart3(series: dict, orders: pd.DataFrame, collection: pd.DataFrame) -> None:
    """Replica of paper Chart 3: official vs interpolated trousers index and their forecasts (index Dec 2010 = 100)."""
    log_p = series[CHART3_ITEM]
    o = orders_for_origin(orders, CHART3_ORIGIN).set_index("item_id").loc[CHART3_ITEM]
    y = observed_levels(log_p, CHART3_ORIGIN)
    res, _, _ = fit_with_fallback(y, int(o.p), bool(o.seasonal))
    smooth = smoothed_levels(res, y)
    f = forecast_item_kalman(log_p, CHART3_ORIGIN, 24, int(o.p), bool(o.seasonal),
                             collection_pattern(collection, CHART3_ITEM, CHART3_ORIGIN)).set_index("target")
    obs = y.dropna()
    assert np.allclose(smooth[obs.index], obs, atol=1e-6), "smoother must hit the collected prices"

    win = slice("2004-01-01", None)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(np.exp(smooth[win]), color="#1f4e9c", lw=1.6, label="Interpolated series (Kalman smoother)")
    ax.plot(np.exp(log_p[win][: CHART3_ORIGIN]), color="#e8601c", lw=1.6, drawstyle="steps-post",
            label="Official series")
    ax.plot(np.exp(f.log_p_latent), color="#1f4e9c", ls=":", lw=1.6, label="Forecast (latent monthly)")
    ax.plot(np.exp(f.log_p_hat), color="#e8601c", ls=":", lw=1.6, drawstyle="steps-post",
            label="Forecast (published-like)")
    ax.plot(np.exp(log_p[CHART3_ORIGIN:"2011-11-01"]), color="grey", lw=0.8, alpha=0.6, label="Official, after origin")
    ax.set_title(f"Chart 3 replica: women's trousers ({CHART3_ITEM}), AR({int(o.p)})"
                 f"{' x SAR(12)' if o.seasonal else ''}, origin {CHART3_ORIGIN:%b %Y}")
    ax.set_ylabel("Index (Dec 2010 = 100)")
    ax.grid(ls=":")
    ax.legend(fontsize=8, ncol=2)
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURES / "chart3_trousers.png", dpi=150)
    print(f"\nChart 3: {CHART3_ITEM} p={int(o.p)} seasonal={bool(o.seasonal)} mu={res.params['mu']:.4f} "
          f"rho={res.params.get('ar.S.L12', np.nan):.3f} -> outputs/figures/chart3_trousers.png")


def main() -> None:
    panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    specs = pd.read_csv(FINAL / "item_specs.csv")
    collection = pd.read_csv(FINAL / "collection.csv", parse_dates=["date"])
    series = {i: g.set_index("date")["log_p"].asfreq("MS") for i, g in panel.groupby("item_id")}

    orders = build_orders(series, specs, force="--force" in sys.argv)
    assert orders.groupby("vintage").item_id.nunique().max() <= 182
    print("\nChosen AR order p per vintage (counts) and seasonal items:")
    print(pd.crosstab(orders.vintage, orders.p).to_string())
    print(orders.groupby("vintage")[["seasonal", "converged"]].sum().to_string())

    sanity_forecasts(series, orders, collection)
    chart3(series, orders, collection)


if __name__ == "__main__":
    main()
