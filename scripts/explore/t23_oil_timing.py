"""T2.3 exploration: which crude-price window lines up best with the BFS oil-item prices?

Correlates the monthly log change of each oil item with the log change of crude-in-CHF measured over different
daily windows (last 10 days before the month, first 5 business days of the month, whole-month average, ...).
Supports decision D-14 rev. (timing of x_t). Not part of run_all.py.
"""
import numpy as np
import pandas as pd

from arima_snb import special
from arima_snb.config import FINAL


def window_series(daily: pd.Series, months: pd.DatetimeIndex, rule: str) -> pd.Series:
    out = {}
    for m in months:
        nxt = m + pd.DateOffset(months=1)
        if rule == "last10_before":
            v = daily[daily.index < m].iloc[-10:]
        elif rule == "first5_of_month":
            v = daily[(daily.index >= m) & (daily.index < nxt)].iloc[:5]
        elif rule == "days6_15_of_month":
            v = daily[(daily.index >= m) & (daily.index < nxt)].iloc[5:15]
        elif rule == "month_avg":
            v = daily[(daily.index >= m) & (daily.index < nxt)]
        elif rule == "prev_month_avg":
            v = daily[(daily.index >= m - pd.DateOffset(months=1)) & (daily.index < m)]
        out[m] = np.log(v.mean())
    return pd.Series(out)


def main() -> None:
    daily = special.load_crude_chf_daily()
    panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    months = pd.date_range("1993-06-01", "2026-10-01", freq="MS")
    rules = ["prev_month_avg", "last10_before", "first5_of_month", "days6_15_of_month", "month_avg"]
    xs = {r: window_series(daily, months, r).diff() for r in rules}
    for item in ["i100", "i130"]:
        dp = panel[panel.item_id == item].set_index("date").log_p.diff().reindex(months)
        for per in [("1993", "2011"), ("2012", "2026")]:
            row = {r: round(dp.loc[per[0]:per[1]].corr(xs[r].loc[per[0]:per[1]]), 3) for r in rules}
            print(item, per, row)


if __name__ == "__main__":
    main()
