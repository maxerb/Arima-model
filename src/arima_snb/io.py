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

    # Dimension columns D0, D1, ... (one for simple cubes like plkopr, two for devkum/zikrepro/snbiprogq).
    # Their codes are joined with "_" into one code, e.g. "M0_USD1" (devkum) or "M_MV" (zikrepro).
    dims = [c for c in df.columns if c.startswith("D") and c[1:].isdigit()]
    df["code"] = df[dims].astype(str).agg("_".join, axis=1)
    df = df.rename(columns={"Date": "date", "Value": "value"})

    # Monthly cubes: "2000-01" -> 2000-01-01. Quarterly cubes (snbiprogq, T1.2): "2004-Q2" -> first month of
    # the quarter, 2004-04-01. format= says exactly how to read it.
    if df["date"].astype(str).str.contains("Q").any():
        df["date"] = pd.PeriodIndex(df["date"].str.replace("-", ""), freq="Q").start_time
    else:
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


# ---------------------------------------------------------------------------
# BFS/SFSO consumer price index (LIK) detail results (T1.1)
# ---------------------------------------------------------------------------
# Layout checked 24.11.2026 on the files from scripts/00_download_bfs_cpi.py:
#  - header in row 4 (index 3) of the first sheet (the "INDEX_m" sheet in the .xlsx files from 2015 on);
#  - old .xls files (bases 1993-2010): column 0 = position number, names spread over several columns
#    (one column per hierarchy level, like an indented outline);
#  - new .xlsx files (2015 on): column 1 = "PosNo", column 3 = "Level", column 5 = German name;
#  - monthly index values sit in the columns whose header is a date; weight columns have year headers;
#  - rows without a position number (special aggregates, footnotes) are dropped.
# LIK10B10 has a second sheet "vor Mai 2000" (old basket rescaled); we read only the first sheet (from May 2000).

BFS_HEADER_ROW = 3


def _bfs_index_sheet(path: Path) -> pd.DataFrame:
    """Read the monthly-index sheet of a BFS LIK detail file with no header (raw cells)."""
    sheet = "INDEX_m" if path.suffix == ".xlsx" else 0
    return pd.read_excel(path, sheet_name=sheet, header=None)


def read_bfs_cpi_items(path: Path, base_code: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read one BFS LIK detail file (e.g. base_code="LIK10B10").

    Returns
    -------
    long : DataFrame in long format; variable = "<base_code>_<PosNo>", e.g. "LIK10B10_1002".
           Index levels are on this file's own base and must be chain-linked later (T1.4).
    positions : one row per position: base, pos_no, level, name_de.
    """
    raw = _bfs_index_sheet(path)
    header = raw.iloc[BFS_HEADER_ROW]
    body = raw.iloc[BFS_HEADER_ROW + 1:]

    # Date columns: header cell is a date (pandas reads them as Timestamp / datetime)
    date_cols = [c for c, h in header.items() if hasattr(h, "year") and hasattr(h, "month")]  # Timestamp or datetime
    assert len(date_cols) > 12, f"{path.name}: found only {len(date_cols)} date columns"
    first_value_col = min(date_cols)

    if path.suffix == ".xlsx":
        assert header[1] == "PosNo" and header[5] == "Position_D", f"{path.name}: unexpected header"
        pos_no = pd.to_numeric(body[1], errors="coerce")
        level = pd.to_numeric(body[3], errors="coerce")
        name = body[5]
    else:
        assert str(header[0]).strip().startswith(("Nr", "GP")), f"{path.name}: unexpected header"
        pos_no = pd.to_numeric(body[0], errors="coerce")
        # Label columns: between the position number (and COICOP/Pos, if present) and the first value column.
        # The hierarchy level is the column in which the name is written (indented outline).
        def is_weight_header(h) -> bool:
            s = str(h).strip()
            return s.startswith("Gewicht") or s[:4].isdigit()

        first_weight_col = min(c for c, h in header.items() if pd.notna(h) and is_weight_header(h))
        label_cols = [c for c in range(1, first_weight_col)
                      if str(header[c]).strip() not in ("COICOP", "Pos")]
        labels = body[label_cols]
        name = labels.bfill(axis=1).iloc[:, 0]
        level = labels.notna().values.argmax(axis=1) + 1
        level = pd.Series(level, index=body.index)

    # The main basket hierarchy comes first; below it BFS lists "Sondergliederungen" (special groupings such as
    # goods/services) that reuse small position numbers. Keep only the first occurrence = the basket position;
    # the special groupings can be rebuilt from the items (snb-arima-aggregate).
    keep = pos_no.notna() & ~pos_no.duplicated(keep="first")
    positions = pd.DataFrame({"base": base_code, "pos_no": pos_no[keep].astype(int),
                              "level": level[keep], "name_de": name[keep].astype(str).str.strip()})

    values = body.loc[keep, date_cols].apply(pd.to_numeric, errors="coerce")
    values.columns = pd.to_datetime([header[c] for c in date_cols]).to_period("M").to_timestamp()
    values.index = base_code + "_" + positions["pos_no"].astype(str)
    long = (values.rename_axis("variable").reset_index()
            .melt(id_vars="variable", var_name="date", value_name="value")
            .dropna(subset=["value"]))
    long["date"] = pd.to_datetime(long["date"])  # melt leaves the column headers as object dtype
    long["source"] = f"BFS LIK detail results {base_code} ({path.name})"
    return long[LONG_COLUMNS].reset_index(drop=True), positions.reset_index(drop=True)


def read_bfs_weights(path: Path) -> pd.DataFrame:
    """Read the BFS GEWICHTUNGEN file: annual weights of every position, per basket.

    Returns long DataFrame: basket (sheet name, e.g. "LIK2010"), pos_no, year, weight (in % of the total).
    Weights of year y apply Jan-Dec of y with base December y-1 (chained Laspeyres, AGENTS.md §7).
    The first weight column of the 2000 basket is labelled "2000/01" (May 2000 - Dec 2001); we store it as
    year 2000 and leave the mapping to months to the panel step (T1.5). LIK1993 has one fixed weight
    ("Gewichte / Poids"), stored as year 1993.
    """
    out = []
    for sheet in ["LIK1993", "LIK2000", "LIK2005", "LIK2010", "LIK2015", "LIK2020", "LIK2025"]:
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        header = raw.iloc[BFS_HEADER_ROW]
        body = raw.iloc[BFS_HEADER_ROW + 1:]
        pos_col = header[header == "PosNo"].index[0]
        year_cols = {}
        for c, h in header.items():
            s = str(h).strip()
            if s.startswith("Gewichte"):
                year_cols[c] = 1993
            elif s[:4].isdigit() and 1990 < int(s[:4]) < 2100:
                year_cols[c] = int(s[:4])
        assert year_cols, f"{sheet}: no weight columns"
        pos_no = pd.to_numeric(body[pos_col], errors="coerce")
        for c, year in year_cols.items():
            w = pd.to_numeric(body[c], errors="coerce")
            ok = pos_no.notna() & w.notna()
            out.append(pd.DataFrame({"basket": sheet, "pos_no": pos_no[ok].astype(int),
                                     "year": year, "weight": w[ok]}))
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------------------
# FRED daily series (T1.2): crude oil spot prices, USDCHF
# ---------------------------------------------------------------------------
# Layout checked 24.11.2026: header "observation_date,<SERIES_ID>", one row per business day,
# holidays are empty cells (older files used "."), which we drop.

def read_fred(path: Path) -> pd.DataFrame:
    """Read a FRED fredgraph.csv download into long format with DAILY dates.

    The pipeline averages to months later (oil ECM, D-14); the daily data are kept here because the
    current-month oil nowcast uses prices from before the BFS collection day (paper p. 7).
    """
    df = pd.read_csv(path, na_values=["."])
    sid = df.columns[1]
    df = df.rename(columns={"observation_date": "date", sid: "value"})
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df["variable"] = "fred_" + sid
    df["source"] = "FRED, series " + sid
    df = df.dropna(subset=["value"])
    return df[LONG_COLUMNS].reset_index(drop=True)
