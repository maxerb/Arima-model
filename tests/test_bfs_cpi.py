"""T1.1: BFS CPI loaders return clean long data (skipped if the raw files are not downloaded)."""

import pytest

from arima_snb.io import LONG_COLUMNS, find_raw, read_bfs_cpi_items, read_bfs_weights

BASES = ["LIK93B93", "LIK00B00", "LIK05B05", "LIK10B10", "LIK15B15", "LIK20B20", "LIK25B25"]


def _raw(pattern):
    try:
        return find_raw(pattern)
    except FileNotFoundError:
        pytest.skip("raw BFS file missing; run scripts/00_download_bfs_cpi.py")


@pytest.mark.parametrize("code", BASES)
def test_items_long_format(code):
    long, pos = read_bfs_cpi_items(_raw(f"{code}_*"), code)
    assert list(long.columns) == LONG_COLUMNS
    assert not long.duplicated(["date", "variable"]).any()
    assert (long["date"].dt.day == 1).all()
    # Levels > 1000 are real: PCs and TVs back-cast to the 1980s (scripts/explore/check_bfs_extreme_values.py)
    assert (long["value"] > 0).all(), "index levels must be positive (we take logs)"
    assert pos["pos_no"].is_unique and len(pos) > 250
    assert pos["name_de"].iloc[0] == "Total"


def test_weights_sum_to_100():
    w = read_bfs_weights(_raw("GEWICHTUNGEN_*"))
    total = w[w["pos_no"].isin([10, 100])].groupby(["basket", "year"])["weight"].first()
    assert (total.round(3) == 100).all()
    assert set(range(2002, 2027)) <= set(w["year"])
