"""T4.1 collection-frequency state-space model: simulation recovery, equivalence with ARIMA, no look-ahead."""

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from arima_snb.kalman_ext import (fit_collection_model, forecast_item_kalman, observed_levels,
                                  published_path, select_order, smoothed_levels)

MU, PHI, SIGMA = 0.002, (0.5, -0.3), 0.01


def _simulate(n: int = 300, seed: int = 1) -> tuple[pd.Series, pd.Series]:
    """Latent AR(2) monthly changes with drift; published level observed quarterly in the first half, monthly after.

    Returns (published log price with carried-forward months, true latent log level).
    """
    rng = np.random.default_rng(seed)
    u = np.zeros(n + 50)
    eps = rng.normal(0, SIGMA, n + 50)
    for t in range(2, n + 50):
        u[t] = PHI[0] * u[t - 1] + PHI[1] * u[t - 2] + eps[t]
    dlog = MU + u[50:]
    dates = pd.date_range("1993-01-01", periods=n, freq="MS")
    true = pd.Series(np.cumsum(dlog), index=dates)
    collected = np.where(np.arange(n) < n // 2, dates.month.isin([2, 5, 8, 11]), True)
    collected[0] = True
    published = true.where(collected).ffill()       # SFSO carries the last collected price forward
    return published, true


def test_simulation_recovers_parameters():
    """Estimated mu, phi, sigma^2 are close to the truth although half the sample is quarterly."""
    published, true = _simulate(n=1200)            # long sample: estimates within ~2 s.e. of the truth
    y = observed_levels(published, published.index[-1])
    assert y.isna().sum() > 300                       # the gaps are really treated as missing
    res = fit_collection_model(y, p=2, seasonal=False)
    # mu is the mean latent change: compare with the realised sample mean (the truth up to sampling error)
    realised = (true.iloc[-1] - true.iloc[0]) / (len(true) - 1)
    assert abs(res.params["mu"] - realised) < 0.0005 and abs(res.params["mu"] - MU) < 0.003
    assert abs(res.params["ar.L1"] - PHI[0]) < 0.15 and abs(res.params["ar.L2"] - PHI[1]) < 0.15
    assert abs(np.sqrt(res.params["sigma2"]) - SIGMA) < 0.002
    # Kalman smoother: interpolated levels hit the collections and track the latent changes in the quarterly half
    smooth = smoothed_levels(res, y)
    obs = y.dropna()
    assert np.allclose(smooth[obs.index], obs, atol=1e-6)
    half = true.index[: len(true) // 2]
    corr = np.corrcoef(smooth[half].diff().dropna(), true[half].diff().dropna())[0, 1]
    assert corr > 0.6


def test_sic_picks_true_order():
    published, _ = _simulate(seed=2)
    y = observed_levels(published, published.index[-1])
    table = select_order(y, seasonal=False, p_max=4)
    assert table.loc[table.sic.idxmin(), "p"] == 2


def test_monthly_collection_equals_plain_arima():
    """With a collection every month the model is a plain ARIMA(p,1,0) with drift (same phi, mu, likelihood)."""
    _, true = _simulate(seed=3)
    y = observed_levels(true, true.index[-1], tol=0.0)   # every month observed
    assert y.notna().all()
    res = fit_collection_model(y, p=2, seasonal=False)
    d = true.diff().dropna()
    plain = SARIMAX(d - d.mean(), order=(2, 0, 0)).fit(disp=False)
    assert abs(res.params["ar.L1"] - plain.params["ar.L1"]) < 0.02
    assert abs(res.params["mu"] - d.mean()) < 0.0005


def test_no_look_ahead():
    """Changing prices after the origin leaves the forecast unchanged."""
    published, _ = _simulate(seed=4)
    origin = published.index[200]
    base = forecast_item_kalman(published, origin, 12, p=2, seasonal=False, months=[2, 5, 8, 11])
    shocked = published.copy()
    shocked[shocked.index > origin] += np.random.default_rng(9).normal(0, 1, (shocked.index > origin).sum())
    again = forecast_item_kalman(shocked, origin, 12, p=2, seasonal=False, months=[2, 5, 8, 11])
    pd.testing.assert_frame_equal(base, again)
    assert base.target.min() == origin + pd.offsets.MonthBegin(1)


def test_published_path_carries_forward():
    latent = pd.Series([1.0, 2.0, 3.0, 4.0], index=pd.date_range("2010-12-01", periods=4, freq="MS"))
    assert published_path(latent, 0.5, [2]).tolist() == [0.5, 0.5, 3.0, 3.0]
    assert published_path(latent, 0.5, []).tolist() == [0.5] * 4
