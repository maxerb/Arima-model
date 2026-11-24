# Arima-model

Replication of the Swiss National Bank's disaggregate ARIMA model for short-term inflation forecasts:
Huwiler, M. and D. Kaufmann (2013), *Combining disaggregate forecasts for inflation: The SNB's ARIMA model*,
SNB Economic Studies 7/2013. Part of a Bachelor's thesis (HS26).

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m pytest -q
```

## Data

Raw data is not stored in this repository (decision D-08). Download it into `data/raw/` first:

| Dataset | Source | Used for |
|---|---|---|
| KOF Consensus Forecast (mean, median) | [KOF data service](https://datenservice.kof.ethz.ch) | Consensus benchmark, Table 1 (D-06) |

More sources (CPI items and weights, oil, exchange rate, mortgage rates) are added as the project goes on.
Exact steps for every file are in [`docs/data_sources.md`](docs/data_sources.md).

## Rebuild everything

```powershell
.venv\Scripts\python scripts\run_all.py
```

## Where things are

- `AGENTS.md` — project plan, rules and task board (start here)
- `docs/paper_spec.md` — what the paper specifies, incl. its result tables
- `docs/decisions.md` — choices where the paper is silent
- `docs/data_sources.md` — where every raw file comes from
- `src/arima_snb/` — the code; `scripts/` — entry points; `tests/` — checks
