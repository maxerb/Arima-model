"""T4.2: pseudo-out-of-sample evaluation of the extended ARIMA(182) - paper Table 4 (p. 15).

Skills: snb-arima-evaluation, snb-arima-kalman-extension.

What the "extended ARIMA(182)" is (paper pp. 14-15, D-41)
--------------------------------------------------------
Every one of the 182 items gets the collection-frequency state-space model of `kalman_ext` (latent monthly AR(p),
optionally x seasonal AR(12), estimated on log levels with the non-collection months missing). Oil products and
rents are NOT given their special models (p. 15: "we do not use the alternative approaches for prices of oil
products and rents in the extended ARIMA model"). The item forecasts are aggregated exactly like the plain model
(`evaluate.aggregate_origin`, chained Laspeyres with the weights known at the origin) and compared with

* ``arima182``         - the plain disaggregate ARIMA of T3.1 (Table 4, row 2), and
* ``arima182_special`` - our analogue of the real-time ARIMA (Table 4, row 3; D-50).

At each origin (32 origins Feb/May/Aug/Nov 2004-2011, D-04) the AR order comes from the annual vintage of the
year before (D-44), the parameters are re-estimated on data from 1993 up to the origin (expanding window, D-03),
and the expected collection months are those observed in the year before the origin (paper pp. 14-15, D-43).
The item forecasts used for aggregation are the published-like paths (prices carried forward between expected
collection months, as the SFSO does).

The DMW-HLN test lives here (`dmw_hln`) because `evaluate.py` belongs to T3.2/T3.3 at the moment; T3.3 can call it
from `evaluate.dmw_test` (D-52).

No look-ahead (AGENTS.md rule 1): `kalman_item_forecasts` receives the full data and cuts CPI and collection flags
at the origin itself; `kalman_ext.observed_levels` cuts again inside every fit.
"""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from arima_snb import evaluate
from arima_snb.config import FORECAST_STEPS, KALMAN_N_JOBS
from arima_snb.kalman_ext import forecast_item_kalman, orders_for_origin
from arima_snb.panel import collection_pattern

MODEL_KALMAN = "kalman182"          # extended ARIMA(182), Table 4 row 1
OOS_CACHE = evaluate.OOS_CACHE      # same per-origin cache folder as T3.1 (D-51), different file names


# ---------------------------------------------------------------------------
# Item forecasts at one origin
# ---------------------------------------------------------------------------
def _forecast_one(args) -> tuple[pd.DataFrame | None, dict]:
    """Worker: extended-model forecast of one item at one origin (runs in a separate process)."""
    item_id, log_p, origin, steps, p, seasonal, months = args
    try:
        f = forecast_item_kalman(log_p, origin, steps, p, seasonal, months)
        log = {"item_id": item_id, "p_vintage": p, "p_used": int(f.p.iloc[0]),
               "seasonal_used": bool(f.seasonal.iloc[0]), "mu": float(f.mu.iloc[0]),
               "n_months_collected": len(months), "note": ""}
        return f.assign(item_id=item_id)[["origin", "target", "item_id", "log_p_hat", "log_p_latent"]], log
    except Exception as exc:   # D-53: an item whose model cannot be fitted at all drops out of the aggregate
        return None, {"item_id": item_id, "p_vintage": p, "p_used": np.nan, "seasonal_used": np.nan,
                      "mu": np.nan, "n_months_collected": len(months), "note": f"failed: {exc!r}"[:200]}


def kalman_item_forecasts(inputs: dict, orders: pd.DataFrame, origin, steps: int = FORECAST_STEPS,
                          n_jobs: int = KALMAN_N_JOBS, cache: Path | None = OOS_CACHE, force: bool = False
                          ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extended-model forecasts of all items at `origin` (origin, target, item_id, log_p_hat, log_p_latent) + log.

    inputs : `evaluate.load_inputs()` - FULL sample; cut at the origin here.
    orders : data/final/kalman_orders.csv (one row per vintage and item, D-44).
    Items without a published price at the origin get no forecast (D-30, as in T3.1).
    The result is cached per origin, so a stopped run resumes (D-51).
    """
    origin = pd.Timestamp(origin)
    f_path = log_path = None
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        f_path = cache / f"{MODEL_KALMAN}_{origin:%Y-%m}_items.csv"
        log_path = cache / f"{MODEL_KALMAN}_{origin:%Y-%m}_log.csv"
        if f_path.exists() and log_path.exists() and not force:
            return (pd.read_csv(f_path, parse_dates=["origin", "target"]),
                    pd.read_csv(log_path, parse_dates=["origin"]))

    wide = inputs["panel"].pivot(index="date", columns="item_id", values="log_p").sort_index().asfreq("MS")
    wide = wide.loc[:origin]                                     # no look-ahead: CPI known at the origin
    coll = inputs["collection"][pd.to_datetime(inputs["collection"].date) <= origin]
    o = orders_for_origin(orders, origin).set_index("item_id")  # D-44: vintage of the previous year
    jobs = []
    for item_id in wide.columns:
        s = wide[item_id]
        if item_id not in o.index or pd.isna(s.get(origin, np.nan)):
            continue                                             # D-30: not published at the origin
        months = collection_pattern(coll, item_id, origin)       # D-43: collection months of the previous year
        jobs.append((item_id, s, origin, steps, int(o.loc[item_id, "p"]), bool(o.loc[item_id, "seasonal"]),
                     months))
    if n_jobs > 1:
        with ProcessPoolExecutor(n_jobs) as pool:
            results = list(pool.map(_forecast_one, jobs, chunksize=1))
    else:
        results = [_forecast_one(j) for j in jobs]
    fc = pd.concat([f for f, _ in results if f is not None], ignore_index=True)
    log = pd.DataFrame([lg for _, lg in results]).assign(origin=origin)
    if cache is not None:
        fc.to_csv(f_path, index=False)
        log.to_csv(log_path, index=False)
    return fc, log


def run_kalman_oos(inputs: dict, orders: pd.DataFrame, origins, n_jobs: int = KALMAN_N_JOBS,
                   cache: Path | None = OOS_CACHE, force: bool = False, verbose: bool = True
                   ) -> dict[str, pd.DataFrame]:
    """Item forecasts, monthly aggregates and quarterly y-o-y (h = 1..5) of the extended model for all origins."""
    parts = {k: [] for k in ("items", "monthly", "quarterly", "log")}
    for i, origin in enumerate(origins, 1):
        t0 = time.perf_counter()
        fc, log = kalman_item_forecasts(inputs, orders, origin, n_jobs=n_jobs, cache=cache, force=force)
        fc = fc.assign(model=MODEL_KALMAN)
        monthly, quarterly = evaluate.aggregate_origin(inputs, fc, origin, MODEL_KALMAN)
        for k, v in (("items", fc), ("monthly", monthly), ("quarterly", quarterly), ("log", log)):
            parts[k].append(v)
        if verbose:
            tot = quarterly[quarterly["aggregate"] == "total"].pi_hat.round(2).tolist()
            print(f"[{i:2d}/{len(origins)}] origin {pd.Timestamp(origin):%Y-%m} {time.perf_counter() - t0:6.1f}s "
                  f"items {fc.item_id.nunique()}  total pi_hat h=1..5: {tot}", flush=True)
    return {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}


# ---------------------------------------------------------------------------
# Diebold-Mariano-West test with the Harvey-Leybourne-Newbold correction
# ---------------------------------------------------------------------------
def dmw_hln(e_bench, e_ref, h: int) -> tuple[float, float]:
    """DMW test of equal squared-error loss, HLN small-sample correction; returns (statistic, two-sided p-value).

    d_t = e_bench,t^2 - e_ref,t^2 (> 0 on average => the reference model is more accurate).
    An h-step forecast error is autocorrelated up to lag h-1 (overlapping horizons), so the long-run variance of d
    uses the autocovariances up to lag h-1 with equal weights (rectangular kernel, Diebold & Mariano 1995). If that
    estimate is not positive, the Newey-West (Bartlett) weights are used instead. HLN (1997):
    DM* = DM * sqrt((T + 1 - 2h + h(h-1)/T) / T), compared with Student t(T-1). Skill snb-arima-evaluation, D-52.
    """
    d = np.asarray(e_bench, float) ** 2 - np.asarray(e_ref, float) ** 2
    T = len(d)
    dbar = d.mean()
    dc = d - dbar
    gamma = [np.dot(dc[k:], dc[: T - k]) / T for k in range(h)]
    v = gamma[0] + 2 * sum(gamma[1:])
    if v <= 0:
        v = gamma[0] + 2 * sum((1 - k / h) * gamma[k] for k in range(1, h))
    if v <= 0:
        return np.nan, np.nan
    dm = dbar / np.sqrt(v / T)
    dm_star = dm * np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    p = 2 * stats.t.sf(abs(dm_star), df=T - 1)
    return float(dm_star), float(p)


# ---------------------------------------------------------------------------
# Table 4 in the paper's layout
# ---------------------------------------------------------------------------
def comparison_table(ev: pd.DataFrame, reference: str, benchmarks: list[str],
                     actual: str = "pi_actual") -> pd.DataFrame:
    """Long table: reference absolute RMSFE, then each benchmark's relative RMSFE and DMW-HLN p-value, per h.

    Relative RMSFE = RMSFE_benchmark / RMSFE_reference (> 1 => reference better), paper p. 10. Only origins where
    both models have a forecast enter each pair.
    """
    rows = []
    wide = ev.pivot_table(index=["origin_q", "h"], columns="model", values="pi_hat")
    act = ev.groupby(["origin_q", "h"])[actual].first()
    for h, g in wide.groupby(level="h"):
        e_ref_all = act.loc[g.index] - g[reference]
        rows.append({"row": reference, "h": h, "value": evaluate.rmsfe(e_ref_all.dropna()), "p_value": np.nan,
                     "T": int(e_ref_all.notna().sum())})
        for b in benchmarks:
            pair = pd.DataFrame({"ref": e_ref_all, "bench": act.loc[g.index] - g[b]}).dropna()
            _, p = dmw_hln(pair.bench, pair.ref, int(h))
            rows.append({"row": b, "h": h, "value": evaluate.rmsfe(pair.bench) / evaluate.rmsfe(pair.ref),
                         "p_value": p, "T": len(pair)})
    return pd.DataFrame(rows)
