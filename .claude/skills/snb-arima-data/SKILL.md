---
name: snb-arima-data
description: Find, download and document the raw data for the SNB disaggregate-ARIMA inflation replication - Swiss CPI (LIK) item-level indices and expenditure weights from BFS/SFSO, headline CPI, crude oil prices, USDCHF, mortgage rates, consensus and SNB conditional inflation forecasts, and transcribing the paper's appendix tables. Use for tasks T1.1–T1.3 or whenever a new series is needed, a download fails, or the codebook must be updated.
---

# SNB ARIMA — data acquisition (T1.1–T1.3)

## Outputs
- Raw files in `data/raw/` (read-only afterwards; original name, add download date if missing). `data/raw/` is not in
  git (D-08), so every file must be re-downloadable: a `scripts/00_download_*.py` script, or exact manual steps.
- One row per series in `codebook.csv` (columns: `variable, description, source, series_id, url, unit, orig_freq,
  to_quarterly, transform, sample_start, sample_end, download_date, script, notes`).
- `docs/data_sources.md`: per dataset — provider, exact page/URL, how to download (clicks or API call), vintage, licence note.
- Loader functions in `src/arima_snb/io.py` returning the long format `date, variable, value, source`
  (`read_snb_cube` in `io.py` for SNB data-portal cubes; copied from the old thesis-root `snb.py` in T0.0).

## Datasets and where to look (verify every URL; record what you actually used)
| Need | Provider | Notes |
|---|---|---|
| CPI item indices (all positions, monthly) | BFS/SFSO — "Landesindex der Konsumentenpreise (LIK)", detailed results / historical index values per base | One file per base (May 2000=100, Dec 2005=100, Dec 2010=100, Dec 2015=100, Dec 2020=100, newer). Need the **lowest published level** (Positionen/expenditure items). Also look on opendata.swiss. |
| CPI weights | BFS — file `[GEWICHTUNGEN]` on the "Warenkorb und Gewichtung" page | One sheet per basket, one column per weight year (annual since 2000/01). The detail files of 2015+ carry only their latest weight year. |
| Headline CPI and core | BFS or SNB data portal | Needed as the evaluation target (official inflation). |
| Collection calendars | Paper App. A (Tables 5–8) + BFS methodology docs ("Methodenübersicht") | For years after 2011, infer from data (see `snb-arima-cpi-panel`). |
| Crude oil spot (daily) | e.g. FRED `DCOILBRENTEU` (Brent) / `DCOILWTICO` (WTI) | Paper says "crude oil spot price" — log choice (D-xx). |
| USDCHF (daily + monthly) | SNB data portal (FX cube) or FRED `DEXSZUS` | Needed to convert oil to CHF. |
| Mortgage rates | SNB data portal (bank interest rates) for the cantonal-bank series up to 2008Q2; BWO (Bundesamt für Wohnungswesen) average mortgage rate / Referenzzinssatz after | Paper fn. 3: linked in 2008Q2. |
| Consensus forecasts | KOF Consensus (`data/raw/kof_*`, copied in T0.0) as substitute for Consensus Economics | Decision D-06. |
| SNB conditional inflation forecast | SNB monetary policy assessment press releases (quarterly tables), 2004–2011 | Hand-collect into a CSV with `publication_date, target_quarter, value`; keep PDFs/links in `data_sources.md`. |

## Procedure
1. Before downloading, check `data/raw/` and `codebook.csv` — don't duplicate.
2. Prefer machine-readable sources (CSV/XLSX/API). For web pages, use the browser or a fetch tool; if a file needs a
   manual click/download by the user, give them exact steps and the target folder instead of scraping around it.
3. Save raw files untouched. Write a loader in `io.py` that turns each file into long format with explicit parsing
   (`sep`, `skiprows`, date `format=`), documented by a comment saying when the layout was checked — follow `read_snb_cube` in `io.py`.
4. Add codebook rows (`transform` = what the pipeline later does, e.g. `log, chain-link`).
5. **T1.3 transcription:** create `data/meta/items_paper_table9.csv` (`item_en, weight_2010, agg6, agg14`) from PDF
   pp. 21–25 and `data/meta/collection_calendar_paper.csv` (`period, group, item, months` or `aperiodic`/`seasonal`) from
   Tables 5–8. Verify: Table 9 182-item weights sum to **92.788**, ARIMA(6) and ARIMA(14) weights sum to **100.000**.

## Checks
- Every loader returns no duplicate `(date, variable)` pairs, a monotone monthly date index, and plausible value ranges.
- Item file coverage: print number of items per base and the first/last date per base.
- Spot check: headline CPI y-o-y from our file matches a known value (e.g. 2008 peak ≈ 3 % in 2008Q3, paper Chart 2).

## Pitfalls
- BFS XLSX files have multi-row headers, German/French labels, and footnote rows — parse by position *and* assert labels.
- Index levels in different bases are not comparable — never concatenate bases without chain-linking (next skill).
- Bases 1993–2010 are `.xls` (needs `xlrd`). Position numbers repeat below the main hierarchy (BFS special
  groupings) — keep the first occurrence. Index levels > 1000 are real for PCs/TVs back-cast to the 1980s.
- Do not put personal data or credentials into requests; public sources need no login.
