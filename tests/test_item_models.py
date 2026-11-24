"""T2.2 item models: no look-ahead, SIC selection, CLS vs ML, quarterly items, fallbacks."""

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from arima_snb.item_models import (adhoc_path, fit_cls, forecast_arma, forecast_item, forecast_items, plausible,
                                   select_order, sic)

RNG = np.random.default_rng(1)
DATES = pd.date_range("2000-05-01", "2012-12-01", freq="MS")
ORIGIN = pd.Timestamp("2009-02-01")


def _ar_sim(phi, n, mu=0.002, sigma=0.005, rho=0.0, seed=0):
    """Simulate (1 - φ(L))(1 - ρL^12)(y - μ) = ε."""
    rng = np.random.default_rng(seed)
    a = np.convolve(np.r_[1, -np.asarray(phi)], np.r_[1, np.zeros(11), -rho])
    w = np.zeros(n + 200)
    e = rng.normal(0, sigma, n + 200)
    for t in range(len(a), n + 200):
        w[t] = -np.dot(a[1:], w[t - 1:t - len(a):-1]) + e[t]
    return w[200:] + mu


def _spec(**kw):
    base = {"item_id": "i1", "method": "arima", "seasonal": False, "quarterly_lags": False,
            "collection_freq": "monthly"}
    base.update(kw)
    return pd.Series(base)


def _items():
    """Monthly AR(2) item i1 and a quarterly-collected item i2 (changes in Feb/May/Aug/Nov only)."""
    n = len(DATES)
    d1 = _ar_sim([0.5, 0.2], n, seed=3)
    d2 = np.where(DATES.month.isin([2, 5, 8, 11]), RNG.normal(0.004, 0.01, n), 0.0)
    return {"i1": pd.Series(np.cumsum(d1), DATES), "i2": pd.Series(np.cumsum(d2), DATES)}


def test_sic_formula():
    assert np.isclose(sic(2.0, 100, 3), np.log(0.02) + 3 * np.log(100) / 100)


def test_no_look_ahead_single_item():
    """Garbage after the origin must not change the forecast (AGENTS.md rule 1)."""
    for iid, spec in [("i1", _spec()), ("i2", _spec(item_id="i2", quarterly_lags=True, collection_freq="quarterly"))]:
        x = _items()[iid]
        base, _ = forecast_item(x, spec, ORIGIN, 13, [2, 5, 8, 11])
        y = x.copy()
        y[y.index > ORIGIN] = RNG.normal(0, 10, (y.index > ORIGIN).sum())
        pert, _ = forecast_item(y, spec, ORIGIN, 13, [2, 5, 8, 11])
        pd.testing.assert_frame_equal(base, pert)


def test_no_look_ahead_all_items():
    """Same through forecast_items: post-origin prices and collection flags perturbed."""
    items = _items()
    panel = pd.concat([pd.DataFrame({"date": DATES, "item_id": k, "log_p": v.values}) for k, v in items.items()])
    coll = pd.concat([pd.DataFrame({"date": DATES, "item_id": k, "source": "inferred",
                                    "collected": v.diff().abs().values >= 1e-3}) for k, v in items.items()])
    specs = pd.DataFrame([_spec(), _spec(item_id="i2", quarterly_lags=True, collection_freq="quarterly")])
    base = forecast_items(panel, specs, coll, ORIGIN, n_jobs=1)
    later = panel.date > ORIGIN
    panel.loc[later, "log_p"] = RNG.normal(0, 10, later.sum())
    coll.loc[coll.date > ORIGIN, "collected"] = True
    pert = forecast_items(panel, specs, coll, ORIGIN, n_jobs=1)
    pd.testing.assert_frame_equal(base[0], pert[0])
    pd.testing.assert_frame_equal(base[1], pert[1])


def test_sic_picks_true_ar_order():
    """AR(2) data: SIC on the D-02 grid picks p = 2, q = 0 in most replications.

    (An AR(2) with a negative φ2 is often approximated by an MA(1) with one parameter less, which SIC then
    prefers legitimately - so the test uses φ = (0.3, 0.4), which no short MA mimics.)
    """
    hits = 0
    for seed in range(6):
        y = _ar_sim([0.3, 0.4], 240, seed=seed)
        best = select_order(y, seasonal=False, quarterly=False)["fit"]
        hits += (best["p"], best["q"]) == (2, 0)
    assert hits >= 4, hits


def test_seasonal_ar_estimated():
    y = _ar_sim([0.3], 300, rho=0.6, seed=5)
    f = fit_cls(y, 1, 0, True, 12, 13)
    from arima_snb.item_models import _unpack
    mu, phi, rho, theta = _unpack(f["params"], 1, 0, True)
    assert abs(phi[0] - 0.3) < 0.1 and abs(rho - 0.6) < 0.1 and abs(mu - 0.002) < 0.002


def test_cls_close_to_ml_and_forecast_recursion():
    """CLS AR(1) ≈ SARIMAX exact ML on a long sample; forecasts follow μ + φ^h (y_T - μ)."""
    y = _ar_sim([0.6], 400, seed=7)
    f = fit_cls(y, 1, 0, False, 12, 1)
    from arima_snb.item_models import _unpack
    mu, phi, _, _ = _unpack(f["params"], 1, 0, False)
    ml = SARIMAX(y, order=(1, 0, 0), trend="c").fit(disp=False)
    phi_ml = ml.params[1]
    assert abs(phi[0] - phi_ml) < 0.02
    assert abs(mu - ml.params[0] / (1 - phi_ml)) < 5e-4
    fc = forecast_arma(f, y, 12, 5)
    manual = mu + phi[0] ** np.arange(1, 6) * (y[-1] - mu)
    assert np.allclose(fc, manual)


def test_cls_ma_invertible():
    """MA candidates stay invertible (transform) and recover θ roughly."""
    rng = np.random.default_rng(11)
    e = rng.normal(0, 1, 501)
    y = e[1:] + 0.5 * e[:-1]
    f = fit_cls(y, 0, 1, False, 12, 0)
    from arima_snb.item_models import _unpack
    assert abs(_unpack(f["params"], 0, 1, False)[3][0] - 0.5) < 0.1


def test_quarterly_item_steps_only_in_collection_months():
    x = _items()["i2"]
    spec = _spec(item_id="i2", quarterly_lags=True, collection_freq="quarterly")
    fc, log = forecast_item(x, spec, ORIGIN, 13, [2, 5, 8, 11])
    assert log["quarterly"] and log["method"] in ("arima", "adhoc_avg_yoy")
    if log["method"] == "arima":
        step = fc.set_index("target").log_p_hat.diff()
        step.iloc[0] = fc.log_p_hat.iloc[0] - x[ORIGIN]
        moving = step[step.abs() > 1e-12].index.month
        assert set(moving) <= {2, 5, 8, 11}


def test_adhoc_rules_and_plausibility():
    x = pd.Series(np.arange(30) * 0.01, pd.date_range("2000-01-01", periods=30, freq="MS"))
    assert np.allclose(adhoc_path(x, "adhoc_last", 3), x.iloc[-1])
    assert np.allclose(adhoc_path(x, "adhoc_avg_mom", 3), x.iloc[-1] + 0.01 * np.arange(1, 4))
    assert np.allclose(adhoc_path(x, "adhoc_avg_yoy", 3), x.iloc[-1] + 0.01 * np.arange(1, 4))
    noisy = x + RNG.normal(0, 0.01, 30)
    assert plausible(noisy, adhoc_path(noisy, "adhoc_avg_yoy", 13))
    assert not plausible(noisy, noisy.iloc[-1] + np.full(13, 1.0))


def test_less_than_quarterly_is_flat():
    x = _items()["i1"]
    fc, log = forecast_item(x, _spec(method="adhoc_last"), ORIGIN, 13)
    assert log["method"] == "adhoc_last" and np.allclose(fc.log_p_hat, x[ORIGIN])
