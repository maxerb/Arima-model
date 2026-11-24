"""T2.5 rows for the shared logs (decisions.md, skill_feedback.md); used by t25_stage_own_changes.py.

Kept as code (AGENTS.md rule 7) so the rows can be appended to the HEAD version of a shared file whose
working copy also holds other sessions' uncommitted rows.
"""

DECISIONS = [
    "| D-45 | G9 | Aggregate forecasts: item forecasts of log prices are turned into index levels by exp(log_p_hat) "
    "(point forecast, no log-normal variance correction) and spliced to the actual item indices up to the origin; "
    "the spliced panel goes through the same chained Laspeyres formula as the actuals (D-13, D-29, D-30). Index "
    "levels are on the full-history chain, so actual and forecast months share one scale; y-o-y for h = 1…5 uses "
    "actual months where known (`aggregate.forecast_aggregates`, `forecast_quarterly_yoy`) | Paper aggregates item "
    "point forecasts with CPI weights (p. 5); the bias correction exp(σ²/2) is tiny for monthly item errors and "
    "would cancel largely in y-o-y rates | exp(log_p_hat + σ²/2); aggregate log changes with fixed weights "
    "(ruled out by AGENTS.md §7) | proposed |",
    "| D-46 | — | Aggregates built in T2.5: total, CPI excl. oil products (all items but heating oil i100 and fuels "
    "i130, `special == oil`), the 6 ARIMA(6) and 14 ARIMA(14) groups of `items.csv`. BFS core inflation (core 1: "
    "excl. fresh/seasonal products, energy and fuel) is **not** built: Table 9 has no membership list and Tables 1–4 "
    "evaluate headline CPI only | Paper mentions core only as a by-product (p. 5) | Build BFS core 1 from the BFS "
    "special-grouping membership if needed in T5 | proposed |",
    "| D-47 | G12 | Benchmark inputs (T3.2, `data/final/subaggregates_long.csv`): ARIMA(1) is fitted on the **official** "
    "headline CPI (SNB cube `plkopr`, Dec 2010 = 100; same series as the AR(1) benchmark D-05 and the evaluation "
    "target); ARIMA(6)/(14) on sub-aggregates re-aggregated from the 182 items with summed item weights "
    "(`subaggregate_weights.csv`; re-aggregating them gives the 182-item total exactly) | Paper Table 9: ARIMA(1) = "
    "total CPI (weight 100); BFS publishes no index for the paper's custom groups (domestic/imported, transport "
    "excl. oil, …), so ARIMA(6)/(14) cover ~93 % of the basket, not 100 % as in the paper | ARIMA(1) on the 182-item "
    "total (same basket for all four levels) | confirmed (user, 2026-11-24) |",
]

FEEDBACK = [
    "| F-043 | 2026-11-24 | snb-arima-aggregate | T2.5 | missing | `aggregate_index` never started the chain of a "
    "sub-aggregate whose items all enter after May 1993 (Education, May 2000), so the ARIMA(14) groups did not add up "
    "to the total (rel. gap 1.5e-3) | failed check in `08_aggregate_forecasts.py` | Add check 'sub-aggregates "
    "re-aggregated with summed weights equal the item total' to Checks (code fixed in T2.5) | open |",
    "| F-044 | 2026-11-24 | snb-arima-aggregate | T2.5 | ambiguous | 'ARIMA(1): one ARIMA on total CPI' and "
    "`build_subaggregate_series(level='agg1')` (items) disagree with paper Table 9 (weights sum to 100 = full basket) "
    "| new decision D-47 asked of the user | State: ARIMA(1) on official CPI, ARIMA(6)/(14) from the 182 items (D-47) "
    "| open |",
    "| F-045 | 2026-11-24 | snb-arima-aggregate | T2.5 | missing | Interface lists no forecast-side functions (splice "
    "actual+forecast, weights known at origin, h -> target quarter); pitfall: a column named `aggregate` clashes with "
    "`DataFrame.aggregate` | improvised `weights_known_at`, `splice_forecast`, `forecast_aggregates`, "
    "`forecast_quarterly_yoy`, `subaggregate_weights`; KeyError from `q.aggregate == ...` | Add the five signatures "
    "and the df['aggregate'] note to Interface | open |",
    "| F-046 | 2026-11-24 | snb-arima-item-models | T2.2 | one-off | `06_item_models.py` re-read old origins parsing "
    "only `origin`, so `target` got two date formats once a second origin was appended | ValueError in "
    "`pd.to_datetime` in T2.5 | Code fixed (parse both; readers use format='ISO8601'); no skill edit | applied |",
]


def add_to(text: str) -> str:
    """Insert the FEEDBACK rows after the last F- row of a skill_feedback.md text (keeps its line endings)."""
    nl = chr(13) + chr(10) if chr(13) + chr(10) in text else chr(10)
    lines = text.split(nl)
    if any(l.startswith("| F-043 |") for l in lines):
        return text
    last = max(i for i, l in enumerate(lines) if l.startswith("| F-"))
    lines[last + 1:last + 1] = FEEDBACK
    return nl.join(lines)
