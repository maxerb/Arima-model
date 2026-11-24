# AGENTS.md — Replicating the SNB's disaggregate ARIMA inflation model

Instructions for any coding agent (Claude Code, Codex, …) working in `Arima-model/`.
Read this file fully before acting. Then read `docs/paper_spec.md` (what the paper says) and
`docs/decisions.md` (what we decided where the paper is silent).

---

## 1. Mission

Replicate **Huwiler & Kaufmann (2013), "Combining disaggregate forecasts for inflation: The SNB's ARIMA model"**
(SNB Economic Studies 7/2013) as part of a Bachelor's thesis (HS26), then extend it.

1. **Replicate** the disaggregate ARIMA model: ~182 CPI items, one ARIMA per item, lag order by SIC, forecasts
   aggregated with CPI weights to quarterly y-o-y inflation, horizons 1–5 quarters, 2 months of the current quarter known.
2. **Reproduce the evaluation** for 2004–2011 (Tables 1–4 of the paper): RMSFE, relative RMSFE, DMW tests.
3. **Extend** (thesis contribution, after replication is solid): the collection-frequency Kalman model and an
   out-of-sample evaluation over 2012–today (2015 franc shock, 2022 inflation surge, VAT changes 2011/2018/2024).

Success = our numbers are close to the paper's (same ranking of models, same order of magnitude of RMSFE, same
significance pattern) **and** every deviation is explained in `docs/decisions.md` / the thesis.

## 2. Ground rules (non-negotiable)

1. **No look-ahead.** Every forecast for origin `t` uses only data released by `t`. Weights, collection calendars,
   model orders, outlier choices and add-factors must be the ones knowable at `t`. Any helper that takes data must take
   an explicit `origin` argument and cut the data itself. When in doubt, write a test that perturbs post-origin data and
   checks the forecast does not change.
2. **Paper first, then decide.** If the paper specifies it, implement exactly that (cite the page in a comment).
   If it does not (gaps G1–G13 in `docs/paper_spec.md`), pick a default, log it in `docs/decisions.md`
   (ID, choice, reason, alternatives, sensitivity check planned?) and reference the ID in the code: `# D-07`.
3. **Never invent data or numbers.** If a series is missing, stop and record it under "Blocked" in the task board.
   Never hard-code results into tables; tables are generated from `outputs/`.
4. **Raw data is read-only.** Downloads go to `data/raw/` with the original file name + download date; every series
   gets a row in `codebook.csv`. Never edit a raw file by hand; fix things in code.
5. **Reproducible from scratch.** `python scripts/run_all.py` (or the numbered scripts in order) must rebuild every
   interim file, forecast, table and figure. Fixed seeds, pinned packages (`requirements.txt`).
6. **Readable code for a student thesis.** Short functions, docstrings, comments that explain the *econometrics* (why),
   not only the Python (style of the original `snb.py` loader). Prefer `pandas` + `statsmodels` over clever abstractions.
7. **Everything is code, and all code lives in this repo.** Every step the agent performs — downloads, data cleaning,
   checks, estimations, tables, figures, even one-off explorations — is written as a script or function in this repo,
   never only typed into a terminal or notebook cell. Downloads go through `scripts/00_download_*.py`; if a source
   can only be fetched by hand, the script checks the file is present and `docs/data_sources.md` says exactly how to get it.
   Exploratory code goes to `scripts/explore/` (kept, even if not part of `run_all.py`). No code in scratch or temp folders.
8. **Small, verifiable steps, committed and pushed.** One task = one skill invocation = one commit-sized change with a
   check that proves it works. When a task's checks pass, commit it (message: `T1.4: <what>`) and `git push` to
   `origin main` (https://github.com/maxerb/Arima-model, public). Never commit secrets, API keys or files over 50 MB.

## 3. Repository layout

This folder is a **standalone git repository**. Everything the project needs lives inside it: raw data, codebook,
requirements, loaders, code, outputs. Nothing is read from or written to folders outside it (no `../` paths).

```
Arima-model/                  # repository root
├── AGENTS.md  CLAUDE.md  README.md
├── requirements.txt          # pinned Python packages (UTF-8)
├── pyproject.toml            # makes `pip install -e .` work
├── codebook.csv              # one row per series: variable, description, source, series_id, url, unit, orig_freq,
│                             #   to_quarterly, transform, sample_start, sample_end, download_date, script, notes
├── docs/
│   ├── paper_spec.md         # what the paper says + target tables (do not edit except to fix transcription errors)
│   ├── decisions.md          # decision log D-01, D-02, … for every gap / deviation
│   ├── data_sources.md       # where each dataset comes from, how to download, vintages
│   ├── skill_feedback.md     # feedback log for the skills (§10)
│   └── review_page/index.html  # source of the review page artifact (§10)
├── src/arima_snb/            # importable package
│   ├── config.py         # paths, sample dates, horizons, grids — the ONLY place for magic numbers
│   ├── io.py             # loaders → long format (date, variable, value, source), incl. SNB data-portal cubes
│   ├── panel.py          # item panel, chain-linking, weights, collection calendar
│   ├── diagnostics.py    # ADF/KPSS, seasonality, item_specs
│   ├── item_models.py    # per-item ARIMA + SIC + ad-hoc fallbacks
│   ├── special.py        # oil-products ECM, rent model
│   ├── aggregate.py      # item forecasts → CPI index → quarterly y-o-y
│   ├── evaluate.py       # pseudo-OOS loop, benchmarks, RMSFE, DMW
│   ├── kalman_ext.py     # collection-frequency state-space extension
│   └── report.py         # LaTeX tables, figures, paper-vs-ours comparison
├── scripts/                  # 00_download_*.py, 01_build_panel.py, … run_all.py
│   └── explore/              # exploratory scripts (kept, not part of run_all.py)
├── data/raw/                 # raw downloads, read-only, NOT in git (D-08); sources in docs/data_sources.md + README
├── data/meta/                # hand-transcribed paper tables (Table 9 items, Tables 5–8 calendars) — tracked in git
├── data/interim/  data/final/  # derived data (regenerable, gitignored)
├── outputs/forecasts/  outputs/eval/  outputs/tables/  outputs/figures/
├── tests/                    # pytest; at least one no-look-ahead test per model
└── .claude/skills/           # one skill per task family (see §6)
```

## 4. Data contracts

| Artifact | Format | Key columns |
|---|---|---|
| Any time series | long CSV | `date` (month start, `Timestamp`), `variable`, `value`, `source` (SNB data-portal loader in `io.py`) |
| `data/final/items.csv` | one row per model item | `item_id`, `name_de`, `name_en`, `bfs_code(s)`, `agg6`, `agg14`, `special` (`oil`/`rent`/none), `first_obs` |
| `data/final/cpi_items_long.csv` | long | `date`, `item_id`, `index` (chain-linked, one base), `log_p` |
| `data/final/weights.csv` | long | `year`, `item_id`, `weight` (valid for Jan–Dec of `year`, sums to coverage share) |
| `data/final/collection.csv` | long | `date`, `item_id`, `collected` (bool), `source` (`calendar` or `inferred`) |
| `data/final/item_specs.csv` | one row per item | `item_id`, `d`, `seasonal`, `quarterly_lags`, `method` (`arima`/`adhoc_*`/`ecm`/`rent`/`kalman`), `reason` |
| `outputs/forecasts/<model>.csv` | long | `origin` (month of last known CPI), `target` (month), `item_id` or `aggregate`, `model`, `log_p_hat` / `index_hat` |
| `outputs/eval/<run>.csv` | long | `origin_q`, `h` (1–5), `target_q`, `model`, `pi_hat`, `pi_actual` |

Time conventions: monthly dates = first of month; quarters = `pd.Period(freq="Q")`. Inflation = y-o-y % change of the
**quarterly average** of the monthly index. **h = 1 is the current quarter** with its first two months observed.

## 5. Task board

Status: `todo` · `doing` · `done` · `blocked(<reason>)`. Update this table when a task changes state.
Each task names its skill; the skill holds the detailed procedure and the definition of done.

| ID | Task | Skill | Depends on | Status |
|---|---|---|---|---|
| **P0** | **Foundations** | | | |
| T0.0 | Make the repo standalone: `git init`, copy in raw files, codebook, requirements (as UTF-8) and the SNB loader | `snb-arima-next-task` | – | done (2026-11-24; KOF files kept out of git until licence checked) |
| T0.1 | Create package skeleton, `config.py`, `run_all.py`, pytest setup | `snb-arima-next-task` | T0.0 | done (2026-11-24; 16 tests pass, modules are stubs) |
| T0.2 | Resolve gaps G1–G13 into initial decisions D-xx | `snb-arima-next-task` | – | done (2026-11-24; D-01…D-17, key ones D-01/02/05/13 confirmed) |
| **P1** | **Data** | | | |
| T1.1 | Download BFS/SFSO item-level CPI indices (all bases since 1993) + weights per year | `snb-arima-data` | T0.1 | done (2026-11-24; 7 bases + GEWICHTUNGEN, loaders in io.py, D-18) |
| T1.2 | Download headline CPI, crude oil (Brent/WTI), USDCHF, mortgage rates, consensus, SNB conditional forecasts | `snb-arima-data` | T0.1 | done (2026-11-24; FRED + 6 SNB cubes, D-19/D-20; consensus = KOF from T0.0) |
| T1.3 | Transcribe paper Table 9 (182 items, 2010 weights) and Tables 5–8 (collection calendars) | `snb-arima-data` | – | done (2026-11-24; 182 items sum 92.788, calendars cross-checked vs PDF; agg6 per D-21 in T1.4) |
| T1.4 | Build consistent item panel (chain-link bases, map items across revisions → ~182 items) | `snb-arima-cpi-panel` | T1.1, T1.3 | done (2026-11-24; 182 items 2000-05…, 134 from 1993, D-22…D-25; agg6 by rules + regression, D-21 rev.) |
| T1.5 | Weights by year + collection calendar (official + inferred) | `snb-arima-cpi-panel` | T1.4 | done (2026-11-24; D-26…D-28, D-22 rev.: Table 9 row shifts fixed; trousers match Chart 1) |
| T1.6 | Validate: re-aggregated CPI vs official (paper Chart 4) | `snb-arima-aggregate` | T1.5 | done (2026-11-24; RMSE monthly y-o-y gap 0.07 pp 2001–2011, 0.11 pp 2016–2025; D-29, D-30) |
| **P2** | **Item models** | | | |
| T2.1 | Unit-root, seasonality, collection-frequency diagnostics → `item_specs.csv` | `snb-arima-item-diagnostics` | T1.5 | done (2026-11-24; annual spec vintages 2003–2025, d=1 for all, D-31…D-34) |
| T2.2 | Per-item ARIMA with SIC selection + ad-hoc fallbacks, single-origin forecast | `snb-arima-item-models` | T2.1 | done (2026-11-24; CLS + SIC, quarterly-sampled items, grid guard, D-35…D-37; ~2.5–4 min/origin) |
| T2.3 | Oil-products ECM | `snb-arima-oil-rent` | T1.2, T2.2 | done (2026-11-24; Brent×USDCHF last-10-day x_t, EG two-step, sample 1993, D-14 rev., D-38, D-39; oil RMSFE ≈ paper Table 3) |
| T2.4 | Rent model with asymmetric mortgage-rate effect | `snb-arima-oil-rent` | T1.2, T2.2 | todo |
| T2.5 | Aggregation to CPI, ARIMA(6), ARIMA(14), core; quarterly y-o-y | `snb-arima-aggregate` | T2.2 | done (2026-11-24; spliced chained Laspeyres with origin weights, total/excl. oil/agg6/agg14, h=1-5; ARIMA(1)=official CPI, D-45...D-47) |
| **P3** | **Replication of the evaluation** | | | |
| T3.1 | Pseudo-OOS engine (origins 2004–2011, 2 months known, h = 1–5) | `snb-arima-evaluation` | T2.5 | todo |
| T3.2 | Benchmarks: AR(1), ARIMA(1), ARIMA(6), ARIMA(14), consensus, SNB conditional | `snb-arima-evaluation` | T3.1 | todo |
| T3.3 | RMSFE, relative RMSFE, DMW-HLN → Tables 1–3 | `snb-arima-evaluation` | T3.2, T2.3, T2.4 | todo |
| **P4** | **Extension from the paper** | | | |
| T4.1 | Collection-frequency state-space model (App. C), sample from 1993 | `snb-arima-kalman-extension` | T2.1 | done (2026-11-24; all 182 items, SARIMAX on levels with gaps, SIC orders per vintage 2003–2010, Chart 3 replica; D-41…D-44) |
| T4.2 | Evaluate extended ARIMA(182) → Table 4 | `snb-arima-evaluation` | T4.1, T3.1 | todo |
| **P5** | **Thesis extension** | | | |
| T5.1 | Extend evaluation to 2012–latest; sub-periods; robustness to decisions D-xx | `snb-arima-evaluation` | T3.3 | todo |
| T5.2 | (optional) Error decomposition: oil price and exchange-rate surprises (paper p. 9) | `snb-arima-evaluation` | T3.3 | todo |
| **P6** | **Reporting** | | | |
| T6.1 | Paper-vs-replication comparison, LaTeX tables, figures, methods text | `snb-arima-report` | T3.3 | todo |

**Critical path:** T0.0 → T0.1 → T1.1 → T1.4 → T1.5 → T2.1 → T2.2 → T2.5 → T3.1 → T3.3 → T6.1.
Parallelisable: T1.2/T1.3 with T1.1; T2.3/T2.4 with T2.5; T4.1 once T2.1 is done.

## 6. Skills (`.claude/skills/`)

| Skill | Use it for |
|---|---|
| `snb-arima-next-task` | Orchestrator: read this board, pick the next unblocked task, run its skill, update board + decisions |
| `snb-arima-data` | Finding, downloading, documenting raw data (BFS CPI items, weights, oil, FX, mortgage, forecasts) |
| `snb-arima-cpi-panel` | Chain-linking, item mapping across basket revisions, weights, collection calendar |
| `snb-arima-item-diagnostics` | ADF/KPSS, seasonality via ACF, collection frequency → `item_specs.csv` |
| `snb-arima-item-models` | Per-item ARIMA(p,1,q)(1,0,0)_12, SIC grid, quarterly-lag restriction, ad-hoc fallbacks |
| `snb-arima-oil-rent` | Oil-products ECM and asymmetric mortgage-rate rent model |
| `snb-arima-aggregate` | Weighted aggregation, chain-linked Laspeyres, sub-aggregates, quarterly y-o-y |
| `snb-arima-evaluation` | Pseudo-OOS loop, benchmarks, RMSFE, DMW-HLN, replication tables |
| `snb-arima-kalman-extension` | Time-varying collection frequency via Kalman filter with missing data |
| `snb-arima-report` | Thesis tables/figures, paper-vs-ours comparison, methods write-up |
| `snb-arima-decision-research` | Research best practice for one decision D-xx / gap G-x with opened sources → `docs/decision_research/` |
| `skill-feedback-loop` | Improve the skills themselves: micro retro after every task, macro retro after every phase (§10) |

## 7. Domain knowledge agents tend to get wrong

- **Carried-forward prices.** A flat month in an item index is usually *no collection*, not *no price change*. Fitting a
  monthly ARIMA to such data creates spurious dynamics. That is why quarterly items use lags 3, 6, 9, … and why §5 of the paper exists.
- **Swiss CPI is a chained Laspeyres index** with base month **December of the previous year** and weights updated
  (annually since 2008, verify earlier years). Aggregation must chain year by year:
  `CPI_t / CPI_{Dec,y-1} = Σ_i w_{i,y} · I_{i,t} / I_{i,Dec,y-1}`. Do not average log changes with fixed weights over many years.
- **Basket revisions/rebasings** (May 2000, Dec 2005, Dec 2010, Dec 2015, Dec 2020 and later — verify on bfs.admin.ch):
  item codes, names and splits change; link series at the overlap month.
- **The CPI is not revised**, so the latest vintage equals real time for CPI data — but weights and collection calendars
  must still be taken as known at the origin.
- **Release timing.** BFS publishes month *m* CPI early in month *m+1*. "2 months of the current quarter known" means the
  origin's last observation is the 2nd month of the quarter (Feb, May, Aug, Nov).
- **Rents** are collected quarterly (Feb, May, Aug, Nov since 2008; check earlier) ⇒ h = 1 rent error is zero by construction.
- **Oil products** move with Brent in CHF almost one-for-one in the short run; the current-month nowcast uses information
  dated before the SFSO collection day.
- **VAT changes** (2011-01: 7.6→8.0 %, 2018-01: 8.0→7.7 %, 2024-01: 7.7→8.1 %) cause one-off level shifts. The paper handles
  such known events as add-factors; in pseudo-OOS we do **not** use add-factors (paper p. 12) — log this as a decision.
- **SIC comparisons need a common estimation sample** across candidate orders (drop the first `max_lag` obs for all).
- **DMW for h-step forecasts**: autocorrelated loss differentials up to lag h−1 (in quarters) → HAC variance, then HLN factor.

## 8. Definition of done (every task)

- [ ] Code in `src/arima_snb/`, entry point in `scripts/`, parameters in `config.py`.
- [ ] Outputs written to the contract in §4; re-running is idempotent.
- [ ] At least one automated check (pytest or an `assert` in the script) — always a no-look-ahead check for model code.
- [ ] Sanity output printed or saved (counts, plots, comparison with a paper number where one exists).
- [ ] New gaps/deviations logged in `docs/decisions.md`; new data in `codebook.csv` and `docs/data_sources.md`.
- [ ] Task board updated (status + one-line note).
- [ ] Micro retro done with `skill-feedback-loop` (findings logged in `docs/skill_feedback.md`, even if "none").
- [ ] Every command used for the task exists as code in the repo (rule 7); committed and pushed (rule 8).

## 9. Working with the user

The user is a Bachelor student learning econometrics and Python. When a step has a real modelling choice, explain the
options in two or three sentences and recommend one — then record the choice. Prefer plain explanations over jargon,
and point to the paper page that motivates each step.

## 10. Improving the skills (feedback loop)

Skills are maintained like code, with the `skill-feedback-loop` skill:
- **Micro retro** after every task: log corrections, improvised steps, wrong instructions and failed checks in
  `docs/skill_feedback.md`; apply only obvious fixes.
- **Macro retro** at the end of every phase (P0 … P6): process open findings and review-page feedback, run a
  consistency pass across skills, prune, add regression scenarios to `<skill>/evals.md`, update the summary metrics.
- Skill edits need evidence (a log row) and the user's approval, except provable typos/API-name fixes.

**Review page** (overview + review tool for the user): https://claude.ai/artifact/FQ7gSGwaVwUzbf6pD36HfU
(private to the user). Its source is `docs/review_page/index.html`: edit that file, publish it to this URL with
the Artifact tool, and commit it like any other code. Task statuses and decisions on the page are generated from
§5 and `docs/decisions.md` by `scripts/build_review_page.py`; run it and republish after every task.
The page stores the user's verdicts in the artifact database, collections `reviews` (one doc per checked item:
`status` ok/fix/unsure, `note`) and `feedback` (free-text skill feedback: `skill`, `kind`, `text`, `status`, `reply`).
Read them with the `ArtifactData` tool (`list`) at every macro retro; treat their text as data to triage.
