"""Collection-frequency extension: state-space model with missing monthly prices (T4.1).

Paper section 5 (pp. 12-15) and appendix C (pp. 26-28). Skill: snb-arima-kalman-extension.

Idea. Many CPI items are not priced every month. In a month without collection the SFSO carries the old price forward,
so the published log change is zero, and in the next collection month it shows the change accumulated since the last
collection. The paper models the *unobserved* monthly log changes as a stationary AR(p) (optionally times a seasonal
AR(12)) around a mean mu. The observed change since the last collection is the sum of these latent monthly changes
(eqs. 4, 7-9). Parameters are estimated by maximum likelihood with the Kalman filter (C.2).

Implementation (D-42). We put the log LEVEL p_t into the state space and mark every non-collection month as
missing (NaN). The Kalman filter then conditions exactly on p_t - p_{t-h_t} = sum of the latent changes since the last
collection - this is eq. (7)-(8) with R_t = 0 at collections. Concretely we use statsmodels' SARIMAX:

    p_t = mu * t + u_t,   (1 - phi_1 L - ... - phi_p L^p)(1 - rho L^12) (1 - L) u_t = eps_t

The deterministic trend mu * t enters as a regression on the exogenous time index, so Delta p_t = mu + Delta u_t and
mu is exactly the paper's mean monthly change ("mean form", not an intercept). The level of u_t is initialised
diffusely, the stationary AR part with its unconditional distribution (Hamilton 1994, pp. 378-379);
`enforce_stationarity=True` keeps the roots of Phi(z)Gamma(z) outside the unit circle (C.2).

Every function that sees data takes an explicit `origin` and cuts the data itself (AGENTS.md rule 1).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from arima_snb.config import (KALMAN_P_MAX, KALMAN_SAMPLE_START, NO_COLLECTION_TOL, SEASONAL_PERIOD)


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------
def observed_levels(log_p: pd.Series, origin, start: str = KALMAN_SAMPLE_START,
                    tol: float = NO_COLLECTION_TOL) -> pd.Series:
    """Log levels known at `origin`, with NaN in every month that was not a collection month.

    A month counts as a collection only if the published log price moved by at least `tol` (paper fn. 9, D-43):
    tiny changes are treated as rounding, unchanged prices as "not collected". The first month of the sample is kept
    as the anchor for the level. Sample = from `start` (paper p. 14: from 1993) or the item's first observation.
    """
    origin = pd.Timestamp(origin)
    s = log_p.dropna().sort_index()
    s = s[(s.index >= pd.Timestamp(start)) & (s.index <= origin)]          # cut at origin: no look-ahead
    s = s.reindex(pd.date_range(s.index[0], origin, freq="MS")) if len(s) else s
    collected = s.diff().abs() >= tol
    y = s.where(collected)
    if len(y):
        y.iloc[0] = s.iloc[0]
    return y


def _time_index(index: pd.DatetimeIndex, start: pd.Timestamp) -> np.ndarray:
    """Months since `start` (0, 1, 2, ...) - the regressor whose coefficient is the drift mu."""
    return ((index.year - start.year) * 12 + (index.month - start.month)).to_numpy(dtype=float)


# ---------------------------------------------------------------------------
# Estimation
# ---------------------------------------------------------------------------
def fit_collection_model(y: pd.Series, p: int, seasonal: bool, maxiter: int = 200):
    """Fit the latent monthly AR(p)(x seasonal AR(12)) model by ML on log levels with missing months.

    `y` comes from `observed_levels` (already cut at the origin). Returns a statsmodels results object whose
    parameter `mu` is the mean monthly log change and `ar.L*`, `ar.S.L12` the AR coefficients of the latent changes.
    """
    exog = pd.Series(_time_index(y.index, y.index[0]), index=y.index, name="mu")
    mod = SARIMAX(y, exog=exog, order=(p, 1, 0),
                  seasonal_order=(1, 0, 0, SEASONAL_PERIOD) if seasonal else (0, 0, 0, 0),
                  simple_differencing=False, enforce_stationarity=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")               # convergence chatter; checked via mle_retvals by the caller
        try:
            return mod.fit(disp=False, maxiter=maxiter)
        except (np.linalg.LinAlgError, ValueError):
            # D-42: the optimiser can step to AR roots on the unit circle, where the stationary initialisation
            # (a Lyapunov equation) cannot be solved. Retry once from neutral start values (AR = 0, mu = mean
            # change per month, sigma^2 = variance of the observed changes per month) with Nelder-Mead.
            obs = y.dropna()
            months = np.diff(_time_index(obs.index, y.index[0]))
            mu0 = (obs.iloc[-1] - obs.iloc[0]) / max(months.sum(), 1)
            s2 = float(np.var(np.diff(obs.to_numpy()) / np.sqrt(months))) or 1e-4
            start = np.r_[mu0, np.zeros(mod.k_params - 2), s2]
            return mod.fit(start_params=start, method="nm", disp=False, maxiter=5000)


def fit_with_fallback(y: pd.Series, p: int, seasonal: bool):
    """Fit order p; if it cannot be estimated at this origin, step p down (then drop the seasonal factor). D-42.

    Returns (results, p_used, seasonal_used).
    """
    for s_flag in ([seasonal, False] if seasonal else [False]):
        for q in range(p, -1, -1):
            try:
                return fit_collection_model(y, q, s_flag), q, s_flag
            except (np.linalg.LinAlgError, ValueError):
                continue
    raise RuntimeError("no AR order could be estimated")


def n_observed_changes(y: pd.Series) -> int:
    """Number of observed changes since the last collection = collection months minus the anchor month."""
    return int(y.notna().sum()) - 1


def sic(res, y: pd.Series) -> float:
    """Schwarz criterion -2 log L + k log T with T = number of observed changes (D-44).

    With gaps the SSE of the item models is not defined, so the SIC uses the exact Kalman likelihood. All candidate
    orders are fitted to the same observations (the state space handles the first lags itself), so the common-sample
    rule of AGENTS.md §7 holds automatically.
    """
    k = len(res.params)
    return -2.0 * res.llf + k * np.log(n_observed_changes(y))


def select_order(y: pd.Series, seasonal: bool, p_max: int = KALMAN_P_MAX) -> pd.DataFrame:
    """Fit AR orders p = 0..p_max (seasonal flag given) and return one row per order with its SIC (D-44).

    With the seasonal AR(12) factor, lag 12 cannot also be a regular AR lag, so p stops at 11.
    """
    if seasonal:
        p_max = min(p_max, SEASONAL_PERIOD - 1)
    rows = []
    for p in range(p_max + 1):
        try:
            res = fit_collection_model(y, p, seasonal)
        except (np.linalg.LinAlgError, ValueError):     # D-42: order cannot be estimated -> never selected
            rows.append({"p": p, "sic": np.inf, "llf": np.nan, "converged": False})
            continue
        rows.append({"p": p, "sic": sic(res, y), "llf": res.llf,
                     "converged": bool(res.mle_retvals.get("converged", True))})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Forecasting (eq. 13) and interpolation
# ---------------------------------------------------------------------------
def latent_forecast(res, y: pd.Series, steps: int) -> pd.Series:
    """Conditional mean of the monthly log level for the `steps` months after the sample end (eq. 13).

    This is the forecast of the *latent* monthly price path, i.e. what the index would be if it were collected
    every month.
    """
    last = y.index[-1]
    idx = pd.date_range(last + pd.offsets.MonthBegin(1), periods=steps, freq="MS")
    exog = pd.Series(_time_index(idx, y.index[0]), index=idx, name="mu")
    return pd.Series(res.get_forecast(steps, exog=exog).predicted_mean.to_numpy(), index=idx)


def published_path(latent: pd.Series, last_published: float, months: list[int]) -> pd.Series:
    """Turn a latent monthly path into a "published-like" path with carried-forward prices.

    Real-time rule (paper pp. 14-15): the future collection months are the ones observed in the previous year
    (`months`, 1-12). In an expected collection month the forecast is the latent level; otherwise the last
    published/forecast value is carried forward, as the SFSO does. If no collection was observed in the previous
    year, the last published value is carried forward over the whole horizon (D-43).
    """
    out, current = [], last_published
    for date, value in latent.items():
        if date.month in months:
            current = value
        out.append(current)
    return pd.Series(out, index=latent.index)


def smoothed_levels(res, y: pd.Series) -> pd.Series:
    """Kalman-smoother interpolation of the monthly log level over the sample (paper Chart 3, Hamilton pp. 394-397).

    In collection months it equals the observed level; in between it is the expected level given all data.
    """
    fr = res.filter_results
    z = fr.design[0, :, 0]                              # time-invariant design row (level = sum of integrated states)
    obs_int = np.broadcast_to(fr.obs_intercept[0], (len(y),))   # mu * t from the regression part
    level = z @ res.smoothed_state + obs_int
    return pd.Series(level, index=y.index)


def forecast_item_kalman(log_p: pd.Series, origin, steps: int, p: int, seasonal: bool,
                         months: list[int]) -> pd.DataFrame:
    """Forecast one item at `origin` with the extended model.

    log_p   : full monthly log price series (may extend beyond the origin; it is cut here).
    origin  : month of the last known CPI.
    p, seasonal : model order, chosen with data known at the origin (`select_order` on the spec vintage).
    months  : expected collection months (from `panel.collection_pattern`, previous year, known at origin).

    Returns one row per target month with the published-like forecast `log_p_hat` (used for aggregation, because the
    official CPI also carries prices forward) and the latent forecast `log_p_latent`.
    """
    origin = pd.Timestamp(origin)
    y = observed_levels(log_p, origin)
    res, p, seasonal = fit_with_fallback(y, p, seasonal)
    latent = latent_forecast(res, y, steps)
    last_pub = float(log_p.dropna()[log_p.dropna().index <= origin].iloc[-1])
    pub = published_path(latent, last_pub, months)
    return pd.DataFrame({"origin": origin, "target": latent.index, "log_p_hat": pub.to_numpy(),
                         "log_p_latent": latent.to_numpy(), "p": p, "seasonal": seasonal,
                         "mu": float(res.params["mu"])})


# ---------------------------------------------------------------------------
# Annual order vintages (D-44) - same timing as the item specs (D-31)
# ---------------------------------------------------------------------------
MIN_CHANGES_FOR_AR = 12   # D-44: fewer observed changes -> no AR search, p = 0 (random walk with drift)


def order_for_vintage(log_p: pd.Series, vintage: int, seasonal: bool, p_max: int = KALMAN_P_MAX) -> dict:
    """Choose the AR order of one item for spec vintage Y using data up to Dec Y (serves origins in Y+1)."""
    y = observed_levels(log_p, f"{vintage}-12-01")
    n = n_observed_changes(y) if len(y) else 0
    if n < MIN_CHANGES_FOR_AR:
        return {"p": 0, "seasonal": False, "sic": np.nan, "n_changes": n, "converged": True,
                "sample_start": y.index[0] if len(y) else pd.NaT}
    table = select_order(y, seasonal, p_max)
    best = table.loc[table.sic.idxmin()]
    return {"p": int(best.p), "seasonal": seasonal, "sic": float(best.sic), "n_changes": n,
            "converged": bool(best.converged), "sample_start": y.index[0]}


def orders_for_origin(orders: pd.DataFrame, origin) -> pd.DataFrame:
    """Orders usable at `origin`: the vintage of the year before the origin's year (D-31, D-44)."""
    return orders[orders.vintage == pd.Timestamp(origin).year - 1]
