"""T2.4: rent model - estimates at the latest evaluation origin and a pseudo-OOS check against paper Table 3.

Paper p. 7 (rent model), p. 12 (information set), Table 3 (rent rows); decisions D-15 rev., D-19, D-48.
For each of the 32 origins Feb 2004 ... Nov 2011 (D-04) the rent item (i094) is forecast with the rent model
(quarterly AR + lagged asymmetric mortgage-rate changes) and with the plain quarterly ARIMA of T2.2 (the
Table 3 "Rents (ARIMA)" benchmark). The rent index paths are turned into quarterly y-o-y inflation for
h = 1..5. The DMW tests follow in T3.3; here we print RMSFE and relative RMSFE.

Writes
  outputs/forecasts/rent_items.csv       origin, target, item_id, model, log_p_hat (rent model and ARIMA)
  outputs/eval/t24_rent.csv              origin_q, h, target_q, model, pi_hat, pi_actual
  outputs/tables/t24_rent_table3.csv     RMSFE by h, ours vs paper
  outputs/tables/t24_rent_estimates.csv  rent-model estimates per origin

    python scripts/07_rent_model.py
"""

import numpy as np
import pandas as pd

from arima_snb import aggregate, special
from arima_snb.config import EVAL, FINAL, FORECASTS, HORIZONS, RENT_SAMPLE_START, TABLES
from arima_snb.diagnostics import specs_for_origin
from arima_snb.item_models import forecast_item

RENT_ITEM = "i094"
ORIGINS = pd.date_range("2004-02-01", "2011-11-01", freq="3MS")      # D-04: 2nd month of each quarter
PAPER_RENT = [0.00, 0.24, 0.46, 0.56, 0.61]                           # Table 3, absolute RMSFE
PAPER_ARIMA_REL = [np.nan, 1.18, 1.44, 1.72, 1.90]                    # Table 3, relative RMSFE ARIMA / rent model


def main() -> None:
    panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    all_specs = pd.read_csv(FINAL / "item_specs.csv")
    mortgage = special.load_mortgage_rate()
    logp = panel[panel.item_id == RENT_ITEM].set_index("date")["log_p"].sort_index().asfreq("MS")
    pi_actual = aggregate.quarterly_yoy(np.exp(logp.loc[RENT_SAMPLE_START:]))

    fc_rows, est_rows, eval_rows = [], [], []
    for origin in ORIGINS:
        spec = specs_for_origin(all_specs, origin).set_index("item_id").loc[RENT_ITEM].rename(RENT_ITEM)
        assert spec["method"] == "rent"
        f_rent, lg = forecast_item(logp, spec, origin, mortgage_rate=mortgage)
        f_ar, lg_ar = forecast_item(logp, spec, origin)            # no mortgage rate -> plain quarterly ARIMA
        assert lg["method"] == "rent" and lg_ar["method"] != "rent"
        oq = origin.to_period("Q")
        for model, f in [("rent_model", f_rent), ("arima", f_ar)]:
            fc_rows.append(f.assign(origin=origin, item_id=RENT_ITEM, model=model))
            idx = np.exp(pd.concat([logp.loc[RENT_SAMPLE_START:origin], f.set_index("target").log_p_hat]))
            pi_hat = aggregate.quarterly_yoy(idx)
            for h in HORIZONS:
                tq = oq + (h - 1)
                eval_rows.append({"origin_q": str(oq), "h": h, "target_q": str(tq), "model": model,
                                  "pi_hat": pi_hat.get(tq, np.nan), "pi_actual": pi_actual.get(tq, np.nan)})
        # estimates for the record (same fit as inside forecast_rent)
        x = logp.loc[RENT_SAMPLE_START:origin]
        m = mortgage[mortgage.index < special.crude_info_cutoff(origin)]
        fit = special.fit_rent_model(special.rent_quarterly_changes(x, origin),
                                     special.quarterly_mortgage(m, oq))
        est_rows.append({"origin": origin, "p": fit["p"], "t_eff": fit["t_eff"],
                         "sample_start": str(fit["sample_start"]), **fit["params"],
                         **{f"se_{n}": v for n, v in fit["se"].items()}})

    fc = pd.concat(fc_rows, ignore_index=True)[["origin", "target", "item_id", "model", "log_p_hat"]]
    ev = pd.DataFrame(eval_rows)
    est = pd.DataFrame(est_rows)

    # --- checks ---------------------------------------------------------------------------
    assert len(ORIGINS) == 32
    assert fc.log_p_hat.notna().all() and (fc.target > fc.origin).all()
    assert ev.pi_hat.notna().all(), ev[ev.pi_hat.isna()]
    ev["e"] = ev.pi_hat - ev.pi_actual
    # rents are collected in the 2nd month of the quarter -> the current quarter is fully known (Table 3, h = 1)
    assert ev[(ev.h == 1) & (ev.model == "rent_model")].e.abs().max() < 1e-10

    # --- outputs --------------------------------------------------------------------------
    for d in (FORECASTS, EVAL, TABLES):
        d.mkdir(parents=True, exist_ok=True)
    fc.to_csv(FORECASTS / "rent_items.csv", index=False)
    ev.drop(columns="e").to_csv(EVAL / "t24_rent.csv", index=False)
    est.to_csv(TABLES / "t24_rent_estimates.csv", index=False)

    r = ev.groupby(["model", "h"]).e.apply(lambda e: np.sqrt(np.mean(e ** 2))).unstack("model")
    rel = (r["arima"] / r["rent_model"]).where(r["rent_model"] > 1e-10)
    tab = pd.DataFrame({"h": list(HORIZONS), "rent_rmsfe": r["rent_model"].values, "paper_rent_rmsfe": PAPER_RENT,
                        "arima_rmsfe": r["arima"].values, "arima_rel": rel.values,
                        "paper_arima_rel": PAPER_ARIMA_REL,
                        "n": ev[ev.model == "rent_model"].groupby("h").size().values})
    tab.to_csv(TABLES / "t24_rent_table3.csv", index=False)

    # --- sanity output --------------------------------------------------------------------
    pd.set_option("display.width", 200)
    print("Rents, quarterly y-o-y: RMSFE (pp) of the rent model and ARIMA/rent relative RMSFE vs paper Table 3")
    print(tab.round(2).to_string(index=False))
    last = est.iloc[-1]
    print(f"\nRent-model estimates at origin {ORIGINS[-1]:%Y-%m} (standard errors in brackets), "
          f"p = {last.p}, T = {last.t_eff}, sample from {last.sample_start}:")
    for n in ["c"] + [f"phi_{j}" for j in range(1, int(last.p) + 1)] + ["beta_pos", "beta_neg"]:
        print(f"  {n:9s} = {last[n]: .4f} ({last['se_' + n]:.4f})")
    print("\nAR order p over origins:")
    print(est.p.value_counts().sort_index().to_string())
    print("\nrange of beta_pos and beta_neg over origins:")
    print(est[["beta_pos", "beta_neg"]].agg(["min", "median", "max"]).round(4).to_string())


if __name__ == "__main__":
    main()
