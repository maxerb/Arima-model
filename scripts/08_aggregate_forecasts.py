"""T2.5: item forecasts -> aggregate CPI forecasts and quarterly y-o-y inflation; benchmark inputs for T3.2.

Paper pp. 5, 8, 11; decisions D-13 (weights known at origin), D-29/D-30 (chaining, coverage), D-45...D-47.

Reads  outputs/forecasts/arima182_items.csv     (T2.2, every origin in the file)
Writes outputs/forecasts/arima182_aggregates.csv  origin, target, aggregate, model, index_hat (monthly)
       outputs/forecasts/arima182_quarterly.csv   origin, origin_q, h, target_q, aggregate, model, pi_hat
       data/final/subaggregates_long.csv           date, level, group, index, log_p   (ARIMA(1)/(6)/(14) inputs;
                                                   agg1 = official CPI, agg6/agg14 = 182-item groups, D-47)
       data/final/subaggregate_weights.csv         year, level, group, weight

    python scripts/08_aggregate_forecasts.py
"""

import numpy as np
import pandas as pd

from arima_snb import aggregate, io
from arima_snb.config import FINAL, FORECASTS, HORIZONS
from arima_snb.item_models import MODEL_NAME

LEVELS = ("agg6", "agg14")   # ARIMA(6)/(14) from the 182 items; ARIMA(1) = official CPI (D-47)


def official_cpi() -> pd.Series:
    """Official headline CPI (Dec 2010 = 100), SNB cube plkopr - the paper's 'total CPI' and evaluation target."""
    cube = io.read_snb_cube(io.find_raw("snb-data-plkopr-*.csv"), "plkopr")
    return cube[cube.variable == "plkopr_LD2010100"].set_index("date")["value"].astype(float).sort_index()


def main() -> None:
    long = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    weights = pd.read_csv(FINAL / "weights.csv")
    items = pd.read_csv(FINAL / "items.csv")
    wide = long.pivot(index="date", columns="item_id", values="index").asfreq("MS")

    # --- 1. benchmark inputs: historical sub-aggregate indices (no forecasts involved) -----------------------
    subs, subw = [], []
    for level in LEVELS:
        s = aggregate.build_subaggregate_series(wide, weights, items, level)
        s.index.name = "date"
        subs.append(s.reset_index().melt(id_vars="date", var_name="group", value_name="index").assign(level=level))
        subw.append(aggregate.subaggregate_weights(weights, items, level).assign(level=level))
    official = official_cpi()
    subs.append(pd.DataFrame({"date": official.index, "group": "total", "index": official.values, "level": "agg1"}))
    subw.append(pd.DataFrame({"year": sorted(weights.year.unique()), "group": "total", "weight": 100.0,
                              "level": "agg1"}))
    subs = pd.concat(subs, ignore_index=True).dropna(subset=["index"])
    subs["log_p"] = np.log(subs["index"])
    subw = pd.concat(subw, ignore_index=True)
    subs[["date", "level", "group", "index", "log_p"]].to_csv(FINAL / "subaggregates_long.csv", index=False)
    subw[["year", "level", "group", "weight"]].to_csv(FINAL / "subaggregate_weights.csv", index=False)

    # Check: re-aggregating the sub-aggregates with their summed weights gives the item aggregate back.
    total = aggregate.aggregate_index(wide, weights)
    for level in ("agg6", "agg14"):
        g = subs[subs.level == level].pivot(index="date", columns="group", values="index").asfreq("MS")
        w = subw[subw.level == level].rename(columns={"group": "item_id"})
        back = aggregate.aggregate_index(g, w)
        gap = (back / total.reindex(back.index) - 1).abs().max()
        print(f"{level}: {g.shape[1]} groups, max rel. gap to item aggregate {gap:.2e}")
        assert gap < 1e-3, f"{level} sub-aggregates do not add up to the total"

    # --- 2. aggregate forecasts for every origin in the item forecast file -----------------------------------
    fc_items = pd.read_csv(FORECASTS / f"{MODEL_NAME}_items.csv")
    for c in ("origin", "target"):   # older files mix "2004-03-01" and "2004-03-01 00:00:00"
        fc_items[c] = pd.to_datetime(fc_items[c], format="ISO8601")
    monthly, quarterly = [], []
    for origin, f in fc_items.groupby("origin"):
        agg = aggregate.forecast_aggregates(wide, weights, items, f, origin)
        agg = agg[agg.target >= pd.Timestamp(f"{origin.year - 1}-01-01")]   # enough history for y-o-y
        q = aggregate.forecast_quarterly_yoy(agg, HORIZONS)
        assert q.loc[q["aggregate"] == "total", "pi_hat"].notna().all(), f"missing h for origin {origin:%Y-%m}"
        monthly.append(agg[agg.target > origin])
        quarterly.append(q)
    monthly = pd.concat(monthly, ignore_index=True).assign(model=MODEL_NAME)
    quarterly = pd.concat(quarterly, ignore_index=True).assign(model=MODEL_NAME)
    monthly[["origin", "target", "aggregate", "model", "index_hat"]].to_csv(
        FORECASTS / f"{MODEL_NAME}_aggregates.csv", index=False)
    quarterly[["origin", "origin_q", "h", "target_q", "aggregate", "model", "pi_hat"]].to_csv(
        FORECASTS / f"{MODEL_NAME}_quarterly.csv", index=False)

    # --- 3. sanity output: forecast vs actual (re-aggregated items and official CPI) -------------------------
    act = pd.DataFrame({"actual_182": aggregate.quarterly_yoy(total),
                        "actual_official": aggregate.quarterly_yoy(official)})
    tot = quarterly[quarterly["aggregate"] == "total"].join(act, on="target_q")
    pd.set_option("display.width", 200)
    print("\nTotal CPI, quarterly y-o-y inflation (%):")
    cols = ["origin_q", "h", "target_q", "pi_hat", "actual_182", "actual_official"]
    print(tot[cols].to_string(index=False, float_format="%.2f"))
    sub = quarterly[(quarterly.h == 1) & quarterly["aggregate"].str.startswith("agg6")]
    print("\nARIMA(6) groups, h = 1:")
    print(sub[["origin_q", "aggregate", "pi_hat"]].to_string(index=False, float_format="%.2f"))
    print("\nwrote", FORECASTS / f"{MODEL_NAME}_aggregates.csv", "and", FORECASTS / f"{MODEL_NAME}_quarterly.csv")


if __name__ == "__main__":
    main()
