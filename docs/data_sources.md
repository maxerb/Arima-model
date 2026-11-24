# Data sources

One section per dataset in `data/raw/`: provider, how to get it, vintage, licence, and whether it is tracked in git (D-08).
Every series also has a row in `codebook.csv`.

## SNB data portal — money market rates (`zimoma`)
- File: `snb-data-zimoma-en-all-20261102_1430.csv` (published 2026-11-02 14:30)
- Provider: Swiss National Bank, data portal https://data.snb.ch, cube `zimoma`
- How to get it: open the cube on data.snb.ch, choose "all" series, English, download CSV.
- Content: 13 monthly series (e.g. SARON), 1972-01 to 2026-10. Loader: `arima_snb.io.read_snb_cube(path, "zimoma")`.
- Licence: SNB data may be used for non-commercial purposes with the source cited. Tracked in git.
- Imported from the thesis repository by `scripts/00_import_from_thesis_repo.py` (T0.0).

## SNB data portal — official interest rates (`snboffzisa`)
- File: `snb-data-snboffzisa-en-all-20261021_0900.csv` (published 2026-10-21 09:00)
- Provider: Swiss National Bank, data portal https://data.snb.ch, cube `snboffzisa`
- How to get it: as above, cube `snboffzisa`.
- Content: 10 monthly series, 2000-01 to 2026-09. Loader: `read_snb_cube(path, "snboffzisa")`.
- Licence: as above. Tracked in git.
- Imported by `scripts/00_import_from_thesis_repo.py` (T0.0).

## KOF Consensus Forecast (mean and median)
- Files: `kof_kof_consensus_forecast_mean_ts_2026-11-16_14_50_38.xlsx`,
  `kof_kof_consensus_forecast_median_ts_2026-11-16_14_51_14.xlsx` (downloaded 2026-11-16)
- Provider: KOF Swiss Economic Institute, ETH Zurich, KOF data service (https://datenservice.kof.ethz.ch)
- How to get it: search "KOF Consensus Forecast" in the KOF data service, export the mean and median time series as XLSX.
- Use: substitute for Consensus Economics in Table 1 (D-06).
- Licence: **not yet checked** for redistribution, so the files are **not tracked in git** (`.gitignore`) until the
  terms are confirmed. Re-download as described above.
- Imported by `scripts/00_import_from_thesis_repo.py` (T0.0). No loader yet (T1.2).
