"""Exploration for decision D-06 (G12): what does the KOF Consensus Forecast file contain?

Prints sheet names, the first rows, the date range and the variable names that mention
inflation / CPI, so we can judge whether KOF Consensus can replace Consensus Economics
for 2004-2011. Read-only on data/raw (AGENTS.md rule 4).
"""
import pandas as pd

from arima_snb.config import RAW


def describe(path):
    """Print the structure of one KOF consensus Excel file."""
    print(f"\n=== {path.name}")
    sheets = pd.read_excel(path, sheet_name=None, header=None)
    for name, df in sheets.items():
        print(f"--- sheet {name!r}: shape {df.shape}")
        # Row 0 holds the variable names, column 0 the survey dates
        labels = [str(v) for v in df.iloc[0]]
        dates = pd.to_datetime(df.iloc[1:, 0], errors="coerce").dropna()
        print("survey dates:", dates.min().date(), "to", dates.max().date(), f"({len(dates)} surveys)")
        hits = [v for v in labels if any(k in v.lower() for k in ("infl", "cpi", "lik", "teuer", "prices"))]
        print("inflation-related variables:", hits)
        for col, name in enumerate(labels):
            if name in hits:
                first = df.iloc[1:, [0, col]].dropna().iloc[0]
                print(f"  {name}: first non-missing survey {pd.to_datetime(first.iloc[0]).date()}")


if __name__ == "__main__":
    for f in sorted(RAW.glob("kof_kof_consensus_forecast_*.xlsx")):
        describe(f)
