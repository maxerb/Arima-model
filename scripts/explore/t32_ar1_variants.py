"""T3.2 exploration: why the AR(1) benchmark (D-05, monthly Δlog CPI) zig-zags in RMSFE across h.

The Swiss CPI has a strong seasonal pattern since 2000 (clothing sales in Jan/Jul). A non-seasonal AR(1) on
monthly log changes converges to the average monthly change, so y-o-y forecasts of quarters whose year-ago
quarter had a seasonal dip/peak miss. Compares D-05 with two seasonality-robust AR(1) variants, same origins,
same information set (CPI up to the origin month):
  a) AR(1) on monthly y-o-y inflation (12-month log change), iterated; index path rebuilt from the forecast y-o-y
  b) AR(1) on monthly Δlog CPI with 12 monthly dummies (seasonal means)
"""
import numpy as np
import pandas as pd

from arima_snb import aggregate, benchmarks as bm, evaluate
from arima_snb.config import FORECAST_STEPS, ITEM_SAMPLE_START


def ar1_yoy(cpi, origin, steps=FORECAST_STEPS):
    x = np.log(cpi.loc[:origin])
    z = (x - x.shift(12)).loc[pd.Timestamp(ITEM_SAMPLE_START):].dropna()
    X = np.column_stack([np.ones(len(z) - 1), z.values[:-1]])
    c, phi = np.linalg.lstsq(X, z.values[1:], rcond=None)[0]
    lx = x.copy()
    last = z.iloc[-1]
    for t in pd.date_range(origin + pd.DateOffset(months=1), periods=steps, freq="MS"):
        last = c + phi * last
        lx[t] = lx[t - pd.DateOffset(months=12)] + last
    return np.exp(lx)


def ar1_dummies(cpi, origin, steps=FORECAST_STEPS):
    x = np.log(cpi.loc[pd.Timestamp(ITEM_SAMPLE_START):origin])
    y = x.diff().dropna()
    D = pd.get_dummies(y.index.month).astype(float).values
    X = np.column_stack([D[1:], y.values[:-1]])
    b = np.linalg.lstsq(X, y.values[1:], rcond=None)[0]
    lx, last = x.copy(), y.iloc[-1]
    for t in pd.date_range(origin + pd.DateOffset(months=1), periods=steps, freq="MS"):
        last = b[t.month - 1] + b[-1] * last
        lx[t] = lx.iloc[-1] + last
    return np.exp(lx)


if __name__ == "__main__":
    cpi = evaluate.official_cpi()
    act = aggregate.quarterly_yoy(cpi)
    rows = []
    for o in evaluate.evaluation_origins():
        c = cpi.loc[:o]
        d05 = pd.concat([c, bm.forecast_ar1(c, o, month_dummies=False).set_index("target").index_hat])
        for name, s in (("ar1 (D-05)", d05), ("ar1 on m y-o-y", ar1_yoy(c, o)), ("ar1 + month dummies", ar1_dummies(c, o))):
            q = bm.quarterly_from_index(s, o).assign(model=name)
            rows.append(q)
    q = pd.concat(rows)
    q["err"] = q.target_q.map(act) - q.pi_hat
    print(q.groupby(["model", "h"]).err.agg(evaluate.rmsfe).unstack("h").round(3).to_string())
# Result 2026-11-25 (origins 2004-2011): D-05 0.083/0.819/0.768/1.183/1.070; dummies 0.088/0.478/0.742/0.958/1.074;
# y-o-y 0.114/0.619/0.963/1.105/1.112 -> user chose month dummies (D-05 rev.).
