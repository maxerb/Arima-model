"""Loader for SNB data portal cubes.

Turns one SNB CSV file into the long format used by the whole pipeline:
date, variable, value, source
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def read_snb_cube(path, cube_id):
    """Read one SNB cube CSV and return it in long format."""
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
    return df[["date", "variable", "value", "source"]].reset_index(drop=True)


if __name__ == "__main__":
    # Quick test on the file you saved by hand
    path = RAW / "snb-data-zimoma-en-all-20261102_1430.csv"
    df = read_snb_cube(path, "zimoma")
    print(df.head(10))
    print(df.dtypes)
    print(df["variable"].value_counts())
    print(df[df["variable"] == "zimoma_SARON"].head(10))