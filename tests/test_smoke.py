"""Smoke tests for T0.0/T0.1: the package imports, paths stay inside the repo, the loader works."""

import importlib
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from arima_snb import config
from arima_snb.io import LONG_COLUMNS, find_raw, read_snb_cube

MODULES = ["config", "io", "panel", "diagnostics", "item_models", "special",
           "aggregate", "evaluate", "kalman_ext", "report"]


@pytest.mark.parametrize("name", MODULES)
def test_modules_import(name):
    importlib.import_module(f"arima_snb.{name}")


def test_all_paths_inside_repo():
    """AGENTS.md §3: nothing is read from or written to folders outside the repository."""
    for name, value in vars(config).items():
        if isinstance(value, Path):
            assert value.resolve().is_relative_to(config.ROOT), f"{name} points outside the repo"


def test_no_parent_paths_in_code():
    """No parent-folder paths in package, scripts or tests (the one-time import script is the exception)."""
    pattern = re.compile(r"\.\./|\.\.\\")
    for folder in ["src", "scripts", "tests"]:
        for py in (config.ROOT / folder).rglob("*.py"):
            if py.name == "00_import_from_thesis_repo.py":
                continue
            assert not pattern.search(py.read_text(encoding="utf-8")), f"parent-folder path in {py}"


@pytest.mark.parametrize("cube", ["zimoma", "snboffzisa"])
def test_snb_loader_long_format(cube):
    df = read_snb_cube(find_raw(f"snb-data-{cube}-*.csv"), cube)
    assert list(df.columns) == LONG_COLUMNS
    assert len(df) > 0
    assert not df.duplicated(["date", "variable"]).any()
    assert (df["date"].dt.day == 1).all()          # monthly dates are first of month


def test_sic_matches_paper_formula():
    """eq. (3): SIC = log(SSE/T) + k*log(T)/T."""
    from arima_snb.item_models import sic
    assert sic(sse=2.0, n_obs=100, n_params=3) == pytest.approx(np.log(0.02) + 3 * np.log(100) / 100)


def test_quarterly_yoy_constant_growth():
    """An index growing exactly 2 % per year gives 2.0 % y-o-y inflation."""
    from arima_snb.aggregate import quarterly_yoy
    dates = pd.date_range("2000-01-01", periods=60, freq="MS")
    index = pd.Series(100 * 1.02 ** (np.arange(60) / 12), index=dates)
    assert quarterly_yoy(index).dropna().to_numpy() == pytest.approx(2.0)
