"""Per-item ARIMA models with SIC lag selection and ad-hoc fallbacks (T2.2).

Skill: snb-arima-item-models. Paper pp. 5-7, eqs. (1)-(3).

Every item i gets an ARIMA(p,1,q) on its log price, i.e. an ARMA(p,q) on the monthly log change
y_t = Δlog p_t, with a constant (D-01) and - where the T2.1 diagnostics allow it (D-33) - a multiplicative
seasonal AR term at lag 12 (eq. 2):

    (1 - φ_1 L - ... - φ_p L^p)(1 - ρ L^12)(y_t - μ) = (1 + θ_1 L + ... + θ_q L^q) ε_t

The lag order (p, q) is chosen anew at every forecast origin by the Schwarz criterion of eq. (3),
SIC = log(SSE/T) + k·log(T)/T, on one common estimation sample for all candidates (AGENTS.md §7).

Estimation is by conditional least squares (CLS, D-35): the first observations of the sample are taken as
given and the sum of squared one-step residuals is minimised. That is the SSE the paper's SIC is built on.

Quarterly-collected items (D-36): their monthly index is flat between collections, so a monthly ARMA would
fit spurious dynamics. We sample the log price every 3 months at the collection months, fit the ARMA on the
3-month changes (lags 1, 2, ... in quarters = 3, 6, ... months, paper p. 6) and let the forecast change the
level only in future collection months - exactly how SFSO publishes such prices.

No look-ahead (AGENTS.md rule 1): `forecast_item` cuts the series at `origin` itself.
"""

from __future__ import annotations

import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.signal import lfilter
from statsmodels.tsa.statespace.tools import constrain_stationary_univariate, unconstrain_stationary_univariate

from arima_snb.config import (FORECAST_STEPS, INCLUDE_CONSTANT, ITEM_N_JOBS, ITEM_SAMPLE_START, MIN_SIC_OBS_MONTHLY,
                              MIN_SIC_OBS_QUARTERLY, NO_COLLECTION_TOL, P_MAX_MONTHLY, P_MAX_QUARTERLY,
                              PLAUSIBLE_PCTL, Q_MAX_MONTHLY, Q_MAX_QUARTERLY, SEASONAL_PERIOD,
                              SEASONAL_PERIOD_QUARTERLY)

MODEL_NAME = "arima182"
ROOT_MARGIN = 1.0 + 1e-4   # roots must lie outside the unit circle by at least this (stationary / invertible)
CLS_MAX_NFEV = 100         # optimiser budget per candidate; hitting it counts as a failed fit (D-35)


# ---------------------------------------------------------------------------
# Schwarz criterion and the CLS fit of one ARMA candidate
# ---------------------------------------------------------------------------
def sic(sse: float, n_obs: int, n_params: int) -> float:
    """Schwarz criterion as in the paper, eq. (3): log(SSE/T) + k*log(T)/T."""
    return float(np.log(sse / n_obs) + n_params * np.log(n_obs) / n_obs)


def ar_polynomial(phi: np.ndarray, rho: float | None, period: int) -> np.ndarray:
    """Coefficients [1, A_1, ..., A_L] of the full AR polynomial (1 - φ(L))(1 - ρL^s) (eq. 2, multiplicative)."""
    nonseasonal = np.r_[1.0, -np.asarray(phi, dtype=float)]
    if rho is None:
        return nonseasonal
    seasonal = np.zeros(period + 1)
    seasonal[0], seasonal[period] = 1.0, -rho
    return np.convolve(nonseasonal, seasonal)


def _unpack(params: np.ndarray, p: int, q: int, seasonal: bool, transformed: bool = True):
    """Split a parameter vector into μ, φ, ρ, θ.

    The optimiser works on unconstrained values; `transformed=True` maps them to coefficients of a stationary
    AR part and an invertible MA part (partial-autocorrelation transform of Monahan 1984, as in statsmodels'
    SARIMAX). Every candidate therefore stays causal and invertible (paper App. C) and CLS cannot drift into
    the non-invertible region, where conditional residuals explode.
    """
    mu = params[0] if INCLUDE_CONSTANT else 0.0
    i = 1 if INCLUDE_CONSTANT else 0
    phi = params[i:i + p]
    rho = params[i + p] if seasonal else None
    theta = params[i + p + seasonal:i + p + seasonal + q]
    if transformed:
        phi = constrain_stationary_univariate(phi) if p else phi
        rho = float(np.tanh(rho)) if seasonal else None
        theta = -constrain_stationary_univariate(theta) if q else theta
    return mu, phi, rho, theta


def _to_unconstrained(phi: np.ndarray) -> np.ndarray:
    """Inverse transform for start values; shrinks a non-stationary OLS start towards zero first."""
    phi = np.asarray(phi, dtype=float)
    while not _roots_ok(np.r_[1.0, -phi]):
        phi = 0.8 * phi
    return unconstrain_stationary_univariate(phi)


def cls_residuals(params, y, p, q, seasonal, period, start) -> np.ndarray:
    """One-step residuals ε_t for t >= start, conditional on y_0..y_{start-1} and ε_t = 0 before `start`.

    A(L)(y_t - μ) = Θ(L)ε_t  ⇒  ε = Θ(L)^{-1} A(L)(y - μ). Both filters are applied with scipy's lfilter;
    `start` >= the AR order, so the AR part never uses pre-sample zeros. `params` are unconstrained.
    """
    mu, phi, rho, theta = _unpack(params, p, q, seasonal)
    a = ar_polynomial(phi, rho, period)
    u = lfilter(a, [1.0], y - mu)[start:]
    return lfilter([1.0], np.r_[1.0, theta], u) if q else u


def _roots_ok(poly: np.ndarray) -> bool:
    """True if all roots of 1 + c_1 z + ... + c_n z^n lie outside the unit circle."""
    poly = np.trim_zeros(np.asarray(poly, dtype=float), "b")
    if len(poly) <= 1:
        return True
    return bool(np.all(np.abs(np.roots(poly[::-1])) > ROOT_MARGIN))


def fit_cls(y: np.ndarray, p: int, q: int, seasonal: bool, period: int, start: int) -> dict | None:
    """Conditional least squares fit of one candidate (D-35). Returns None if the fit fails.

    Start values: μ = sample mean, φ by OLS of y on its p lags, ρ = θ = 0. The transform in `_unpack` keeps
    AR stationary and MA invertible; a candidate whose optimisation fails (or ends with a root numerically on
    the unit circle) is dropped from the SIC grid by the caller (D-11).
    """
    y = np.asarray(y, dtype=float)
    mu0 = y.mean()
    phi0 = np.zeros(p)
    if p:
        z = y[start:] - mu0
        X = np.column_stack([y[start - j:len(y) - j] - mu0 for j in range(1, p + 1)])
        phi0 = np.linalg.lstsq(X, z, rcond=None)[0]
    x0 = np.r_[[mu0] if INCLUDE_CONSTANT else [], _to_unconstrained(phi0) if p else [], [0.0] * seasonal,
               np.zeros(q)]
    args = (y, p, q, seasonal, period, start)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = least_squares(cls_residuals, x0, args=args, method="lm", max_nfev=CLS_MAX_NFEV)
    except Exception:  # noqa: BLE001 - any numerical failure means: drop this candidate
        return None
    if not res.success or not np.all(np.isfinite(res.x)):
        return None
    mu, phi, rho, theta = _unpack(res.x, p, q, seasonal)
    if not (_roots_ok(ar_polynomial(phi, rho, period)) and _roots_ok(np.r_[1.0, theta])):
        return None
    e = cls_residuals(res.x, *args)
    n = len(e)
    k = len(res.x)
    sse = float(e @ e)
    if sse <= 0:
        return None
    return {"p": p, "q": q, "seasonal": seasonal, "params": res.x, "resid": e, "sse": sse,
            "t_eff": n, "k": k, "sic": sic(sse, n, k)}


def forecast_arma(fit: dict, y: np.ndarray, period: int, steps: int) -> np.ndarray:
    """Iterate the fitted ARMA forward `steps` periods (future ε = 0; in-sample ε for the MA terms)."""
    mu, phi, rho, theta = _unpack(fit["params"], fit["p"], fit["q"], fit["seasonal"])
    a = ar_polynomial(phi, rho, period)
    w = list(np.asarray(y, dtype=float) - mu)
    e = list(np.zeros(len(y) - len(fit["resid"]))) + list(fit["resid"])
    out = []
    for _ in range(steps):
        ar = -sum(a[i] * w[-i] for i in range(1, len(a)))
        ma = sum(theta[j - 1] * e[-j] for j in range(1, len(theta) + 1))
        w.append(ar + ma)
        e.append(0.0)
        out.append(w[-1] + mu)
    return np.array(out)


# ---------------------------------------------------------------------------
# SIC grid search on a common sample, with the short-sample guard (D-37)
# ---------------------------------------------------------------------------
def select_order(y: np.ndarray, seasonal: bool, quarterly: bool) -> dict:
    """Fit every (p, q) of the D-02 grid on one common sample and return the SIC-minimising fit.

    Grid (D-02, D-36): monthly p 0-12, q 0-2; quarterly p 0-4, q 0-2 (in quarters). Guard (D-37): the common
    sample, which drops the first p_max + s observations for every candidate, keeps at least MIN_SIC_OBS obs;
    otherwise p_max shrinks, and the seasonal term is dropped if even p = 0 does not fit. A seasonal model has
    p <= s - 1, because lag s cannot be identified in both φ(L) and the seasonal factor.
    """
    period = SEASONAL_PERIOD_QUARTERLY if quarterly else SEASONAL_PERIOD
    p_cap = P_MAX_QUARTERLY if quarterly else P_MAX_MONTHLY
    q_max = Q_MAX_QUARTERLY if quarterly else Q_MAX_MONTHLY
    min_obs = MIN_SIC_OBS_QUARTERLY if quarterly else MIN_SIC_OBS_MONTHLY
    T = len(y)
    notes = []
    if seasonal and T - period < min_obs:
        seasonal = False
        notes.append("seasonal term dropped: sample too short")
    s = period if seasonal else 0
    if seasonal:
        p_cap = min(p_cap, period - 1)
    p_max = min(p_cap, T - min_obs - s)
    info = {"p_max_eff": p_max, "q_max": q_max, "period": period, "seasonal_used": seasonal,
            "n_candidates": 0, "n_failed": 0, "notes": notes}
    if p_max < 0:
        info["notes"].append("sample too short for any ARMA")
        return {"fit": None, **info}
    start = p_max + s
    best = None
    for p in range(p_max + 1):
        for q in range(q_max + 1):
            info["n_candidates"] += 1
            f = fit_cls(y, p, q, seasonal, period, start)
            if f is None:
                info["n_failed"] += 1
                continue
            if best is None or f["sic"] < best["sic"]:
                best = f
    return {"fit": best, **info}


# ---------------------------------------------------------------------------
# Ad-hoc rules (paper p. 7)
# ---------------------------------------------------------------------------
def adhoc_path(log_p: pd.Series, method: str, steps: int) -> np.ndarray:
    """Forecast path of log prices for the ad-hoc rules (paper p. 7).

    adhoc_last: last value carried forward; adhoc_avg_mom: + average Δlog of the last 12 months per month;
    adhoc_avg_yoy: + 1/12 of the average 12-month log change over the available sample per month.
    """
    last = log_p.iloc[-1]
    h = np.arange(1, steps + 1)
    if method == "adhoc_last" or len(log_p) < 2:
        return np.full(steps, last)
    if method == "adhoc_avg_mom":
        g = log_p.diff().iloc[-12:].mean()
    elif method == "adhoc_avg_yoy":
        yoy = log_p.diff(12).dropna()
        g = yoy.mean() / 12 if len(yoy) else log_p.diff().mean()
    else:
        raise ValueError(method)
    return last + g * h


def plausible(log_p: pd.Series, path: np.ndarray) -> bool:
    """D-11: the implied 12-month change lies within the [1st, 99th] percentile of the item's own past changes."""
    hist = log_p.diff(12).dropna()
    if len(hist) < 12 or len(path) < 12:
        return True
    lo, hi = np.percentile(hist, PLAUSIBLE_PCTL)
    change = path[11] - log_p.iloc[-1]
    return bool(lo - 1e-12 <= change <= hi + 1e-12)


# ---------------------------------------------------------------------------
# Quarterly-collected items (D-36)
# ---------------------------------------------------------------------------
def last_collection_month(log_p: pd.Series, origin: pd.Timestamp, pattern: list[int] | None) -> pd.Timestamp:
    """Latest collection month in (origin-2, ..., origin): from last year's calendar pattern (D-28), else the
    latest month with an observed price change, else the origin itself."""
    window = [origin - pd.DateOffset(months=k) for k in range(3)]
    if pattern:
        hits = [m for m in window if m.month in pattern]
        if hits:
            return hits[0]
    d = log_p.diff().abs()
    for m in window:
        if m in d.index and d[m] >= NO_COLLECTION_TOL:
            return m
    return origin


def quarterly_series(log_p: pd.Series, anchor: pd.Timestamp) -> pd.Series:
    """Log price every 3 months ending at the anchor collection month."""
    x = log_p.loc[:anchor]
    return x.iloc[::-1].iloc[::3].iloc[::-1]


# ---------------------------------------------------------------------------
# One item, one origin
# ---------------------------------------------------------------------------
def forecast_item(log_p: pd.Series, spec: pd.Series, origin, steps: int = FORECAST_STEPS,
                  pattern: list[int] | None = None,
                  crude_chf_daily: pd.Series | None = None) -> tuple[pd.DataFrame, dict]:
    """Forecast one item's log price for the `steps` months after `origin`, using data up to `origin` only.

    `spec` = the item's row of item_specs.csv valid at `origin` (`diagnostics.specs_for_origin`, D-31).
    `pattern` = collection months of the year before the origin (`panel.collection_pattern`, D-28), used for
    quarterly items. Returns the forecast (target, log_p_hat) and a log dict (method, order, SIC, notes).
    Oil (`ecm`) items use the error-correction model of `special.forecast_oil_item` (T2.3) when the daily
    crude price in CHF is passed as `crude_chf_daily`; without it they get a plain ARIMA, which is the
    "Oil products (ARIMA)" benchmark of paper Table 3. Rent (`rent`) items get a plain ARIMA until T2.4.
    """
    origin = pd.Timestamp(origin)
    if spec["method"] == "ecm" and crude_chf_daily is not None:
        from arima_snb.special import forecast_oil_item   # T2.3: cuts prices and crude at the origin itself
        return forecast_oil_item(log_p, crude_chf_daily, origin, steps)
    x = log_p.loc[pd.Timestamp(ITEM_SAMPLE_START):origin].dropna()   # paper sample from May 2000 (p. 5)
    targets = pd.date_range(origin + pd.DateOffset(months=1), periods=steps, freq="MS")
    log = {"spec_method": spec["method"], "method": spec["method"], "p": np.nan, "q": np.nan,
           "seasonal": False, "sic": np.nan, "t_eff": np.nan, "p_max_eff": np.nan, "n_candidates": 0,
           "n_failed": 0, "quarterly": False, "note": ""}
    if x.empty or x.index[-1] != origin:
        log.update(method="none", note="no observation at origin")
        return pd.DataFrame(columns=["target", "log_p_hat"]), log

    method = spec["method"]
    quarterly = bool(spec["quarterly_lags"]) or (method in ("ecm", "rent") and spec["collection_freq"] == "quarterly")
    log["quarterly"] = quarterly
    if method in ("ecm", "rent"):
        log["note"] = f"plain ARIMA for {method} (no special model)"
        method = "arima"

    path = None
    if method == "arima":
        if quarterly:
            anchor = last_collection_month(x, origin, pattern)
            yq = quarterly_series(x, anchor).diff().dropna().to_numpy()
            sel = select_order(yq, bool(spec["seasonal"]), quarterly=True)
        else:
            y = x.diff().dropna().to_numpy()
            sel = select_order(y, bool(spec["seasonal"]), quarterly=False)
        fit = sel["fit"]
        log.update(p_max_eff=sel["p_max_eff"], n_candidates=sel["n_candidates"], n_failed=sel["n_failed"])
        notes = list(sel["notes"])
        if fit is None:
            notes.append("no ARMA candidate could be fitted -> adhoc_avg_yoy")
            method = "adhoc_avg_yoy"
        else:
            log.update(p=fit["p"], q=fit["q"], seasonal=fit["seasonal"], sic=fit["sic"], t_eff=fit["t_eff"])
            if quarterly:
                # Quarterly changes land in future collection months anchor+3, anchor+6, ...; the level is
                # carried forward in between (D-36).
                n_q = int(np.ceil((steps + 2) / 3)) + 1
                dq = forecast_arma(fit, yq, sel["period"], n_q)
                coll_months = [anchor + pd.DateOffset(months=3 * (k + 1)) for k in range(n_q)]
                path = np.array([x.iloc[-1] + dq[[m <= t for m in coll_months]].sum() for t in targets])
            else:
                path = x.iloc[-1] + np.cumsum(forecast_arma(fit, y, sel["period"], steps))
            if not plausible(x, path):   # D-11
                notes.append("implausible 12-month change -> adhoc_avg_yoy")
                method, path = "adhoc_avg_yoy", None
        log["note"] = "; ".join(filter(None, [log["note"], *notes]))
    if path is None:
        path = adhoc_path(x, method, steps)
    log["method"] = method
    return pd.DataFrame({"target": targets, "log_p_hat": path}), log


# ---------------------------------------------------------------------------
# All items at one origin
# ---------------------------------------------------------------------------
def _forecast_one(args):
    """Worker for one item (top-level so that it can run in a separate process)."""
    item_id, x, spec, origin, steps, pattern, crude = args
    f, lg = forecast_item(x, spec, origin, steps, pattern, crude)
    f.insert(0, "item_id", item_id)
    return f, {"item_id": item_id, **lg}


def forecast_items(panel: pd.DataFrame, specs: pd.DataFrame, collection: pd.DataFrame, origin,
                   steps: int = FORECAST_STEPS, n_jobs: int = ITEM_N_JOBS,
                   crude_chf_daily: pd.Series | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Forecast every item of `specs` (the vintage valid at `origin`) and return (forecasts, order log).

    crude_chf_daily: daily crude price in CHF (`special.load_crude_chf_daily()`); given -> oil items use the
    ECM (T2.3), None -> plain ARIMA for oil items (Table 3 benchmark). It is cut at the paper's p. 12
    information cut-off inside the oil model, and here already at that cut-off for safety.

    forecasts follow AGENTS.md §4: origin, target, item_id, model, log_p_hat. The log has one row per item.
    Items are independent, so they run in `n_jobs` parallel processes (1 = sequential).
    """
    from arima_snb.panel import collection_pattern   # local import: panel pulls in the data loaders

    origin = pd.Timestamp(origin)
    wide = panel.pivot(index="date", columns="item_id", values="log_p").sort_index()
    wide = wide.loc[:origin]   # nothing after the origin ever reaches the models
    coll = collection[pd.to_datetime(collection.date) <= origin]
    if crude_chf_daily is not None:
        from arima_snb.special import crude_info_cutoff
        crude_chf_daily = crude_chf_daily[crude_chf_daily.index < crude_info_cutoff(origin)]
    jobs, logs = [], []
    for spec in specs.itertuples(index=False):
        spec = pd.Series(spec._asdict())
        if spec.item_id not in wide:
            logs.append({"item_id": spec.item_id, "method": "none", "note": "item not in panel"})
            continue
        pattern = collection_pattern(coll, spec.item_id, origin)
        crude = crude_chf_daily if spec.method == "ecm" else None
        jobs.append((spec.item_id, wide[spec.item_id], spec, origin, steps, pattern, crude))
    if n_jobs > 1:
        with ProcessPoolExecutor(max_workers=n_jobs) as pool:
            results = list(pool.map(_forecast_one, jobs, chunksize=4))
    else:
        results = [_forecast_one(j) for j in jobs]
    fc = [f for f, _ in results]
    logs += [lg for _, lg in results]
    out = pd.concat(fc, ignore_index=True)
    out.insert(0, "origin", origin)
    out["model"] = MODEL_NAME
    log = pd.DataFrame(logs)
    log.insert(0, "origin", origin)
    return out[["origin", "target", "item_id", "model", "log_p_hat"]], log
