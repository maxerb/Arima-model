"""Benchmark forecasts for the evaluation (T3.2): AR(1), ARIMA(1), ARIMA(6), ARIMA(14), SNB, KOF consensus.

Skill: snb-arima-evaluation. Paper pp. 8-11, Tables 1-2.

All benchmarks are built at the same 32 origins as the disaggregate model (Feb/May/Aug/Nov 2004-2011, two months
of the current quarter known, D-04) and scored on the same target, quarterly y-o-y inflation of the **official**
CPI (paper p. 10, D-50).

* ``ar1``     - AR(1) on monthly Δlog headline CPI with monthly intercepts, iterated forward (D-05 rev., paper
                p. 8: "same information set" as the ARIMA model, i.e. the two known months of the current quarter).
                ``ar1_plain`` = the original D-05 with one constant (sensitivity).
* ``arima1``  - ARIMA on the official headline CPI (D-47): the "no disaggregation" end of Table 2.
* ``arima6``, ``arima14`` - one ARIMA per sub-aggregate (paper Table 9 groups), forecasts aggregated with the
                summed item weights by the same chained Laspeyres formula as the 182 items (D-13, D-45, D-47).
  ARIMA(1)/(6)/(14) are specified exactly like an item (D-55): annual spec vintage with ADF/KPSS and ACF
  seasonality (D-31, D-33), ARIMA(p,1,q)(1,0,0)_12 chosen by SIC on the D-02 grid (CLS, D-35), sample from May
  2000 like the items, quarterly-lag model for a quarterly-collected group (Rents), D-11 fallback. Differences to
  ARIMA(182) therefore come only from the level of disaggregation. Oil products and rents are plain ARIMA, as in
  Table 2 (p. 11).
* ``snb_conditional`` - SNB conditional forecast of the assessment published in the 3rd month of the origin
                quarter (SNB cube snbiprogq, D-20). The cube starts with June 2004, so 2004Q1 has none.
* ``kof_consensus`` - KOF Consensus mean of `prices_cy` / `prices_ny` (D-06 rev.), the survey of the origin's own
                quarter (D-56). KOF forecasts only annual averages, so it is scored on the annual target
                (`annual_eval`), never on quarterly y-o-y.

No look-ahead (AGENTS.md rule 1): every forecast function takes the full data and an `origin` and cuts the data
itself (CPI <= origin; sub-aggregate specs of the vintage before the origin year; weights known at the origin).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from arima_snb import aggregate
from arima_snb.config import (FINAL, FORECAST_STEPS, HORIZONS, INTERIM, ITEM_SAMPLE_START, NO_COLLECTION_TOL,
                              OOS_N_JOBS, SPEC_VINTAGES)

LEVEL_MODEL = {"agg1": "arima1", "agg6": "arima6", "agg14": "arima14"}
AR1 = "ar1"
AR1_PLAIN = "ar1_plain"   # original D-05 without month intercepts (sensitivity)
SNB = "snb_conditional"
KOF = "kof_consensus"
BENCH_CACHE = INTERIM / "oos"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
def subaggregate_panel() -> pd.DataFrame:
    """Sub-aggregate indices as an 'item' panel: date, item_id ('<level>:<group>'), level, index, log_p.

    agg1 = official CPI (SNB plkopr, D-47); agg6/agg14 = groups re-aggregated from the 182 items (T2.5).
    The history in year Y is chained with the weights of Y, which BFS publishes in February of Y, i.e. before
    our first origin of that year (D-13) - so the file contains no look-ahead up to any origin.
    """
    s = pd.read_csv(FINAL / "subaggregates_long.csv", parse_dates=["date"])
    s["item_id"] = s.level + ":" + s.group
    return s[["date", "item_id", "level", "index", "log_p"]]


def subaggregate_weights() -> pd.DataFrame:
    """Annual weights of the groups (year, item_id, weight) = summed item weights (T2.5, D-47)."""
    w = pd.read_csv(FINAL / "subaggregate_weights.csv")
    return w.assign(item_id=w.level + ":" + w.group)[["year", "item_id", "weight", "level"]]


def group_collection(panel: pd.DataFrame) -> pd.DataFrame:
    """Collection flags of each sub-aggregate: collected in month t if ANY member item is collected in t (D-55).

    Item flags come from data/final/collection.csv (official calendar of paper Tables 5-8 where it exists, else
    inferred from carried-forward prices; an item counts as collected if either source says so), plus the
    group's own index change |Δlog p| >= 1e-3 (fn. 9). Inferring flags from the group index alone undercounts
    (the Rents group then looks 'less than quarterly' in years with an unchanged rent quarter). A group with one
    monthly item is monthly; only groups whose items are all collected in the same few months (Rents) get the
    quarterly-lag model, like the rent item. Written with source 'inferred' so that the item machinery
    (`diagnostics.collection_frequency`, `panel.collection_pattern`) reads it unchanged.
    """
    coll = pd.read_csv(FINAL / "collection.csv", parse_dates=["date"])
    coll["collected"] = coll.collected.astype("boolean").fillna(False).astype(bool)
    item_flag = coll.groupby(["date", "item_id"]).collected.any()
    items = pd.read_csv(FINAL / "items.csv")
    rows = []
    for item_id, g in panel.sort_values("date").groupby("item_id"):
        level, group = item_id.split(":", 1)
        members = items.item_id if level == "agg1" else items.loc[items[level] == group, "item_id"]
        f = item_flag[item_flag.index.get_level_values("item_id").isin(members)].groupby("date").any()
        own = g.set_index("date").log_p.diff().abs() >= NO_COLLECTION_TOL
        flag = own | f.reindex(own.index, fill_value=False)
        rows.append(pd.DataFrame({"date": own.index, "item_id": item_id, "collected": flag.values,
                                  "source": "inferred"}))
    return pd.concat(rows, ignore_index=True)


def subaggregate_specs(panel: pd.DataFrame, collection: pd.DataFrame, vintages=SPEC_VINTAGES) -> pd.DataFrame:
    """Spec vintages of the 21 sub-aggregate series, exactly as for items (T2.1, D-31...D-34, D-55)."""
    from arima_snb.diagnostics import SPEC_COLUMNS, diagnose_item

    wide = panel.pivot(index="date", columns="item_id", values="log_p")
    rows = [diagnose_item(wide[c], collection, c, None, v) for v in vintages for c in wide.columns]
    return pd.DataFrame(rows).reindex(columns=SPEC_COLUMNS)


def load_inputs() -> dict:
    """Everything the benchmarks need, FULL sample (cut per origin inside the forecast functions)."""
    from arima_snb.evaluate import official_cpi

    panel = subaggregate_panel()
    collection = group_collection(panel)
    spec_path = FINAL / "subaggregate_specs.csv"
    specs = pd.read_csv(spec_path) if spec_path.exists() else subaggregate_specs(panel, collection)
    return {"sub_panel": panel, "sub_collection": collection, "sub_specs": specs,
            "sub_weights": subaggregate_weights(), "cpi": official_cpi()}


# ---------------------------------------------------------------------------
# AR(1) on monthly inflation (D-05)
# ---------------------------------------------------------------------------
def forecast_ar1(cpi: pd.Series, origin, steps: int = FORECAST_STEPS, month_dummies: bool = True) -> pd.DataFrame:
    """AR(1) on y_t = Δlog CPI_t, OLS on May 2000 ... origin, iterated `steps` months ahead (D-05 rev.).

    month_dummies=True (D-05 rev., user 2026-11-25): y_t = c_{m(t)} + φ y_{t-1} + e_t with one intercept per
    calendar month. The Swiss CPI has a strong seasonal pattern since 2000 (clothing sales in January and July);
    with a single constant the AR(1) path converges to the average monthly change and misses it, which makes the
    y-o-y forecasts of the quarters after a seasonal month zig-zag (RMSFE 0.82 at h = 2 vs 0.77 at h = 3).
    month_dummies=False is the original D-05 (one constant), kept as the sensitivity row `ar1_plain`.
    Returns (target, index_hat) on the CPI's scale.
    """
    origin = pd.Timestamp(origin)
    x = np.log(cpi.loc[pd.Timestamp(ITEM_SAMPLE_START):origin].dropna())
    y = x.diff().dropna()
    months = y.index.month.to_numpy()
    if month_dummies:
        D = (months[1:, None] == np.arange(1, 13)[None, :]).astype(float)
    else:
        D = np.ones((len(y) - 1, 1))
    b = np.linalg.lstsq(np.column_stack([D, y.values[:-1]]), y.values[1:], rcond=None)[0]
    c, phi = b[:-1], b[-1]
    targets = pd.date_range(origin + pd.DateOffset(months=1), periods=steps, freq="MS")
    path, last = [], y.iloc[-1]
    for t in targets:
        last = (c[t.month - 1] if month_dummies else c[0]) + phi * last
        path.append(last)
    return pd.DataFrame({"target": targets, "index_hat": np.exp(x.iloc[-1] + np.cumsum(path))})


# ---------------------------------------------------------------------------
# ARIMA(1), ARIMA(6), ARIMA(14) (D-47, D-55)
# ---------------------------------------------------------------------------
def subaggregate_item_forecasts(inputs: dict, origin, n_jobs: int = OOS_N_JOBS, cache: Path | None = BENCH_CACHE,
                                force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """ARIMA forecasts of the 21 sub-aggregate series at `origin` (item machinery of T2.2), cached per origin."""
    from arima_snb.diagnostics import specs_for_origin
    from arima_snb.item_models import forecast_items

    origin = pd.Timestamp(origin)
    paths = None
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        paths = (cache / f"subagg_{origin:%Y-%m}_fc.csv", cache / f"subagg_{origin:%Y-%m}_log.csv")
        if all(p.exists() for p in paths) and not force:
            return pd.read_csv(paths[0], parse_dates=["origin", "target"]), pd.read_csv(paths[1])
    specs = specs_for_origin(inputs["sub_specs"], origin)   # D-31: vintage of the previous year
    fc, log = forecast_items(inputs["sub_panel"], specs, inputs["sub_collection"], origin, n_jobs=n_jobs)
    if cache is not None:
        fc.to_csv(paths[0], index=False)
        log.to_csv(paths[1], index=False)
    return fc, log


def aggregate_level(inputs: dict, sub_fc: pd.DataFrame, origin, level: str) -> pd.Series:
    """Monthly forecast index of one benchmark (history + forecast) from the sub-aggregate forecasts at `origin`.

    agg1: the official CPI with its own forecast spliced on. agg6/agg14: actual group indices up to the origin,
    exp(log_p_hat) after it, chained Laspeyres with the group weights known at the origin (D-13, D-45).
    """
    origin = pd.Timestamp(origin)
    panel = inputs["sub_panel"]
    ids = panel.loc[panel.level == level, "item_id"].unique()
    wide = panel[panel.item_id.isin(ids)].pivot(index="date", columns="item_id", values="index")
    spliced = aggregate.splice_forecast(wide, sub_fc[sub_fc.item_id.isin(ids)], origin)
    if level == "agg1":
        return spliced.iloc[:, 0]
    w = inputs["sub_weights"]
    w = aggregate.weights_known_at(w[w.level == level], origin, spliced.index.max().year)
    return aggregate.aggregate_index(spliced, w[["year", "item_id", "weight"]])


def quarterly_from_index(index_m: pd.Series, origin, horizons=HORIZONS) -> pd.DataFrame:
    """origin_q, h, target_q, pi_hat from a monthly index path (actuals <= origin, forecasts after)."""
    yoy = aggregate.quarterly_yoy(index_m.dropna())
    oq = pd.Timestamp(origin).to_period("Q")
    return pd.DataFrame([{"origin_q": oq, "h": h, "target_q": oq + (h - 1), "pi_hat": yoy.get(oq + (h - 1), np.nan)}
                         for h in horizons])


def forecast_origin(inputs: dict, origin, n_jobs: int = OOS_N_JOBS, cache: Path | None = BENCH_CACHE,
                    force: bool = False) -> dict:
    """Quarterly y-o-y forecasts of AR(1), ARIMA(1), ARIMA(6), ARIMA(14) at one origin (+ monthly paths, log)."""
    origin = pd.Timestamp(origin)
    cpi = inputs["cpi"].loc[:origin]                       # nothing after the origin
    paths = {m: pd.concat([cpi, forecast_ar1(cpi, origin, month_dummies=d).set_index("target").index_hat])
             for m, d in ((AR1, True), (AR1_PLAIN, False))}
    sub_fc, log = subaggregate_item_forecasts(inputs, origin, n_jobs, cache, force)
    for level, model in LEVEL_MODEL.items():
        if not (inputs["sub_panel"].level == level).any():
            continue
        paths[model] = aggregate_level(inputs, sub_fc, origin, level)
    q = pd.concat([quarterly_from_index(s, origin).assign(model=m) for m, s in paths.items()], ignore_index=True)
    monthly = pd.concat([pd.DataFrame({"origin": origin, "target": s.index, "aggregate": "total", "model": m,
                                       "index_hat": s.values})[lambda d: d.target > origin]
                         for m, s in paths.items()], ignore_index=True)
    return {"quarterly": q, "monthly": monthly, "items": sub_fc, "log": log}


# ---------------------------------------------------------------------------
# SNB conditional forecast (D-20) and KOF consensus (D-06 rev., D-56)
# ---------------------------------------------------------------------------
ASSESSMENT_MONTH = {"M": 3, "J": 6, "S": 9, "D": 12}


def snb_conditional_paths() -> pd.DataFrame:
    """All SNB assessments: publication quarter, target quarter, forecast (snbiprogq 'P' series, D-20).

    Series code e.g. 'J2004PL05P' = June 2004 assessment (policy rate assumption 0.5 %). M/J/S/D = March, June,
    September, December assessment.
    """
    from arima_snb import io

    cube = io.read_snb_cube(io.find_raw("snb-data-snbiprogq-*.csv"), "snbiprogq")
    p = cube[cube.variable.str.endswith("_P")].dropna(subset=["value"])
    code = p.variable.str.split("_").str[1]
    m = code.str.extract(r"^([MJSD])(\d{4})")
    pub = pd.PeriodIndex([pd.Period(f"{y}-{ASSESSMENT_MONTH[l]:02d}", freq="M").asfreq("Q")
                          for l, y in zip(m[0], m[1])])
    out = pd.DataFrame({"pub_q": pub, "code": code.values, "target_q": pd.PeriodIndex(p.date, freq="Q"),
                        "pi_hat": p.value.astype(float).values})
    assert not out.duplicated(["pub_q", "target_q"]).any(), "two assessments in one quarter"
    return out


def snb_forecast_origin(paths: pd.DataFrame, origin, horizons=HORIZONS) -> pd.DataFrame:
    """SNB forecast for an origin (2nd month of quarter t): the assessment published in quarter t (D-20).

    Published in the 3rd month of t, i.e. at the time of the paper's forecasting meeting (p. 8). Empty if the
    cube has no assessment in t (2004Q1).
    """
    oq = pd.Timestamp(origin).to_period("Q")
    a = paths[paths.pub_q == oq].set_index("target_q").pi_hat
    return pd.DataFrame([{"origin_q": oq, "h": h, "target_q": oq + (h - 1), "pi_hat": a.get(oq + (h - 1), np.nan)}
                         for h in horizons])


def kof_consensus() -> pd.DataFrame:
    """KOF Consensus mean forecasts per survey: survey_date, survey_q, prices_cy, prices_ny (D-06 rev.)."""
    from arima_snb import io

    df = pd.read_excel(io.find_raw("kof_kof_consensus_forecast_mean_ts_*.xlsx"), header=None)
    df.columns = [str(c) for c in df.iloc[0]]
    df = df.iloc[1:]
    pick = {c: re.search(r"prices_(cy|ny)\.mean$", c).group(1) for c in df.columns if re.search(r"prices_(cy|ny)\.mean$", c)}
    out = df[["date", *pick]].rename(columns={k: f"prices_{v}" for k, v in pick.items()})
    out["survey_date"] = pd.to_datetime(out.pop("date"))
    out["survey_q"] = out.survey_date.dt.to_period("Q")
    return out.astype({"prices_cy": float, "prices_ny": float})[["survey_date", "survey_q", "prices_cy", "prices_ny"]]


def kof_for_origin(kof: pd.DataFrame, origin) -> pd.Series | None:
    """The survey of the origin's own quarter (D-56): dated in the 3rd month, like the SNB assessment (D-20).

    Its respondents know the CPI of the first two months of the quarter (the ARIMA's information set, p. 8) but
    not the 3rd month's CPI, which is released only in the following quarter.
    """
    oq = pd.Timestamp(origin).to_period("Q")
    s = kof[kof.survey_q == oq]
    return None if s.empty else s.iloc[-1]


# ---------------------------------------------------------------------------
# Annual-average target (D-06 rev., D-57)
# ---------------------------------------------------------------------------
def annual_from_quarterly(q_fc: pd.DataFrame, actual_q: pd.Series) -> pd.DataFrame:
    """Annual-average inflation of the current (h_year = 0) and next year (h_year = 1) per origin and model.

    D-57: annual-average inflation = mean of the four quarterly y-o-y rates of the calendar year; quarters
    before the origin quarter are actuals, the others the model's forecasts (h = 1..5). A year is only scored
    where h <= 5 covers all its remaining quarters: the current year at every origin, the next year only at
    Q4 origins (h = 2..5 = Q1..Q4 of next year).
    q_fc: origin_q, h, target_q, model, pi_hat. actual_q: quarterly y-o-y of official CPI (PeriodIndex).
    """
    rows = []
    for (oq, model), g in q_fc.groupby(["origin_q", "model"]):
        oq = pd.Period(oq, freq="Q")
        fc = g.assign(tq=pd.PeriodIndex(g.target_q.astype(str), freq="Q")).set_index("tq").pi_hat
        for h_year in (0, 1):
            year = oq.year + h_year
            qs = pd.period_range(f"{year}Q1", f"{year}Q4", freq="Q")
            vals = [actual_q.get(q) if q < oq else fc.get(q, np.nan) for q in qs]
            rows.append({"origin_q": str(oq), "h_year": h_year, "target_y": year, "model": model,
                         "pi_hat": float(np.mean(vals)) if np.all(np.isfinite(vals)) else np.nan})
    return pd.DataFrame(rows)


def annual_actuals(actual_q: pd.Series) -> pd.Series:
    """Actual annual-average inflation per year = mean of the four quarterly y-o-y rates (D-57)."""
    a = actual_q.dropna()
    g = a.groupby(a.index.year)
    return g.mean()[g.count() == 4]
