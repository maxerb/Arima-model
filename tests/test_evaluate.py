"""T3.1 pseudo-OOS engine: origins, no look-ahead, trivial benchmark reproduced exactly, RMSFE."""

import numpy as np
import pandas as pd
import pytest

from arima_snb import aggregate, evaluate
from arima_snb.config import FINAL

needs_data = pytest.mark.skipif(not (FINAL / "item_specs.csv").exists(), reason="run scripts/01-05 first")

ORIGIN = pd.Timestamp("2008-08-01")
# monthly items, a quarterly-collected item, heating oil (ECM) and rents: covers every code path
SUBSET = ["i001", "i006", "i029", "i100", "i130", "i094"]


def test_origins_are_second_month_of_quarter():
    o = evaluate.evaluation_origins()
    assert len(o) == 32 and o[0] == pd.Timestamp("2004-02-01") and o[-1] == pd.Timestamp("2011-11-01")
    assert {d.month for d in o} == {2, 5, 8, 11}


def test_swap_items_replaces_only_given_items():
    base = pd.DataFrame({"item_id": ["a", "a", "b"], "target": [1, 2, 1], "log_p_hat": [0.0, 0.0, 0.0]})
    repl = pd.DataFrame({"item_id": ["b"], "target": [1], "log_p_hat": [9.0]})
    out = evaluate.swap_items(base, repl).set_index("item_id")
    assert (out.loc["a", "log_p_hat"] == 0).all() and out.loc["b", "log_p_hat"] == 9.0


def test_rmsfe_by_h():
    ev = pd.DataFrame({"model": "m", "h": [1, 1, 2, 2], "pi_hat": [0, 0, 0, 0], "pi_actual": [3, 4, 1, -1]})
    t = evaluate.rmsfe_by_h(ev)
    assert np.isclose(t.loc["m", 1], np.sqrt(12.5)) and np.isclose(t.loc["m", 2], 1.0)


def _subset_inputs():
    inp = evaluate.load_inputs()
    inp["panel"] = inp["panel"][inp["panel"].item_id.isin(SUBSET)]
    inp["index_wide"] = inp["index_wide"][SUBSET]
    inp["specs"] = inp["specs"][inp["specs"].item_id.isin(SUBSET)]
    inp["items"] = inp["items"][inp["items"].item_id.isin(SUBSET)]
    inp["weights"] = inp["weights"][inp["weights"].item_id.isin(SUBSET)]
    inp["collection"] = inp["collection"][inp["collection"].item_id.isin(SUBSET)]
    return inp


def _perturb_after(inp: dict, origin: pd.Timestamp) -> dict:
    """Change every piece of data that is NOT known at `origin`."""
    rng = np.random.default_rng(0)
    out = dict(inp)
    p = inp["panel"].copy()
    late = p.date > origin
    p.loc[late, "log_p"] += rng.normal(0, 0.2, late.sum())
    p.loc[late, "index"] = np.exp(p.loc[late, "log_p"])
    out["panel"] = p
    w = inp["index_wide"].copy()
    w.loc[w.index > origin] *= 1.7
    out["index_wide"] = w
    c = inp["collection"].copy()
    c.loc[c.date > origin, "collected"] = ~c.loc[c.date > origin, "collected"].astype(bool)
    out["collection"] = c
    wt = inp["weights"].copy()
    wt.loc[wt.year > origin.year, "weight"] *= rng.uniform(0.2, 5, (wt.year > origin.year).sum())
    out["weights"] = wt
    s = inp["specs"].copy()   # spec vintages built with data after the origin must not be used (D-31)
    later = s.vintage >= origin.year
    s.loc[later, "seasonal"] = ~s.loc[later, "seasonal"].astype(bool)
    s.loc[later, "quarterly_lags"] = ~s.loc[later, "quarterly_lags"].astype(bool)
    out["specs"] = s
    cr = inp["crude"].copy()
    cr[cr.index >= origin + pd.DateOffset(months=1)] *= 2.0   # crude known only before the 1st of origin+1
    out["crude"] = cr
    if inp.get("mortgage") is not None:
        m = inp["mortgage"].copy()
        m[m.index >= origin + pd.DateOffset(months=1)] += 3.0
        out["mortgage"] = m
    return out


@needs_data
def test_no_look_ahead():
    inp = _subset_inputs()
    base = evaluate.forecast_origin(inp, ORIGIN, n_jobs=1, cache=None)
    pert = evaluate.forecast_origin(_perturb_after(inp, ORIGIN), ORIGIN, n_jobs=1, cache=None)
    for model in (evaluate.MODEL_PLAIN, evaluate.MODEL_SPECIAL):
        a, b = base[model]["quarterly"], pert[model]["quarterly"]
        assert a.pi_hat.notna().all()
        np.testing.assert_allclose(a.pi_hat.to_numpy(), b.pi_hat.to_numpy(), rtol=0, atol=1e-10)
        np.testing.assert_allclose(base[model]["items"].log_p_hat.to_numpy(),
                                   pert[model]["items"].log_p_hat.to_numpy(), rtol=0, atol=1e-12)
    # oil items really use the ECM in the special variant and differ from the plain ARIMA
    sp = base[evaluate.MODEL_SPECIAL]["items"].set_index(["item_id", "target"]).log_p_hat
    pl = base[evaluate.MODEL_PLAIN]["items"].set_index(["item_id", "target"]).log_p_hat
    assert (sp.loc["i100"] - pl.loc["i100"]).abs().max() > 1e-6


@needs_data
def test_random_walk_benchmark_reproduced_exactly():
    """Items flat after the origin -> aggregate flat -> h = 1 forecast known analytically."""
    inp = _subset_inputs()
    origin = ORIGIN
    targets = pd.date_range(origin + pd.DateOffset(months=1), periods=13, freq="MS")
    last = inp["panel"][inp["panel"].date == origin].set_index("item_id").log_p
    fc = pd.DataFrame([dict(item_id=i, target=t, log_p_hat=v) for i, v in last.items() for t in targets])
    _, q = evaluate.aggregate_origin(inp, fc, origin, "rw")
    total = aggregate.aggregate_index(inp["index_wide"], inp["weights"])
    m1, m2 = origin - pd.DateOffset(months=1), origin
    q_now = (total[m1] + 2 * total[m2]) / 3
    q_prev = total[m1 - pd.DateOffset(months=12): m2 + pd.DateOffset(months=-11)].mean()
    expected_h1 = 100 * (q_now / q_prev - 1)
    got = q[(q["aggregate"] == "total") & (q.h == 1)].pi_hat.iloc[0]
    assert np.isclose(got, expected_h1, atol=1e-8)
