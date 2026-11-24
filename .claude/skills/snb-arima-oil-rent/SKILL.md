---
name: snb-arima-oil-rent
description: Special models of the SNB ARIMA inflation framework - error-correction model for oil-product CPI items (heating oil, petrol, diesel) cointegrated with the crude oil price in Swiss francs, and the quarterly rent model with asymmetric lagged mortgage-rate changes. Use for tasks T2.3–T2.4, for replicating the paper's Table 3, or when oil/rent forecasts dominate the errors.
---

# SNB ARIMA — oil products ECM and rent model (T2.3–T2.4)

Both items are special because oil is very volatile and rents weigh ≈ 20 % (paper p. 7). Both must respect the same
interface as `forecast_item` (see `snb-arima-item-models`) plus exogenous data cut at the right date.

## A. Oil products ECM (heating oil, petrol, diesel — each separately)
Paper: cointegrated with crude spot price in CHF; nowcast of current month uses daily crude and USDCHF at the start of the
month; afterwards crude-in-CHF held constant at the **average of the last 10 daily observations**.

Proposed specification (log a decision for each choice, G10):
1. `x_t = log(crude_USD × CHF_per_USD)` — monthly value = average of daily obs over the window before the SFSO collection
   day (decision: first ~5 business days of the month, or previous month's average).
2. Engle–Granger: long-run `p_t = a + b·x_t + u_t` (check `b` ≈ plausible share, ADF on `u_t` → cointegration, report).
3. ECM: `Δp_t = c + γ·u_{t−1} + Σ_{i=0..k} β_i Δx_{t−i} + Σ_{j=1..m} α_j Δp_{t−j} + e_t`, lags k, m by SIC (same formula as items).
4. Information set at origin (pseudo-OOS, paper p. 12): exogenous data **up to the first day of the last month of the current
   quarter** → enables a nowcast of month 3. Path after that: `x` constant at mean of last 10 daily obs.
5. Benchmarks for Table 3: plain ARIMA on the same item (SIC), and the real-time ARIMA if available.

## B. Rent model
Paper: rents collected quarterly; quarterly ARIMA in first differences + **4th lag of the change in the mortgage rate**,
separately for positive and negative changes; AR order by SIC; mortgage rate constant over the horizon.

1. Quarterly series: `Δr_q = log rent index (collection month) − previous`. Mortgage rate `m_q` quarterly average
   (linked series per paper fn. 3: cantonal-bank average → BWO average from 2008Q2).
2. `Δm⁺_q = max(Δm_q, 0)`, `Δm⁻_q = min(Δm_q, 0)`.
3. `Δr_q = c + Σ φ_j Δr_{q−j} + β⁺ Δm⁺_{q−4} + β⁻ Δm⁻_{q−4} + e_q` (SARIMAX with exog, or OLS — AR only); p by SIC.
4. Forecast: `m` constant at last known value ⇒ future `Δm = 0`, but lagged known changes still enter for 4 quarters.
5. Since 2008 rents are collected in the 2nd month of the quarter ⇒ with 2 months known, h = 1 error = 0 (paper Table 3).
6. Note in decisions: since 2008 Swiss rent law links rents to the **reference rate** (Referenzzinssatz) — an obvious
   extension for 2012+ (thesis P5).

## Checks
- Table 3 replication: oil ECM absolute RMSFE (on oil sub-index y-o-y) ≈ 1.14, 6.72, 12.49, 15.25, 17.10; rent model ≈ 0.00,
  0.24, 0.46, 0.56, 0.61. Relative ARIMA RMSFE > 1, significant where the paper finds it.
- No-look-ahead test with exogenous data: perturb oil/FX/mortgage data after the allowed cut-off → forecast unchanged.
- Print estimated `b`, `γ` (should be negative), `β⁺`, `β⁻` with standard errors for the latest origin.
