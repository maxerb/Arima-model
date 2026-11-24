"""Aggregation of item indices to CPI and sub-aggregates; quarterly y-o-y inflation (T1.6, T2.5).

Skill: snb-arima-aggregate.

The Swiss CPI is a chained Laspeyres index (AGENTS.md §7). Within one weight period the aggregate relative to
the period's price-reference ("link") month is the weighted mean of the item relatives:

    A_t / A_L = sum_i w_i * I_{i,t} / I_{i,L}        (weights normalised over the included items)

and the periods are chained at the link months. From 2002 every calendar year is one period with link month
December of the previous year. Before that the basket periods are longer (D-29): the 1993 basket runs
May 1993 - Apr 2000 with link May 1993 (fixed-base Laspeyres, one weight set), the 2000 basket's weights
("2000/01" column, D-26) run May 2000 - Dec 2001 with link May 2000.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from arima_snb.config import EARLY_WEIGHT_PERIODS


def weight_periods(first: pd.Timestamp, last: pd.Timestamp) -> pd.DataFrame:
    """Table of chaining periods: weight_year, link (price-reference month), start, end (inclusive). D-29."""
    rows = [dict(weight_year=wy, link=pd.Timestamp(link), start=pd.Timestamp(s), end=pd.Timestamp(e))
            for wy, link, s, e in EARLY_WEIGHT_PERIODS]
    year0 = rows[-1]["end"].year + 1 if rows else first.year
    for y in range(year0, last.year + 1):
        rows.append(dict(weight_year=y, link=pd.Timestamp(f"{y - 1}-12-01"),
                         start=pd.Timestamp(f"{y}-01-01"), end=pd.Timestamp(f"{y}-12-01")))
    per = pd.DataFrame(rows)
    return per[(per.end >= first) & (per.start <= last)].reset_index(drop=True)


def aggregate_index(item_index: pd.DataFrame, weights: pd.DataFrame,
                    items: list[str] | None = None) -> pd.Series:
    """Chain-linked Laspeyres aggregate of item indices (actuals or forecast paths).

    item_index: wide DataFrame, monthly DatetimeIndex x item_id columns (index levels, not logs).
    weights:    long DataFrame year, item_id, weight (any scale; normalised per period over the items that
                have a weight and an observed index in the link month and month t, D-30).
    Returns the aggregate with value 100 at the first link month that has data.
    """
    if items is not None:
        item_index = item_index[[c for c in item_index.columns if c in items]]
    wide_w = weights.pivot(index="year", columns="item_id", values="weight")
    per = weight_periods(item_index.index.min(), item_index.index.max())

    level, out = 100.0, {}
    for p in per.itertuples():
        if p.link not in item_index.index or p.weight_year not in wide_w.index:
            continue
        w = wide_w.loc[p.weight_year].reindex(item_index.columns).dropna()
        base = item_index.loc[p.link, w.index]
        months = item_index.loc[p.start:p.end, w.index]
        rel = months / base                                   # item relatives vs link month
        ok = rel.notna()
        ww = ok.mul(w, axis=1)
        ratio = (rel.fillna(0) * ww).sum(axis=1) / ww.sum(axis=1)  # D-30: normalise over included items
        started = any(np.isfinite(v) for v in out.values())
        if not started and base.notna().any():
            # The chain starts at the first period whose link month has data. For the total that is May 1993;
            # a sub-aggregate whose items all enter later (e.g. Education, May 2000) starts there (T2.5).
            out = {p.link: level}
        level_link = out.get(p.link, np.nan)
        for t, r in ratio.items():
            out[t] = level_link * r
    return pd.Series(out, name="index").sort_index()


def quarterly_yoy(index_m: pd.Series) -> pd.Series:
    """Year-on-year % change of the quarterly average of a monthly index (only complete quarters)."""
    s = index_m.copy()
    s.index = pd.DatetimeIndex(s.index)
    g = s.resample("QS")
    q = g.mean().where(g.count() == 3)
    q.index = q.index.to_period("Q")
    return 100 * (q / q.shift(4) - 1)


def monthly_yoy(index_m: pd.Series) -> pd.Series:
    """Year-on-year % change of a monthly index (12-month change)."""
    s = index_m.asfreq("MS")
    return 100 * (s / s.shift(12) - 1)


def build_subaggregate_series(item_index: pd.DataFrame, weights: pd.DataFrame, items: pd.DataFrame,
                              level: str) -> pd.DataFrame:
    """Historical monthly sub-aggregate indices (ARIMA(1)/(6)/(14) inputs). level: 'agg1', 'agg6', 'agg14'."""
    if level == "agg1":
        return aggregate_index(item_index, weights).to_frame("total")
    groups = items.groupby(level)["item_id"].apply(list)
    return pd.DataFrame({g: aggregate_index(item_index, weights, ids) for g, ids in groups.items()})


# ---------------------------------------------------------------------------------------------------------
# T2.5: from item forecasts to aggregate forecasts
# ---------------------------------------------------------------------------------------------------------
# An aggregate forecast is the same chained Laspeyres formula applied to a "spliced" item panel: the actual
# item indices up to the origin, the forecast item indices after it (skill snb-arima-aggregate). Because the
# formula is in index LEVELS, forecast log prices are exponentiated first (exp(log_p_hat) is the median, not
# the mean, of a log-normal forecast; the paper aggregates point forecasts the same way, D-45).


def weights_known_at(weights: pd.DataFrame, origin, last_year: int) -> pd.DataFrame:
    """Weights an analyst knows at `origin`, extended to `last_year` (D-13).

    BFS publishes the weights of year y with the January index of y (released in February), so at an origin in
    year y (Feb, May, Aug or Nov) the weights of y are known and those of y+1 are not. Years after the origin
    year reuse the latest known weights (D-13). Rows of later years in `weights` are dropped, never used.
    """
    origin = pd.Timestamp(origin)
    known = weights[weights.year <= origin.year]
    latest = known.year.max()
    extra = [known[known.year == latest].assign(year=y) for y in range(latest + 1, last_year + 1)]
    return pd.concat([known, *extra], ignore_index=True)


def splice_forecast(item_index: pd.DataFrame, item_fc: pd.DataFrame, origin) -> pd.DataFrame:
    """Wide monthly panel: actual item index up to `origin`, exp(log_p_hat) for the forecast months after it.

    item_index: wide actual index levels (month x item_id); everything after `origin` is discarded here.
    item_fc:    long forecasts of ONE origin (target, item_id, log_p_hat), AGENTS.md §4.
    Items without a forecast have no value after the origin and drop out of those months (D-30).
    """
    origin = pd.Timestamp(origin)
    actual = item_index.loc[:origin]
    fc = item_fc.assign(target=pd.to_datetime(item_fc.target, format="ISO8601"))
    fc = fc[fc.target > origin].pivot(index="target", columns="item_id", values="log_p_hat")
    future = np.exp(fc).reindex(columns=actual.columns)
    return pd.concat([actual, future]).sort_index().asfreq("MS")


def aggregate_groups(items: pd.DataFrame) -> dict[str, list[str]]:
    """Item lists of every aggregate built in T2.5: total, CPI excl. oil products, ARIMA(6) and ARIMA(14) groups.

    Names: 'total', 'excl_oil', 'agg6:<group>', 'agg14:<group>' (groups as in data/final/items.csv, paper Table 9).
    """
    groups = {"total": items.item_id.tolist(),
              "excl_oil": items.loc[items.special.fillna("") != "oil", "item_id"].tolist()}
    for level in ("agg6", "agg14"):
        for g, ids in items.groupby(level)["item_id"]:
            groups[f"{level}:{g}"] = ids.tolist()
    return groups


def forecast_aggregates(item_index: pd.DataFrame, weights: pd.DataFrame, items: pd.DataFrame,
                        item_fc: pd.DataFrame, origin) -> pd.DataFrame:
    """Monthly forecast index of every aggregate for one origin (long: origin, target, aggregate, index_hat).

    Uses only data known at `origin`: actual item indices up to the origin, the item forecasts made at the
    origin and the weights known at the origin (D-13). The index level is the full-history chain (first link
    month = 100), so actual and forecast months of the same aggregate are on one scale. Rows cover the whole
    history up to the last forecast month; months <= origin are actuals (re-aggregated), later ones forecasts.
    """
    origin = pd.Timestamp(origin)
    panel = splice_forecast(item_index, item_fc, origin)
    w = weights_known_at(weights, origin, panel.index.max().year)
    out = []
    for name, ids in aggregate_groups(items).items():
        s = aggregate_index(panel, w, ids)
        out.append(pd.DataFrame({"target": s.index, "aggregate": name, "index_hat": s.values}))
    df = pd.concat(out, ignore_index=True)
    df.insert(0, "origin", origin)
    return df


def forecast_quarterly_yoy(agg_fc: pd.DataFrame, horizons=range(1, 6)) -> pd.DataFrame:
    """Quarterly y-o-y inflation forecasts from the monthly aggregate paths of one or more origins.

    h = 1 is the origin's own quarter (its first two months are actual, the third is forecast); target quarter
    = origin quarter + h - 1. Quarter q-4 of the y-o-y rate is always fully actual for h <= 4 and partly
    forecast for h = 5 (AGENTS.md §4). Returns origin, origin_q, h, target_q, aggregate, pi_hat.
    """
    rows = []
    for (origin, name), g in agg_fc.groupby(["origin", "aggregate"]):
        s = g.set_index(pd.DatetimeIndex(g.target))["index_hat"]
        yoy = quarterly_yoy(s)
        oq = pd.Timestamp(origin).to_period("Q")
        for h in horizons:
            tq = oq + (h - 1)
            rows.append(dict(origin=origin, origin_q=oq, h=h, target_q=tq, aggregate=name,
                             pi_hat=yoy.get(tq, np.nan)))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Benchmark inputs ARIMA(1)/(6)/(14) (T3.2): historical sub-aggregate indices and their weights
# ---------------------------------------------------------------------------------------------------------

def subaggregate_weights(weights: pd.DataFrame, items: pd.DataFrame, level: str) -> pd.DataFrame:
    """Annual weight of each sub-aggregate = sum of its items' weights (year, group, weight).

    With these weights, aggregate_index() applied to the sub-aggregate indices reproduces the item aggregate
    exactly (chained Laspeyres is consistent in aggregation when all are chained at the same link months).
    """
    if level == "agg1":
        grp = pd.Series("total", index=items.item_id)
    else:
        grp = items.set_index("item_id")[level]
    w = weights.assign(group=weights.item_id.map(grp)).dropna(subset=["group"])
    return w.groupby(["year", "group"], as_index=False)["weight"].sum()
