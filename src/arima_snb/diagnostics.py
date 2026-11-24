"""Item diagnostics: unit-root tests, seasonality, collection frequency -> item_specs.csv (T2.1).

Skill: snb-arima-item-diagnostics. Paper p. 6: the specification step (integration order, seasonality,
collection frequency) is done "only every few years"; the lag order is chosen later by SIC (T2.2).

No look-ahead (AGENTS.md rule 1): every function takes a `vintage` year Y and uses only data up to
December of Y. Specs of vintage Y are used by forecast origins in year Y+1 (D-31).
"""

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf, adfuller, kpss

from arima_snb.config import (ACF_MAX_LAG, DIAG_ALPHA, FREQ_6X_MIN, FREQ_MONTHLY_MIN, FREQ_QUARTERLY_MIN,
                              ITEM_SAMPLE_START, MIN_OBS_MONTHLY, MIN_OBS_QUARTERLY, SEASONAL_LAGS)

SPEC_COLUMNS = ["vintage", "item_id", "d", "d_flag", "adf_p_level", "kpss_p_level", "adf_p_diff", "kpss_p_diff",
                "seasonal", "acf12", "acf24", "collection_freq", "n_collected", "quarterly_lags", "n_obs",
                "method", "reason"]


def cut(series: pd.Series, vintage: int) -> pd.Series:
    """Item series from the paper's sample start (May 2000, p. 5) up to Dec of the vintage year."""
    s = series.dropna()
    return s[(s.index >= pd.Timestamp(ITEM_SAMPLE_START)) & (s.index <= pd.Timestamp(f"{vintage}-12-01"))]


def every_third(x: pd.Series) -> pd.Series:
    """Quarterly sampling ending at the last observation (changes between collection months)."""
    return x.iloc[::-1].iloc[::3].iloc[::-1]


def unit_root_tests(log_p: pd.Series) -> dict:
    """ADF (H0: unit root) and KPSS (H0: stationary) on levels (with trend) and first differences (constant).

    I(1) looks like: levels -> ADF does not reject, KPSS rejects; differences -> ADF rejects, KPSS does not.
    KPSS p-values in statsmodels are truncated to [0.01, 0.10] (interpolation table), so we store a flag too.
    """
    out = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # KPSS "p-value outside table" warnings
        for name, x, reg in [("level", log_p, "ct"), ("diff", log_p.diff().dropna(), "c")]:
            if x.std() == 0:  # constant series: tests undefined
                out[f"adf_p_{name}"] = out[f"kpss_p_{name}"] = np.nan
                continue
            out[f"adf_p_{name}"] = adfuller(x, regression=reg, autolag="BIC")[1]
            out[f"kpss_p_{name}"] = kpss(x, regression=reg, nlags="auto")[1]
    a = DIAG_ALPHA
    levels_stationary = out["adf_p_level"] < a and out["kpss_p_level"] >= a
    diffs_nonstationary = out["adf_p_diff"] >= a or out["kpss_p_diff"] < a
    # D-32: the paper keeps d = 1 for all items ("very few" reject I(1), p. 6); we only flag.
    out["d_flag"] = bool(levels_stationary or diffs_nonstationary)
    return out


def seasonality(dlog: pd.Series, step: int = 1) -> dict:
    """Lag-12 seasonality from the ACF of log changes (paper p. 6: spikes at multiples of 12).

    `step` = 1 for monthly changes; 3 for quarterly items, whose changes are taken between collection
    months, so 12 months = 4 lags. Carried-forward monthly data of quarterly items would give spurious
    spikes at lags 3 and 12. D-33: seasonal if the ACF at lag 12 or 24 is positive and outside +-1.96/sqrt(T).
    """
    x = dlog.dropna()
    T = len(x)
    lags = [l // step for l in SEASONAL_LAGS]
    if T <= max(lags) + 2 or x.std() == 0:
        return {"acf12": np.nan, "acf24": np.nan, "seasonal": False}
    r = acf(x, nlags=min(ACF_MAX_LAG // step, T - 1), fft=True)
    band = 1.96 / np.sqrt(T)
    vals = [r[l] for l in lags]
    return {"acf12": vals[0], "acf24": vals[1], "seasonal": bool(any(v > band for v in vals))}


def collection_frequency(collection: pd.DataFrame, item_id: str, vintage: int) -> tuple[str, int]:
    """Collections in the vintage year Y (the year before the origins that use it, D-28/D-31).

    Inferred flags undercount (an unchanged price in a collected month looks 'not collected'), so where the
    official calendar (paper Tables 5-8, published in advance) covers year Y we take the larger count (D-34).
    """
    c = collection[(collection.item_id == item_id) & (collection.date.dt.year == vintage)]
    n_inf = int(c.loc[c.source == "inferred", "collected"].astype("boolean").fillna(False).sum())
    cal = c.loc[c.source == "calendar", "collected"].astype("boolean")
    n_cal = int(cal.fillna(False).sum()) if cal.notna().any() else 0
    n = max(n_inf, n_cal)
    if n >= FREQ_MONTHLY_MIN:
        return "monthly", n
    if n >= FREQ_6X_MIN:
        return "6x", n
    if n >= FREQ_QUARTERLY_MIN:
        return "quarterly", n
    return "less_than_quarterly", n


def assign_method(special, freq: str, n_obs: int, quarterly: bool) -> tuple[str, str]:
    """Method per item (paper pp. 6-7)."""
    if special == "oil":
        return "ecm", "oil product: ECM with crude in CHF (p. 7)"
    if special == "rent":
        return "rent", "rent model with mortgage rate (p. 7)"
    if freq == "less_than_quarterly":
        return "adhoc_last", "collected less than once a quarter: no model (p. 7)"
    if (quarterly and n_obs // 3 < MIN_OBS_QUARTERLY) or n_obs < MIN_OBS_MONTHLY:
        return "adhoc_avg_yoy", "too few observations (p. 7, D-09)"
    if quarterly:
        return "arima", "quarterly collection: lags 3, 6, 9, ... (p. 6, D-10)"
    return "arima", f"{freq} collection: monthly ARIMA"


def diagnose_item(log_p: pd.Series, collection: pd.DataFrame, item_id: str, special, vintage: int) -> dict:
    """All diagnostics and the method choice for one item and one spec vintage (data to Dec of `vintage`)."""
    x = cut(log_p, vintage)
    freq, n_coll = collection_frequency(collection, item_id, vintage)
    quarterly = freq == "quarterly"
    row = {"vintage": vintage, "item_id": item_id, "d": 1, "n_obs": len(x),
           "collection_freq": freq, "n_collected": n_coll}
    if len(x) > 24:
        row.update(unit_root_tests(x))
        row.update(seasonality(every_third(x).diff(), step=3) if quarterly else seasonality(x.diff()))
    else:
        row.update({"d_flag": False, "seasonal": False, "acf12": np.nan, "acf24": np.nan})
    row["method"], row["reason"] = assign_method(special, freq, len(x), quarterly)
    row["quarterly_lags"] = quarterly and row["method"] == "arima"
    return row


def item_specs(panel: pd.DataFrame, collection: pd.DataFrame, items: pd.DataFrame, vintages) -> pd.DataFrame:
    """item_specs for every item and vintage (long: one row per vintage x item)."""
    wide = panel.pivot(index="date", columns="item_id", values="log_p")
    rows = [diagnose_item(wide[it.item_id], collection, it.item_id, it.special, v)
            for v in vintages for it in items.itertuples() if it.item_id in wide]
    return pd.DataFrame(rows).reindex(columns=SPEC_COLUMNS)


def specs_for_origin(specs: pd.DataFrame, origin) -> pd.DataFrame:
    """Specs usable at `origin`: the vintage of the year before the origin's year (D-31)."""
    return specs[specs.vintage == pd.Timestamp(origin).year - 1]
