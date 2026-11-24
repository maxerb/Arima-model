"""T2.1 item diagnostics: no look-ahead, method rules, seasonality on synthetic data."""

import numpy as np
import pandas as pd

from arima_snb.diagnostics import assign_method, item_specs, seasonality, specs_for_origin

RNG = np.random.default_rng(0)
DATES = pd.date_range("2000-05-01", "2012-12-01", freq="MS")


def _data(seasonal_item: bool = True):
    """Two synthetic items: i1 random walk with monthly seasonal pattern, i2 quarterly-collected random walk."""
    n = len(DATES)
    season = np.tile([0.03, -0.01, -0.01, -0.01, 0, 0, -0.03, 0.01, 0.01, 0.01, 0, 0], n // 12 + 1)[:n]
    dlog1 = 0.001 + RNG.normal(0, 0.005, n) + (season if seasonal_item else 0)
    dlog2 = np.where(DATES.month.isin([2, 5, 8, 11]), RNG.normal(0.003, 0.01, n), 0.0)
    panel = pd.concat([pd.DataFrame({"date": DATES, "item_id": i, "log_p": np.cumsum(d)})
                       for i, d in [("i1", dlog1), ("i2", dlog2)]])
    coll = pd.concat([pd.DataFrame({"date": DATES, "item_id": i, "source": "inferred",
                                    "collected": np.abs(d) >= 1e-3}) for i, d in [("i1", dlog1), ("i2", dlog2)]])
    items = pd.DataFrame({"item_id": ["i1", "i2"], "special": [np.nan, np.nan]})
    return panel, coll, items


def test_no_look_ahead():
    """Changing prices and collection flags after Dec of the vintage year leaves that vintage's specs unchanged."""
    panel, coll, items = _data()
    base = item_specs(panel, coll, items, [2006])
    later = panel.date > "2006-12-01"
    panel.loc[later, "log_p"] += RNG.normal(0, 1, later.sum())
    coll.loc[coll.date > "2006-12-01", "collected"] = False
    pd.testing.assert_frame_equal(base, item_specs(panel, coll, items, [2006]))


def test_classification():
    panel, coll, items = _data()
    s = item_specs(panel, coll, items, [2008]).set_index("item_id")
    assert s.loc["i1", "seasonal"] and s.loc["i1", "collection_freq"] == "monthly"
    assert s.loc["i2", "collection_freq"] == "quarterly" and s.loc["i2", "quarterly_lags"]
    assert (s.d == 1).all()


def test_white_noise_not_seasonal():
    x = pd.Series(RNG.normal(0, 1, 150))
    assert not seasonality(x)["seasonal"]


def test_method_rules():
    assert assign_method("oil", "monthly", 100, False)[0] == "ecm"
    assert assign_method("rent", "quarterly", 100, True)[0] == "rent"
    assert assign_method(np.nan, "less_than_quarterly", 100, False)[0] == "adhoc_last"
    assert assign_method(np.nan, "monthly", 20, False)[0] == "adhoc_avg_yoy"
    assert assign_method(np.nan, "monthly", 100, False)[0] == "arima"


def test_origin_uses_previous_year():
    specs = pd.DataFrame({"vintage": [2006, 2007], "item_id": ["i1", "i1"]})
    assert specs_for_origin(specs, "2007-02-01").vintage.tolist() == [2006]
