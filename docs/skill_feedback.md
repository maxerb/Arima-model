# Skill feedback log

Maintained by the `skill-feedback-loop` skill. One row per finding; rows are never deleted, only their status changes.
Types: `wrong` · `missing` · `ambiguous` · `trigger` · `bloat` · `project-fact` · `one-off`.
Status: `open` · `proposed` · `applied` · `rejected` · `deferred`.

## Findings

| ID | Date | Skill | Task | Type | Finding | Evidence | Fix | Status |
|---|---|---|---|---|---|---|---|---|
| F-001 | 2026-11-24 | snb-arima-next-task | T0.0 | missing | T0.0 did not mention pytest, which is not in the old requirements; had to add it and re-freeze | improvised step | Add "install pytest, then `pip freeze --exclude-editable > requirements.txt`" to T0.0 | applied |
| F-002 | 2026-11-24 | snb-arima-next-task | T0.0 | missing | T0.0 assumed every raw file can be tracked; KOF licence unknown, so those files had to be gitignored | improvised step | Add "check each raw file's licence before tracking it (D-08)" to T0.0 | applied |
| F-003 | 2026-11-24 | snb-arima-next-task | T0.0 | ambiguous | T0.0 needed `config.py` (for RAW) before T0.1 creates it | improvised: created config.py paths in T0.0 | Say T0.0 creates the paths part of config.py | applied |
| F-004 | 2026-11-24 | snb-arima-next-task | T0.1 | one-off | Self-check test flagged its own docstring for containing the forbidden path pattern | failed check | Reworded the test; no skill change | applied |
| F-005 | 2026-11-24 | snb-arima-data | T1.1 | wrong | Skill says weights come from "LIK Gewichtung per year"; actually all annual weights are in one BFS file `GEWICHTUNGEN` (one sheet per basket); the 2015/2020 detail files carry only their latest weight year | improvised step | Name `GEWICHTUNGEN` and the detailresultate page in the dataset table | applied |
| F-006 | 2026-11-24 | snb-arima-data | T1.1 | missing | Old BFS files are .xls → needs `xlrd`; repeated PosNo for special groupings below the main hierarchy; index levels > 1000 for back-cast PCs/TVs | improvised step | Add these three to Pitfalls | applied |
| F-007 | 2026-11-24 | snb-arima-data | T1.1 | one-off | Scripts must run with `.venv/Scripts/python` (package installed there), not the system python | failed check | none (environment) | – |
| F-008 | 2026-11-24 | snb-arima-next-task | T0.0–T1.4 | missing | Review page never updated after tasks: statuses and decisions were typed into the HTML and no step refreshed it (showed 0/22 done and D-01…D-08 after 7 tasks and 25 decisions) | user question "does the page update when tasks are done?" | `scripts/build_review_page.py` generates both from AGENTS.md / decisions.md; new step 9 "Refresh the review page" in the skill; `tests/test_review_page.py` fails when stale (user approved) | applied |
| F-009 | 2026-11-24 | snb-arima-data | T1.2 | wrong | SNB conditional forecasts said "hand-collect"; they exist as SNB cube `snbiprogq` | improvised step (T1.2 retro) | Name the cube in the datasets table | applied (P1 retro, user OK; eval data S-1) |
| F-010 | 2026-11-24 | snb-arima-data | T1.2 | wrong | Mortgage rates: BWO page is JS-only (no file); SNB `zikrepro` `M_MV` covers 1976–today | failed download | List `zikrepro` first, BWO only as reference | applied (P1 retro, user OK; eval data S-2) |
| F-011 | 2026-11-24 | snb-arima-data | T1.3 | wrong | Step 5 implies Table 9 has per-item agg6/agg14 (it has only totals) and gives printed pp. 21–25 (= PDF pp. 23–27) | improvised step | Real columns, agg6 left empty (D-21), both page numbers | applied (P1 retro, user OK; eval data S-3) |
| F-012 | 2026-11-24 | snb-arima-data | T1.3 | missing | Calendar 'x' marks have no position in the PDF text layer; page headers leak into rows ("Table 8 continued Beef") | improvised method | Add method: render pages to PNG, transcribe, cross-check mark counts with text layer; skip headers | applied (P1 retro, user OK; eval data S-3) |
| F-013 | 2026-11-24 | snb-arima-cpi-panel | T1.4/T1.5 | wrong | Table 9 weights are LIK2005-basket weights for 2010 and are printed one row off for items 85–93, 119–124; matching inherited it (shoe repairs mapped twice) | failed check found in T1.5 | Step 1: match by those weights then order; check no BFS position used twice unless a documented merge (D-22 rev.) | applied (P1 retro, user OK; eval cpi-panel S-1) |
| F-014 | 2026-11-24 | snb-arima-cpi-panel | T1.5 | wrong | Step 3 says weights constant between revisions; BFS GEWICHTUNGEN has a column per year from 2002 (1993 col → 1993–99, 2000/01 → 2000–01); merges in later baskets need a split rule | improvised + asked user (D-26, D-27) | Replace step-3 rule; add split rule | applied (P1 retro, user OK; eval cpi-panel S-2) |
| F-015 | 2026-11-24 | snb-arima-cpi-panel | T1.4 | wrong | Check "no jump > 20 % at link month" cannot detect wrong links (ratio linking never jumps) | failed check | Replace by agreement of linked changes with BFS back-casts (`panel.backcast_agreement`) | applied (P1 retro, user OK; eval cpi-panel S-3) |
| F-016 | 2026-11-24 | snb-arima-cpi-panel | T1.4 | missing | 1993 and 2025 baskets renumber positions; names repeat (retail vs restaurant wine/beer) | improvised rule D-25 | Add pitfall | applied (P1 retro, user OK; eval cpi-panel S-1) |
| F-017 | 2026-11-24 | snb-arima-cpi-panel | T1.4 | wrong | Step 4: agg6 is neither in Table 9 nor in BFS files | resolved with user (D-21 rev.) | Point to `data/meta/agg6_rules.csv` + `classify.item_agg6` | applied (P1 retro, user OK; eval cpi-panel S-4) |
| F-018 | 2026-11-24 | snb-arima-cpi-panel | T1.5 | missing | Calendar rows are BFS sub-groups, not model items | improvised `data/meta/collection_calendar_items.csv` | Mention the hand map in step 5 | applied (P1 retro, user OK; eval cpi-panel S-4) |
| F-019 | 2026-11-24 | snb-arima-cpi-panel | T1.5 | wrong | Coverage check 92.8 % is the paper's sum; true BFS weights give 92.70 % (skirts 0.230 vs 0.143) | check value | Change check to ≈ 92.7 % | applied (P1 retro, user OK; eval cpi-panel S-4) |
| F-020 | 2026-11-24 | snb-arima-aggregate | T1.6 | wrong | Interface: `aggregate_index` takes index levels (`item_index`), not logs; `build_subaggregate_series` needs `items` | API mismatch with code | Copy real signatures | applied (P1 retro, user OK; eval aggregate S-1) |
| F-021 | 2026-11-24 | snb-arima-aggregate | T1.6 | ambiguous | "verify base month for 2000–2007": answer is basket periods May 1993→May 2000, May 2000→Dec 2001, then yearly Dec chaining; old period must include the overlap month | D-29 | State it, cite D-29 | applied (P1 retro, user OK; eval aggregate S-2) |
| F-022 | 2026-11-24 | snb-arima-next-task | T1.1/T1.2/T1.6 | missing | Recurring (F-007 + T1.2 + T1.6): scripts need `.venv/Scripts/python`; pip built matplotlib from source → `--only-binary=:all:`; `sed` with escaped pipes corrupted decisions.md → edit markdown tables with Python | 3 tasks | Add to Rules | applied (P1 retro, user OK; eval next-task S-1) |
| F-023 | 2026-11-24 | snb-arima-decision-research | D-xx batch | missing | User wanted all decisions in one file; PDFs unreadable via fetch could be read with Read(pages=…) | user request + improvised | Allow batch file `best_practice.md`; PDF fallback; table of unreachable sources | applied (P1 retro, user OK; eval decision-research 5) |
| F-024 | 2026-11-24 | snb-arima-next-task | T0.2 | one-off | T0.2 check `tests/test_decisions.py` not named in skill | improvised | none (T0.2 never recurs) | rejected |
| F-025 | 2026-11-24 | snb-arima-kalman-extension | T4.1 | wrong | Integration says the extension covers 'all items except oil and rent', but paper Table 4 / p. 15 use it for all 182 items (special models not used); user confirmed all 182 (D-41) | paper p. 15 + user answer | Replace with 'all 182 items incl. oil and rents (D-41)' | proposed |
| F-026 | 2026-11-24 | snb-arima-kalman-extension | T4.1 | wrong | Recommended `trend="t"` is SARIMAX's intercept form; the paper's mean mu is obtained exactly with an exogenous time index regression (Delta p = mu + Delta u), verified by simulation test | tests/test_kalman_ext.py | Replace the trend line with `exog = time index` (mean form, D-42) | proposed |
| F-027 | 2026-11-24 | snb-arima-kalman-extension | T4.1 | missing | With seasonal AR(12), p = 12 is invalid in SARIMAX (lag 12 in both polynomials) - crash at first run | ValueError in order search | Add: p <= 11 when seasonal | proposed |
| F-028 | 2026-11-24 | snb-arima-kalman-extension | T4.1 | missing | ML optimiser steps onto unit-circle AR roots -> LinAlgError in the stationary initialisation; background run of 182 items crashed after ~10 min | LinAlgError traceback | Add: catch, retry from neutral start (Nelder-Mead), SIC = inf for failed orders, step p down at forecast time | proposed |
| F-029 | 2026-11-24 | snb-arima-kalman-extension | T4.1 | missing | Skill gives no compute budget: SIC over p 0..12 per origin x 182 items x 32 origins ~ 2 days; asked user, chose yearly order vintages (D-44) | timing prototype scripts/explore/t41_kalman_prototype.py | Add timing note + 'present vintage scheme as a choice' | proposed |
| F-030 | 2026-11-24 | snb-arima-kalman-extension | T4.1 | one-off | Skill's simulation check with T = 300 is too short for a tolerance of 0.15 on phi (one seed gives phi1 = 0.30 with full monthly data too); test uses T = 1200 | test failure | Mention T >= 1000 in the check | proposed |
| F-031 | 2026-11-24 | snb-arima-next-task | T4.1 | one-off | Two sessions in one checkout picked overlapping decision IDs (T2.2 used D-35..D-37 in config.py); T4.1 moved to D-41..D-44 and noted it in the shared notes folder | config.py diff | Orchestrator could reserve ID blocks per parallel session | open |
| F-032 | 2026-11-24 | snb-arima-item-models | T2.2 | wrong | Estimation prescribes SARIMAX ML with powell/lbfgs retries: 0.1-0.8 s per fit, ~30 CPU h for 32 origins, and eq. (3) is an SSE criterion anyway; user chose conditional least squares (D-35) | scripts/explore/t22_fit_timing.py | Replace the Estimation bullet by CLS with PACF transform (stationary/invertible), nfev cap, failed = dropped | proposed |
| F-033 | 2026-11-24 | snb-arima-item-models | T2.2 | missing | Seasonal AR(12) with p = 12 is not identified (lag 12 in both factors; SARIMAX raises ValueError) - same as F-027 | ValueError in timing script | Add: p <= s - 1 when seasonal | proposed |
| F-034 | 2026-11-24 | snb-arima-item-models | T2.2 | missing | No rule for short samples: at origin 2004-02 the common SIC sample has 21 obs for up to 16 parameters; user chose a grid guard (D-37) | asked user | Add the guard (>= 24 monthly / 12 quarterly obs in the common sample, drop seasonal if needed) | proposed |
| F-035 | 2026-11-24 | snb-arima-item-models | T2.2 | wrong | Fallback table says plausibility band 'e.g. +-3 SD'; decision D-11 (now confirmed) uses the [1st, 99th] percentile of the item's own 12-month changes | decisions.md D-11 | Point the plausibility row to D-11 | proposed |
| F-036 | 2026-11-24 | snb-arima-item-models | T2.2 | ambiguous | Quarterly items: skill said quarterly-sampled series, D-10 said monthly series with lag lists; user chose quarterly sampling (D-36, D-10 revised). Interface: `collection` argument is really last year's pattern; function also returns a log dict | conflicting texts | Align the Model section with D-36; update the interface signature | proposed |
| F-037 | 2026-11-24 | snb-arima-item-models | T2.2 | missing | Runtime: joblib is not installed (stdlib ProcessPoolExecutor + __main__ guard on Windows used); MA candidates drifting to a unit root took 25 s each until the optimiser budget was capped (100 nfev, a 10x budget rescues none); 2.5-4 min per origin with 4 processes | scripts/explore/t22_profile_fit.py, t22_failed_fits.py | Replace the joblib hint; add budget cap and per-origin timing | proposed |
| F-038 | 2026-11-24 | snb-arima-item-models | T2.2 | one-off | Check 'SIC picks the true AR(2) order' failed with phi = (0.5, -0.3): MA(1) mimics it with one parameter less and wins legitimately; test uses phi = (0.3, 0.4) | test failure, scripts/explore/t22_sic_check.py | Mention a non-MA-like AR(2) in the check | proposed |
| F-039 | 2026-11-24 | snb-arima-oil-rent | T2.3 | wrong | Part A says 'heating oil, petrol, diesel - each separately', but the model panel (Table 9) has two oil items: heating oil i100 and fuels i130 (petrol and diesel in one position) | items.csv special == 'oil' | Replace with 'each oil item of items.csv (special == oil): i100 heating oil, i130 fuels' | proposed |
| F-040 | 2026-11-24 | snb-arima-oil-rent | T2.3 | ambiguous | Step 1 offers 'first ~5 business days of the month, or previous month's average' for x_t; user chose the last 10 daily prices before the 1st of month t (D-14 rev.), which also makes the step-4 'constant at last 10 days' rule consistent; the first-5-days variant was tested and is slightly worse out of sample | decisions D-14 rev., scripts/explore/t23_oil_timing.py | Step 1: state D-14 rev. timing; list first-days as the tested alternative (OIL_X_RULE) | proposed |
| F-041 | 2026-11-24 | snb-arima-oil-rent | T2.3 | missing | Estimation sample start for the ECM not mentioned; item models start May 2000, which leaves ~45 months at the 2004 origin; user chose May 1993 (D-38) | decision D-38 | Add to step 2: 'sample from OIL_SAMPLE_START (1993-05, D-38)' | proposed |
| F-042 | 2026-11-24 | snb-arima-oil-rent | T2.3 | missing | Interface: skill says 'same interface as forecast_item' but not how the exogenous series reaches it; implemented as optional `crude_chf_daily` argument of forecast_item / forecast_items (None = plain ARIMA benchmark, D-39). Table 3 check also needs the oil sub-index aggregation; 32 origins with ARIMA benchmark take ~4 min (run in background) | item_models.py diff, scripts/07_oil_ecm.py | Add one line on the crude_chf_daily switch and the runtime | proposed |
| F-043 | 2026-11-24 | snb-arima-aggregate | T2.5 | missing | `aggregate_index` never started the chain of a sub-aggregate whose items all enter after May 1993 (Education, May 2000), so the ARIMA(14) groups did not add up to the total (rel. gap 1.5e-3) | failed check in `08_aggregate_forecasts.py` | Add check 'sub-aggregates re-aggregated with summed weights equal the item total' to Checks (code fixed in T2.5) | open |
| F-044 | 2026-11-24 | snb-arima-aggregate | T2.5 | ambiguous | 'ARIMA(1): one ARIMA on total CPI' and `build_subaggregate_series(level='agg1')` (items) disagree with paper Table 9 (weights sum to 100 = full basket) | new decision D-47 asked of the user | State: ARIMA(1) on official CPI, ARIMA(6)/(14) from the 182 items (D-47) | open |
| F-045 | 2026-11-24 | snb-arima-aggregate | T2.5 | missing | Interface lists no forecast-side functions (splice actual+forecast, weights known at origin, h -> target quarter); pitfall: a column named `aggregate` clashes with `DataFrame.aggregate` | improvised `weights_known_at`, `splice_forecast`, `forecast_aggregates`, `forecast_quarterly_yoy`, `subaggregate_weights`; KeyError from `q.aggregate == ...` | Add the five signatures and the df['aggregate'] note to Interface | open |
| F-046 | 2026-11-24 | snb-arima-item-models | T2.2 | one-off | `06_item_models.py` re-read old origins parsing only `origin`, so `target` got two date formats once a second origin was appended | ValueError in `pd.to_datetime` in T2.5 | Code fixed (parse both; readers use format='ISO8601'); no skill edit | applied |
| F-047 | 2026-11-24 | snb-arima-oil-rent | T2.4 | wrong | Part B step 1 says the mortgage rate is the cantonal-bank average linked to the BWO rate in 2008Q2; the confirmed decision D-19 uses the continuous SNB series zikrepro M_MV instead | decisions D-19 | Step 1: 'mortgage rate = SNB M_MV (D-19), quarterly average (D-15 rev.)'; keep fn. 3 splice as the paper's original | proposed |
| F-048 | 2026-11-24 | snb-arima-oil-rent | T2.4 | project-fact | Step 5 says rents are collected in the 2nd month of the quarter 'since 2008'; the linked rent index changes only in Feb/May/Aug/Nov from 1993 on (scripts/explore/t24_rent_data.py) | data check | Step 5: 'since 1993 (D-48)'; AGENTS.md §7 'check earlier' can be answered | proposed |
| F-049 | 2026-11-24 | snb-arima-oil-rent | T2.4 | missing | Rent part silent on sample start, AR grid, information set for the current quarter's mortgage rate and the interface switch; user chose 1993Q2 and p = 0..4 (D-48); implemented `mortgage_rate` argument of forecast_item(s) (None = ARIMA benchmark, D-49); run takes ~25 s for 32 origins | decisions D-15 rev., D-48, D-49 | Add one line each to Part B (sample, grid, info set = months <= origin, mortgage_rate switch) | proposed |
| F-050 | 2026-11-24 | snb-arima-oil-rent | T2.4 | one-off | Script number 10_ clashed with T3.1's 10_pseudo_oos.py running in parallel; renamed to 07_rent_model.py (next to 07_oil_ecm.py) | sibling notes | none | applied |
| F-051 | 2026-11-24 | snb-arima-evaluation | T3.1 | ambiguous | Benchmarks row 'ARIMA(182) / real-time ARIMA' mixes Table 2's plain-ARIMA ARIMA(182) and the special-model variant; Table 1's reference is the real-time ARIMA | had to define two variants (D-50) | Split the row: `arima182` (plain oil/rent, Tables 2/4) and `arima182_special` (ECM + rent, Table 1 analogue), both from one fit per origin | open |
| F-052 | 2026-11-24 | snb-arima-evaluation | T3.1 | missing | No guidance on run time, worker count and cache granularity (item fits ~1–2 min/origin on 7 processes, special models seconds); pitfall `q.aggregate` = DataFrame method, not the column | empty selection in the random-walk test; improvised cache | Add: cache plain item fits per origin, recompute special rows each run; use q['aggregate'] | open |
| F-053 | 2026-11-24 | snb-arima-evaluation | T3.1 | missing | Checks list a random-walk engine check but no concrete form | improvised: items flat after origin -> aggregate flat -> h=1 value computable by hand (`tests/test_evaluate.py`) | Name that construction in Checks | open |
| F-060 | 2026-11-25 | snb-arima-evaluation | T4.2 | one-off | Skill says implement DMW in `evaluate.py`; that file was owned by the parallel T3.2 session, so DMW-HLN went to `kalman_eval.dmw_hln` (D-52) | own work, shared checkout | None (T3.3 can delegate `evaluate.dmw_test` to it) | one-off |
| F-061 | 2026-11-25 | snb-arima-evaluation | T4.2 | missing | No step for when a replication table misses the paper (Table 4 gain not reproduced): improvised a decomposition by ARIMA(14) sub-aggregate + item-level loss contributions + cheap no-refit variants from the cache (`scripts/explore/t42_diagnose_extended.py`) | own work | Add a 'diagnose a miss' bullet: decompose by sub-aggregate, then items, using cached forecasts before refitting | proposed |
| F-062 | 2026-11-25 | snb-arima-kalman-extension | T4.2 | missing | Skill silent on whether items on an ad-hoc fallback (sticky 'last value' items) get the state-space model; with a 1993 drift they lose in Health; hybrid improves h=4,5 (D-53 sensitivity) | Table 4 run | Mention the choice and point to D-41/D-53 | proposed |

## Summary per skill (updated at each macro retro)

Uses = tasks in which the skill was followed. Findings by type: w = wrong, m = missing, a = ambiguous, o = one-off.
User corrections = the user had to correct the agent (decisions the user was asked to make do not count).

| Skill | Uses | Findings (w/m/a/o) | User corrections | Corrections per use | Last retro |
|---|---|---|---|---|---|
| snb-arima-next-task | 9 (T0.0–T1.6) | 6 (0/4/1/1) | 1 (F-008) | 0.11 | P1, 2026-11-24 |
| snb-arima-data | 3 (T1.1–T1.3) | 7 (4/2/0/1) | 0 | 0 | P1, 2026-11-24 |
| snb-arima-cpi-panel | 2 (T1.4–T1.5) | 7 (5/2/0/0) | 0 | 0 | P1, 2026-11-24 |
| snb-arima-aggregate | 1 (T1.6) | 2 (1/0/1/0) | 0 | 0 | P1, 2026-11-24 |
| snb-arima-decision-research | 1 | 1 (0/1/0/0) | 0 | 0 | P1, 2026-11-24 |
| snb-arima-item-diagnostics | 0 (T2.1 running) | 0 | 0 | – | – |
| snb-arima-item-models | 0 | 0 | 0 | – | – |
| snb-arima-oil-rent | 0 | 0 | 0 | – | – |
| snb-arima-evaluation | 0 | 0 | 0 | – | – |
| snb-arima-kalman-extension | 0 | 0 | 0 | – | – |
| snb-arima-report | 0 | 0 | 0 | – | – |
| skill-feedback-loop | 10 (micro retros + P1 macro) | 0 | 0 | 0 | P1, 2026-11-24 |

**P1 macro retro (2026-11-24).** 15 findings applied (F-009…F-023), 1 rejected (F-024). Review page: no `reviews` or
`feedback` rows yet. Consistency pass: skill file contracts match AGENTS.md §4; `aggregate` signatures were out of date
(F-020, fixed). Pattern: P1 skills were written before the data were seen, so most findings are `wrong` facts about BFS
files and the paper's tables (8 of 15) — expect fewer once P2 skills are used against real data. Pruning: none needed
(all SKILL.md ≤ 100 lines). Generalisable lessons (candidates for a user-level skill, not created): "edit markdown tables
with Python, not sed"; "ratio chain-linking cannot be checked by level jumps — compare with back-casts".

## Ideas (not evidence yet; do not apply)

_P1 micro-retro candidates below were processed in the P1 macro retro as F-009…F-024._

### Micro retro T0.2 (2026-11-24) — snb-arima-next-task
- Finding: skill lists G4 among the "important" gaps to confirm, but the ask tool fits 4 questions; G4 (origins) was left `proposed` since it follows directly from the paper. No skill edit needed.
- Added `tests/test_decisions.py` as the T0.2 check (skill did not name one) — candidate addition to the skill's T0.2 section.

### Micro retro D-xx research (2026-11-24) — snb-arima-decision-research (new skill)
- User asked for all decisions in one file; the skill prescribes one note per decision. Improvised `docs/decision_research/best_practice.md` with one section per D-xx. Candidate skill edit: allow a "batch mode" writing one combined file.
- Many official PDFs failed for automated fetching (BFS image-only PDFs, IMF 404, StatCan/BoC/Harvard 403). Saved PDFs could be read page-by-page with the Read tool (worked for ECB WP 247 and SNB press release). Candidate skill edit: "if web-fetch gets an unreadable PDF, read the saved copy with Read(pages=…)"; list unreachable sources in a table instead of dropping them.
- Local data check (KOF consensus) changed a decision (D-06 refine) — step 5 of the skill proved useful.

### Micro retro T1.2 (2026-11-24) — snb-arima-data
- Skill says SNB conditional forecasts must be hand-collected; they exist as SNB cube `snbiprogq`. Candidate edit: name the cube in the datasets table.
- Skill suggests BWO for mortgage rates after 2008; BWO page is JS-only (no file). SNB `zikrepro` `M_MV` covers 1976–today. Candidate edit: list `zikrepro` first.
- `read_snb_cube` only handled one dimension and monthly dates; extended for D0/D1 and quarterly cubes (no skill change needed).
- Scripts need the project venv (`.venv/Scripts/python`); plain `python` lacked the package. Candidate edit: mention in next-task skill.
- 2026-11-24: user confirmed D-06 revision (KOF evaluated on annual-average inflation, cy/ny). Pending skill edit (needs approval): `snb-arima-evaluation` consensus row should say "annual-average target per D-06 rev." instead of the open "convert … only if defensible". → applied 2026-11-24 with user approval.

### Micro retro T1.3 (2026-11-24) — snb-arima-data
- Skill implies Table 9 gives `agg6, agg14` per item; it does not (only sub-aggregate totals). agg14 derived from item order, agg6 deferred to T1.4 (D-21). Candidate edit: say so in step 5.
- Skill says PDF pp. 21-25 for Table 9; those are printed page numbers (PDF pages 23-27). Calendars are PDF pp. 19-23. Candidate edit: give both.
- Improvised: the calendar 'x' marks have no column position in the text layer; rendered pages to PNG and transcribed visually, then cross-checked mark counts against the text layer. Candidate edit: describe this method.

### Micro retro T1.4 (2026-11-24) — snb-arima-cpi-panel
- Skill assumes the item list comes from Table 9 names; matching works only via weights, and the weights are those of the **2005 basket for 2010** (not the 2010 basket). Candidate edit: step 1 "match Table 9 by LIK2005 weights of 2010, then by order".
- Skill check "no jump > 20 % at a link month" cannot detect wrong links (ratio-linking never creates a level jump; seasonal items jump anyway). Improvised a better check: compare linked monthly changes with BFS back-casts in newer files. Candidate edit: replace the check.
- Skill does not mention that the 1993 and 2025 baskets use different position numbers, and that names repeat (retail vs restaurant wine/beer). Improvised name + dynamics rule (D-25). Candidate edit: add pitfall.
- D-21 plan (agg6 from BFS special groupings) does not work: groupings are aggregate series without membership lists. Candidate edit to snb-arima-data/cpi-panel once a source is found.
- Transcription bug from T1.3 fixed (item 9 "Table 8 continued Beef" -> "Beef"; page header was not skipped).
- agg6 follow-up (2026-11-24): BFS methods PDFs (2005, 2010 bases) publish domestic/imported and goods/services only as totals (Anhang 2), no per-position list. Membership regression on BFS grouping series (`src/arima_snb/classify.py`) reproduces the paper's ARIMA(6) totals on the full basket (16.3/28.2/18.9/8.6/23.9 vs 16.9/27.8/19.5/8.7/23.4) but item-level labels are not identified (e.g. margarine -> public services). Not wired into the pipeline; awaiting user decision.

- agg6 resolved with user (rules + data check, D-21 rev.). Candidate skill edit (snb-arima-cpi-panel step 4): agg6 is not in Table 9 nor in BFS files; use data/meta/agg6_rules.csv + classify.item_agg6.

## T1.5 micro retro (2026-11-24, snb-arima-cpi-panel)
- Wrong input found: paper Table 9 prints weights one row off in two blocks (items 85–93, 119–124); T1.4's weight matching inherited it (shoe repairs mapped twice). Fixed by name overrides (D-22 rev.). Candidate edit (step 1 / checks): "after weight matching, read the English↔German name pairs once and assert no BFS position is used by two items unless a documented merge".
- Skill step 3 says "before annual updating the weight is constant between revisions" — wrong for BFS: GEWICHTUNGEN has a new weight column every year from 2002 (2000/01 for 2000–01, one 1993 column). Candidate edit: replace with "use the GEWICHTUNGEN column of each year; 1993 column covers 1993–99, 2000/01 covers 2000–01 (D-26)".
- Skill step 3 does not cover one position carrying several items (merge in a later basket); asked user (D-27: split by last separate shares). Candidate edit: add the rule.
- Skill step 5 assumes calendar rows name model items; in fact they are BFS sub-groups. Improvised `data/meta/collection_calendar_items.csv`. Candidate edit: mention the hand map.
- Check "2010 coverage ≈ 92.8 %" is 92.70 with true BFS weights (paper's skirts weight 0.230 vs BFS 0.143). Candidate edit to the check value.
- Tooling: Bash `sed 's/\|...\|/'` (escaped pipes) matched the empty string and corrupted every line of decisions.md; reverted. Use Python for edits containing `|`.
- Observation for T5.1: coverage drops to 86–88 % from 2016 and 60 % in 2026 (2015 splits such as package holidays abroad/domestic and hospital in/outpatient map to one child only; 54 items without 2025 link, D-25).

### T1.6 micro retro (2026-11-24, snb-arima-aggregate)
- Skill interface `aggregate_index(item_log_p, ...)` takes log prices, but the Laspeyres formula needs index levels; implemented with levels (`item_index`). Candidate edit: rename the argument in the skill.
- Skill says "verify the base month for 2000–2007 bases": answer is basket periods May 1993→May 2000 and May 2000→Dec 2001, then Dec-chaining yearly (D-29). Off-by-one: the old basket period must include the overlap month (May 2000) or the chain breaks — candidate edit: state this.
- `build_subaggregate_series` needs the `items` table for groupings (signature in skill lacks it).
- Tooling: matplotlib was not in requirements/venv; `pip install matplotlib==3.9.2` tried to build from source on this Python → use `--only-binary=:all:` (pinned 3.11.2).
- Check passed: monthly y-o-y RMSE 0.067 pp (2001–2011); gaps > 0.2 pp only around the 2000 basket switch and 4 months 2018–2026.

### Micro retro T2.1 (snb-arima-item-diagnostics), 2026-11-24
- Skill default "two vintages (2003, 2007)" replaced by annual vintages at the user's choice (D-31); candidate edit: present vintage scheme as a choice, not a default.
- Skill's frequency classes have no count thresholds; improvised ≥10 / 5–9 / 3–4 / ≤2 per year and max(inferred, calendar) because inferred flags undercount (D-34). Candidate edit: state thresholds and the undercount pitfall.
- Skill says paper finds "very few" items failing I(1); our d_flag fires for 13–26 % of items. Not a skill error (d stays 1), worth noting as expected.
- Tooling: system `python` lacks statsmodels; use `.venv/Scripts/python.exe`. Full run takes ~2.5 min (per-item filtering of collection.csv) — acceptable.
- Checks passed: no-look-ahead test, rice non-seasonal, trousers quarterly→6x (2008)→monthly (2011), seasonal throughout (paper Chart 1).

### Micro retro T4.1 (snb-arima-kalman-extension), 2026-11-24
- No user corrections; three choices put to the user (items, lag-order timing, collection rule), all recommended options taken (D-41, D-44, D-43).
- Skill wrong on item scope and drift parametrisation (F-025, F-026); missing p <= 11 with SAR(12), fit failures, compute budget (F-027..F-029). All queued as `proposed` for the P4 retro.
- Checks passed: simulation recovery (quarterly -> monthly collection), monthly = plain ARIMA, SIC picks the true order, no-look-ahead, smoother hits collected prices.

### Micro retro T2.2 (snb-arima-item-models), 2026-11-24
- No user corrections; four choices put to the user (estimation, quarterly items, short samples, fallbacks), all recommended options taken (D-35, D-36, D-37, D-11 confirmed).
- Skill wrong/outdated on estimation and plausibility band (F-032, F-035), ambiguous on quarterly items (F-036), missing seasonal p cap, short-sample guard and runtime notes (F-033, F-034, F-037). All queued as `proposed` for the P2 retro.
- Checks passed: no-look-ahead (single item and all items, prices and collection flags perturbed), SIC picks true AR(2), CLS vs SARIMAX ML, MA invertibility, quarterly steps only in collection months, ad-hoc rules. Single-origin runs 2004-02 and 2011-02: all 182 items forecast, 1-2 plausibility fallbacks.

### Micro retro T2.3 (snb-arima-oil-rent, oil ECM), 2026-11-24
- No user corrections; four choices put to the user (timing of x_t, Brent vs WTI, sample start, lags), all recommended options taken (D-14 rev., D-38).
- Skill wrong on the oil item list (F-039), ambiguous on the crude timing (F-040), silent on sample start and on the exogenous-data interface (F-041, F-042). All queued as `proposed` for the P2 retro.
- Improvised: an in-sample timing check (heating oil fits the first 5 days of month t better) was overturned by the out-of-sample RMSFE; logged in D-14 rev. as a sensitivity result.
- Checks passed: parameter recovery on simulated ECM, no-look-ahead for item prices and crude (both timing rules), crude just before the cut-off does move the nowcast, convergence to the long run, routing through forecast_item / forecast_items; Table 3 oil RMSFE 1.15/7.70/12.85/15.45/16.94 vs paper 1.14/6.72/12.49/15.25/17.10.

### Micro retro T2.4 (snb-arima-oil-rent, rent model), 2026-11-24
- No user corrections; three choices put to the user (sample start, quarterly mortgage measure, AR grid), all recommended options taken (D-48, D-15 rev.).
- Skill wrong on the mortgage series (F-047, superseded by D-19) and on the start of quarterly rent collection (F-048); silent on sample, grid, info set and interface (F-049). Queued as `proposed` for the P2 retro.
- Checks passed: parameter recovery (β⁺, β⁻), no-look-ahead for rents and mortgage rate (origin-month rate does move the forecast, origin+1 does not), changes only in collection months, h = 1 error 0, routing through forecast_item / forecast_items; Table 3 rent RMSFE 0.00/0.26/0.51/0.64/0.76 vs paper 0.00/0.24/0.46/0.56/0.61, ARIMA/rent 1.01/1.12/1.20/1.20 vs paper 1.18/1.44/1.72/1.90.

### Micro retro T4.2 (snb-arima-evaluation, extended ARIMA → Table 4), 2026-11-25
- No user corrections (task ran as a side session). Paper settled the model (p. 15: no oil/rent models in the extension), so no choice was put to the user; D-52 (DMW-HLN), D-53 (mechanics + sensitivity) proposed.
- Improvised: diagnosis of the missed Table 4 gain (F-061); DMW placed outside `evaluate.py` because of file ownership (F-060); ad-hoc items question (F-062).
- Checks passed: no-look-ahead (post-origin prices and collection flags perturbed → identical forecasts), DMW-HLN vs two hand-computed examples (incl. Newey-West fallback), 182 items at every origin, 0 failed fits, T = 32 per h; RMSFE 0.086/0.459/0.750/0.918/1.006 vs paper 0.06/0.32/0.64/0.86/1.00.
