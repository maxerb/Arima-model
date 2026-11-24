# Best practice for every decision D-01 … D-17

Produced with the `snb-arima-decision-research` skill on 2026-11-24. One section per decision in
`docs/decisions.md`. **Rule used:** a source appears under "Evidence" only if it was actually opened and read
(the list of sources is at the end). Leads that came only from search-result snippets, or that could not be opened
(several PDFs returned 403/404 or had no text layer), are listed separately as **open leads**. Nothing here changes a
decision's status: confirmed decisions stay confirmed, proposed ones stay proposed until you confirm them.

**Evidence strength:** ●●● direct, from a source close to our setting · ●●○ indirect or general · ●○○ only our own
reasoning or the paper itself.

## Summary

| ID | Topic | Our choice | Verdict after research | Strength |
|---|---|---|---|---|
| D-01 | Constant in item models | include | **keep** | ●●○ |
| D-02 | SIC grid p ≤ 12, q ≤ 2 | as is | **keep, but check overlap with seasonal AR(12)** | ●●○ |
| D-03 | Recursive window, re-select order each origin | as is | **keep** | ●●● |
| D-04 | 32 origins Feb/May/Aug/Nov 2004–2011 | as is | **keep** (matches the SNB's quarterly meeting dates) | ●●● |
| D-05 | AR(1) on monthly Δlog CPI | as is | **keep**; add random walk with drift as an extra benchmark | ●●○ |
| D-06 | KOF Consensus instead of Consensus Economics | annual-average target | **adopted (confirmed 2026-11-24)**: KOF has only annual forecasts (current and next year) | ●●● (own data check) |
| D-07 | No add-factors in pseudo-OOS | as is | **keep** (paper p. 12) | ●○○ |
| D-08 | Raw data not in git | as is | n/a (repo housekeeping) | – |
| D-09 | ≥ 36 monthly obs for an ARIMA | as is | **keep**; FPP's auto.arima caps orders at n/3 for short series | ●○○ |
| D-10 | Quarterly items: lags 3, 6, 9, 12 only | as is | **keep** (paper p. 6), no outside source found | ●○○ |
| D-11 | Mechanical "implausible forecast" rule | as is | **keep provisionally**; literature lead not verified | ●○○ |
| D-12 | Item mapping across basket revisions | as is | **keep**; BFS methodology still to be read | ●○○ |
| D-13 | Chained Laspeyres, Dec link, latest known weights | as is | **keep** — same as Hubrich (2003) | ●●● |
| D-14 | Oil ECM (Engle–Granger, Brent in CHF) | as is | **keep provisionally**; check Brent vs WTI empirically | ●○○ |
| D-15 | Rent model with asymmetric Δmortgage(t−4) | as is | **keep**; mortgage reference rate starts 2008 (lead) | ●○○ |
| D-16 | SNB conditional forecasts transcribed by hand | as is | **keep** — press releases contain quarterly tables (verified for 2008) | ●●● |
| D-17 | Kalman extension in statsmodels | as is | **keep**; custom `MLEModel` with a time-varying transition matrix | ●●○ |

---

## D-01 (G1) — Constant in the item models
**Question.** Should ARIMA(p,1,q) models for log item prices include a constant (drift)?
**Paper.** It leaves the constant out only to keep the notation simple (p. 6).
**Evidence.**
- FPP3 §9.5 [S3]: with one difference (d = 1) and no constant, long-run forecasts go to a constant *level*, so
  forecast inflation goes to zero. With a constant, the *level* forecast follows a straight line, so inflation goes to
  the item's average. For price indices that rise on average, the version without a constant is biased at long horizons.
- `forecast::auto.arima` [S2] tries models with drift by default (`allowdrift = TRUE`), and FPP3 §9.7 [S3, summary]
  keeps the constant when it improves the information criterion.
- Hubrich (2003, p. 15) [S1] uses a random walk *with drift* as the benchmark for HICP components.
**Recommendation.** Keep the constant. Without it the forecast for h = 4–5 shrinks towards 0 % item inflation, which
is clearly wrong for items such as rents or services.
**Sensitivity.** In T5.1, rerun without a constant and compare RMSFE at h ≥ 3. Optionally let the Schwarz criterion
(SIC) decide whether to include it, as auto.arima does.

## D-02 (G2) — SIC search grid
**Question.** What maximum p and q should the Schwarz criterion search over?
**Evidence.**
- `auto.arima` defaults [S2]: max.p = 5, max.q = 5, seasonal max.P = max.Q = 2, information criterion AICc. The source
  code also caps p and q at n/3 for short series.
- FPP3 §9.6 [S3]: information criteria cannot compare models with different d. Choose d first (unit-root tests),
  then p and q by the criterion. This is the same order as the paper (unit-root tests, then SIC).
- Hubrich (2003, p. 15–16) [S1]: the AR order of each component is chosen by the Schwarz criterion and re-selected at
  every recursive sample. The chosen lags "hardly change" across samples.
**Recommendation.** Keep p ≤ 12, q ≤ 2, which allows more AR lags than auto.arima and is reasonable for monthly data.
**Watch out:** an ordinary AR term at lag 12 *and* a seasonal AR(12) term measure nearly the same thing. When the
seasonal term is included, cap p at 11, or check in T2.2 that SIC never picks both. Use a common estimation sample for
all candidate orders (AGENTS.md §7). FPP does not state this explicitly, but it is needed for the SIC values to be
comparable.
**Sensitivity.** Report how often the upper bound is chosen. If it binds often, use q ≤ 5 (the auto.arima default).

## D-03 (G3) — Recursive vs rolling window
**Evidence.**
- Hubrich (2003, p. 13, 16) [S1]: recursive (expanding) samples, every model re-estimated and the SIC order
  re-selected at each origin. She argues against choosing models on a separate pseudo-OOS period when the sample is
  short (p. 16).
- Stock & Watson (1998) NBER WP 6607, abstract [S8]: "fully recursive" forecasts to simulate real-time use.
**Recommendation.** Keep recursive estimation with the order re-selected at each origin. This also matches the paper,
which re-selects the lag order whenever the models are re-estimated (p. 7).
**Sensitivity.** A rolling 10-year window in T5.1, especially for 2012+ (the franc shock and the 2022 inflation surge
can change the dynamics).

## D-04 (G4) — Forecast origins
**Evidence.**
- SNB monetary-policy decisions page [S6]: assessments are in March, June, September and December, mid-month (for
  example 2004-03-18 … 2011-12-15). By then BFS has published the CPI for February, May, August and November, so two
  months of the quarter are known. This matches our origins exactly.
- Hubrich (2003, p. 18) [S1]: keeps the same origins for all horizons. More origins at short horizons would make the
  comparison across horizons unfair.
**Recommendation.** Keep 32 origins. Report all h on the same origins and note that h = 5 target quarters run into
2012/2013.
**Sensitivity.** Restrict to a common window of target quarters as a robustness table.

## D-05 (G5) — AR(1) benchmark
**Evidence.**
- Hubrich (2003, p. 15) [S1]: the benchmarks are a random walk with drift (often hard to beat) and an AR chosen by SIC.
- The paper says the AR(1) uses the same information set (p. 8). A monthly model is the only way to use the two known
  months of the current quarter.
**Recommendation.** Keep the AR(1) on monthly Δlog CPI, iterated forward to the quarterly y-o-y rate. Add a random walk
for quarterly y-o-y inflation ("no change") as an extra, clearly labelled non-paper benchmark. It is cheap and standard.
**Sensitivity.** AR(1) on quarterly y-o-y inflation.

## D-06 (G12a) — Substitute for Consensus Economics
**Evidence (own data check).** `scripts/explore/research_kof_consensus.py` on our KOF files [S7]: quarterly surveys
from 2001-03 to 2026-09 (103 surveys). Inflation appears only as `prices_cy` and `prices_ny`, that is, **average annual
CPI inflation for the current and the next year** (plus `prices_5y` from 2015). There is **no quarterly path**.
**Recommendation (refinement).** Keep KOF as the substitute, but compare it with the models on the measure KOF actually
forecasts. Aggregate our quarterly forecasts to **annual-average inflation for the current and next year**, and
evaluate all models on that target. As a secondary option, interpolate the annual figures to quarters, clearly marked
as an approximation. Document that the paper's Consensus Economics row cannot be replicated exactly.
**Open lead.** Check whether Consensus Economics is also annual-only and how the paper mapped it to h = 1–5. The paper
text should say; re-read p. 8.

## D-07 — No add-factors in pseudo-OOS
**Evidence.** Only the paper (p. 12). No outside source looked for.
**Recommendation.** Keep, because it is what the paper does. The VAT-adjusted variant (2011, 2018, 2024) belongs in
T5.1.

## D-09 (G7a) — Minimum sample for an ARIMA
**Evidence.** `auto.arima` [S2] reduces max p and q to about n/3 for short series. With p ≤ 12 plus a seasonal AR term,
n = 36 is the smallest sample where the largest model is still estimable.
**Recommendation.** Keep 36 months. Log which items fall below it at each origin.

## D-10 (G6) — Quarterly-collected items
**Evidence.** Only the paper (p. 6). The relevant mechanics come from statsmodels [S4]: lag lists and fixed
parameters are possible in `SARIMAX`.
**Recommendation.** Keep. Implement with `SARIMAX(order=([3,6,9,12],1,0))`, or with fixed zeros for the other lags.
Validate on simulated data that the model with only lags 3, 6, 9, 12 recovers a quarterly process.

## D-11 (G7b) — "Implausible" forecasts
**Evidence.** None opened. **Open lead:** Stock & Watson (1998, NBER WP 6607) is often cited for an "insanity filter"
that replaces a forecast with a no-change forecast when it lies outside the historical range. The PDF is a scan
without a text layer, so the rule is **unverified**.
**Recommendation.** Keep the percentile rule provisionally. Before T2.2, verify the Stock–Watson rule (OCR the PDF or
get the JBES version) and, if it is confirmed, adopt that exact rule because it is citable.

## D-12 (G8) — Item mapping across basket revisions
**Evidence.** The BFS methodology document could not be read (the PDFs we found are image-only or the wrong file).
**Recommendation.** Keep the default. Before T1.4, read the BFS "Methodische Grundlagen" (news item 2021-0079) by hand
for how new or split items are linked.

## D-13 (G9) — Aggregation across weight years
**Evidence.**
- Hubrich (2003, p. 17) [S1]: the HICP is a chain index with weights changing every year. Forecasts are aggregated
  with the component weights of the year known in real time, at prices of December of the previous year, and component
  forecasts are rebased to the December link month before aggregating. Weights for forecast years beyond the estimation
  sample are those last known. This is our D-13 almost word for word.
- Hubrich (2003, fn. 22) [S1]: the resulting forecast error includes the effect of next year's weight change. This is
  small, but it should be mentioned in the thesis.
**Recommendation.** Keep (already confirmed). Add the fn. 22 caveat to the thesis text.

## D-14 (G10) — Oil-products ECM
**Evidence.** None opened (Bank of Canada WP 2002-38 returned 403). **Open leads:** that paper uses an ECM of Canadian
retail energy prices on world crude. Search snippets mention full pass-through for gasoline and that the results depend
on the ECM lag length.
**Recommendation.** Keep the Engle–Granger ECM. Choose Brent vs WTI empirically in T2.3 (cointegration test and SIC).
Brent is the European benchmark and is the natural default.

## D-15 (G11) — Rent model and mortgage rate
**Evidence.** BFS and BWO pages could not be opened. **Open leads (snippets only):** the mortgage reference rate
(Referenzzinssatz) has existed since 2008, is derived from a volume-weighted average mortgage rate surveyed by the SNB
at quarter ends, and is rounded to 0.25 pp. Swiss tenancy law ties a rent change of about 3 % to each 0.25 pp move.
This supports the paper's link to the average rate in 2008Q2.
**Recommendation.** Keep. For 2012+ (T5.1) test the reference rate itself as the regressor, because legally it is the
rate that matters. Verify the 3 %/0.25 pp rule and the start date on bwo.admin.ch by hand.

## D-16 (G12b) — SNB conditional forecasts
**Evidence.** SNB press release of 18 September 2008 [S5], p. 5: a table with the conditional forecast for each
quarter (y-o-y %, e.g. 2008Q3 = 2.96) and observed inflation. The SNB holds assessments quarterly [S6].
**Recommendation.** Keep. Transcribe the quarterly tables from the press releases of all 32 assessments 2004–2011 into
`data/meta/snb_conditional_forecasts.csv`. **To verify:** whether the 2004–2007 releases already contain quarterly
tables (only 2008 was checked).

## D-17 (G13) — Kalman extension
**Evidence.** statsmodels 0.15 docs [S4]: the state-space framework supports missing observations; `SARIMAX` has
`enforce_stationarity` and `enforce_invertibility` (both on by default) and approximate-diffuse initialisation by
default. A custom `MLEModel` can set time-varying `design` and `transition` matrices and define `start_params` and
`transform_params`.
**Recommendation.** Keep. Use a custom `MLEModel` with the state vector (monthly change d_t, running sum c_t since the
last collection). The transition resets c_t after a collection month (time-varying `transition`), the observation is
y_t = c_t, and non-collected months are NaN. Write a unit test that NaNs are skipped in the likelihood, because the
docs do not state it outright, and validate on simulated data.

---

## Sources actually opened
- [S1] Hubrich, K. (2003). *Forecasting euro area inflation: Does aggregating forecasts by HICP component improve
  forecast accuracy?* ECB Working Paper 247, pp. 13–19. https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp247.pdf (accessed 2026-11-24)
- [S2] Hyndman, R. et al. `forecast` R package 8.23.0, `auto.arima` reference.
  https://search.r-project.org/CRAN/refmans/forecast/html/auto.arima.html (accessed 2026-11-24)
- [S3] Hyndman, R. & Athanasopoulos, G. *Forecasting: Principles and Practice*, 3rd ed., ch. 9 (§9.1, 9.5, 9.6 read in
  full; §9.7 from a summary only). https://otexts.com/fpp3/arima-r.html (accessed 2026-11-24)
- [S4] statsmodels 0.15 documentation: SARIMAX, State space methods, Custom state space models.
  https://www.statsmodels.org/stable/statespace.html (accessed 2026-11-24)
- [S5] Swiss National Bank (2008). Press release, *Monetary policy assessment of 18 September 2008*, pp. 1–5.
  https://www.snb.ch/en/publications/communication/press-releases/2008/pre_20080918_3 (accessed 2026-11-24)
- [S6] Swiss National Bank, *Monetary policy decisions* (list of assessment dates).
  https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/decisions (accessed 2026-11-24)
- [S7] KOF Consensus Forecast files in `data/raw/` (downloaded 2026-11-16), inspected with
  `scripts/explore/research_kof_consensus.py`.
- [S8] Stock, J. & Watson, M. (1998). NBER WP 6607, abstract page. https://www.nber.org/papers/w6607 (accessed 2026-11-24)

## Could not be opened (to read by hand)
| Source | Needed for | Problem |
|---|---|---|
| IMF/ILO *CPI Manual 2020*, chapter on chain linking | D-13, D-12 | old link 404; download from the ILO page |
| BFS *LIK Methodische Grundlagen* (Dec 2020 = 100) | D-12, D-10, D-15 | PDFs image-only / wrong file |
| Stock & Watson, *Phillips curve inflation forecasts* (Harvard PDF) | D-03, D-05 | 403 |
| Stock & Watson (1998) NBER WP 6607 full text | D-11 | scanned PDF, no text |
| Chacra (2002), Bank of Canada WP 2002-38 | D-14 | 403 |
| BWO reference-rate method PDF | D-15 | 404 |
| Statistics Canada CPI Reference Paper ch. 8 | D-13 | 403 |
