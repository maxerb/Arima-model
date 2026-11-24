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
