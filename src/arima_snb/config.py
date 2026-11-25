"""Project settings: paths, sample dates, horizons and model grids.

This is the ONLY place for numbers and paths that steer the analysis (AGENTS.md §3).
Every other module imports from here, so a change in one place changes the whole pipeline.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (everything lives inside this repository, AGENTS.md §3)
# ---------------------------------------------------------------------------
# config.py sits in src/arima_snb/, so the repository root is three levels up.
ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"
RAW = DATA / "raw"            # downloads, read-only
META = DATA / "meta"          # hand-transcribed tables from the paper
INTERIM = DATA / "interim"    # intermediate results, regenerable
FINAL = DATA / "final"        # cleaned inputs for the models, regenerable

OUTPUTS = ROOT / "outputs"
FORECASTS = OUTPUTS / "forecasts"
EVAL = OUTPUTS / "eval"
TABLES = OUTPUTS / "tables"
FIGURES = OUTPUTS / "figures"
LOGS = OUTPUTS / "logs"

CODEBOOK = ROOT / "codebook.csv"

# ---------------------------------------------------------------------------
# Samples and evaluation (docs/paper_spec.md §4, decisions D-03, D-04)
# ---------------------------------------------------------------------------
ITEM_SAMPLE_START = "2000-05"      # CPI revision May 2000; most item series start here (paper p. 5)
KALMAN_SAMPLE_START = "1993-01"    # extension estimated from 1993 (paper p. 14)
EVAL_START = "2004Q1"              # evaluation 2004-2011 (paper p. 8)
EVAL_END = "2011Q4"
HORIZONS = range(1, 6)             # h = 1..5 quarters, h = 1 is the current quarter
MONTHS_KNOWN_IN_QUARTER = 2        # two months of CPI of the current quarter are known (paper p. 8)
SIGNIFICANCE = 0.10                # DMW tests: bold at 10 % (paper p. 10)

# ---------------------------------------------------------------------------
# Item models (paper pp. 6-7, decisions D-01, D-02)
# ---------------------------------------------------------------------------
INCLUDE_CONSTANT = True            # D-01
P_MAX_MONTHLY = 12                 # D-02: AR lags 0..12 for monthly items
Q_MAX_MONTHLY = 2                  # D-02: MA lags 0..2
P_MAX_QUARTERLY = 4                # D-02: quarterly items, lags in quarters (3, 6, 9, 12 months)
SEASONAL_PERIOD = 12               # seasonal AR term at lag 12 (eq. 2)
MIN_OBS_MONTHLY = 36               # fewer observations -> ad-hoc rule (paper p. 7; threshold is ours)
MIN_OBS_QUARTERLY = 12
Q_MAX_QUARTERLY = 2                # D-36: MA lags in quarters (3 and 6 months) for quarterly items
SEASONAL_PERIOD_QUARTERLY = 4      # D-36: seasonal AR at 4 quarters = 12 months
MIN_SIC_OBS_MONTHLY = 24           # D-37: the common SIC sample keeps at least this many obs (grid shrinks otherwise)
MIN_SIC_OBS_QUARTERLY = 12         # D-37: same for quarterly-sampled items
FORECAST_STEPS = 13                # months after an origin in the 2nd month of a quarter to the end of quarter t+4 (h = 5)
PLAUSIBLE_PCTL = (1, 99)           # D-11: 12-month forecast change outside these percentiles of history -> avg y-o-y
ITEM_N_JOBS = 4                    # parallel worker processes for the item models (T2.2)

# ---------------------------------------------------------------------------
# Oil-products ECM (T2.3, paper p. 7, decision D-14 rev.)
# ---------------------------------------------------------------------------
OIL_CRUDE_SERIES = "DCOILBRENTEU"  # D-14: Brent spot (FRED); WTI = robustness
OIL_FX_SERIES = "DEXSZUS"          # D-14: CHF per USD, daily (FRED)
OIL_WINDOW_DAYS = 10               # paper p. 7: last 10 daily obs; x_t = mean of last 10 days before the 1st of t
OIL_X_RULE = "before"              # D-14 rev.: x_t = mean of last 10 days before the 1st of t ("first_days" = alt.)
OIL_FIRST_DAYS = 5                 # "first_days" rule: first 5 daily prices of month t
OIL_SAMPLE_START = "1993-05"       # D-14 rev.: oil items and crude from the 1993 basket on (longer than D-09)
OIL_K_MAX = 3                      # D-14: Δx lags 0..3, chosen by SIC
OIL_M_MAX = 3                      # D-14: Δp lags 0..3, chosen by SIC

# ---------------------------------------------------------------------------
# Rent model (T2.4, paper p. 7, decisions D-15 rev., D-19, D-48)
# ---------------------------------------------------------------------------
RENT_MORTGAGE_SERIES = "zikrepro_M_MV"  # D-19: SNB mean variable mortgage rate, monthly, percent
RENT_SAMPLE_START = "1993-05"      # D-48: linked rent series from the 1993 basket (user choice 2026-11-24)
RENT_COLLECTION_MONTHS = (2, 5, 8, 11)  # rents collected Feb/May/Aug/Nov; holds in the data since 1993 (D-48)
RENT_MORTGAGE_LAG = 4              # paper p. 7: 4th lag of the quarterly change in the mortgage rate
RENT_P_MAX = 4                     # D-48: AR order p = 0..4 (quarters) by SIC on a common sample

# ---------------------------------------------------------------------------
# Collection frequency (paper fn. 9)
# ---------------------------------------------------------------------------
NO_COLLECTION_TOL = 1e-3           # |log change| below this counts as "not collected"
CALENDAR_LAST_YEAR = 2012          # D-28: paper's "2011-" calendar (Table 8) applied up to the paper's writing

# ---------------------------------------------------------------------------
# Collection-frequency extension (T4.1, paper section 5 / App. C, decisions D-41 ... D-44)
# ---------------------------------------------------------------------------
KALMAN_P_MAX = 12                  # D-44: AR order p = 0..12 of the latent monthly changes, chosen by SIC per vintage
KALMAN_VINTAGES = range(2003, 2011)  # D-44: order vintages needed for origins 2004-2011 (Table 4); extend for T5.1
KALMAN_N_JOBS = 6                  # parallel worker processes for the order search

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 20131

# ---------------------------------------------------------------------------
# Aggregation (T1.6, D-29): chaining periods before annual Dec-based chaining starts in 2002.
# (weight_year in weights.csv, link month, first month, last month)
# ---------------------------------------------------------------------------
EARLY_WEIGHT_PERIODS = [
    (1993, "1993-05-01", "1993-06-01", "2000-05-01"),   # 1993 basket, base May 1993; overlap month May 2000
    (2000, "2000-05-01", "2000-06-01", "2001-12-01"),   # 2000 basket, "2000/01" weights, base May 2000
]

# ---------------------------------------------------------------------------
# Item diagnostics (T2.1, paper p. 6, decisions D-31 ... D-34)
# ---------------------------------------------------------------------------
SPEC_VINTAGES = range(2003, 2026)  # D-31: spec vintage Y uses data to Dec Y, serves origins in year Y+1
DIAG_ALPHA = 0.05                  # ADF/KPSS significance (paper p. 6)
ACF_MAX_LAG = 36                   # months
SEASONAL_LAGS = (12, 24)           # D-33: seasonal if ACF at lag 12 or 24 positive and significant
FREQ_MONTHLY_MIN = 10              # D-34: collections per year >= 10 -> monthly
FREQ_6X_MIN = 5                    # 5-9 -> "6x" (bimonthly-like), modelled monthly
FREQ_QUARTERLY_MIN = 3             # 3-4 -> quarterly (lags 3, 6, 9, ...); 1-2 -> less than quarterly

# ---------------------------------------------------------------------------
# Pseudo-out-of-sample engine (T3.1, paper pp. 8-12, decisions D-03, D-04, D-50 ...)
# ---------------------------------------------------------------------------
OOS_N_JOBS = 7                     # worker processes for the item fits at each origin (~1-2 min/origin at 7 on 8 cores)
# Paper RMSFE rows used as sanity targets (pp. 9 and 11; transcribed in docs/paper_spec.md §6), h = 1..5
PAPER_RMSFE = {
    "arima182": (0.08, 0.41, 0.72, 0.92, 1.04),          # Table 2, ARIMA(182) - plain ARIMA for oil and rents
    "arima182_special": (0.04, 0.36, 0.66, 0.83, 0.96),  # Table 1, real-time ARIMA (closest analogue, D-50)
}

# ---------------------------------------------------------------------------
# Extended ARIMA evaluation (T4.2, paper Table 4 p. 15; decisions D-41 ... D-44, D-52, D-53)
# ---------------------------------------------------------------------------
# (value, DMW p-value) per h = 1..5; first row absolute RMSFE (no test), others relative RMSFE vs extended ARIMA(182)
PAPER_TABLE4 = {
    "kalman182": ((0.06, None), (0.32, None), (0.64, None), (0.86, None), (1.00, None)),
    "arima182": ((1.18, 0.278), (1.28, 0.067), (1.11, 0.157), (1.07, 0.184), (1.04, 0.438)),
    "arima182_special": ((0.57, 0.003), (1.12, 0.321), (1.02, 0.466), (0.97, 0.258), (0.95, 0.203)),
}
