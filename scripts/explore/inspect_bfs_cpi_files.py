"""Explore (T1.1): print sheet names and the top-left corner of each BFS CPI raw file to learn the layout."""
import sys
import pandas as pd
from arima_snb.config import RAW

for f in sorted(RAW.glob("LIK*")) + sorted(RAW.glob("GEWICHTUNGEN*")):
    xl = pd.ExcelFile(f)
    print("=" * 30, f.name, xl.sheet_names)
    sheet = sys.argv[1] if len(sys.argv) > 1 else xl.sheet_names[0]
    df = pd.read_excel(f, sheet_name=0, header=None, nrows=8)
    print(df.iloc[:8, :12].to_string())
    print("shape cols:", pd.read_excel(f, sheet_name=0, header=None).shape)
