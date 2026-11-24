---
name: snb-arima-evaluation
description: Pseudo-out-of-sample forecast evaluation for the SNB disaggregate ARIMA replication - recursive quarterly forecast origins with two months of the current quarter known, horizons 1–5 quarters, benchmarks (AR(1), ARIMA(1)/(6)/(14), consensus, SNB conditional forecast), RMSFE, relative RMSFE and Diebold-Mariano-West tests with the Harvey-Leybourne-Newbold correction. Use for tasks T3.1–T3.3, T4.2, T5.1–T5.2, to reproduce the paper's Tables 1–4, or for any new out-of-sample comparison.
---

# SNB ARIMA — evaluation (T3.x, T4.2, T5.x)

## Forecast engine (`src/arima_snb/evaluate.py`)
```python
def run_pseudo_oos(model_fn, origins: list[pd.Timestamp], horizons=range(1, 6)) -> pd.DataFrame:
    """For each origin (last known CPI month = 2nd month of a quarter) call model_fn(origin) → monthly
    aggregate index forecast; splice with actuals; compute quarterly y-o-y for h = 1..5 (h=1 current quarter).
    Returns long: origin_q, h, target_q, model, pi_hat, pi_actual."""
```
- Origins per D-04: Feb, May, Aug, Nov of 2004 … 2011 (32). Thesis extension (T5.1): continue to the latest data.
- Cache every model run in `outputs/eval/<model>.csv`; re-running skips existing `(model, origin)` unless `--force`.
- Each `model_fn` must enforce the data cut itself (CPI ≤ origin; oil/FX ≤ first day of the 3rd quarter month; weights,
  specs, collection calendar as known at origin).

## Benchmarks
| Name | Construction |
|---|---|
| ARIMA(182) / real-time ARIMA | full model (item models + oil ECM + rent model for "real-time-like"; plain ARIMA for oil/rent in Table 2) |
| ARIMA(14), ARIMA(6), ARIMA(1) | see `snb-arima-aggregate` |
| AR(1) | D-05 |
| Consensus | KOF consensus (D-06 rev., confirmed): mean of `prices_cy` / `prices_ny` from the latest survey published **before** the origin date. Evaluate on **annual-average CPI inflation of the current and next year** — average our quarterly forecasts to calendar years (realised quarters = actuals) and score every model on that same target. Interpolating KOF to quarters is only a labelled secondary variant; say in the tables that the paper's Consensus Economics row is not replicated exactly |
| SNB conditional | hand-collected from MPA press releases; quarter of publication ↔ origin of that quarter |
The paper's "real-time ARIMA" vintages are not public — our closest analogue is ARIMA(182) with special models; state this clearly.

## Metrics and test
- `RMSFE_h = sqrt(mean((π − π̂)²))` over origins with available actuals for horizon h.
- Relative RMSFE = RMSFE_benchmark / RMSFE_reference (> 1 ⇒ reference better), as in the paper's tables.
- DMW: `d_t = e_bench,t² − e_ref,t²`; `DM = d̄ / sqrt(V̂/T)` with `V̂` = autocovariances of `d` up to lag h−1 (rectangular kernel;
  fall back to Newey–West if V̂ ≤ 0). HLN: `DM* = DM · sqrt((T + 1 − 2h + h(h−1)/T) / T)`; p-value two-sided from Student t(T−1).
  Implement in `evaluate.py` and unit-test against a hand-computed example.
- Bold = p < 0.10.

## Replication tables
- `outputs/tables/table1.csv` … `table4.csv` in the paper's layout: first row absolute RMSFE, then relative RMSFE (p-value).
- `outputs/tables/compare_paper.csv`: ours vs paper (from `docs/paper_spec.md` §6) with differences, per cell.
- Interpretation checklist: Does disaggregation beat ARIMA(1) at h = 2–3? Is h = 1 RMSFE tiny (two months known)? Do oil-
  price surprises explain most h > 1 error (regress errors on crude-oil changes, R² ≈ 60 % in paper)?

## T5 extension ideas
Sub-period tables (2004–2011, 2012–2019, 2020–latest), rolling relative RMSFE plots, sensitivity to each `proposed`
decision (D-01 constant, D-02 grid, D-03 window), Giacomini–White conditional test as a robustness check.

## Checks
- The engine reproduces a trivial benchmark exactly (random-walk-in-levels → known analytic errors).
- No-look-ahead test: shift all post-origin data → identical `pi_hat`.
- Count of forecasts per h equals expected number of origins with available actuals.
