"""T3.2 exploration: survey dates of the KOF consensus and the variable codes of the SNB cube snbiprogq.

Read-only on data/raw. Answers: when are KOF surveys dated relative to our origins (Feb/May/Aug/Nov), and
which snbiprogq series belongs to which assessment (D-06 rev., D-20).
"""
import pandas as pd

from arima_snb import io

def main():
    path = io.find_raw("kof_kof_consensus_forecast_mean_ts_*.xlsx")
    for name, df in pd.read_excel(path, sheet_name=None, header=None).items():
        labels = list(df.iloc[0])
        cols = [0] + [i for i, lab in enumerate(labels) if "price" in str(lab)]
        print(name, df.shape, [labels[i] for i in cols])
        print(df.iloc[list(range(1, 4)) + list(range(10, 28)), cols].to_string())
    cube = io.read_snb_cube(io.find_raw("snb-data-snbiprogq-*.csv"), "snbiprogq")
    print(cube.head())
    print(sorted(cube.variable.unique())[:12], cube.variable.nunique())
    one = cube[cube.variable.str.contains("2004PL")]
    print(one.dropna(subset=["value"]).head(30).to_string())


def snb_paths():
    """Forecast quarters (P) of a few assessments: does the path start in the publication quarter?"""
    cube = io.read_snb_cube(io.find_raw("snb-data-snbiprogq-*.csv"), "snbiprogq")
    p = cube[cube.variable.str.endswith("_P")].dropna(subset=["value"])
    for code in ["J2004PL05P", "S2004PL075P", "D2004PL075P", "M2005PL075P", "D2011PL000P", "M2009PL050P"]:
        g = p[p.variable == f"snbiprogq_{code}_P"]
        print(code, g.date.min().date(), g.date.max().date(), len(g), g.value.head(3).tolist())
    codes = sorted({v.split("_")[1] for v in cube.variable})
    print(len(codes), codes[:6], codes[-6:])


if __name__ == "__main__":
    main()
    snb_paths()
