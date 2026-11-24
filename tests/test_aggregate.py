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


# ---------------------------------------------------------------------------------------------------------
# T2.5: aggregation of item forecasts
# ---------------------------------------------------------------------------------------------------------
ORIGIN = pd.Timestamp("2003-05-01")


def _items() -> pd.DataFrame:
    return pd.DataFrame({"item_id": ["a", "b", "c"], "agg6": ["G1", "G1", "Oil products"],
                         "agg14": ["X", "Y", "Y"], "special": [None, None, "oil"]})


def _item_fc(origin=ORIGIN, steps=13, growth=None) -> pd.DataFrame:
    """Forecast log prices: each item grows 0.2 % per month from its last actual value (panel below)."""
    g0 = np.log(1.002)
    growth = growth or {"a": g0, "b": g0, "c": g0}
    panel = _panel3()
    rows = []
    for k, g in growth.items():
        last = np.log(panel.loc[origin, k])
        for s in range(1, steps + 1):
            rows.append(dict(target=origin + pd.DateOffset(months=s), item_id=k, log_p_hat=last + g * s))
    return pd.DataFrame(rows)


def _panel3() -> pd.DataFrame:
    return _panel({"a": lambda t: 100 * 1.002 ** t, "b": lambda t: 100 * 1.002 ** t, "c": lambda t: 100 * 1.002 ** t})


def test_weights_known_at_drops_future_and_extends_latest():
    w = _weights({"a": 1, "b": 2}, years=range(2002, 2005)).copy()
    w.loc[w.year == 2004, "weight"] = 99.0      # next year's weights: must not be used at a 2003 origin
    known = aggregate.weights_known_at(w, ORIGIN, last_year=2004)
    assert set(known.year) == {2002, 2003, 2004}
    assert (known[known.year == 2004].set_index("item_id").weight == known[known.year == 2003].set_index("item_id").weight).all()


def test_identical_item_forecasts_give_that_path_and_horizons():
    agg = aggregate.forecast_aggregates(_panel3(), _weights({"a": 1, "b": 2, "c": 3}), _items(), _item_fc(), ORIGIN)
    tot = agg[agg["aggregate"] == "total"].set_index("target").index_hat
    path = 100 * 1.002 ** np.arange(len(tot))   # every item grows 0.2 % per month, actual and forecast
    assert np.allclose(tot.values, path)
    q = aggregate.forecast_quarterly_yoy(agg)
    qt = q[q["aggregate"] == "total"]
    assert list(qt.h) == [1, 2, 3, 4, 5]
    assert list(qt.target_q.astype(str)) == ["2003Q2", "2003Q3", "2003Q4", "2004Q1", "2004Q2"]  # h = 1 is origin's quarter
    assert np.allclose(qt.pi_hat, 100 * (1.002 ** 12 - 1))


def test_forecast_aggregates_no_look_ahead():
    """Perturbing actual prices after the origin and weights of later years must not change the forecast."""
    panel, w, items, fc = _panel3(), _weights({"a": 1, "b": 2, "c": 3}), _items(), _item_fc()
    base = aggregate.forecast_aggregates(panel, w, items, fc, ORIGIN)
    panel2 = panel.copy()
    panel2.loc[panel2.index > ORIGIN] *= 1.5
    w2 = w.astype({"weight": float})
    w2.loc[w2.year > ORIGIN.year, "weight"] = [10.0, 0.1, 5.0]
    pert = aggregate.forecast_aggregates(panel2, w2, items, fc, ORIGIN)
    pd.testing.assert_frame_equal(base, pert)


def test_excl_oil_and_groups():
    fc = _item_fc(growth={"a": 0.002, "b": 0.002, "c": 0.02})   # oil item c jumps
    agg = aggregate.forecast_aggregates(_panel3(), _weights({"a": 1, "b": 2, "c": 3}), _items(), fc, ORIGIN)
    last = agg.target.max()
    v = agg[agg.target == last].set_index("aggregate").index_hat
    assert v["excl_oil"] < v["total"]
    assert np.isclose(v["excl_oil"], v["agg6:G1"])           # excl. oil = items a and b = group G1 here
    assert {"agg14:X", "agg14:Y", "agg6:Oil products"} <= set(v.index)


def test_subaggregates_add_up_to_total_incl_late_group():
    """Sub-aggregate indices re-aggregated with summed weights give the item total, also when a group starts late."""
    panel = _panel({"a": lambda t: 100 * 1.003 ** t, "b": lambda t: 100 + 5 * np.sin(t),
                    "c": lambda t: np.where(t >= 13, 100 * 1.01 ** t, np.nan)})   # c enters in Jan 2003
    w = _weights({"a": 1, "b": 2})
    w = pd.concat([w, pd.DataFrame(dict(year=[2003, 2004], item_id="c", weight=3.0))], ignore_index=True)
    items = _items()
    total = aggregate.aggregate_index(panel, w)
    subs = aggregate.build_subaggregate_series(panel, w, items, "agg6")
    assert subs["Oil products"].notna().sum() > 0                  # the late group's chain starts in Dec 2002
    sw = aggregate.subaggregate_weights(w, items, "agg6").rename(columns={"group": "item_id"})
    back = aggregate.aggregate_index(subs, sw)
    assert np.allclose(back, total.reindex(back.index))
