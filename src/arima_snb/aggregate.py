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
    Returns the aggregate with value 100 at the first link month.
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
        if not out:
            out[p.link] = level
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
