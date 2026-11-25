"""T4.2: extended ARIMA(182) pseudo-OOS - no look-ahead, DMW-HLN against hand-computed examples, table layout."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from arima_snb.kalman_eval import MODEL_KALMAN, comparison_table, dmw_hln, kalman_item_forecasts

ORIGIN = pd.Timestamp("2008-05-01")


def _inputs(seed: int = 0) -> dict:
    """Two synthetic items 1993-2010: one collected monthly, one quarterly (prices carried forward in between)."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("1993-01-01", "2010-12-01", freq="MS")
    rows, coll = [], []
    for item_id, quarterly in (("i001", False), ("i002", True)):
        lp = np.cumsum(0.002 + rng.normal(0, 0.01, len(dates)))
        collected = dates.month.isin([2, 5, 8, 11]) if quarterly else np.ones(len(dates), bool)
        collected[0] = True
        lp = pd.Series(lp, index=dates).where(collected).ffill()
        rows.append(pd.DataFrame({"date": dates, "item_id": item_id, "log_p": lp.values,
                                  "index": np.exp(lp.values)}))
        coll.append(pd.DataFrame({"date": dates, "item_id": item_id, "collected": collected,
                                  "source": "inferred"}))
    return {"panel": pd.concat(rows, ignore_index=True), "collection": pd.concat(coll, ignore_index=True)}


ORDERS = pd.DataFrame({"vintage": [2007, 2007], "item_id": ["i001", "i002"], "p": [1, 1],
                       "seasonal": [False, False]})


def test_no_look_ahead():
    """Changing every price and collection flag after the origin leaves the extended-model forecasts unchanged."""
    base = _inputs()
    fc, _ = kalman_item_forecasts(base, ORDERS, ORIGIN, n_jobs=1, cache=None)
    pert = _inputs()
    late = pert["panel"].date > ORIGIN
    pert["panel"].loc[late, "log_p"] += 5.0
    pert["panel"].loc[late, "index"] *= 100.0
    pert["collection"].loc[pert["collection"].date > ORIGIN, "collected"] = True
    fc2, _ = kalman_item_forecasts(pert, ORDERS, ORIGIN, n_jobs=1, cache=None)
    pd.testing.assert_frame_equal(fc, fc2)
    assert fc.groupby("item_id").size().eq(13).all() and fc.target.min() == ORIGIN + pd.offsets.MonthBegin(1)


def test_quarterly_item_carries_forward_between_expected_collections():
    """Published-like path of the quarterly item moves only in Feb/May/Aug/Nov (collection months of 2007)."""
    fc, log = kalman_item_forecasts(_inputs(), ORDERS, ORIGIN, n_jobs=1, cache=None)
    q = fc[fc.item_id == "i002"].set_index("target").log_p_hat
    moved = q.diff().abs().gt(0)
    assert set(q.index[moved].month) <= {2, 5, 8, 11}
    assert (log.n_months_collected.tolist() == [12, 4])


def test_dmw_hln_hand_example_h1():
    d_bench, d_ref = np.sqrt([1.0, 0.0, 2.0, 0.0]), np.sqrt([0.0, 1.0, 0.0, 0.0])   # d = [1, -1, 2, 0]
    stat, p = dmw_hln(d_bench, d_ref, h=1)
    dm = 0.5 / np.sqrt(1.25 / 4)                        # d_bar = 0.5, gamma_0 = 1.25
    hln = dm * np.sqrt((4 + 1 - 2) / 4)
    assert stat == pytest.approx(hln) and p == pytest.approx(2 * stats.t.sf(hln, 3))


def test_dmw_hln_hand_example_h2_newey_west_fallback():
    """With h = 2 the rectangular variance is negative here (gamma_1 = -0.9375) -> Bartlett weights."""
    stat, _ = dmw_hln(np.sqrt([1.0, 0.0, 2.0, 0.0]), np.sqrt([0.0, 1.0, 0.0, 0.0]), h=2)
    v = 1.25 + 2 * 0.5 * (-0.9375)
    expected = 0.5 / np.sqrt(v / 4) * np.sqrt((4 + 1 - 4 + 2 / 4) / 4)
    assert stat == pytest.approx(expected)


def test_dmw_equal_errors_not_significant_and_table_layout():
    rng = np.random.default_rng(3)
    rows = []
    for h in (1, 2):
        act = rng.normal(size=40)
        for m, noise in ((MODEL_KALMAN, 0.5), ("arima182", 1.0)):
            rows.append(pd.DataFrame({"origin_q": [f"q{i}" for i in range(40)], "h": h, "model": m,
                                      "pi_actual": act, "pi_hat": act + rng.normal(0, noise, 40)}))
    tab = comparison_table(pd.concat(rows), MODEL_KALMAN, ["arima182"])
    rel = tab[tab.row == "arima182"]
    assert (rel.value > 1).all() and (rel.p_value < 0.10).all() and (tab["T"] == 40).all()
    e = rng.normal(size=50)
    assert np.isnan(dmw_hln(e, e, 1)[1])               # identical errors: zero variance -> no test
