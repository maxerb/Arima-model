"""T2.4 rent model: no look-ahead (rents and mortgage rate), parameter recovery, booking in collection months, routing."""

import numpy as np
import pandas as pd

from arima_snb import special
from arima_snb.item_models import forecast_item, forecast_items

MONTHS = pd.date_range("1993-05-01", "2013-12-01", freq="MS")
ORIGIN = pd.Timestamp("2009-02-01")
C, PHI1, BPOS, BNEG = 0.003, 0.3, 0.03, 0.005


def _simulate(seed: int = 0):
    """Monthly mortgage rate (random walk, steps every month) and a rent index changing in Feb/May/Aug/Nov only."""
    rng = np.random.default_rng(seed)
    mm = pd.date_range("1990-01-01", MONTHS[-1], freq="MS")
    mort = pd.Series(4 + np.cumsum(rng.normal(0, 0.08, len(mm))), mm)
    m_q = special.quarterly_mortgage(mort, MONTHS[-1].to_period("Q"))
    dpos, dneg = special.mortgage_changes(m_q)
    coll = MONTHS[MONTHS.month.isin([2, 5, 8, 11])]
    r, d_prev, level = {}, 0.0, 0.0
    for t in coll:
        q = t.to_period("Q")
        d = C + PHI1 * d_prev + BPOS * dpos[q] + BNEG * dneg[q] + rng.normal(0, 0.001)
        level += d
        r[t] = level
        d_prev = d
    log_rent = pd.Series(r).reindex(MONTHS).ffill().fillna(0.0)
    return log_rent, mort


def _spec():
    return pd.Series({"item_id": "rent", "method": "rent", "seasonal": False, "quarterly_lags": False,
                      "collection_freq": "quarterly"})


def test_parameter_recovery():
    r, mort = _simulate()
    m = mort[mort.index <= ORIGIN]
    fit = special.fit_rent_model(special.rent_quarterly_changes(r.loc[:ORIGIN], ORIGIN),
                                 special.quarterly_mortgage(m, ORIGIN.to_period("Q")))
    assert fit["p"] >= 1
    assert abs(fit["params"]["beta_pos"] - BPOS) < 0.01
    assert abs(fit["params"]["beta_neg"] - BNEG) < 0.01


def test_no_look_ahead_rent_and_mortgage():
    """Perturbing rents after the origin and mortgage data from the month after the origin leaves the forecast unchanged."""
    r, mort = _simulate()
    base, _ = special.forecast_rent(r, mort, ORIGIN)
    r2, m2 = r.copy(), mort.copy()
    r2[r2.index > ORIGIN] += 5.0
    m2[m2.index > ORIGIN] += 3.0          # month origin+1 onwards is not known at the origin (paper p. 12)
    pert, _ = special.forecast_rent(r2, m2, ORIGIN)
    pd.testing.assert_frame_equal(base, pert)
    # ... while the mortgage value of the origin month itself is in the information set
    m3 = mort.copy()
    m3[ORIGIN] += 3.0
    moved, _ = special.forecast_rent(r, m3, ORIGIN)
    assert not np.allclose(base.log_p_hat, moved.log_p_hat)


def test_changes_only_in_collection_months():
    """Forecast level moves only in Feb/May/Aug/Nov and is carried forward in between; first target = origin level."""
    r, mort = _simulate()
    f, log = special.forecast_rent(r, mort, ORIGIN)
    assert log["method"] == "rent" and len(f) == 13
    path = pd.Series(np.r_[r[ORIGIN], f.log_p_hat.to_numpy()], index=[ORIGIN, *f.target])
    moved = path.diff().abs() > 0
    assert set(path.index[moved].month) <= {2, 5, 8, 11}
    assert f.log_p_hat.iloc[0] == r[ORIGIN]       # March = February (no collection) -> h = 1 error 0


def test_constant_mortgage_after_origin():
    """Future quarterly mortgage changes are zero once the rate is held constant (paper p. 7)."""
    _, mort = _simulate()
    m = mort[mort.index <= ORIGIN]
    m_q = special.quarterly_mortgage(m, ORIGIN.to_period("Q") + 6)
    assert np.allclose(m_q.loc[ORIGIN.to_period("Q") + 1:].diff().dropna(), 0)


def test_routing_forecast_item_and_items():
    """forecast_item uses the rent model only when the mortgage rate is passed; forecast_items routes it to rents."""
    r, mort = _simulate()
    f1, lg1 = forecast_item(r, _spec(), ORIGIN, mortgage_rate=mort)
    f0, lg0 = forecast_item(r, _spec(), ORIGIN, pattern=[2, 5, 8, 11])
    assert lg1["method"] == "rent" and lg0["method"] != "rent"
    panel = pd.DataFrame({"date": r.index, "item_id": "i094", "log_p": r.to_numpy()})
    specs = _spec().to_frame().T.assign(item_id="i094")
    coll = pd.DataFrame(columns=["date", "item_id", "collected", "source"])
    out, log = forecast_items(panel, specs, coll, ORIGIN, n_jobs=1, mortgage_rate=mort)
    assert log.method.iloc[0] == "rent"
    np.testing.assert_allclose(out.log_p_hat.to_numpy(), f1.log_p_hat.to_numpy())
