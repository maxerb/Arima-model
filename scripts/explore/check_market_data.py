"""T1.2 sanity checks: coverage of every downloaded market series and spot checks against known values."""

import pandas as pd

from arima_snb.io import find_raw, read_fred, read_snb_cube

CUBES = ["plkopr", "plkoprinfla", "plkoprex", "devkum", "zikrepro", "snbiprogq"]


def main() -> None:
    frames = [read_fred(find_raw(f"fred_{s}_*.csv")) for s in ["DCOILBRENTEU", "DCOILWTICO", "DEXSZUS"]]
    frames += [read_snb_cube(find_raw(f"snb-data-{c}-*.csv"), c) for c in CUBES]
    for df in frames:
        assert not df.duplicated(["date", "variable"]).any(), df["source"].iloc[0]
    df = pd.concat(frames)
    keep = ["fred_DCOILBRENTEU", "fred_DCOILWTICO", "fred_DEXSZUS", "plkopr_LD2010100", "plkopr_VVP",
            "plkoprinfla_K1", "plkoprinfla_TLK", "plkoprex_IE", "plkoprex_IW", "devkum_M0_USD1", "zikrepro_M_MV"]
    cov = df[df.variable.isin(keep)].groupby("variable").agg(first=("date", "min"), last=("date", "max"),
                                                            n=("value", "size"), min=("value", "min"),
                                                            max=("value", "max"))
    print(cov.to_string())

    # Spot check (paper Chart 2): headline y-o-y inflation peaked near 3 % in 2008Q3
    yoy = df[df.variable == "plkopr_VVP"].set_index("date")["value"]
    q3 = yoy["2008-07":"2008-09"].mean()
    print(f"\nCPI y-o-y 2008Q3 average: {q3:.2f} %")
    assert 2.5 < q3 < 3.5

    # Brent in mid-2008 ~ 130 USD, USDCHF ~ 1.0
    brent = df[df.variable == "fred_DCOILBRENTEU"].set_index("date")["value"]
    assert 120 < brent["2008-07"].mean() < 145

    fc = df[df.source.str.contains("snbiprogq")]
    print(f"SNB conditional forecasts: {fc.variable.nunique()} series (assessment x observed/forecast), "
          f"{fc.date.min():%Y-%m} .. {fc.date.max():%Y-%m}")


if __name__ == "__main__":
    main()
