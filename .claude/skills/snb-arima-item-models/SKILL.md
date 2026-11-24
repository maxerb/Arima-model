---
name: snb-arima-item-models
description: Estimate and forecast the per-item models of the SNB disaggregate ARIMA inflation model - ARIMA(p,1,q) on log CPI item prices with optional seasonal AR(12), lag order chosen by the Schwarz criterion on a common sample, quarterly-lag restriction for quarterly-collected items, and the ad-hoc fallbacks (last value, average m-o-m, average y-o-y). Use for task T2.2 or whenever item forecasts misbehave.
---

# SNB ARIMA — per-item models (T2.2)

## Interface (in `src/arima_snb/item_models.py`)
```python
def forecast_item(log_p: pd.Series, spec: pd.Series, origin: pd.Timestamp, steps: int,
                  collection: pd.Series | None = None) -> pd.DataFrame:
    """Forecast log price of one item for `steps` months after `origin`.
    Uses only log_p.loc[:origin]. Returns columns: target, log_p_hat, method, order, sic."""
```
`steps` = months to the end of quarter origin+4 (with origin = 2nd month of quarter → 13 months; the paper's "15 months"
refers to the production run — make it a parameter).

## Model (paper eqs. 1–3, p. 6–7)
- Data: `y_t = Δ log_p_t` (monthly), sample from item start (May 2000 for most) to `origin`. Constant per D-01.
- Candidates: ARIMA(p,0,q) on `y_t` for p, q in the D-02 grid; if `spec.seasonal`, multiply by `(1 − ρL^12)`:
  `SARIMAX(y, order=(p,0,q), seasonal_order=(1,0,0,12), trend="c")`.
- **Quarterly items** (`spec.quarterly_lags`): build the quarterly series `y_q = log_p` at collection months, differenced
  (`Δ3`); fit ARMA on lags in quarters (≙ monthly lags 3, 6, 9, …). Forecast at future collection months and carry the
  level forward in between (that is how SFSO publishes it). Seasonal quarterly items: seasonal AR at lag 4.
- **SIC** exactly as eq. (3): `SIC = log(SSE/T) + k·log(T)/T`, with `T` the **same effective sample** for all candidates
  (drop the first `max(p_max, 12·seasonal + p_max)` observations for every candidate) and `k` = number of estimated
  ARMA + seasonal + constant parameters. Compute SSE from in-sample one-step residuals. Do **not** use statsmodels' `bic`
  directly — it is likelihood-based with a different scaling; keep it only as a cross-check.
- Estimation: `SARIMAX(...).fit(disp=False)`; enforce stationarity/invertibility (default). On non-convergence try another
  start (`method="powell"` then `"lbfgs"`); if all fail, drop that candidate and log it.
- Forecast `y` for `steps` months, cumulate onto `log_p[origin]` → `log_p_hat`.

## Fallbacks (paper p. 7) — `method` values
| Method | Rule |
|---|---|
| `adhoc_last` | `log_p_hat = log_p[origin]` for all steps (less than quarterly collection) |
| `adhoc_avg_mom` | add the average `Δlog_p` over the last 12 months each month |
| `adhoc_avg_yoy` | add 1/12 of the average y-o-y log change over the available sample each month |
| plausibility override | if the 12-month-ahead implied change is beyond `PLAUSIBLE_BAND` (decision, e.g. ±3 SD of historical 12-month changes), switch to `adhoc_avg_yoy` and log the item + origin |

## Checks
- Unit test on simulated AR(2)+seasonal data: SIC picks the true order most of the time; forecasts match `statsmodels` manual recursion.
- **No-look-ahead test**: set all data after `origin` to garbage → identical forecast.
- Per origin, log: chosen orders, how often grid bounds bind (p = p_max), number of fallbacks. Save to `outputs/logs/item_orders.csv`.
- Runtime: ~182 items × grid × 32 origins — parallelise with `joblib` if > 10 min and cache fits by `(item, origin)`.

## Pitfalls
- `trend="c"` with `order=(p,0,q)` on `Δlog_p` is a drift in levels — do not also difference inside SARIMAX.
- Items with long flat stretches (carried forward) and monthly fitting = misspecification; that is exactly why quarterly
  items get quarterly lags. Double-check the spec, not the optimiser, when such items behave strangely.
- Suppress convergence warnings only after logging them.
