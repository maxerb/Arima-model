---
name: snb-arima-kalman-extension
description: Implement the collection-frequency extension of the SNB ARIMA model (paper section 5 and appendix C) - a state-space model for unobserved monthly log price changes of irregularly collected CPI items, estimated by maximum likelihood with the Kalman filter, used for forecasting and Kalman-smoother interpolation. Use for task T4.1, for the "extended ARIMA(182)" in Table 4, or whenever irregular collection / missing monthly prices must be modelled.
---

# SNB ARIMA — time-varying collection frequency (T4.1)

## Idea (paper eqs. 4–8, App. C)
Latent monthly changes `Δp_t − μ` follow AR(p) (optionally × (1 − ρL^12)). We only observe the change since the last
collection, which equals the **sum** of latent changes since then. Non-collection months carry no information.

## Implementation route (recommended): SARIMAX on log levels with missing values
Equivalent formulation: put the **log level** `p_t` in the state (d = 1 handled inside the state space) and set `p_t = NaN`
in every non-collection month. The Kalman filter then automatically conditions on `p_t − p_{t−h_t}` = sum of latent changes,
exactly eqs. (7)–(8) with `R_t = 0` at collections.
```python
y = log_p.where(collected)            # NaN where SFSO did not collect (|Δ| < 1e-3 → not collected, fn. 9)
mod = SARIMAX(y, order=(p, 1, 0), seasonal_order=(1, 0, 0, 12) if seasonal else (0, 0, 0, 0),
              trend="t",              # with d=1, a linear trend in levels = drift μ in Δp (verify!)
              simple_differencing=False, enforce_stationarity=True)
res = mod.fit(disp=False)
```
- **Verify the drift parametrisation** by simulation before trusting it (see checks). If it does not behave, implement a
  small `statsmodels.tsa.statespace.mlemodel.MLEModel` subclass with state `[p_t, Δp_t−μ, …]` and `μ` as a parameter.
- Order p by SIC as in the item models, but `SSE` is not defined with gaps — use `−2·loglike/T + k·log(T)/T` on the
  observed points (log as decision; G13).
- Sample from **1993** (paper p. 14) where data exist; earlier bases must be chain-linked (panel skill).

## Forecasting (eq. 13)
- `res.get_forecast(steps)` gives the latent monthly path → monthly `log_p_hat` for **every** month.
- To mimic published data, apply the expected **collection months of the previous year** (real-time rule): published
  forecast = last forecast level at the latest expected collection month, carried forward. Use these "published-like"
  paths in aggregation, because the official CPI also carries forward.
- Interpolation: `res.smoothed_state` → interpolated monthly series (reproduce paper Chart 3 for trousers).

## Integration
- New `method = "kalman"` in `item_specs.csv` (all items except oil and rent in the paper's Table 4 run — note paper says
  special models were **not** used in the extension, p. 15).
- Plug into `forecast_item` dispatch; evaluate with `snb-arima-evaluation` → Table 4 (target: 0.06, 0.32, 0.64, 0.86, 1.00).

## Checks
- **Simulation test**: simulate monthly AR(2) changes with drift (T = 300), observe the level quarterly for the first half
  and monthly afterwards; estimated `φ, μ, σ²` within sampling error of the truth; smoothed changes correlate highly with truth.
- With monthly collection throughout, the extended model's estimates ≈ a plain ARIMA(p,1,0) fit.
- No-look-ahead test as in other model skills; collection-month assumption uses only data from before the origin.
- Chart 3 replica: trousers interpolated vs official, `outputs/figures/chart3_trousers.png`.
