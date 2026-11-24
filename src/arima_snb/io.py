"""Loaders: turn raw files from data/raw/ into the long format used by the whole pipeline.

Long format (AGENTS.md §4): one row per observation with the columns
    date      first day of the month (pandas Timestamp)
    variable  our name for the series, e.g. "zimoma_SARON"
    value     the number
    source    where it came from, in words
"""

from pathlib import Path

import pandas as pd

from arima_snb.config import RAW

LONG_COLUMNS = ["date", "variable", "value", "source"]


def read_snb_cube(path: Path, cube_id: str) -> pd.DataFrame:
    """Read one SNB data-portal cube CSV and return it in long format.

    Originally written in the thesis repository (src/snb.py, kept in
    scripts/explore/original_snb_loader.py); moved here in T0.0.
    """
    # Layout (checked 19.11.2026): 2 metadata lines, 1 empty line, then the header.
    # sep=";" because SNB uses semicolons; the quotes are removed automatically.
    df = pd.read_csv(path, sep=";", skiprows=3)

    # Give the columns our own names
    df = df.rename(columns={"Date": "date", "D0": "code", "Value": "value"})

    # "2000-01" -> a real date (2000-01-01). format= says exactly how to read it.
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m")

    # New columns, computed for all rows at once
    df["variable"] = cube_id + "_" + df["code"]          # e.g. "snboffzisa_LZ"
    df["source"] = "SNB data portal, cube " + cube_id

    # Drop rows where the value is missing
    df = df.dropna(subset=["value"])

    # Keep only the four standard columns, and renumber the rows 0, 1, 2, ...
    return df[LONG_COLUMNS].reset_index(drop=True)


def find_raw(pattern: str) -> Path:
    """Return the newest file in data/raw/ matching a glob pattern, e.g. 'snb-data-zimoma-*.csv'.

    Raw files keep their original names with the download date, so the newest
    download sorts last.
    """
    matches = sorted(RAW.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file in {RAW} matches {pattern!r}. See docs/data_sources.md.")
    return matches[-1]
