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

# ---------------------------------------------------------------------------
# Collection frequency (paper fn. 9)
# ---------------------------------------------------------------------------
NO_COLLECTION_TOL = 1e-3           # |log change| below this counts as "not collected"

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED = 20131
