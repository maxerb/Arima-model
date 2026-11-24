"""T2.3: oil-products ECM - estimates at the latest evaluation origin and a pseudo-OOS check against paper Table 3.

Paper p. 7 (ECM), p. 12 (information set), Table 3 (oil rows); decisions D-04, D-14 rev.
For each of the 32 origins Feb 2004 ... Nov 2011 (D-04) both oil items (heating oil i100, fuels i130) are
forecast with the ECM and with the plain ARIMA of T2.2 (the Table 3 "Oil products (ARIMA)" benchmark).
The item paths are aggregated to the oil sub-index (chained Laspeyres, T1.6) and turned into quarterly
y-o-y inflation for h = 1..5. The full DMW tests follow in T3.3; here we print RMSFE and relative RMSFE.

Writes
  outputs/forecasts/oil_ecm_items.csv     origin, target, item_id, model, log_p_hat (ECM and ARIMA)
  outputs/eval/t23_oil.csv                origin_q, h, target_q, model, pi_hat, pi_actual (oil sub-index)
  outputs/tables/t23_oil_table3.csv       RMSFE by h, ours vs paper
  outputs/tables/t23_oil_estimates.csv    ECM estimates per origin and item

    python scripts/07_oil_ecm.py                 # default timing (config OIL_X_RULE)
    python scripts/07_oil_ecm.py first_days      # alternative timing, written with a suffix
"""

import sys

import numpy as np
import pandas as pd

from arima_snb import aggregate, special
from arima_snb.config import EVAL, FINAL, FORECASTS, HORIZONS, OIL_SAMPLE_START, OIL_X_RULE, TABLES
from arima_snb.diagnostics import specs_for_origin
from arima_snb.item_models import forecast_item

OIL_ITEMS = ["i100", "i130"]
ORIGINS = pd.date_range("2004-02-01", "2011-11-01", freq="3MS")      # D-04: 2nd month of each quarter
PAPER_ECM = [1.14, 6.72, 12.49, 15.25, 17.10]                           # Table 3, absolute RMSFE
PAPER_ARIMA_REL = [1.34, 1.30, 1.13, 1.07, 1.04]                        # Table 3, relative RMSFE ARIMA / ECM


def oil_quarterly_yoy(index_wide: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    """Oil sub-index (chained Laspeyres over the oil items) -> quarterly y-o-y inflation in %."""
    return aggregate.quarterly_yoy(aggregate.aggregate_index(index_wide, weights, OIL_ITEMS))


def main() -> None:
    rule = sys.argv[1] if len(sys.argv) > 1 else OIL_X_RULE
    suffix = "" if rule == OIL_X_RULE else f"_{rule}"
    panel = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    weights = pd.read_csv(FINAL / "weights.csv")
    all_specs = pd.read_csv(FINAL / "item_specs.csv")
    crude = special.load_crude_chf_daily()
    logp = panel[panel.item_id.isin(OIL_ITEMS)].pivot(index="date", columns="item_id", values="log_p").asfreq("MS")
    actual_index = np.exp(logp.loc[OIL_SAMPLE_START:])
    pi_actual = oil_quarterly_yoy(actual_index, weights)

    fc_rows, est_rows, eval_rows = [], [], []
    for origin in ORIGINS:
        specs = specs_for_origin(all_specs, origin).set_index("item_id")
        paths = {"oil_ecm": {}, "arima": {}}
        for item in OIL_ITEMS:
            x = logp[item]
            f_ecm, lg = special.forecast_oil_item(x, crude, origin, rule=rule)
            f_ar, _ = forecast_item(x, specs.loc[item].rename(item), origin)   # no crude -> plain ARIMA
            for model, f in [("oil_ecm", f_ecm), ("arima", f_ar)]:
                paths[model][item] = f.set_index("target").log_p_hat
                fc_rows.append(f.assign(origin=origin, item_id=item, model=model))
            # estimates for the record (same fit as inside forecast_oil_item)
            daily = crude[crude.index < special.crude_info_cutoff(origin)]
            p = x.loc[OIL_SAMPLE_START:origin]
            fit = special.fit_oil_ecm(p, special.monthly_crude(daily, p.index[0], origin, rule=rule))
            est_rows.append({"origin": origin, "item_id": item, "a": fit["a"], "b": fit["b"], "se_b": fit["se_b"],
                             "k": fit["k"], "m": fit["m"], "t_eff": fit["t_eff"],
                             **{f"{n}": v for n, v in fit["params"].items()},
                             **{f"se_{n}": v for n, v in fit["se"].items()}})
        oq = origin.to_period("Q")
        for model, pth in paths.items():
            # history up to the origin + forecast path afterwards, then aggregate exactly like the actuals
            fut = pd.DataFrame(pth)
            idx = np.exp(pd.concat([logp.loc[OIL_SAMPLE_START:origin], fut]))
            pi_hat = oil_quarterly_yoy(idx, weights)
            for h in HORIZONS:
                tq = oq + (h - 1)
                eval_rows.append({"origin_q": str(oq), "h": h, "target_q": str(tq), "model": model,
                                  "pi_hat": pi_hat.get(tq, np.nan), "pi_actual": pi_actual.get(tq, np.nan)})

    fc = pd.concat(fc_rows, ignore_index=True)[["origin", "target", "item_id", "model", "log_p_hat"]]
    ev = pd.DataFrame(eval_rows)
    est = pd.DataFrame(est_rows)

    # --- checks ---------------------------------------------------------------------------
    assert len(ORIGINS) == 32
    assert fc.log_p_hat.notna().all() and (fc.target > fc.origin).all()
    assert ev.pi_hat.notna().all(), ev[ev.pi_hat.isna()]
    assert (est.gamma < 0).all(), "error-correction coefficient must be negative (adjustment to the long run)"

    # --- outputs --------------------------------------------------------------------------
    for d in (FORECASTS, EVAL, TABLES):
        d.mkdir(parents=True, exist_ok=True)
    fc.to_csv(FORECASTS / f"oil_ecm_items{suffix}.csv", index=False)
    ev.to_csv(EVAL / f"t23_oil{suffix}.csv", index=False)
    est.to_csv(TABLES / f"t23_oil_estimates{suffix}.csv", index=False)

    ev["e"] = ev.pi_hat - ev.pi_actual
    r = ev.groupby(["model", "h"]).e.apply(lambda e: np.sqrt(np.mean(e ** 2))).unstack("model")
    tab = pd.DataFrame({"h": list(HORIZONS), "ecm_rmsfe": r["oil_ecm"].values, "paper_ecm_rmsfe": PAPER_ECM,
                        "arima_rel": (r["arima"] / r["oil_ecm"]).values, "paper_arima_rel": PAPER_ARIMA_REL,
                        "n": ev[ev.model == "oil_ecm"].groupby("h").size().values})
    tab.to_csv(TABLES / f"t23_oil_table3{suffix}.csv", index=False)

    # --- sanity output --------------------------------------------------------------------
    pd.set_option("display.width", 200)
    print(f"timing rule: {rule}")
    print("\nOil sub-index, quarterly y-o-y: RMSFE (pp) of the ECM and ARIMA/ECM relative RMSFE vs paper Table 3")
    print(tab.round(2).to_string(index=False))
    last = est[est.origin == ORIGINS[-1]]
    print(f"\nECM estimates at origin {ORIGINS[-1]:%Y-%m} (standard errors in brackets):")
    for row in last.itertuples():
        print(f"  {row.item_id}: b = {row.b:.3f} ({row.se_b:.3f}), gamma = {row.gamma:.3f} ({row.se_gamma:.3f}), "
              f"beta_0 = {row.beta_0:.3f} ({row.se_beta_0:.3f}), k = {row.k}, m = {row.m}, T = {row.t_eff}")
    print("\nECM orders over all origins (k, m):")
    print(est.groupby(["item_id", "k", "m"]).size().to_string())
    print("\nrange of b and gamma over origins:")
    print(est.groupby("item_id")[["b", "gamma", "beta_0"]].agg(["min", "max"]).round(3).to_string())


if __name__ == "__main__":
    main()
