"""T1.3 checks on the transcribed paper tables in data/meta/ (tracked in git, no raw data needed)."""

import pandas as pd

from arima_snb.config import META


def test_table9_items():
    it = pd.read_csv(META / "items_paper_table9.csv")
    assert len(it) == 182 and it["item_en"].is_unique
    assert round(it["weight_2010"].sum(), 3) == 92.788
    assert it["agg14"].nunique() == 14


def test_table9_subaggregates_sum_to_100():
    sub = pd.read_csv(META / "paper_table9_subaggregates.csv")
    for model in ["ARIMA(6)", "ARIMA(14)"]:
        s = sub[(sub.model == model) & (sub.subaggregate != "TOTAL")]["weight_2010"].sum()
        assert round(s, 3) == 100.0


def test_calendar_months_valid():
    cal = pd.read_csv(META / "collection_calendar_paper.csv")
    assert set(cal["table"]) == {5, 6, 7, 8}
    for m in cal["months"]:
        if m not in ("aperiodic", "seasonal"):
            months = [int(x) for x in m.split(";")]
            assert months == sorted(set(months)) and all(1 <= x <= 12 for x in months)
