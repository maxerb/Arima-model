# Paper specification — single source of truth

> Huwiler, M. and D. Kaufmann (2013). *Combining disaggregate forecasts for inflation: The SNB's ARIMA model.*
> SNB Economic Studies No. 7/2013. JEL C22, C52, C53, E37.
> Landing page: https://www.snb.ch/de/publications/research/economic-studies/2013/03/economic_studies_2013_07
> PDF: https://www.snb.ch/public/asset/de/www-snb-ch/publications/research/economic-studies/2013/03/economic_studies_2013_07/publications0/economic_studies_2013_07.n.pdf

Everything below is taken from the paper (page numbers in brackets). Anything the paper does **not**
pin down is listed under "Gaps" and must be resolved in `docs/decisions.md`, never silently.

---

## 1. Purpose and use [p. 3]
- Short-term forecast of Swiss CPI inflation, typically **15 months ahead**.
- Part of the suite behind the SNB's quarterly conditional inflation forecast; gets large weight in the first quarters.
- Core idea: **do not** model total CPI directly. Model each **CPI expenditure item**, forecast it, and
  **aggregate with CPI expenditure weights**. That also yields core inflation and sub-aggregates (goods, services, ...).

## 2. Data [pp. 4–5, App. A, B]
- Lowest level for which SFSO (BFS) publishes **price indices and expenditure weights**. At the time: **217 items**.
- Sample mostly starts **May 2000** (CPI revision; clothing/footwear collection went half-yearly → quarterly, sales prices start).
  Some series shorter (introduced later, e.g. mobile telephony, Internet), some longer (fresh food, monthly and consistent before 2000).
- **Collection frequency** (App. A, Tables 5–8): SFSO publishes monthly, but many items are collected less often; SFSO
  **carries forward** the last collected index value. Until end-2007 only food, heating oil and fuels monthly; most items
  quarterly or less. Frequency raised in **2008 and 2011** (e.g. trousers: quarterly → 6×/year from 2008 → monthly from 2011).
- Calendars: Table 5 (2000–2005), Table 6 (2006–2007), Table 7 (2008–2010), Table 8 (since 2011). "Aperiodic" items exist.

## 3. Item model [pp. 5–7]
- Prices in logs `p_t`; all items assumed **I(1)**, modelled in first log-differences `Δp_t` (d = 1).
- ARIMA(p,1,q), eq. (1) (constant omitted "to keep the exposition simple"):
  `Δp_t = φ1 Δp_{t-1} + … + φp Δp_{t-p} + ε_t + θ1 ε_{t-1} + … + θq ε_{t-q}`
- Seasonal variant, eq. (2): multiplicative **seasonal AR term ρ at lag 12**:
  `(1-ρL^12)Δp_t = φ(L)(1-ρL^12)Δp_{t-1} … + ε_t + MA part`  (ρ = 1 ⇒ seasonal differencing; ρ = 0 ⇒ non-seasonal).
- **Two-step specification per item**
  1. *Infrequent (every few years)*: integration order via **ADF** (Dickey–Fuller 1979) and **KPSS** (Kwiatkowski et al. 1992) at 5 %
     (very few of >200 items reject I(1)); **seasonality** via ACF spikes at multiples of 12 → allow seasonal AR term;
     **collection frequency** from SFSO → for **quarterly-collected items only lags that are multiples of 3** (≈ quarterly model).
  2. *Every re-estimation*: lag order chosen automatically by **Schwarz criterion**, eq. (3):
     `SIC = log(SSE/T) + k·log(T)/T` — smallest SIC wins.
- **Other methods for some items** [p. 7] — replace ARIMA with ad-hoc rules: (a) last value carried forward,
  (b) average m-o-m growth, (c) average y-o-y growth. Used when (i) forecast visually implausible/extreme,
  (ii) item too new / too few observations, (iii) item collected **less than once a quarter** (no model estimated).
  Known special factors (announced electricity prices, Pigouvian taxes on tobacco/heating oil) enter as **add-factors**.
- **Oil products** (heating oil, petrol, diesel; weight 3.650 in 2010): **error-correction model**, cointegrated with
  **crude oil spot price in CHF**. Current month nowcast uses daily crude price and USDCHF at the start of the month (SFSO
  collection timing). Beyond: crude price in CHF held **constant at the average of the last 10 daily observations**.
- **Rents** (weight ≈ 20 %, 19.499 in 2010; collected quarterly): **quarterly ARIMA in first differences** + **4th lag of the
  change in the mortgage rate** as exogenous regressor, entered **separately for positive and negative changes**; AR lag order by SIC.
  Mortgage rate assumed **constant** over the horizon. Mortgage series: cantonal-bank average linked in **2008Q2** to the
  Federal Housing Office (BWO) average mortgage rate. (Until 2010 SNB used a richer model with housing-market imbalances.)

## 4. Evaluation [pp. 8–12]
- Target: **quarterly year-on-year CPI inflation** (quarter average). Horizons **1–5 quarters**; horizon 1 = **current quarter**.
- Information set: the forecast as available at the SNB's quarterly forecasting meeting ⇒ **2 months of CPI of the current quarter known**.
  For oil/rent exogenous vars in pseudo-OOS: available **up to the first day of the last month of the current quarter** [p. 12].
- Evaluation period **2004–2011**. Swiss CPI is **not revised** ⇒ pseudo-OOS ≈ real-time.
- Loss: `RMSFE_f = sqrt( (1/T) Σ (π_{t+f} − π_{t+f|t})² )`. Report absolute RMSFE of the reference model, others as **relative RMSFE**
  (benchmark / reference; > 1 ⇒ reference better).
- Test: **Diebold–Mariano–West** with **Harvey–Leybourne–Newbold (1997)** small-sample correction, critical values from
  **Student t with T−1 df**; significance at **10 %**, p-values in brackets.
- Forecast errors are measured against **official** CPI inflation, also for the 182-item reconstruction.
- Disaggregation levels (App. B, Table 9, 2010 weights): **ARIMA(1)** total CPI; **ARIMA(6)** origin × product type;
  **ARIMA(14)** ≈ COICOP divisions; **ARIMA(182)** ≈ full disaggregation (items merged/dropped for a consistent panel;
  covers **92.788 %** of 2010 weights, "93 %" in text). In Table 2 oil and rents use **plain ARIMA**, not ECM/rent model.

### ARIMA(6) sub-aggregates, weights 2010
| Sub-aggregate | Weight |
|---|---|
| Domestic durable goods | 16.875 |
| Domestic private services | 27.818 |
| Rents | 19.499 |
| Public services | 8.711 |
| Imported goods and services excl. oil products | 23.447 |
| Oil products | 3.650 |

### ARIMA(14) sub-aggregates, weights 2010
Food & non-alc. bev. 11.063 · Alcoholic bev. & tobacco 1.764 · Clothing & footwear 4.454 · Housing & energy excl. oil & rents 4.972 ·
Oil products 3.650 · Rents 19.499 · Furnishings & household 4.635 · Health 13.862 · Transport excl. oil 8.643 · Communication 2.785 ·
Recreation & culture 10.356 · Education 0.669 · Restaurants & hotels 8.426 · Misc. goods & services 5.222 (sum 100.000).

The full 182-item list with 2010 weights is Table 9, PDF pp. 21–25 — transcribe it into `data/meta/items_paper_table9.csv`
(task T1.3) rather than copying it here.

## 5. Extension: time-varying collection frequency [pp. 12–15, App. C]
- State space (Hamilton 1994 ch. 13). Latent: monthly `Δp_t − μ`. Measurement: observed change since last collection =
  **sum of latent monthly changes since last collection**, eqs. (4), (5), (7), (8):
  `A_t = h_t·1{Δ^{h_t}p_t ≠ 0}`, `H_t' = [1_(1×h_t)·1{Δ^{h_t}p_t ≠ 0}, 0, …, 0]`, `R_t = r·1{Δ^{h_t}p_t = 0}` (r arbitrary > 0).
  `h_t` = months since last collection. Collection = observed change ≠ 0; **changes < 1e-3 are treated as no collection** (fn. 9).
- Transition: **AR(p)**, optionally with **seasonal AR at lag 12** (only AR used in practice, fn. 8; App. C gives ARMA).
  Parameters `{μ, φ, ρ, σ²}` by **ML via Kalman filter**; constrained **causal/invertible** (roots of Φ(z)Γ(z) outside unit circle).
  (Original optimiser: Sims' csminwel.)
- Estimated on a **longer sample from 1993**. Real-time: future collection months = **those observed in the previous year**.
- Kalman smoother interpolates the missing monthly changes (Chart 3, trousers).

## 6. Target numbers to replicate

**Table 1 — Real-time performance (2004–2011).** Row 1 absolute RMSFE, others relative RMSFE (DMW p-value).
| | h=1 | h=2 | h=3 | h=4 | h=5 |
|---|---|---|---|---|---|
| Real-time ARIMA | 0.04 | 0.36 | 0.66 | 0.83 | 0.96 |
| SNB conditional forecast | 2.40 (0.003) | 1.25 (0.170) | 1.13 (0.280) | 1.11 (0.530) | 1.07 (0.680) |
| Consensus Economics | 3.43 (0.001) | 1.32 (0.028) | 1.04 (0.465) | 1.04 (0.582) | 1.01 (0.918) |
| AR(1) | 3.37 (0.004) | 1.19 (0.087) | 1.08 (0.287) | 1.08 (0.223) | 1.06 (0.292) |

**Table 2 — Optimal disaggregation (pseudo-OOS).**
| | h=1 | h=2 | h=3 | h=4 | h=5 |
|---|---|---|---|---|---|
| ARIMA(182) | 0.08 | 0.41 | 0.72 | 0.92 | 1.04 |
| ARIMA(14) | 1.01 (0.970) | 1.19 (0.182) | 1.04 (0.254) | 1.04 (0.242) | 1.01 (0.898) |
| ARIMA(6) | 1.03 (0.844) | 1.17 (0.002) | 1.05 (0.236) | 1.05 (0.215) | 1.03 (0.625) |
| ARIMA(1) | 1.27 (0.220) | 1.60 (0.002) | 1.40 (0.007) | 1.43 (0.112) | 1.29 (0.317) |

**Table 3 — Oil products and rents.**
| | h=1 | h=2 | h=3 | h=4 | h=5 |
|---|---|---|---|---|---|
| Oil products (ECM) | 1.14 | 6.72 | 12.49 | 15.25 | 17.10 |
| Oil products (ARIMA) | 1.34 (0.030) | 1.30 (0.034) | 1.13 (0.256) | 1.07 (0.497) | 1.04 (0.710) |
| Oil products (real-time) | 0.70 (0.133) | 1.10 (0.268) | 1.08 (0.151) | 1.06 (0.189) | 1.04 (0.040) |
| Rents (ARIMA + mortgage rate) | 0.00 | 0.24 | 0.46 | 0.56 | 0.61 |
| Rents (ARIMA) | – | 1.18 (0.148) | 1.44 (0.005) | 1.72 (0.000) | 1.90 (0.000) |
| Rents (real-time) | – | 1.07 (0.670) | 1.01 (0.975) | 1.01 (0.967) | 1.10 (0.793) |

**Table 4 — Extended ARIMA.**
| | h=1 | h=2 | h=3 | h=4 | h=5 |
|---|---|---|---|---|---|
| Extended ARIMA(182) | 0.06 | 0.32 | 0.64 | 0.86 | 1.00 |
| ARIMA(182) | 1.18 (0.278) | 1.28 (0.067) | 1.11 (0.157) | 1.07 (0.184) | 1.04 (0.438) |
| Real-time ARIMA | 0.57 (0.003) | 1.12 (0.321) | 1.02 (0.466) | 0.97 (0.258) | 0.95 (0.203) |

**Other facts:** regressing real-time errors on crude-oil price changes: R² ≈ 0 at h = 1, ≈ 60 % for h > 1 [p. 9].
Large miss in 2011Q4 (CHF appreciation, import price cuts). Chart 4: 182-item CPI tracks official y-o-y CPI closely.

## 7. Gaps (the paper does not specify — decide in `docs/decisions.md`)
G1 constant/drift in item models · G2 max p, max q of the SIC search grid · G3 recursive vs. rolling window (text implies
recursive, re-estimated each origin) · G4 exact evaluation origins and T per horizon · G5 specification of the AR(1) benchmark
(which series, frequency) · G6 how "multiples of 3" lags are implemented for quarterly items · G7 thresholds for "implausible"
forecasts and "too few observations" · G8 item mapping across basket revisions (2005, 2010, …) to obtain 182 items ·
G9 aggregation formula across weight-update years (chain-linking) · G10 ECM specification (lags, which crude benchmark, CHF
conversion, monthly vs. daily) · G11 rent model sample/frequency details and mortgage-rate source after 2008Q2 ·
G12 substitute for Consensus Economics (paid) and source of real-time SNB conditional forecasts · G13 likelihood setup for the
extension with statsmodels (see `snb-arima-kalman-extension` skill).
