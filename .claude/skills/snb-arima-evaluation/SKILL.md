---
name: snb-arima-evaluation
description: Pseudo-out-of-sample forecast evaluation for the SNB disaggregate ARIMA replication - recursive quarterly forecast origins with two months of the current quarter known, horizons 1–5 quarters, benchmarks (AR(1), ARIMA(1)/(6)/(14), consensus, SNB conditional forecast), RMSFE, relative RMSFE and Diebold-Mariano-West tests with the Harvey-Leybourne-Newbold correction. Use for tasks T3.1–T3.3, T4.2, T5.1–T5.2, to reproduce the paper's Tables 1–4, or for any new out-of-sample comparison.
---

# SNB ARIMA — evaluation (T3.x, T4.2, T5.x)

## Forecast engine (`src/arima_snb/evaluate.py`)
```python
inputs = load_inputs()                                    # panel, specs, collection, weights, crude, mortgage
res = run_pseudo_oos(inputs, evaluation_origins(), n_jobs=OOS_N_JOBS, cache=OOS_CACHE, force=False)
ev = eval_table(res["quarterly"], quarterly_actuals(inputs, official_cpi()))  # origin_q, h, target_q, model, pi_hat, pi_actual
```
Per origin, `forecast_origin` = `plain_item_forecasts` (cached) → `special_item_forecasts` (oil ECM + rent) →
`aggregate_origin` (splice, chain, quarterly y-o-y for h = 1..5, h = 1 current quarter). Two variants from one fit:
`arima182` (plain ARIMA for oil/rent, Tables 2/4) and `arima182_special` (ECM + rent model, Table 1 analogue, D-50).
Benchmarks: `benchmarks.py` (`forecast_origin`, `forecast_ar1`, `snb_forecast_origin`, `kof_for_origin`).
- Origins per D-04: Feb, May, Aug, Nov of 2004 … 2011 (32). Thesis extension (T5.1): continue to the latest data.
- **Cache** the expensive part only: plain item fits per origin in `data/interim/oos/` (~1–2 min/origin at 7 processes);
  recompute special models and aggregation every run (seconds), so a later oil/rent change needs no refit. `--force`
  refits. Full runs take 30–60 min: start them in the background and check the per-origin log.
- Each `model_fn` must enforce the data cut itself (CPI ≤ origin; oil/FX ≤ first day of the 3rd quarter month; weights,
  specs, collection calendar as known at origin).

## Benchmarks
| Name | Construction |
|---|---|
| `arima182` / `arima182_special` | see engine above (D-50) |
| ARIMA(14), ARIMA(6), ARIMA(1) | groups specified and forecast like items (D-55); ARIMA(1) on official CPI (D-47); see `snb-arima-aggregate` |
| AR(1) | monthly Δlog CPI with 12 month intercepts (D-05 rev.) — a one-constant AR(1) misses sales seasonality (RMSFE zig-zags across h); `ar1_plain` = sensitivity |
| Consensus | KOF consensus (D-06 rev., confirmed): mean of `prices_cy` / `prices_ny` from the survey of the **origin quarter** (D-56). Evaluate on **annual-average CPI inflation of the current and next year** — average our quarterly forecasts to calendar years (realised quarters = actuals) and score every model on that same target. Interpolating KOF to quarters is only a labelled secondary variant; say in the tables that the paper's Consensus Economics row is not replicated exactly. Next-year target is scorable at h ≤ 5 only from Q4 origins (D-57) |
| SNB conditional | SNB cube `snbiprogq` (D-20); quarter of publication ↔ origin of that quarter; starts June 2004 ⇒ no 2004Q1, T = 31 |
The paper's "real-time ARIMA" vintages are not public — our closest analogue is ARIMA(182) with special models; state this clearly.

## Metrics and test
- `RMSFE_h = sqrt(mean((π − π̂)²))` over origins with available actuals for horizon h.
- Relative RMSFE = RMSFE_benchmark / RMSFE_reference (> 1 ⇒ reference better), as in the paper's tables.
- DMW: `d_t = e_bench,t² − e_ref,t²`; `DM = d̄ / sqrt(V̂/T)` with `V̂` = autocovariances of `d` up to lag h−1 (rectangular kernel;
  fall back to Newey–West if V̂ ≤ 0). HLN: `DM* = DM · sqrt((T + 1 − 2h + h(h−1)/T) / T)`; p-value two-sided from Student t(T−1).
  Implemented as `evaluate.dmw_hln(e_bench, e_ref, h)` and `evaluate.comparison_table(ev, reference, benchmarks, ...)`
  (D-52; tested on hand examples) — reuse them, do not re-implement.
- Non-quarterly targets (annual KOF): kernel lag = number of overlapping forecasts of the same target − 1
  (current year from 4 quarterly origins → lag 3; next year from Q4 origins only → 0), D-58.
- Bold = p < 0.10.

## Replication tables
- `outputs/tables/table1.csv` … `table4.csv` in the paper's layout: first row absolute RMSFE, then relative RMSFE (p-value).
- `outputs/tables/compare_paper.csv`: ours vs paper (from `docs/paper_spec.md` §6) with differences, per cell.
  Generator: `scripts/13_replication_tables.py` + `report.py`.
- Cells that cannot be replicated are '–' with a footnote: Table 1 Consensus (KOF is annual only → Table 1 panel B on
  the annual target, D-06 rev., D-57), Table 3 real-time rows (vintages not public; use T2.3/T2.4 item errors),
  relative RMSFE with a zero reference (rents h = 1).
- **Diagnose a miss** (a table does not reproduce the paper's ranking or gain): decompose the loss difference by
  ARIMA(14) sub-aggregate, then by item contribution, and try cheap no-refit variants from the cached forecasts
  before refitting anything (`scripts/explore/t42_diagnose_extended.py`).
- Interpretation checklist: Does disaggregation beat ARIMA(1) at h = 2–3? Is h = 1 RMSFE tiny (two months known)? Do oil-
  price surprises explain most h > 1 error (regress errors on crude-oil changes, R² ≈ 60 % in paper)?

## T5 extension ideas
Sub-period tables (2004–2011, 2012–2019, 2020–latest), rolling relative RMSFE plots, sensitivity to each `proposed`
decision (D-01 constant, D-02 grid, D-03 window), Giacomini–White conditional test as a robustness check.

## Checks
- The engine reproduces a trivial benchmark exactly: items flat after the origin → aggregate flat → h = 1 forecast
  computable by hand (`tests/test_evaluate.py::test_random_walk_benchmark_reproduced_exactly`).
- No-look-ahead test: shift all post-origin data → identical `pi_hat`.
- Count of forecasts per h equals expected number of origins with available actuals.
