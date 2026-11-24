"""Tests for the item panel (T1.4): chain-linking, merging split items, Table 9 matching, output contract."""

import numpy as np
import pandas as pd
import pytest

from arima_snb import panel
from arima_snb.config import FINAL


def _series(values, start):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="MS"), dtype=float)


def test_chain_link_keeps_growth_rates():
    old = _series([100, 102, 104], "2005-10-01")          # Oct-Dec 2005 on old base
    new = _series([100, 101, 103], "2005-12-01")          # Dec 2005 = 100 on new base
    linked = panel.chain_link(old, new, pd.Timestamp("2005-12-01"))
    assert linked.loc["2005-12-01"] == 104                 # old level kept up to the link month
    assert np.isclose(linked.loc["2006-01-01"] / linked.loc["2005-12-01"], 1.01)
    assert np.isclose(linked.loc["2006-02-01"] / linked.loc["2006-01-01"], 103 / 101)


def test_chain_link_no_look_ahead_before_link():
    """Changing data after the link month must not change any value up to the link month."""
    old = _series([100, 102, 104], "2005-10-01")
    new = _series([100, 101, 103], "2005-12-01")
    a = panel.chain_link(old, new, pd.Timestamp("2005-12-01"))
    new2 = new.copy()
    new2.iloc[1:] *= 1.5
    b = panel.chain_link(old, new2, pd.Timestamp("2005-12-01"))
    assert a.loc[:"2005-12-01"].equals(b.loc[:"2005-12-01"])


def test_chain_link_missing_overlap_raises():
    with pytest.raises(ValueError):
        panel.chain_link(_series([1, 2], "2005-01-01"), _series([1, 2], "2006-01-01"), pd.Timestamp("2005-12-01"))


def test_match_table9_respects_order():
    """Duplicate weights are resolved by keeping the Table 9 order of BFS positions."""
    pos = pd.DataFrame({"name_de": list("abcd")}, index=pd.Index([10, 20, 30, 40], name="pos_no"))
    weights = pd.Series([0.5, 0.2, 0.5, 0.3], index=pos.index)
    t9 = pd.DataFrame({"weight_2010": [0.2, 0.5, 0.3]})
    out = panel.match_table9_to_basket(t9, pos, weights)
    assert out.tolist() == [20, 30, 40]                    # 0.5 -> 30 (after 20), not 10


def test_name_similarity_ignores_retail_qualifier():
    assert panel.words_contained("Bier", "Bier (Detailhandel)")
    assert panel.name_similarity("Tee", "Tee (Detailhandel)") == 1.0


@pytest.mark.skipif(not (FINAL / "cpi_items_long.csv").exists(), reason="run scripts/02_build_item_panel.py")
def test_panel_contract():
    items = pd.read_csv(FINAL / "items.csv")
    long = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    assert len(items) == 182 and items["item_id"].is_unique
    assert np.isclose(items["weight_2010"].sum(), 92.788)
    assert set(long.columns) == {"date", "item_id", "index", "log_p"}
    assert not long.duplicated(["date", "item_id"]).any()
    assert long["index"].gt(0).all() and long["log_p"].notna().all()
    assert (long["date"].dt.day == 1).all()
    # every item is observed every month from May 2000 to Dec 2015 (replication + early extension sample)
    core = long[(long.date >= "2000-05-01") & (long.date <= "2015-12-01")]
    assert core.groupby("item_id").size().eq(188).all()
    # reference month Dec 2010 = 100
    assert np.allclose(long.loc[long.date == "2010-12-01", "index"], 100)


def test_agg6_rules_file_complete():
    """Every paper item has a valid hand rule for agg6 (D-21 rev.)."""
    from arima_snb.config import META
    rules = pd.read_csv(META / "agg6_rules.csv")
    assert len(rules) == 182 and rules["item_id"].is_unique
    assert set(rules["type"]) <= {"goods", "private", "public"}
    assert set(rules["origin"]) <= {"domestic", "imported", "data"}
    assert rules["reason"].notna().all()


@pytest.mark.skipif(not (FINAL / "items.csv").exists(), reason="run scripts/02_build_item_panel.py")
def test_agg6_labels():
    items = pd.read_csv(FINAL / "items.csv").set_index("item_id")
    assert items["agg6"].notna().all() and items["agg6"].nunique() == 6
    assert (items.loc[items.special == "oil", "agg6"] == "Oil products").all()
    assert (items.loc[items.special == "rent", "agg6"] == "Rents").all()
    # public services close to the paper's 8.711 (items cover all public services of the basket).
    # Use the BFS 2010 weights (weights.csv, T1.5): Table 9 prints some weights one row off (D-22 note).
    if (FINAL / "weights.csv").exists():
        w = pd.read_csv(FINAL / "weights.csv").query("year == 2010").set_index("item_id")["weight"]
        assert abs(w[items.agg6 == "Public services"].sum() - 8.711) < 0.5
