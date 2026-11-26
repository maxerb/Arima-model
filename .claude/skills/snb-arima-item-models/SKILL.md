---
name: snb-arima-item-models
description: Estimate and forecast the per-item models of the SNB disaggregate ARIMA inflation model - ARIMA(p,1,q) on log CPI item prices with optional seasonal AR(12), lag order chosen by the Schwarz criterion on a common sample, quarterly-lag restriction for quarterly-collected items, and the ad-hoc fallbacks (last value, average m-o-m, average y-o-y). Use for task T2.2 or whenever item forecasts misbehave.
---

# SNB ARIMA — per-item models (T2.2)

## Interface (in `src/arima_snb/item_models.py`)
```python
def forecast_item(log_p, spec, origin, steps=FORECAST_STEPS, pattern: list[int] | None = None,
                  crude_chf_daily=None, mortgage_rate=None) -> tuple[pd.DataFrame, dict]:
    """One item, data up to `origin` only. `spec` = row of specs_for_origin (D-31); `pattern` = last year's
    collection months (real-time rule). Returns (forecast frame [target, log_p_hat, ...], log dict)."""
def forecast_items(panel, specs, collection, origin, steps=FORECAST_STEPS, n_jobs=ITEM_N_JOBS,
                   crude_chf_daily=None, mortgage_rate=None) -> tuple[pd.DataFrame, pd.DataFrame]:  # (forecasts, order log)
```
`crude_chf_daily` / `mortgage_rate` switch oil and rent to the special models (`snb-arima-oil-rent`); None = plain ARIMA.
`steps` = months to the end of quarter origin+4 (with origin = 2nd month of quarter → 13 months; the paper's "15 months"
refers to the production run — make it a parameter).

## Model (paper eqs. 1–3, p. 6–7)
- Data: `y_t = Δ log_p_t` (monthly), sample from item start (May 2000 for most) to `origin`. Constant per D-01.
- Candidates: ARIMA(p,0,q) on `y_t` for p, q in the D-02 grid; if `spec.seasonal`, multiply by `(1 − ρL^12)`:
  `SARIMAX(y, order=(p,0,q), seasonal_order=(1,0,0,12), trend="c")`.
- **Quarterly items** (`spec.quarterly_lags`, D-36 — quarterly *sampling*, not a monthly series with lag lists): build
  the quarterly series `y_q = log_p` at collection months, differenced; fit ARMA in quarters (≙ monthly lags 3, 6, 9, …).
  Forecast at future collection months, carry the level forward in between. Seasonal quarterly items: seasonal AR at lag 4.
- With the seasonal AR term, **p ≤ s − 1** (11 monthly, 3 quarterly): at p = s lag s is in both factors (not identified).
- **Short samples** (D-37): the common SIC sample must keep ≥ `MIN_SIC_OBS_MONTHLY` (24) / `_QUARTERLY` (12) obs;
  shrink the grid (and drop the seasonal term) until it does.
- **SIC** exactly as eq. (3): `SIC = log(SSE/T) + k·log(T)/T`, with `T` the **same effective sample** for all candidates
  (drop the first `max(p_max, 12·seasonal + p_max)` observations for every candidate) and `k` = number of estimated
  ARMA + seasonal + constant parameters. Compute SSE from in-sample one-step residuals. Do **not** use statsmodels' `bic`
  directly — it is likelihood-based with a different scaling; keep it only as a cross-check.
- Estimation: **conditional least squares** (D-35, `fit_cls`) — eq. (3) is an SSE criterion and SARIMAX ML costs ~30
  CPU h for 32 origins. PACF transform keeps AR stationary / MA invertible; cap the optimiser at 100 evaluations
  (MA candidates drifting to a unit root otherwise take 25 s each; a 10× budget rescues none); failed = dropped, logged.
- Forecast `y` for `steps` months, cumulate onto `log_p[origin]` → `log_p_hat`.

## Fallbacks (paper p. 7) — `method` values
| Method | Rule |
|---|---|
| `adhoc_last` | `log_p_hat = log_p[origin]` for all steps (less than quarterly collection) |
| `adhoc_avg_mom` | add the average `Δlog_p` over the last 12 months each month |
| `adhoc_avg_yoy` | add 1/12 of the average y-o-y log change over the available sample each month |
| plausibility override | if the 12-month-ahead implied change is outside the [1st, 99th] percentile of the item's own 12-month changes (`PLAUSIBLE_PCTL`, D-11), switch to `adhoc_avg_yoy` and log the item + origin |

## Checks
- Unit test on simulated AR(2)+seasonal data: SIC picks the true order most of the time (use an AR(2) that no MA(1)
  mimics, e.g. φ = (0.3, 0.4); φ = (0.5, −0.3) legitimately loses to MA(1)); forecasts match a manual recursion.
- **No-look-ahead test**: set all data after `origin` to garbage → identical forecast.
- Per origin, log: chosen orders, how often grid bounds bind (p = p_max), number of fallbacks. Save to `outputs/logs/item_orders.csv`.
- Runtime: ~2.5–4 min per origin with 4 processes. `joblib` is not installed: use stdlib `ProcessPoolExecutor` behind
  an `if __name__ == "__main__":` guard (Windows). Cache per origin (see `snb-arima-evaluation`).

## Pitfalls
- `trend="c"` with `order=(p,0,q)` on `Δlog_p` is a drift in levels — do not also difference inside SARIMAX.
- Items with long flat stretches (carried forward) and monthly fitting = misspecification; that is exactly why quarterly
  items get quarterly lags. Double-check the spec, not the optimiser, when such items behave strangely.
- Suppress convergence warnings only after logging them.
