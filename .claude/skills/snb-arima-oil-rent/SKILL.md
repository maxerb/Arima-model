---
name: snb-arima-oil-rent
description: Special models of the SNB ARIMA inflation framework - error-correction model for oil-product CPI items (heating oil, petrol, diesel) cointegrated with the crude oil price in Swiss francs, and the quarterly rent model with asymmetric lagged mortgage-rate changes. Use for tasks T2.3–T2.4, for replicating the paper's Table 3, or when oil/rent forecasts dominate the errors.
---

# SNB ARIMA — oil products ECM and rent model (T2.3–T2.4)

Both items are special because oil is very volatile and rents weigh ≈ 20 % (paper p. 7). Code: `special.py`
(`forecast_oil_item(log_p, crude_chf_daily, origin, steps)`, `forecast_rent(log_rent, mortgage_monthly, origin, steps)`,
both → (frame, log)). They are reached through `forecast_item(s)(..., crude_chf_daily=…, mortgage_rate=…)`; None =
plain ARIMA, which is also the Table 3 benchmark (D-39, D-49). Each cuts its exogenous data itself.

## A. Oil products ECM (each item with `special == oil`: i100 heating oil, i130 fuels = petrol + diesel)
Paper: cointegrated with crude spot price in CHF; nowcast of current month uses daily crude and USDCHF at the start of the
month; afterwards crude-in-CHF held constant at the **average of the last 10 daily observations**.

Proposed specification (log a decision for each choice, G10):
1. `x_t = log(Brent_USD × CHF_per_USD)` — monthly value = mean of the **last 10 daily obs before the 1st of month t**
   (D-14 rev., `OIL_X_RULE = "before"`); the first-5-days variant was tested and is slightly worse out of sample.
2. Sample from `OIL_SAMPLE_START` (1993-05, D-38) — item models start 2000-05, too short for the ECM at 2004. Engle–Granger: long-run `p_t = a + b·x_t + u_t` (check `b` ≈ plausible share, ADF on `u_t` → cointegration, report).
3. ECM: `Δp_t = c + γ·u_{t−1} + Σ_{i=0..k} β_i Δx_{t−i} + Σ_{j=1..m} α_j Δp_{t−j} + e_t`, lags k, m by SIC (same formula as items).
4. Information set at origin (pseudo-OOS, paper p. 12): crude data dated before the 1st of the month after the origin
   (`crude_info_cutoff`) → nowcast of month 3. Path after that: `x` constant at mean of last 10 daily obs.
5. Benchmarks for Table 3: plain ARIMA on the same item (SIC), and the real-time ARIMA if available.

## B. Rent model
Paper: rents collected quarterly; quarterly ARIMA in first differences + **4th lag of the change in the mortgage rate**,
separately for positive and negative changes; AR order by SIC; mortgage rate constant over the horizon.

1. Quarterly series from `RENT_SAMPLE_START` (1993-05, D-48): `Δr_q = log rent (collection month) − previous`.
   Mortgage rate `m_q` = quarterly average of SNB `zikrepro` M_MV (D-19, D-15 rev.; the paper's fn. 3 splice of
   cantonal-bank and BWO rates is not available). Only months ≤ origin enter the current quarter's average.
2. `Δm⁺_q = max(Δm_q, 0)`, `Δm⁻_q = min(Δm_q, 0)`.
3. `Δr_q = c + Σ φ_j Δr_{q−j} + β⁺ Δm⁺_{q−4} + β⁻ Δm⁻_{q−4} + e_q` by OLS; p ∈ 0…`RENT_P_MAX` (4) by SIC, common sample.
4. Forecast: `m` constant at last known value ⇒ future `Δm = 0`, but lagged known changes still enter for 4 quarters.
5. Rents are collected in the 2nd month of the quarter (Feb/May/Aug/Nov) in the data **since 1993** (D-48) ⇒ with
   2 months known, h = 1 error = 0 (paper Table 3).
6. Note in decisions: since 2008 Swiss rent law links rents to the **reference rate** (Referenzzinssatz) — an obvious
   extension for 2012+ (thesis P5).

## Checks
- Table 3 replication: oil ECM absolute RMSFE (on oil sub-index y-o-y) ≈ 1.14, 6.72, 12.49, 15.25, 17.10; rent model ≈ 0.00,
  0.24, 0.46, 0.56, 0.61. Relative ARIMA RMSFE > 1, significant where the paper finds it.
- No-look-ahead test with exogenous data: perturb oil/FX/mortgage data after the allowed cut-off → forecast unchanged.
- Print estimated `b`, `γ` (should be negative), `β⁺`, `β⁻` with standard errors for the latest origin.
- Runtime: oil ECM + ARIMA benchmark ~4 min for 32 origins (run in background), rent ~25 s.
