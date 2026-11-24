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

## BFS/SFSO consumer price index (LIK): item indices and weights (T1.1)
- Script: `scripts/00_download_bfs_cpi.py` (downloads all files below; skips files already present). Loaders:
  `read_bfs_cpi_items` and `read_bfs_weights` in `src/arima_snb/io.py`. Check: `scripts/explore/check_bfs_cpi_loaders.py`.
- Provider: Bundesamt für Statistik (BFS), page "Detailresultate":
  https://www.bfs.admin.ch/bfs/de/home/statistiken/preise/landesindex-konsumentenpreise/detailresultate.html
  and "Warenkorb und Gewichtung": https://www.bfs.admin.ch/bfs/de/home/statistiken/preise/erhebungen/lik/warenkorb.html
- Files (downloaded 2026-11-24, saved as `<code>_<asset>_<date>.<ext>`): one "Detailresultate" file per basket,
  LIK93B93 (May 1993–May 2000), LIK00B00 (May 2000–Dec 2005), LIK05B05 (Dec 2005–Dec 2010), LIK10B10 (May 2000–Dec 2015),
  LIK15B15, LIK20B20, LIK25B25 (back-cast to Dec 1982, latest month Oct 2026), and `GEWICHTUNGEN` (weights per basket and year).
- Manual route: on the pages above, click the file with the code in square brackets (e.g. `[LIK10B10]`) → "Download".
  BFS gives updated files a new asset id; if a download fails, look up the new id on the page and update `ASSETS` in the script.
- Vintage: CPI is not revised, so the latest file is real-time data for indices; weights per year are as published.
- Licence: BFS open data, free use with source attribution ("Quelle: BFS").
