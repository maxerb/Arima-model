# Data sources

One section per dataset in `data/raw/`: provider, how to get it, vintage. `data/raw/` is not tracked in git (D-08),
so these steps (or a `scripts/00_download_*.py` script) are the only way to rebuild it.
Every series also has a row in `codebook.csv`.

## KOF Consensus Forecast (mean and median)
- Files: `kof_kof_consensus_forecast_mean_ts_2026-11-16_14_50_38.xlsx`,
  `kof_kof_consensus_forecast_median_ts_2026-11-16_14_51_14.xlsx` (downloaded 2026-11-16)
- Provider: KOF Swiss Economic Institute, ETH Zurich, KOF data service (https://datenservice.kof.ethz.ch)
- How to get it: search "KOF Consensus Forecast" in the KOF data service, export the mean and median time series as XLSX.
- Use: substitute for Consensus Economics in Table 1 (D-06).
- Imported by `scripts/00_import_from_thesis_repo.py` (T0.0). No loader yet (T1.2).

## Removed
- SNB cubes `zimoma` (money market rates) and `snboffzisa` (official rates), imported in T0.0, were deleted on
  2026-11-24: not used by the model. The SNB loader `read_snb_cube` in `io.py` stays for the mortgage-rate and FX cubes (T1.2).
