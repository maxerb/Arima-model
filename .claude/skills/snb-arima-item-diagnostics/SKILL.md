---
name: snb-arima-item-diagnostics
description: Step 1 of the SNB ARIMA item-model specification - per CPI item run ADF and KPSS unit-root tests on log prices, detect lag-12 seasonality from the ACF of log changes, classify collection frequency, and decide the method per item (ARIMA, quarterly-lag ARIMA, ad-hoc fallback, oil ECM, rent model), writing item_specs.csv. Use for task T2.1 or when an item's specification needs revisiting.
---

# SNB ARIMA — item diagnostics → `item_specs.csv` (T2.1)

Paper p. 6: done "only every few years", so specs are fixed per **spec vintage**. The vintage scheme is a choice to put
to the user (few vintages, e.g. 2003/2007, vs. yearly); this project uses **yearly vintages**: vintage Y uses data to Dec Y
and serves origins in Y+1 (D-31, `SPEC_VINTAGES`, `diagnostics.specs_for_origin`). Never use data after the vintage date.

## Procedure (per item, data up to the vintage date)
1. **Integration order.** On `log_p` (collected months for infrequent items, or quarterly sampling for quarterly items):
   - ADF (`statsmodels.tsa.stattools.adfuller`, regression `"ct"` on levels, autolag `"BIC"`): H0 unit root.
   - KPSS (`kpss`, regression `"ct"`): H0 stationarity.
   - Repeat on `Δlog_p` (regression `"c"`). Expected: levels I(1), differences I(0). Paper keeps **d = 1 for all items**;
     record test outcomes and only flag the rare items where tests disagree at 5 % (`d_flag`), do not change `d`.
2. **Seasonality.** ACF of `Δlog_p` (monthly items) up to lag 36. Seasonal if the ACF at lag 12 (and ideally 24) is outside
   ±1.96/√T and positive. Clothing/footwear and fresh vegetables should come out seasonal; rice should not (paper Chart 1).
3. **Collection frequency** from `collection.csv` as of the vintage, by collections per year (D-34): ≥ 10 `monthly`,
   5–9 `6x`, 3–4 `quarterly`, ≤ 2 `less_than_quarterly`. Take max(inferred, calendar) count: inferred flags
   undercount (a collected but unchanged price looks like no collection).
4. **Method assignment**
   - `special == oil` → `ecm`; `special == rent` → `rent`.
   - `less_than_quarterly` → `adhoc_last` (no model, paper p. 7).
   - fewer than `MIN_OBS` observations (decision; default 36 monthly or 12 quarterly) → `adhoc_avg_yoy`.
   - `quarterly` → `arima` with `quarterly_lags = True` (only lags 3, 6, 9, …).
   - else `arima`, with `seasonal` from step 2.
5. Write `data/final/item_specs.csv` with: `vintage, item_id, d, d_flag, adf_p_level, kpss_p_level, seasonal, acf12,
   collection_freq, quarterly_lags, method, reason`.

## Checks
- Count items per method and per vintage; the vast majority should be `arima` with d = 1. Expect `d_flag` for
  13–26 % of items (more than the paper's "very few"); d stays 1, so this is a note, not an error.
- Plot 3 examples (one seasonal, one quarterly, one monthly non-seasonal) with ACF → `outputs/figures/diag_examples.png`.
- Test: changing data after the vintage date does not change `item_specs` for that vintage.

## Pitfalls
- Running ACF on carried-forward monthly data of a quarterly item gives a spurious spike at lag 3 and 12 — use the
  collection-month series for infrequent items.
- KPSS p-values are truncated to [0.01, 0.1] in statsmodels — store the flag, not just the p-value.
