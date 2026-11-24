"""Special models: oil-products error-correction model and rent model (T2.3-T2.4).

Skill: snb-arima-oil-rent. Paper p. 7 (oil, rents) and p. 12 (information set of the exogenous data).

The file has two separate sections: A. oil products (T2.3), B. rents (T2.4).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from arima_snb.config import (FORECAST_STEPS, OIL_CRUDE_SERIES, OIL_FIRST_DAYS, OIL_FX_SERIES, OIL_K_MAX,
                              OIL_M_MAX, OIL_SAMPLE_START, OIL_WINDOW_DAYS, OIL_X_RULE, RENT_COLLECTION_MONTHS,
                              RENT_MORTGAGE_LAG, RENT_MORTGAGE_SERIES, RENT_P_MAX, RENT_SAMPLE_START)


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

# Rents (weight ≈ 20 %) are collected once a quarter, in Feb/May/Aug/Nov (true in the data since 1993, D-48).
# The paper models them as a quarterly AR in first differences plus the 4th lag of the change in the mortgage
# rate, entered separately for increases and decreases (p. 7):
#
#   Δr_q = c + Σ_{j=1..p} φ_j Δr_{q-j} + β⁺ Δm⁺_{q-4} + β⁻ Δm⁻_{q-4} + e_q
#
# r_q = log rent index in the collection month of quarter q, m_q = quarterly average mortgage rate in percent
# (D-15 rev.), Δm⁺ = max(Δm, 0), Δm⁻ = min(Δm, 0). Swiss tenancy law lets landlords pass on mortgage-rate
# increases (and obliges them, on request, to pass on decreases) with a delay, and in practice increases pass
# through faster/more fully - hence two coefficients. p by SIC (D-48), estimated by OLS.
#
# Forecast: the mortgage rate stays constant at its last known value (paper p. 7) -> future Δm = 0, but the
# known changes of the last 4 quarters still enter through the lag. At an origin in the 2nd month of a quarter
# the current quarter's rent is already observed, so the h = 1 rent error is zero by construction (Table 3).
# Information set (paper p. 12): mortgage data up to the first day of the last month of the quarter = monthly
# values up to the origin month.

RENT_MODEL_NAME = "rent_mortgage"


def load_mortgage_rate() -> pd.Series:
    """Monthly SNB mean variable mortgage rate in percent (zikrepro M_MV, D-19)."""
    from arima_snb import io   # local import: keeps the model code free of file access

    m = io.read_snb_cube(io.find_raw("snb-data-zikrepro-*.csv"), "zikrepro")
    return m[m.variable == RENT_MORTGAGE_SERIES].set_index("date")["value"].sort_index().rename("mortgage")


def quarterly_mortgage(monthly: pd.Series, last_quarter) -> pd.Series:
    """Quarterly average mortgage rate (D-15 rev.), indexed by quarter, up to `last_quarter`.

    `monthly` must already be cut at the information set. Months after its last value are filled with that last
    value (rate constant over the horizon, paper p. 7) before averaging, so a partly known quarter is the
    average of its known months and the last known rate.
    """
    end = pd.Period(last_quarter, freq="Q").end_time.normalize().replace(day=1)
    months = pd.date_range(monthly.index[0], end, freq="MS")
    filled = monthly.reindex(months).ffill()
    return filled.groupby(filled.index.to_period("Q")).mean()


def rent_quarterly_changes(log_rent: pd.Series, anchor: pd.Timestamp) -> pd.Series:
    """Quarterly log changes of the rent index between collection months, ending at `anchor`, indexed by quarter."""
    x = log_rent.loc[:anchor]
    xq = x[[((anchor.year - d.year) * 12 + anchor.month - d.month) % 3 == 0 for d in x.index]]
    dr = xq.diff().dropna()
    dr.index = dr.index.to_period("Q")
    return dr


def _rent_design(dr: np.ndarray, dpos: np.ndarray, dneg: np.ndarray, p: int, start: int):
    """Regressors for rows start..T-1: [1, Δr_{q-1}..Δr_{q-p}, Δm⁺_{q-L}, Δm⁻_{q-L}] with L = RENT_MORTGAGE_LAG.

    dpos/dneg are aligned with dr (same quarters) and already lagged by L.
    """
    T = len(dr)
    cols = [np.ones(T - start)] + [dr[start - j:T - j] for j in range(1, p + 1)] + [dpos[start:], dneg[start:]]
    return np.column_stack(cols), dr[start:]


def mortgage_changes(m_q: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Positive and negative parts of the quarterly mortgage-rate change, lagged RENT_MORTGAGE_LAG quarters."""
    dm = m_q.diff()
    return dm.clip(lower=0).shift(RENT_MORTGAGE_LAG), dm.clip(upper=0).shift(RENT_MORTGAGE_LAG)


def fit_rent_model(dr: pd.Series, m_q: pd.Series) -> dict:
    """OLS of Δr_q on its own lags (p = 0..RENT_P_MAX by SIC, common sample) and lagged Δm⁺, Δm⁻ (paper p. 7)."""
    from arima_snb.item_models import sic   # same Schwarz criterion as the item ARIMAs (eq. 3)

    dpos, dneg = mortgage_changes(m_q)
    df = pd.concat([dr.rename("dr"), dpos.rename("pos"), dneg.rename("neg")], axis=1).loc[dr.index].dropna()
    y, pos, neg = df.dr.to_numpy(), df.pos.to_numpy(), df.neg.to_numpy()
    start = RENT_P_MAX   # all candidates are compared on the same rows (AGENTS.md §7)
    best = None
    for p in range(RENT_P_MAX + 1):
        X, yy = _rent_design(y, pos, neg, p, start)
        f = _ols(yy, X)
        f.update(p=p, sic=sic(f["sse"], f["n"], X.shape[1]))
        if best is None or f["sic"] < best["sic"]:
            best = f
    names = ["c"] + [f"phi_{j}" for j in range(1, best["p"] + 1)] + ["beta_pos", "beta_neg"]
    return {"p": best["p"], "sic": best["sic"], "params": dict(zip(names, best["beta"])),
            "se": dict(zip(names, best["se"])), "t_eff": best["n"],
            "sample_start": df.index[start], "sample_end": df.index[-1]}


def rent_path(fit: dict, dr_hist: np.ndarray, dpos_future: np.ndarray, dneg_future: np.ndarray) -> np.ndarray:
    """Iterate the rent equation forward: future quarterly log changes given known history and Δm± (lagged)."""
    par, p = fit["params"], fit["p"]
    hist = list(dr_hist)
    out = []
    for pos, neg in zip(dpos_future, dneg_future):
        d = par["c"] + sum(par[f"phi_{j}"] * hist[-j] for j in range(1, p + 1)) \
            + par["beta_pos"] * pos + par["beta_neg"] * neg
        hist.append(d)
        out.append(d)
    return np.array(out)


def forecast_rent(log_rent: pd.Series, mortgage_monthly: pd.Series, origin, steps: int = FORECAST_STEPS
                  ) -> tuple[pd.DataFrame, dict]:
    """Rent-model forecast of the rent item's log price for the `steps` months after `origin` (paper p. 7).

    log_rent:          monthly log rent index (may extend past the origin; cut here).
    mortgage_monthly:  monthly mortgage rate in percent (may extend past the cut-off; cut here, paper p. 12).
    The quarterly changes are booked in the future collection months anchor+3, anchor+6, ...; the level is
    carried forward in between, like the published index (D-36). Returns (target, log_p_hat) and a log dict.
    """
    origin = pd.Timestamp(origin)
    targets = pd.date_range(origin + pd.DateOffset(months=1), periods=steps, freq="MS")
    x = log_rent.loc[pd.Timestamp(RENT_SAMPLE_START):origin].dropna()
    log = {"spec_method": "rent", "method": "rent", "p": np.nan, "q": np.nan, "seasonal": False, "sic": np.nan,
           "t_eff": np.nan, "p_max_eff": RENT_P_MAX, "n_candidates": RENT_P_MAX + 1, "n_failed": 0,
           "quarterly": True, "note": ""}
    if x.empty or x.index[-1] != origin:
        log.update(method="none", note="no observation at origin")
        return pd.DataFrame(columns=["target", "log_p_hat"]), log

    # latest collection month <= origin (Feb/May/Aug/Nov)
    anchor = next(origin - pd.DateOffset(months=k) for k in range(3)
                  if (origin - pd.DateOffset(months=k)).month in RENT_COLLECTION_MONTHS)
    dr = rent_quarterly_changes(x, anchor)
    n_q = int(np.ceil((steps + 2) / 3)) + 1
    last_q = anchor.to_period("Q") + n_q
    m = mortgage_monthly[mortgage_monthly.index < crude_info_cutoff(origin)].dropna()   # paper p. 12
    m_q = quarterly_mortgage(m, last_q)
    fit = fit_rent_model(dr, m_q.loc[:anchor.to_period("Q")])
    dpos, dneg = mortgage_changes(m_q)
    fut_q = pd.period_range(anchor.to_period("Q") + 1, periods=n_q, freq="Q")
    dq = rent_path(fit, dr.to_numpy(), dpos.loc[fut_q].to_numpy(), dneg.loc[fut_q].to_numpy())
    coll_months = [anchor + pd.DateOffset(months=3 * (k + 1)) for k in range(n_q)]
    path = np.array([x.iloc[-1] + dq[[c <= t for c in coll_months]].sum() for t in targets])
    par, se = fit["params"], fit["se"]
    log.update(p=fit["p"], sic=fit["sic"], t_eff=fit["t_eff"],
               note=f"rent p={fit['p']} b+={par['beta_pos']:.4f}({se['beta_pos']:.4f}) "
                    f"b-={par['beta_neg']:.4f}({se['beta_neg']:.4f})")
    return pd.DataFrame({"target": targets, "log_p_hat": path}), log
