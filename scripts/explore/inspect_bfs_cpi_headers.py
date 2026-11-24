"""Explore (T1.1): print the header row of the index sheet of each CPI file to locate weight and date columns."""
import warnings
import pandas as pd
from arima_snb.config import RAW
warnings.filterwarnings("ignore")
for f in sorted(RAW.glob("LIK*")):
    sheet = "INDEX_m" if f.suffix == ".xlsx" else 0
    h = pd.read_excel(f, sheet_name=sheet, header=None, nrows=4).iloc[3]
    print(f.name, [(i, v) for i, v in h.items() if pd.notna(v)][:14], "... last:", list(h.dropna().items())[-2:])
