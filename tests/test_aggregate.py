"""T1.6: chained Laspeyres aggregation and quarterly y-o-y."""

import numpy as np
import pandas as pd

from arima_snb import aggregate


def _panel(paths: dict) -> pd.DataFrame:
    idx = pd.date_range("2001-12-01", "2004-12-01", freq="MS")
    return pd.DataFrame({k: f(np.arange(len(idx))) for k, f in paths.items()}, index=idx)


def _weights(w: dict, years=range(2002, 2005)) -> pd.DataFrame:
    return pd.DataFrame([dict(year=y, item_id=k, weight=v) for y in years for k, v in w.items()])


def test_identical_items_give_same_path_and_weights_normalised():
    path = lambda t: 100 * 1.003 ** t
    panel = _panel({"a": path, "b": path})
    agg = aggregate.aggregate_index(panel, _weights({"a": 3.0, "b": 7.0}))  # sums to 10, not 1
    expected = panel["a"] / panel["a"].iloc[0] * 100
    pd.testing.assert_series_equal(agg, expected.loc[agg.index], check_names=False, check_freq=False)


def test_chaining_uses_december_relatives():
    # b doubles in 2003 then stays; weights 50/50 each year -> 2003 Dec = 150, 2004 constant
    panel = _panel({"a": lambda t: 100 + 0 * t, "b": lambda t: np.where(t >= 13, 200.0, 100.0)})
    agg = aggregate.aggregate_index(panel, _weights({"a": 1, "b": 1}))
    assert np.isclose(agg["2003-12-01"], 150) and np.isclose(agg["2004-06-01"], 150)


def test_quarterly_yoy_two_percent():
    idx = pd.date_range("2000-01-01", "2005-12-01", freq="MS")
    s = pd.Series(100 * 1.02 ** (np.arange(len(idx)) / 12), index=idx)
    q = aggregate.quarterly_yoy(s).dropna()
    assert np.allclose(q, 2.0)
