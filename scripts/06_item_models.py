"""T2.2: per-item ARIMA forecasts for one origin -> outputs/forecasts/arima182_items.csv, outputs/logs/item_orders.csv.

Paper pp. 6-7; decisions D-01, D-02, D-09, D-11, D-35...D-37. The full set of origins (2004-2011) is run by the
evaluation engine (T3.1); this script checks the item models at a single origin and prints sanity output:
methods used, the SIC order distribution, how often the grid bounds bind and which fits failed.

    python scripts/06_item_models.py            # origin 2004-02 (first evaluation origin)
    python scripts/06_item_models.py 2011-11    # any other origin
"""

import sys
import time

import numpy as np
import pandas as pd

from arima_snb.config import FINAL, FORECASTS, LOGS
from arima_snb.diagnostics import specs_for_origin
from arima_snb.item_models import MODEL_NAME, forecast_items


def main() -> None:
    origin = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2004-02-01")

    panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    collection = pd.read_csv(FINAL / "collection.csv", parse_dates=["date"])
    specs = specs_for_origin(pd.read_csv(FINAL / "item_specs.csv"), origin)
    items = pd.read_csv(FINAL / "items.csv").set_index("item_id")

    t0 = time.perf_counter()
    fc, log = forecast_items(panel, specs, collection, origin)
    print(f"origin {origin:%Y-%m}: {log.item_id.nunique()} items in {time.perf_counter() - t0:.1f}s")

    # --- checks ---------------------------------------------------------------------------
    assert len(specs) == 182, len(specs)
    assert fc.log_p_hat.notna().all()
    assert (fc.target > origin).all() and fc.groupby("item_id").size().eq(13).all()
    # 12-month implied change per item: nothing absurd (|change| < 50 log points)
    chg = fc[fc.target == origin + pd.DateOffset(months=12)].set_index("item_id").log_p_hat
    last = panel[panel.date == origin].set_index("item_id").log_p
    assert ((chg - last.reindex(chg.index)).abs() < 0.5).all()

    # --- outputs (idempotent: replace this origin's rows) -----------------------------------
    FORECASTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for df, path in [(fc, FORECASTS / f"{MODEL_NAME}_items.csv"), (log, LOGS / "item_orders.csv")]:
        if path.exists():
            old = pd.read_csv(path, parse_dates=["origin"])
            df = pd.concat([old[old.origin != origin], df], ignore_index=True)
        df.to_csv(path, index=False)

    # --- sanity output ----------------------------------------------------------------------
    pd.set_option("display.width", 200)
    print("\nmethod used (spec method -> final):")
    print(pd.crosstab(log.spec_method, log.method, margins=True))
    a = log[log.p.notna()]
    print(f"\nARIMA fits: {len(a)} items ({a.quarterly.sum()} quarterly-sampled, {a.seasonal.sum()} with seasonal AR)")
    print("chosen p (rows) x q (cols):")
    print(pd.crosstab(a.p.astype(int), a.q.astype(int), margins=True))
    bind_p = (a.p == a.p_max_eff) & (a.p_max_eff > 0)
    bind_q = a.q == 2   # D-02/D-36: q_max = 2 for monthly and quarterly items
    print(f"p at its upper bound: {bind_p.sum()} items; q at its upper bound: {bind_q.sum()} items")
    print(f"guard shrank p_max (monthly < 12 / quarterly < 4): "
          f"{((~a.quarterly) & (a.p_max_eff < np.where(a.seasonal, 11, 12))).sum()} monthly, "
          f"{(a.quarterly & (a.p_max_eff < np.where(a.seasonal, 3, 4))).sum()} quarterly")
    print(f"failed candidate fits: {int(log.n_failed.sum())} of {int(log.n_candidates.sum())}")
    notes = log[log.note.fillna("").str.len() > 0][["item_id", "method", "note"]]
    notes = notes.assign(name=notes.item_id.map(items.name_en))
    print("\nitems with notes:")
    print(notes.to_string(index=False))
    print("\nwrote", FORECASTS / f"{MODEL_NAME}_items.csv", "and", LOGS / "item_orders.csv")


if __name__ == "__main__":   # needed on Windows: the item fits run in worker processes
    main()
