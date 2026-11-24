"""Special models: oil-products error-correction model and rent model (T2.3-T2.4).

Skill: snb-arima-oil-rent. Paper p. 7 (oil, rents) and p. 12 (information set of the exogenous data).

The file has two separate sections: A. oil products (T2.3), B. rents (T2.4).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from arima_snb.config import (FORECAST_STEPS, OIL_CRUDE_SERIES, OIL_FIRST_DAYS, OIL_FX_SERIES, OIL_K_MAX,
                              OIL_M_MAX, OIL_SAMPLE_START, OIL_WINDOW_DAYS, OIL_X_RULE)


# ===========================================================================
# A. OIL PRODUCTS - error-correction model (T2.3, paper p. 7, decision D-14)
# ===========================================================================
# The CPI oil items (heating oil i100, fuels i130) follow the crude oil price in Swiss francs almost
# one-for-one in the long run. The paper therefore models each item with an error-correction model (ECM):
#
#   long run  (Engle-Granger step 1, OLS):   p_t = a + b·x_t + u_t
#   short run (step 2, OLS):                 Δp_t = c + γ·u_{t-1} + Σ_{i=0..k} β_i Δx_{t-i} + Σ_{j=1..m} α_j Δp_{t-j} + e_t
#
# p_t = log CPI item index, x_t = log(Brent in USD × CHF per USD). γ < 0 pulls the item back to its long-run
# relation with crude; β_0 is the immediate pass-through of a crude price change.
#
# Timing (D-14 rev.): BFS collects oil prices in the first days of month t, so the monthly crude value that
# belongs to month t is x_t = log of the average of the last OIL_WINDOW_DAYS (10) daily prices BEFORE the 1st
# of month t. Information set (paper p. 12): at an origin in the 2nd month of a quarter, crude data are known
# up to the first day of the 3rd month, so x for the month after the origin is fully known -> the ECM nowcasts
# that month with the actual crude move. Beyond it, crude in CHF stays constant at the average of the last
# 10 daily prices (paper p. 7) = that same x, i.e. Δx = 0 afterwards.

OIL_MODEL_NAME = "oil_ecm"


def load_crude_chf_daily() -> pd.Series:
    """Daily Brent crude price in CHF per barrel = Brent (USD, FRED) × USDCHF (CHF per USD, FRED), D-14.

    Only days on which both series are quoted are kept (US and UK holidays drop out).
    """
    from arima_snb import io   # local import: keeps the model code free of file access

    crude = io.read_fred(io.find_raw(f"fred_{OIL_CRUDE_SERIES}_*.csv")).set_index("date")["value"]
    fx = io.read_fred(io.find_raw(f"fred_{OIL_FX_SERIES}_*.csv")).set_index("date")["value"]
    both = pd.concat([crude, fx], axis=1, join="inner").dropna()
    return (both.iloc[:, 0] * both.iloc[:, 1]).rename("crude_chf").sort_index()


def crude_info_cutoff(origin) -> pd.Timestamp:
    """First day of the month after the origin: crude data dated strictly before it are known (paper p. 12)."""
    return pd.Timestamp(origin) + pd.DateOffset(months=1)


def monthly_crude(daily: pd.Series, first_month, last_month, window: int = OIL_WINDOW_DAYS,
                  rule: str = OIL_X_RULE) -> pd.Series:
    """Monthly log crude price in CHF x_t from daily prices (D-14 rev.).

    rule "before":     mean of the last `window` daily prices dated before the 1st of month t.
    rule "first_days": mean of the first OIL_FIRST_DAYS daily prices of month t (closer to the collection days).
    A month whose window is not complete in `daily` (the data are cut at the information cut-off) gets the
    mean of the last `window` available daily prices - the paper's "constant at the average of the last 10
    daily observations" (p. 7). Callers must cut `daily` first (see forecast_oil_item).
    """
    months = pd.date_range(pd.Timestamp(first_month), pd.Timestamp(last_month), freq="MS")
    vals = daily.to_numpy()
    tail = np.log(vals[-window:].mean())
    start = daily.index.searchsorted(months, side="left")   # number of days strictly before the 1st of month t
    out = []
    for m, n in zip(months, start):
        if rule == "before":
            out.append(np.log(vals[n - window:n].mean()) if n >= window else np.nan)
        elif rule == "first_days":
            if n + OIL_FIRST_DAYS < len(vals):      # the first days of month t are observed (and data go on)
                n_end = daily.index.searchsorted(m + pd.DateOffset(months=1), side="left")
                out.append(np.log(vals[n:n + OIL_FIRST_DAYS].mean()) if n_end - n >= OIL_FIRST_DAYS else np.nan)
            else:                                   # window cut off by the information set -> last 10 days
                out.append(tail)
        else:
            raise ValueError(rule)
    return pd.Series(out, index=months, name="x")


def _ols(y: np.ndarray, X: np.ndarray) -> dict:
    """OLS with classical standard errors."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    s2 = resid @ resid / (n - k)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return {"beta": beta, "se": se, "resid": resid, "sse": float(resid @ resid), "n": n}


def _ecm_design(dp: np.ndarray, dx: np.ndarray, u_lag: np.ndarray, k: int, m: int, start: int):
    """Regressors of the short-run equation for rows start..T-1: [1, u_{t-1}, Δx_t..Δx_{t-k}, Δp_{t-1}..Δp_{t-m}]."""
    T = len(dp)
    rows = range(start, T)
    cols = [np.ones(T - start), u_lag[start:]]
    cols += [dx[start - i:T - i] for i in range(k + 1)]
    cols += [dp[start - j:T - j] for j in range(1, m + 1)]
    return np.column_stack(cols), dp[list(rows)]


def fit_oil_ecm(log_p: pd.Series, x: pd.Series) -> dict:
    """Engle-Granger two-step ECM with short-run lags k, m in 0..3 chosen by SIC on a common sample (D-14).

    log_p and x: monthly series on the same dates (estimation sample, both up to the origin).
    """
    from arima_snb.item_models import sic   # same Schwarz criterion as the item ARIMAs (eq. 3)

    df = pd.concat([log_p.rename("p"), x.rename("x")], axis=1).dropna()
    # Step 1: long-run relation by OLS
    lr = _ols(df.p.to_numpy(), np.column_stack([np.ones(len(df)), df.x.to_numpy()]))
    a, b = lr["beta"]
    u = df.p - a - b * df.x

    # Step 2: short-run ECM on first differences; all candidates use the same rows (AGENTS.md §7)
    dp = df.p.diff().to_numpy()
    dx = df.x.diff().to_numpy()
    u_lag = u.shift(1).to_numpy()
    start = 1 + max(OIL_K_MAX, OIL_M_MAX)   # first row with all lags of the largest candidate defined
    best = None
    for k in range(OIL_K_MAX + 1):
        for m in range(OIL_M_MAX + 1):
            X, y = _ecm_design(dp, dx, u_lag, k, m, start)
            f = _ols(y, X)
            f.update(k=k, m=m, sic=sic(f["sse"], f["n"], X.shape[1]))
            if best is None or f["sic"] < best["sic"]:
                best = f
    names = ["c", "gamma"] + [f"beta_{i}" for i in range(best["k"] + 1)] + [f"alpha_{j}" for j in range(1, best["m"] + 1)]
    return {"a": a, "b": b, "se_b": lr["se"][1], "u": u, "k": best["k"], "m": best["m"], "sic": best["sic"],
            "params": dict(zip(names, best["beta"])), "se": dict(zip(names, best["se"])),
            "t_eff": best["n"], "sample_start": df.index[0], "sample_end": df.index[-1]}


def ecm_path(fit: dict, p_hist: np.ndarray, x_hist: np.ndarray, x_future: np.ndarray) -> np.ndarray:
    """Iterate the ECM forward: future log prices given the known history and the assumed crude path."""
    a, b, k, m, par = fit["a"], fit["b"], fit["k"], fit["m"], fit["params"]
    p = list(p_hist)
    x = list(x_hist)
    out = []
    for xf in x_future:
        x.append(xf)
        dxs = [x[-1 - i] - x[-2 - i] for i in range(k + 1)]
        dps = [p[-j] - p[-j - 1] for j in range(1, m + 1)]
        u_prev = p[-1] - a - b * x[-2]
        dp = par["c"] + par["gamma"] * u_prev + sum(par[f"beta_{i}"] * dxs[i] for i in range(k + 1)) \
            + sum(par[f"alpha_{j}"] * dps[j - 1] for j in range(1, m + 1))
        p.append(p[-1] + dp)
        out.append(p[-1])
    return np.array(out)


def forecast_oil_item(log_p: pd.Series, crude_chf_daily: pd.Series, origin, steps: int = FORECAST_STEPS,
                      rule: str = OIL_X_RULE) -> tuple[pd.DataFrame, dict]:
    """ECM forecast of one oil item's log price for the `steps` months after `origin` (paper p. 7).

    log_p:            monthly log item price (may extend past the origin; cut here).
    crude_chf_daily:  daily crude price in CHF (may extend past the information cut-off; cut here).
    No look-ahead: prices up to `origin`, crude only before crude_info_cutoff(origin) (paper p. 12).
    Returns (target, log_p_hat) and a log dict like item_models.forecast_item.
    """
    origin = pd.Timestamp(origin)
    targets = pd.date_range(origin + pd.DateOffset(months=1), periods=steps, freq="MS")
    p = log_p.loc[pd.Timestamp(OIL_SAMPLE_START):origin].dropna()
    log = {"spec_method": "ecm", "method": "ecm", "p": np.nan, "q": np.nan, "seasonal": False, "sic": np.nan,
           "t_eff": np.nan, "p_max_eff": np.nan, "n_candidates": (OIL_K_MAX + 1) * (OIL_M_MAX + 1),
           "n_failed": 0, "quarterly": False, "note": ""}
    if p.empty or p.index[-1] != origin:
        log.update(method="none", note="no observation at origin")
        return pd.DataFrame(columns=["target", "log_p_hat"]), log

    daily = crude_chf_daily[crude_chf_daily.index < crude_info_cutoff(origin)]   # paper p. 12
    x = monthly_crude(daily, p.index[0], targets[0], rule=rule)   # up to the month after the origin (p. 12)
    fit = fit_oil_ecm(p, x.loc[:origin])
    # Crude path: month origin+1 known; afterwards constant at the last 10-day average (paper p. 7) = x[origin+1]
    x_future = np.full(steps, x.iloc[-1])
    path = ecm_path(fit, p.to_numpy(), x.loc[:origin].to_numpy(), x_future)
    log.update(sic=fit["sic"], t_eff=fit["t_eff"],   # p, q stay NaN: they describe ARIMA orders only
               note=f"ECM k={fit['k']} m={fit['m']} b={fit['b']:.3f} gamma={fit['params']['gamma']:.3f}")
    return pd.DataFrame({"target": targets, "log_p_hat": path}), log


# ===========================================================================
# B. RENTS - quarterly ARIMA with asymmetric mortgage-rate effect (T2.4, paper pp. 7-8)
# ===========================================================================

def forecast_rent(log_rent: pd.Series, mortgage_rate: pd.Series, origin: pd.Timestamp, steps: int) -> pd.DataFrame:
    """Quarterly rent model with lagged positive/negative mortgage-rate changes (paper pp. 7-8)."""
    raise NotImplementedError("T2.4")
