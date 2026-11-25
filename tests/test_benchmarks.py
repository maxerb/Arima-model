"""T3.2 benchmarks: no look-ahead, AR(1) arithmetic, SNB/KOF alignment, annual target."""

import numpy as np
import pandas as pd
import pytest

from arima_snb import benchmarks as bm
from arima_snb.config import FINAL

needs_data = pytest.mark.skipif(not (FINAL / "subaggregates_long.csv").exists(), reason="run scripts/01-08 first")
ORIGIN = pd.Timestamp("2008-08-01")


def test_ar1_recovers_known_process():
    """On an exact AR(1) in monthly log changes, the forecast is the analytic iteration c + φ y."""
    dates = pd.date_range("2000-05-01", "2008-08-01", freq="MS")
    y = [0.002]
    for _ in range(len(dates) - 1):
        y.append(0.001 + 0.5 * y[-1] + 0.0)   # no noise: OLS is exact once y has converged...
    y = np.array(y) + np.random.default_rng(0).normal(0, 1e-4, len(y))   # ...so add tiny noise to identify φ
    cpi = pd.Series(100 * np.exp(np.cumsum(y)), index=dates)
    f = bm.forecast_ar1(cpi, dates[-1], steps=3, month_dummies=False)
    dl = np.diff(np.log(np.r_[cpi.iloc[-1], f.index_hat.values]))
    assert np.allclose(dl, 0.002, atol=2e-4)   # stationary mean c / (1 - φ) = 0.002


def test_ar1_month_dummies_reproduce_seasonal_pattern():
    """With month intercepts and a purely seasonal series (φ = 0), each forecast month gets its own mean change."""
    dates = pd.date_range("2000-05-01", "2008-08-01", freq="MS")
    pattern = np.where(dates.month.isin([1, 7]), -0.02, 0.004)
    y = pattern + np.random.default_rng(2).normal(0, 1e-4, len(dates))
    cpi = pd.Series(100 * np.exp(np.cumsum(y)), index=dates)
    f = bm.forecast_ar1(cpi, dates[-1], steps=12)
    dl = np.diff(np.log(np.r_[cpi.iloc[-1], f.index_hat.values]))
    expected = np.where(f.target.dt.month.isin([1, 7]), -0.02, 0.004)
    assert np.allclose(dl, expected, atol=5e-4)


def test_ar1_no_look_ahead():
    dates = pd.date_range("2000-01-01", "2012-12-01", freq="MS")
    cpi = pd.Series(100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0.001, 0.003, len(dates)))), index=dates)
    late = cpi.copy()
    late[late.index > ORIGIN] *= 1.5
    for d in (True, False):
        pd.testing.assert_frame_equal(bm.forecast_ar1(cpi, ORIGIN, month_dummies=d),
                                      bm.forecast_ar1(late, ORIGIN, month_dummies=d))


def test_annual_from_quarterly_uses_actuals_before_origin():
    act = pd.Series(np.arange(8, dtype=float), index=pd.period_range("2008Q1", "2009Q4", freq="Q"))
    q = pd.DataFrame({"origin_q": "2008Q4", "h": [1, 2, 3, 4, 5], "model": "m",
                      "target_q": [str(p) for p in pd.period_range("2008Q4", "2009Q4", freq="Q")],
                      "pi_hat": [10.0, 20, 20, 20, 20]})
    a = bm.annual_from_quarterly(q, act).set_index("h_year").pi_hat
    assert a[0] == pytest.approx((0 + 1 + 2 + 10) / 4) and a[1] == pytest.approx(20)
    q2 = q.assign(origin_q="2008Q3", target_q=[str(p) for p in pd.period_range("2008Q3", "2009Q3", freq="Q")])
    assert np.isnan(bm.annual_from_quarterly(q2, act).set_index("h_year").pi_hat[1])   # 2009Q4 beyond h = 5


@needs_data
def test_snb_and_kof_alignment():
    paths = bm.snb_conditional_paths()
    f = bm.snb_forecast_origin(paths, ORIGIN)
    assert f.origin_q.iloc[0] == pd.Period("2008Q3") and f.pi_hat.notna().all()   # Sept 2008 assessment
    assert bm.snb_forecast_origin(paths, "2004-02-01").pi_hat.isna().all()        # cube starts June 2004
    s = bm.kof_for_origin(bm.kof_consensus(), ORIGIN)
    assert s.survey_q == pd.Period("2008Q3")                                     # D-56: same-quarter survey


@needs_data
def test_subaggregate_benchmarks_no_look_ahead():
    """Perturb every sub-aggregate and CPI value after the origin: ARIMA(1)/(6)/(14) and AR(1) do not change."""
    inp = bm.load_inputs()
    keep = ["agg1:total", "agg6:Rents", "agg6:Oil products", "agg6:Domestic durable goods"]
    inp["sub_panel"] = inp["sub_panel"][inp["sub_panel"].item_id.isin(keep)
                                        | (inp["sub_panel"].level == "agg6")]
    inp["sub_specs"] = inp["sub_specs"][inp["sub_specs"].item_id.isin(inp["sub_panel"].item_id.unique())]
    inp["sub_collection"] = inp["sub_collection"][inp["sub_collection"].item_id.isin(inp["sub_panel"].item_id)]
    base = bm.forecast_origin(inp, ORIGIN, n_jobs=1, cache=None)["quarterly"]

    late = dict(inp)
    p = inp["sub_panel"].copy()
    m = p.date > ORIGIN
    p.loc[m, "log_p"] += np.random.default_rng(0).normal(0, 0.2, m.sum())
    p.loc[m, "index"] = np.exp(p.loc[m, "log_p"])
    late["sub_panel"] = p
    c = inp["sub_collection"].copy()
    c.loc[c.date > ORIGIN, "collected"] = ~c.loc[c.date > ORIGIN, "collected"]
    late["sub_collection"] = c
    late["cpi"] = inp["cpi"].where(inp["cpi"].index <= ORIGIN, inp["cpi"] * 1.3)
    s = inp["sub_specs"].copy()
    s.loc[s.vintage >= ORIGIN.year, "seasonal"] = ~s.loc[s.vintage >= ORIGIN.year, "seasonal"].astype(bool)
    late["sub_specs"] = s
    w = inp["sub_weights"].copy()
    w.loc[w.year > ORIGIN.year, "weight"] *= 3.0
    late["sub_weights"] = w
    pert = bm.forecast_origin(late, ORIGIN, n_jobs=1, cache=None)["quarterly"]
    pd.testing.assert_frame_equal(base, pert)
    assert base.pi_hat.notna().all() and set(base.model) == {"ar1", "ar1_plain", "arima1", "arima6"}


@needs_data
def test_subaggregate_history_has_no_look_ahead():
    """Group history up to the origin rebuilt from items with weights cut at the origin = the stored file."""
    from arima_snb import aggregate

    panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    wide = panel.pivot(index="date", columns="item_id", values="index").asfreq("MS").loc[:ORIGIN]
    weights = pd.read_csv(FINAL / "weights.csv")
    items = pd.read_csv(FINAL / "items.csv")
    rebuilt = aggregate.build_subaggregate_series(wide, weights[weights.year <= ORIGIN.year], items, "agg6")
    stored = bm.subaggregate_panel()
    stored = stored[stored.item_id.str.startswith("agg6:")].pivot(index="date", columns="item_id", values="index")
    stored.columns = stored.columns.str.removeprefix("agg6:")
    common = rebuilt.index.intersection(stored.index)
    assert np.allclose(rebuilt.loc[common, stored.columns], stored.loc[common], equal_nan=True)
