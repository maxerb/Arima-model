---
name: snb-arima-cpi-panel
description: Build the consistent Swiss CPI expenditure-item panel for the SNB ARIMA replication - chain-link item indices across CPI bases/basket revisions, map items to the paper's ~182 model items and to the ARIMA(6)/ARIMA(14) sub-aggregates, construct annual weights and the item collection calendar (official + inferred from carried-forward prices). Use for tasks T1.4–T1.5, or when items, weights or collection months look wrong.
---

# SNB ARIMA — CPI item panel (T1.4–T1.5)

## Inputs
Raw item indices and weights via `src/arima_snb/io.py`; `data/meta/items_paper_table9.csv`;
`data/meta/collection_calendar_paper.csv`.

## Outputs (contracts in AGENTS.md §4)
`data/final/items.csv`, `data/final/cpi_items_long.csv`, `data/final/weights.csv`, `data/final/collection.csv`,
plus `data/interim/item_mapping.csv` (raw BFS position code per base → `item_id`) and a mapping report.

## Procedure
1. **Item mapping.** For each base, list positions at the lowest level. Map them to `item_id`s that are stable over time,
   starting from the paper's Table 9 list. Table 9 weights are the **LIK2005-basket weights for 2010** (not the 2010
   basket): match on those weights, then on order. Table 9 prints weights one row off for items 85–93 and 119–124
   (D-22 rev.) — read the English↔German name pairs once and fix with `data/meta/item_mapping_overrides.csv`.
   Rules (log as decisions):
   - Item split in a revision → merge the children back into the parent using their weights (paper did this, p. 11).
   - Item introduced after May 2000 → keep with a late `first_obs` (handled by fallbacks in item models) or drop if the
     paper dropped it; target ≈ 182 items covering ≈ 93 % of 2010 weight.
   - Keep the mapping as a CSV, never as code-only logic; it must be reviewable.
2. **Chain-linking.** For each item, link successive bases at the overlap month (base month, e.g. Dec 2005):
   `I_linked_t = I_new_t × (I_old_link / I_new_link)` for `t` after the link. Express everything on one reference base.
   Then `log_p = log(I_linked)`.
3. **Weights.** `weights.csv` with one weight per item and year, from the GEWICHTUNGEN column of each year (annual from
   2002; the 1993 column covers 1993–99, the 2000/01 column 2000–01; D-26). Merged items: weight = sum of children. One
   position carrying several items after a later merge: split by their last separate weight shares (D-27). Store raw
   weights; normalisation happens in aggregation.
4. **Sub-aggregate labels.** `agg14` (COICOP-like) from Table 9 order. `agg6` (origin × product type) is neither in
   Table 9 nor in BFS files: use `data/meta/agg6_rules.csv` + `classify.item_agg6` (rules + regression, D-21 rev.).
   `special = oil` for heating oil, petrol, diesel; `special = rent` for rents.
5. **Collection calendar.**
   - Official months from the paper's Tables 5–8 for 2000–2011. Calendar rows are BFS sub-groups, not model items:
     map them with `data/meta/collection_calendar_items.csv` (group level applies unless an item is listed separately).
   - Inferred: month counts as collected if `|Δ log_p| ≥ 1e-3` (paper fn. 9). Store both sources.
   - For real-time use, an origin in year `y` must only use the pattern **observed in year `y−1`** (paper p. 14–15).
6. Write the mapping report: items per agg6/agg14, total weight coverage per year, items with short samples, items whose
   inferred collection disagrees with the official calendar.

## Checks
- Re-aggregate the panel with `snb-arima-aggregate` and compare y-o-y with official CPI (paper Chart 4): mean absolute
  gap in y-o-y inflation should be small (≈ 0.1 pp or less); show the plot `outputs/figures/chart4_reaggregated_vs_official.png`.
- 2010 coverage ≈ 92.7 % with BFS weights (the paper's Table 9 sums to 92.788; F-019); agg6 weights in 2010 close to paper (16.875, 27.818, 19.499, 8.711, 23.447, 3.650 after
  normalising to 100 on the full basket).
- No BFS position is used by two items unless it is a documented merge (catches Table 9 row shifts).
- Linked monthly changes agree with BFS back-casts in newer files (`panel.backcast_agreement`). A "jump at the link
  month" check cannot find wrong links: ratio linking never creates a level jump (F-015).
- Trousers (men/women): quarterly steps until 2007, ~6×/year 2008–2010, monthly from 2011 (paper Chart 1).

## Pitfalls
- Base months differ in level conventions (May 2000 vs December bases) — link at the actual overlap month in the data.
- Carried-forward values are real index values, not missing data — keep them in `cpi_items_long.csv`; the collection
  flag tells models how to treat them.
- Seasonal items (fruit, vegetables, winter sports) can have "seasonal" collection — flag explicitly.
- The 1993 and 2025 baskets renumber positions, and names repeat (retail vs restaurant wine/beer): match on name +
  dynamics, never on position number alone (D-25).
