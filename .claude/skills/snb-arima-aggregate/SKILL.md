---
name: snb-arima-aggregate
description: Aggregate Swiss CPI item-level forecasts or actuals into total CPI, sub-aggregates (ARIMA(6), ARIMA(14), goods/services, core/excl. oil) and quarterly year-on-year inflation, using the chained Laspeyres structure of the Swiss CPI with annual weights based on December of the previous year. Use for tasks T1.6 and T2.5, for building the ARIMA(1)/(6)/(14) benchmark series, or whenever an aggregate looks off versus official CPI.
---

# SNB ARIMA — aggregation (T1.6, T2.5)

## Interface (`src/arima_snb/aggregate.py`)
```python
def aggregate_index(item_index: pd.DataFrame, weights: pd.DataFrame, items: list[str] | None = None) -> pd.Series:
    """Chain-linked Laspeyres aggregate of item index LEVELS (wide: month x item_id; not logs — the formula is in levels)."""
def quarterly_yoy(index_m: pd.Series) -> pd.Series:
    """Quarterly average of a monthly index → y-o-y % change, indexed by pd.Period('Q')."""
def build_subaggregate_series(item_index, weights, items: pd.DataFrame, level: Literal["agg1", "agg6", "agg14"]) -> pd.DataFrame:
    """Historical monthly sub-aggregate indices (inputs for ARIMA(1)/(6)/(14) benchmarks)."""
```

## Formula
For month `t` in year `y`, with weights `w_{i,y}` normalised over the items included:
`A_t / A_{Dec,y−1} = Σ_i w_{i,y} · I_{i,t} / I_{i,Dec,y−1}`, then chain: `A_t = A_{Dec,y−1} · (…)`.
Forecast paths crossing a year boundary use the **weights known at the origin** (next year's weights are unknown →
keep current year's weights; log as decision). Before annual weight updates the basket periods are May 1993→May 2000
and May 2000→Dec 2001, then yearly December chaining (D-29). The old period must **include** the overlap month
(May 2000), else the chain breaks.

Inflation target: `π_q = 100 · (Ā_q / Ā_{q−4} − 1)` with `Ā_q` the 3-month average. When forecasting, splice: actual
months up to origin, forecast months after.

## Disaggregation levels for Table 2
- ARIMA(182): aggregate item forecasts.
- ARIMA(14)/(6): build historical sub-aggregate indices from the same items, fit **one ARIMA per sub-aggregate** with
  the item-model machinery (SIC, seasonal check), then aggregate with sub-aggregate weights.
- ARIMA(1): one ARIMA on total CPI.
- In all four, errors are measured against **official** CPI inflation (paper p. 11).

## Checks
- T1.6 / paper Chart 4: aggregate of actual item indices vs official CPI y-o-y 2001–latest; report mean abs. gap and max
  gap; save `outputs/figures/chart4_reaggregated_vs_official.png`. Investigate gaps > 0.2 pp (wrong link, missing item, wrong base month).
- Unit test: if all items have identical index paths, the aggregate equals that path; weights that do not sum to 1 are normalised.
- Unit test: `quarterly_yoy` on a series growing exactly 2 % p.a. returns 2.0.
