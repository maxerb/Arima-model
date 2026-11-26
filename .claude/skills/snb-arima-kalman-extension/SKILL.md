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
exog = months since sample start      # regression on a time index: Δp = μ + Δu, μ = mean form (D-42)
mod = SARIMAX(y, exog=exog, order=(p, 1, 0), seasonal_order=(1, 0, 0, 12) if seasonal else (0, 0, 0, 0),
              simple_differencing=False, enforce_stationarity=True)
```
- Do **not** use `trend="t"`: that is SARIMAX's intercept form, not the paper's mean μ (verified by simulation, D-42).
- With the seasonal AR(12), **p ≤ 11** (p = 12 puts lag 12 in both polynomials → ValueError).
- The optimiser can step onto unit-circle AR roots → `LinAlgError` in the stationary initialisation. Catch it, retry
  from neutral start values with Nelder-Mead; failed orders get SIC = ∞; at forecast time step p down
  (`kalman_ext.fit_collection_model`, `fit_with_fallback`, D-42). An unguarded 182-item run crashed after ~10 min.
- Order p by SIC, but `SSE` is not defined with gaps — use `−2·loglike + k·log(T)` with T = observed changes (D-44, G13).
- **Compute budget:** SIC over p = 0…12 at every origin × 182 items × 32 origins ≈ 2 days. Time a prototype first and put
  the order-timing scheme to the user (this project: orders per yearly vintage, parameters re-fitted per origin, D-44;
  order search ~1–2 h on 6 processes, `KALMAN_VINTAGES` — extend it for later origins).
- Sample from **1993** (paper p. 14) where data exist; earlier bases must be chain-linked (panel skill).

## Forecasting (eq. 13)
- `res.get_forecast(steps)` gives the latent monthly path → monthly `log_p_hat` for **every** month.
- To mimic published data, apply the expected **collection months of the previous year** (real-time rule): published
  forecast = last forecast level at the latest expected collection month, carried forward. Use these "published-like"
  paths in aggregation, because the official CPI also carries forward.
- Interpolation: `res.smoothed_state` → interpolated monthly series (reproduce paper Chart 3 for trousers).

## Integration
- Used for **all 182 items, incl. oil and rents** (paper p. 15 / Table 4: special models not used in the extension, D-41).
- Items on an ad-hoc rule in the ARIMA(182) (sticky 'last value' items) are a choice to flag: with a 1993 drift they lose
  in Health; a hybrid keeping their ad-hoc rule helps at h = 4–5 (D-53 sensitivity).
- Plug into `forecast_item` dispatch; evaluate with `snb-arima-evaluation` → Table 4 (target: 0.06, 0.32, 0.64, 0.86, 1.00).

## Checks
- **Simulation test**: simulate monthly AR(2) changes with drift (T ≥ 1000; T = 300 is too noisy for a 0.15 tolerance on φ), observe the level quarterly for the first half
  and monthly afterwards; estimated `φ, μ, σ²` within sampling error of the truth; smoothed changes correlate highly with truth.
- With monthly collection throughout, the extended model's estimates ≈ a plain ARIMA(p,1,0) fit.
- No-look-ahead test as in other model skills; collection-month assumption uses only data from before the origin.
- Chart 3 replica: trousers interpolated vs official, `outputs/figures/chart3_trousers.png`.
