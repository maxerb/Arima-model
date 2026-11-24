"""T2.3 oil ECM: no look-ahead (prices and crude), parameter recovery, crude path and timing rules."""

import numpy as np
import pandas as pd

from arima_snb import special
from arima_snb.item_models import forecast_item, forecast_items

MONTHS = pd.date_range("1993-05-01", "2012-12-01", freq="MS")
ORIGIN = pd.Timestamp("2009-02-01")
A, B, GAMMA, BETA0 = 1.0, 0.8, -0.35, 0.5


def _simulate(seed: int = 0):
    """Daily crude in CHF (random walk in logs) and a monthly item following the ECM with the 'before' timing."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("1992-12-01", "2013-02-28")
    crude = pd.Series(np.exp(np.log(60) + np.cumsum(rng.normal(0, 0.02, len(days)))), days)
    x = special.monthly_crude(crude, MONTHS[0], MONTHS[-1], rule="before").to_numpy()
    p = np.empty(len(MONTHS))
    p[0] = A + B * x[0]
    for t in range(1, len(MONTHS)):
        u = p[t - 1] - A - B * x[t - 1]
        p[t] = p[t - 1] + GAMMA * u + BETA0 * (x[t] - x[t - 1]) + rng.normal(0, 0.01)
    return pd.Series(p, MONTHS), crude


def _spec():
    return pd.Series({"item_id": "oil", "method": "ecm", "seasonal": False, "quarterly_lags": False,
                      "collection_freq": "monthly"})


def test_parameter_recovery():
    p, crude = _simulate()
    x = special.monthly_crude(crude, MONTHS[0], ORIGIN)
    fit = special.fit_oil_ecm(p.loc[:ORIGIN], x)
    assert abs(fit["b"] - B) < 0.05
    assert abs(fit["params"]["gamma"] - GAMMA) < 0.1
    assert abs(fit["params"]["beta_0"] - BETA0) < 0.1


def test_no_look_ahead_prices_and_crude():
    """Item prices after the origin and crude prices from the 1st of the month after the origin on (paper p. 12)
    may be anything: the forecast must not change."""
    p, crude = _simulate()
    base, _ = special.forecast_oil_item(p, crude, ORIGIN, 13)
    rng = np.random.default_rng(5)
    p2, c2 = p.copy(), crude.copy()
    p2[p2.index > ORIGIN] = rng.normal(0, 10, (p2.index > ORIGIN).sum())
    cut = special.crude_info_cutoff(ORIGIN)
    c2[c2.index >= cut] = np.exp(rng.normal(5, 2, (c2.index >= cut).sum()))
    pert, _ = special.forecast_oil_item(p2, c2, ORIGIN, 13)
    pd.testing.assert_frame_equal(base, pert)
    # ... but crude prices just before the cut-off are allowed and do matter (nowcast of origin + 1)
    c3 = crude.copy()
    c3[(c3.index < cut) & (c3.index >= cut - pd.Timedelta(days=5))] *= 1.5
    moved, _ = special.forecast_oil_item(p, c3, ORIGIN, 13)
    assert not np.allclose(moved.log_p_hat, base.log_p_hat)


def test_no_look_ahead_first_days_rule():
    p, crude = _simulate()
    base, _ = special.forecast_oil_item(p, crude, ORIGIN, 13, rule="first_days")
    c2 = crude.copy()
    c2[c2.index >= special.crude_info_cutoff(ORIGIN)] *= 3
    pert, _ = special.forecast_oil_item(p, c2, ORIGIN, 13, rule="first_days")
    pd.testing.assert_frame_equal(base, pert)


def test_constant_crude_converges_to_long_run():
    """With crude held constant the ECM path moves towards a + b·x (γ < 0) and its changes die out."""
    p, crude = _simulate()
    f, _ = special.forecast_oil_item(p, crude, ORIGIN, 60)
    d = np.diff(f.log_p_hat.to_numpy())
    assert abs(d[-1]) < abs(d[1]) + 1e-12
    assert abs(d[-1]) < 1e-3


def test_monthly_crude_before_rule():
    days = pd.bdate_range("2020-01-01", "2020-03-31")
    s = pd.Series(np.arange(len(days), dtype=float) + 1, days)
    x = special.monthly_crude(s, "2020-02-01", "2020-03-01", rule="before")
    jan = s[s.index < "2020-02-01"].iloc[-10:].mean()
    assert np.isclose(x["2020-02-01"], np.log(jan))


def test_item_interface_routes_oil_to_ecm():
    """forecast_item / forecast_items use the ECM for `ecm` items when crude is given, plain ARIMA otherwise."""
    p, crude = _simulate()
    f_ecm, lg = forecast_item(p, _spec(), ORIGIN, 13, crude_chf_daily=crude)
    assert lg["method"] == "ecm"
    direct, _ = special.forecast_oil_item(p, crude, ORIGIN, 13)
    pd.testing.assert_frame_equal(f_ecm, direct)
    _, lg_ar = forecast_item(p, _spec(), ORIGIN, 13)
    assert lg_ar["method"] != "ecm"

    panel = pd.DataFrame({"date": MONTHS, "item_id": "oil", "log_p": p.values})
    coll = pd.DataFrame({"date": MONTHS, "item_id": "oil", "collected": True, "source": "inferred"})
    specs = _spec().to_frame().T
    out, log = forecast_items(panel, specs, coll, ORIGIN, 13, n_jobs=1, crude_chf_daily=crude)
    assert log.method.iloc[0] == "ecm"
    np.testing.assert_allclose(out.log_p_hat.to_numpy(), direct.log_p_hat.to_numpy())
