"""Pseudo-out-of-sample evaluation: forecast loop, benchmarks, RMSFE, DMW test (T3.x, T4.2, T5.x).

Skill: snb-arima-evaluation. Paper pp. 8-12.

T3.1 - the pseudo-out-of-sample engine for the disaggregate model
------------------------------------------------------------------
At every quarterly forecast origin (last known CPI month = 2nd month of the quarter, paper p. 8, D-04) we pretend
to be an SNB economist at the quarterly forecasting meeting and

1. take the item specifications of the latest annual vintage (D-31, `diagnostics.specs_for_origin`),
2. re-estimate every item model on all data from May 2000 up to the origin (expanding window, D-03) and
   re-select its lag order by SIC (paper p. 7) - `item_models.forecast_items`,
3. aggregate the item forecasts with the weights known at the origin to total CPI (D-13, D-29, D-30, D-45),
4. turn the monthly index path into quarterly y-o-y inflation for h = 1..5 (h = 1 = current quarter).

Two model variants come out of ONE set of item fits per origin (D-50):

* ``arima182``         - plain ARIMA for every item, also oil products and rents. This is the paper's pseudo-OOS
                         "ARIMA(182)" of Table 2 (p. 11: "oil and rents ... ARIMA") and the benchmark of Table 4.
* ``arima182_special`` - the same, but oil products use the error-correction model (T2.3) and rents the
                         mortgage-rate model (T2.4, plugs in through `special_item_forecasts` once it exists).
                         Closest analogue of the paper's "real-time ARIMA" (Table 1), whose vintages are not public.

The expensive part (182 ARIMA fits) is cached per origin in data/interim/oos/, so an interrupted run resumes and
the special models can be swapped in later without refitting.

No look-ahead (AGENTS.md rule 1): `forecast_origin` gets the full data and cuts everything itself - CPI and
collection flags at the origin, crude oil before the 1st of the month after the origin (p. 12), weights of years
after the origin year are dropped (D-13), specs from the vintage of the previous year (D-31).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from arima_snb import aggregate
from arima_snb.config import (EVAL_END, EVAL_START, FINAL, FORECAST_STEPS, HORIZONS, INTERIM, OOS_N_JOBS,
                              MONTHS_KNOWN_IN_QUARTER)
from arima_snb.diagnostics import specs_for_origin
from arima_snb.item_models import forecast_item, forecast_items

MODEL_PLAIN = "arima182"            # Table 2 / Table 4 benchmark: plain ARIMA for oil and rents
MODEL_SPECIAL = "arima182_special"  # oil ECM + rent model: real-time-ARIMA analogue (Table 1), D-50
OOS_CACHE = INTERIM / "oos"


# ---------------------------------------------------------------------------
# Origins and inputs
# ---------------------------------------------------------------------------
def evaluation_origins(start: str = EVAL_START, end: str = EVAL_END) -> list[pd.Timestamp]:
    """Last known CPI month of every quarter from `start` to `end`: Feb, May, Aug, Nov (paper p. 8, D-04)."""
    quarters = pd.period_range(start, end, freq="Q")
    return [q.start_time + pd.DateOffset(months=MONTHS_KNOWN_IN_QUARTER - 1) for q in quarters]


def official_cpi() -> pd.Series:
    """Official headline CPI (SNB cube plkopr, Dec 2010 = 100) - the evaluation target (paper p. 10, D-47)."""
    from arima_snb import io

    cube = io.read_snb_cube(io.find_raw("snb-data-plkopr-*.csv"), "plkopr")
    return cube[cube.variable == "plkopr_LD2010100"].set_index("date")["value"].astype(float).sort_index()


def load_inputs(with_crude: bool = True) -> dict:
    """All data the engine needs, FULL sample (cut per origin inside `forecast_origin`)."""
    panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    inputs = {
        "panel": panel,
        "index_wide": panel.pivot(index="date", columns="item_id", values="index").asfreq("MS"),
        "specs": pd.read_csv(FINAL / "item_specs.csv"),
        "collection": pd.read_csv(FINAL / "collection.csv", parse_dates=["date"]),
        "weights": pd.read_csv(FINAL / "weights.csv"),
        "items": pd.read_csv(FINAL / "items.csv"),
        "crude": None,
        "mortgage": None,
    }
    if with_crude:
        from arima_snb.special import load_crude_chf_daily
        inputs["crude"] = load_crude_chf_daily()
    inputs["mortgage"] = _load_mortgage()
    return inputs


def _load_mortgage() -> pd.Series | None:
    """Monthly mortgage rate for the rent model (T2.4), or None while T2.4 has not provided its loader."""
    from arima_snb import special

    loader = getattr(special, "load_mortgage_rate", None)
    if loader is None:
        return None
    try:
        return loader()
    except (NotImplementedError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# Special models (oil ECM, rents) - swapped into the plain item forecasts
# ---------------------------------------------------------------------------
def _rent_forecast(log_p: pd.Series, mortgage: pd.Series | None, origin: pd.Timestamp, steps: int):
    """Hook for the T2.4 rent model. Returns (forecast frame, log) or None while T2.4 is not available.

    Uses ``special.forecast_rent(log_rent, mortgage_monthly, origin, steps)`` -> (DataFrame[target, log_p_hat],
    log dict), which cuts the rent series at the origin and the mortgage rate before the 1st day of the
    3rd quarter month itself (paper p. 12). Until T2.4 lands it raises NotImplementedError -> plain ARIMA.
    """
    from arima_snb import special

    if mortgage is None:
        return None
    try:
        return special.forecast_rent(log_p, mortgage, origin, steps)
    except NotImplementedError:
        return None


def special_item_forecasts(inputs: dict, specs: pd.DataFrame, origin, steps: int = FORECAST_STEPS
                           ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Forecasts of the special-model items at `origin`: oil products by ECM (T2.3), rents by T2.4's model.

    Returns (forecasts origin/target/item_id/log_p_hat, log). Items whose special model is not available
    (rents until T2.4 lands) are absent, so they keep their plain-ARIMA forecast.
    """
    origin = pd.Timestamp(origin)
    wide = inputs["panel"].pivot(index="date", columns="item_id", values="log_p").sort_index().loc[:origin]
    fcs, logs = [], []
    for spec in specs[specs.method.isin(["ecm", "rent"])].itertuples(index=False):
        spec = pd.Series(spec._asdict())
        if spec.item_id not in wide:
            continue
        if spec.method == "ecm":
            if inputs.get("crude") is None:
                continue
            res = forecast_item(wide[spec.item_id], spec, origin, steps, crude_chf_daily=inputs["crude"])
        else:
            res = _rent_forecast(wide[spec.item_id], inputs.get("mortgage"), origin, steps)
            if res is None:
                logs.append({"item_id": spec.item_id, "method": "arima", "note": "rent model pending (T2.4)"})
                continue
        f, lg = res
        fcs.append(f.assign(item_id=spec.item_id))
        logs.append({"item_id": spec.item_id, **lg})
    fc = pd.concat(fcs, ignore_index=True) if fcs else pd.DataFrame(columns=["target", "log_p_hat", "item_id"])
    fc.insert(0, "origin", origin)
    return fc[["origin", "target", "item_id", "log_p_hat"]], pd.DataFrame(logs)


def swap_items(base: pd.DataFrame, replacement: pd.DataFrame) -> pd.DataFrame:
    """Item forecasts `base` with the rows of every item in `replacement` replaced."""
    keep = base[~base.item_id.isin(replacement.item_id.unique())]
    return pd.concat([keep, replacement], ignore_index=True)


# ---------------------------------------------------------------------------
# One origin
# ---------------------------------------------------------------------------
def plain_item_forecasts(inputs: dict, origin, n_jobs: int = OOS_N_JOBS, cache: Path | None = OOS_CACHE,
                         force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Plain-ARIMA forecasts of all items at `origin` (the expensive step), cached per origin.

    Oil and rent items get the plain ARIMA too (crude_chf_daily=None): Table 2's ARIMA(182) (paper p. 11).
    """
    origin = pd.Timestamp(origin)
    f_path = log_path = None
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        f_path = cache / f"{MODEL_PLAIN}_{origin:%Y-%m}_items.csv"
        log_path = cache / f"{MODEL_PLAIN}_{origin:%Y-%m}_log.csv"
        if f_path.exists() and log_path.exists() and not force:
            return (pd.read_csv(f_path, parse_dates=["origin", "target"]),
                    pd.read_csv(log_path, parse_dates=["origin"]))
    specs = specs_for_origin(inputs["specs"], origin)   # D-31
    fc, log = forecast_items(inputs["panel"], specs, inputs["collection"], origin, n_jobs=n_jobs)
    if cache is not None:
        fc.to_csv(f_path, index=False)
        log.to_csv(log_path, index=False)
    return fc, log


def aggregate_origin(inputs: dict, item_fc: pd.DataFrame, origin, model: str
                     ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Monthly aggregate forecasts (after the origin) and quarterly y-o-y forecasts for h = 1..5 (T2.5)."""
    origin = pd.Timestamp(origin)
    agg = aggregate.forecast_aggregates(inputs["index_wide"], inputs["weights"], inputs["items"], item_fc, origin)
    agg = agg[agg.target >= pd.Timestamp(f"{origin.year - 1}-01-01")]   # history needed for y-o-y of h = 5
    q = aggregate.forecast_quarterly_yoy(agg, HORIZONS).assign(model=model)
    return agg[agg.target > origin].assign(model=model), q


def forecast_origin(inputs: dict, origin, n_jobs: int = OOS_N_JOBS, cache: Path | None = OOS_CACHE,
                    force: bool = False) -> dict:
    """Everything for one origin: item forecasts, monthly aggregates and quarterly y-o-y of both variants."""
    origin = pd.Timestamp(origin)
    plain, log = plain_item_forecasts(inputs, origin, n_jobs, cache, force)
    special, special_log = special_item_forecasts(inputs, specs_for_origin(inputs["specs"], origin), origin)
    out = {"log": log, "special_log": special_log.assign(origin=origin)}
    for model, items_fc in [(MODEL_PLAIN, plain), (MODEL_SPECIAL, swap_items(plain, special))]:
        items_fc = items_fc.assign(model=model)
        monthly, quarterly = aggregate_origin(inputs, items_fc, origin, model)
        out[model] = {"items": items_fc, "monthly": monthly, "quarterly": quarterly}
    return out


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------
def quarterly_actuals(inputs: dict, official: pd.Series) -> pd.DataFrame:
    """Actual quarterly y-o-y inflation: official CPI (the target, p. 10) and the 182-item re-aggregation."""
    total_182 = aggregate.aggregate_index(inputs["index_wide"], inputs["weights"])
    return pd.DataFrame({"pi_actual": aggregate.quarterly_yoy(official),
                         "pi_actual_182": aggregate.quarterly_yoy(total_182)})


def run_pseudo_oos(inputs: dict, origins, n_jobs: int = OOS_N_JOBS, cache: Path | None = OOS_CACHE,
                   force: bool = False, verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Run `forecast_origin` for every origin and stack the results.

    Returns frames 'items', 'monthly', 'quarterly' (both model variants, all aggregates) and 'log'.
    """
    parts = {k: [] for k in ("items", "monthly", "quarterly", "log", "special_log")}
    for i, origin in enumerate(origins, 1):
        t0 = time.perf_counter()
        res = forecast_origin(inputs, origin, n_jobs, cache, force)
        for model in (MODEL_PLAIN, MODEL_SPECIAL):
            for k in ("items", "monthly", "quarterly"):
                parts[k].append(res[model][k])
        parts["log"].append(res["log"])
        parts["special_log"].append(res["special_log"])
        if verbose:
            tot = res[MODEL_PLAIN]["quarterly"]
            tot = tot[tot["aggregate"] == "total"].pi_hat.round(2).tolist()
            print(f"[{i:2d}/{len(origins)}] origin {pd.Timestamp(origin):%Y-%m} "
                  f"{time.perf_counter() - t0:6.1f}s  total pi_hat h=1..5: {tot}", flush=True)
    return {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}


def eval_table(quarterly: pd.DataFrame, actuals: pd.DataFrame, aggregate_name: str = "total") -> pd.DataFrame:
    """Long evaluation frame of AGENTS.md §4: origin_q, h, target_q, model, pi_hat, pi_actual (+ pi_actual_182)."""
    q = quarterly[quarterly["aggregate"] == aggregate_name].copy()
    q["target_q"] = q.target_q.astype(str)
    act = actuals.copy()
    act.index = act.index.astype(str)
    q = q.join(act, on="target_q")
    return q[["origin_q", "h", "target_q", "model", "pi_hat", "pi_actual", "pi_actual_182"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Loss and tests
# ---------------------------------------------------------------------------
def rmsfe(errors: pd.Series) -> float:
    """Root mean squared forecast error (paper p. 10)."""
    return float(np.sqrt(np.mean(np.square(errors))))


def rmsfe_by_h(ev: pd.DataFrame, actual: str = "pi_actual") -> pd.DataFrame:
    """RMSFE per model (rows) and horizon (columns) over all forecasts with an actual value; plus counts T."""
    ev = ev.dropna(subset=["pi_hat", actual])
    err = ev[actual] - ev.pi_hat
    return ev.assign(err=err).groupby(["model", "h"]).err.agg(rmsfe).unstack("h")


def dmw_test(e_bench: pd.Series, e_ref: pd.Series, h: int) -> tuple[float, float]:
    """Diebold-Mariano-West test with the Harvey-Leybourne-Newbold correction; returns (statistic, p-value)."""
    raise NotImplementedError("T3.3")
