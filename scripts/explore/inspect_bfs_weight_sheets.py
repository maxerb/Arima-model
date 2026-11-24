"""Explore (T1.1): which weight years exist in the GEWICHTUNGEN file and the 'Weights' sheet of LIK25B25."""
import warnings
import pandas as pd
from arima_snb.config import RAW
warnings.filterwarnings("ignore")
g = next(RAW.glob("GEWICHTUNGEN*"))
for s in ["LIK2010", "LIK2015", "LIK2020", "LIK20->LIK25", "LIK2025"]:
    d = pd.read_excel(g, sheet_name=s, header=None)
    print(s, d.shape, list(d.iloc[3].dropna())[:20], "rows:", len(d))
w = pd.read_excel(next(RAW.glob("LIK25B25*")), sheet_name="Weights", header=None)
print("LIK25B25 Weights", w.shape); print(w.iloc[:6, :20].to_string())
