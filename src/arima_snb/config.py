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
