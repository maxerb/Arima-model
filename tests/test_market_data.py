"""T1.2 loaders: SNB cubes (monthly, multi-dimension, quarterly) and FRED daily series."""

import pandas as pd
import pytest

from arima_snb.config import RAW
from arima_snb.io import find_raw, read_fred, read_snb_cube

needs = pytest.mark.skipif(not list(RAW.glob("snb-data-snbiprogq-*.csv")),
                           reason="run scripts/00_download_market_data.py first")


@needs
@pytest.mark.parametrize("cube", ["plkopr", "devkum", "zikrepro", "snbiprogq"])
def test_snb_cube_long_format(cube):
    df = read_snb_cube(find_raw(f"snb-data-{cube}-*.csv"), cube)
    assert list(df.columns) == ["date", "variable", "value", "source"]
    assert not df.duplicated(["date", "variable"]).any()
    assert (df["date"].dt.day == 1).all()


@needs
def test_quarterly_forecast_dates_are_quarter_starts():
    df = read_snb_cube(find_raw("snb-data-snbiprogq-*.csv"), "snbiprogq")
    assert df["date"].dt.month.isin([1, 4, 7, 10]).all()
    assert "snbiprogq_J2004PL05P_P" in set(df["variable"])


@needs
def test_fred_daily():
    df = read_fred(find_raw("fred_DEXSZUS_*.csv"))
    assert df["date"].is_monotonic_increasing and df["value"].notna().all()
    assert df.loc[df.date.between("2011-08-01", "2011-08-31"), "value"].min() < 0.8  # franc peak Aug 2011
