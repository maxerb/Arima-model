"""Tests for T1.5: annual item weights and the collection calendar (D-26 ... D-28)."""

import numpy as np
import pandas as pd
import pytest

from arima_snb import panel
from arima_snb.config import FINAL


def _series(values, start):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="MS"), dtype=float)


def test_infer_collection_flat_month_is_not_collected():
    lp = np.log(_series([100, 100, 101, 101, 101.05, 102], "2010-01-01"))
    c = panel.infer_collection(lp)
    assert np.isnan(c.iloc[0])                              # first month: no change -> unknown
    assert c.iloc[1:].tolist() == [False, True, False, False, True]   # 101 -> 101.05 is < 1e-3 in logs


def test_collection_pattern_uses_previous_year_only():
    """No look-ahead: changing flags in the origin's year or later must not change the pattern."""
    dates = pd.date_range("2008-01-01", "2010-12-01", freq="MS")
    coll = pd.DataFrame({"date": dates, "item_id": "x", "source": "inferred",
                         "collected": [d.month in (2, 5, 8, 11) for d in dates]})
    origin = pd.Timestamp("2010-05-01")
    a = panel.collection_pattern(coll, "x", origin)
    coll2 = coll.copy()
    coll2.loc[coll2.date >= "2010-01-01", "collected"] = True
    assert a == panel.collection_pattern(coll2, "x", origin) == [2, 5, 8, 11]


def test_weight_years_cover_mixed_baskets():
    assert panel.weight_years("LIK1993")[1993] == list(range(1993, 2000))
    assert panel.weight_years("LIK2000")[2000] == [2000, 2001]


@pytest.mark.skipif(not (FINAL / "weights.csv").exists(), reason="run scripts/03_build_weights_collection.py")
def test_weights_contract():
    w = pd.read_csv(FINAL / "weights.csv")
    assert list(w.columns) == ["year", "item_id", "weight"]
    assert not w.duplicated(["year", "item_id"]).any() and (w.weight > 0).all()
    cov = w.groupby("year").weight.sum()
    assert np.isclose(cov[2010], 92.701, atol=0.002)        # paper 92.788 minus the skirts misprint
    assert (cov.loc[2000:2015] > 90).all()                  # replication period fully covered
    # D-27: shared coats + jackets position split, total equals the merged BFS weight
    piv = w.pivot(index="year", columns="item_id", values="weight")
    assert piv.loc[2016, "i073"] / piv.loc[2016, "i076"] == pytest.approx(piv.loc[2015, "i073"] / piv.loc[2015, "i076"])


@pytest.mark.skipif(not (FINAL / "collection.csv").exists(), reason="run scripts/03_build_weights_collection.py")
def test_collection_contract_and_paper_chart1():
    c = pd.read_csv(FINAL / "collection.csv", parse_dates=["date"])
    assert set(c.source) == {"calendar", "inferred"}
    inf = c[(c.source == "inferred") & (c.item_id == "i075")]       # women's trousers, paper Chart 1
    per_year = inf.groupby(inf.date.dt.year).collected.sum()
    assert per_year.loc[2002:2007].eq(4).all() and per_year.loc[2011:2012].eq(12).all()
    rent = c[(c.source == "calendar") & (c.item_id == "i094") & (c.date.dt.year == 2009)]
    assert sorted(rent.loc[rent.collected == True, "date"].dt.month) == [2, 5, 8, 11]  # noqa: E712
