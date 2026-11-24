"""T1.2: download headline/core CPI, crude oil, USDCHF, mortgage rates and SNB conditional inflation forecasts.

Sources (all public, no login, checked 2026-11-24):
  - FRED (St. Louis Fed) CSV endpoint https://fred.stlouisfed.org/graph/fredgraph.csv?id=<series>
      DCOILBRENTEU  Brent crude spot, USD/barrel, daily              (oil ECM, D-14)
      DCOILWTICO    WTI crude spot, USD/barrel, daily                (robustness for D-14)
      DEXSZUS       CHF per USD, noon buying rate NY, daily          (oil price in CHF, daily nowcast)
  - SNB data portal API https://data.snb.ch/api/cube/<cube>/data/csv/en
      plkopr       headline CPI index + y-o-y (evaluation target)
      plkoprinfla  core inflation (SFSO core 1/2, SNB trimmed mean)
      plkoprex     CPI excluding special groups (e.g. without petroleum products / housing rental)
      devkum       FX monthly averages / end of month (USD1 = CHF per USD)
      zikrepro     bank interest rates incl. variable mortgage rate (MV), monthly since 1976 (rent model, D-19)
      snbiprogq    SNB conditional inflation forecasts, every quarterly assessment since June 2004 (D-16)

The KOF consensus files (D-06) were copied in T0.0 and are not downloaded here (see docs/data_sources.md).
Files are saved untouched in data/raw/ as `fred_<id>_<date>.csv` and `snb-data-<cube>-<date>.csv`.
A file already downloaded (any date) is not fetched again, so the script is idempotent; delete it to refresh.
"""

from datetime import date

import requests

from arima_snb.config import RAW

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
SNB = "https://data.snb.ch/api/cube/{cube}/data/csv/en"

FRED_SERIES = ["DCOILBRENTEU", "DCOILWTICO", "DEXSZUS"]
SNB_CUBES = ["plkopr", "plkoprinfla", "plkoprex", "devkum", "zikrepro", "snbiprogq"]


def fetch(url: str, prefix: str, check: str) -> None:
    """Download `url` to data/raw/<prefix><today>.csv unless a file with that prefix exists."""
    existing = sorted(RAW.glob(f"{prefix}*.csv"))
    if existing:
        print(f"present: {existing[-1].name}")
        return
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    # Guard against error pages: the expected header text must be in the first line(s)
    assert check in r.text[:300], f"{url}: unexpected content {r.text[:200]!r}"
    path = RAW / f"{prefix}{date.today():%Y-%m-%d}.csv"
    path.write_bytes(r.content)
    print(f"saved:   {path.name} ({len(r.content) / 1e3:.0f} kB)")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for sid in FRED_SERIES:
        fetch(FRED.format(sid=sid), f"fred_{sid}_", sid)
    for cube in SNB_CUBES:
        fetch(SNB.format(cube=cube), f"snb-data-{cube}-", cube)


if __name__ == "__main__":
    main()
