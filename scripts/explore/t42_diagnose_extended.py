"""T4.2 exploration: why does the extended ARIMA(182) not beat ARIMA(182) as in paper Table 4?

1. Sensitivity: aggregate the LATENT monthly paths instead of the published-like ones (D-43 / D-53 alternative).
2. RMSFE by ARIMA(14) sub-aggregate, extended vs plain, with each group's actual y-o-y as target.
Reads the per-origin caches of scripts/10_pseudo_oos.py and scripts/11_kalman_oos.py (run those first).

    .venv/Scripts/python scripts/explore/t42_diagnose_extended.py
"""

import numpy as np
import pandas as pd

from arima_snb import aggregate, evaluate
from arima_snb.config import EVAL, FORECASTS, HORIZONS
from arima_snb.kalman_eval import MODEL_KALMAN, OOS_CACHE


def main() -> None:
    inputs = evaluate.load_inputs(with_crude=False)
    origins = evaluate.evaluation_origins()
    actuals = evaluate.quarterly_actuals(inputs, evaluate.official_cpi())

    # 1. latent paths ----------------------------------------------------------------------------------------
    qs = []
    for o in origins:
        fc = pd.read_csv(OOS_CACHE / f"{MODEL_KALMAN}_{o:%Y-%m}_items.csv", parse_dates=["origin", "target"])
        fc = fc.assign(log_p_hat=fc.log_p_latent, model="kalman182_latent")
        _, q = evaluate.aggregate_origin(inputs, fc, o, "kalman182_latent")
        qs.append(q)
    ev_lat = evaluate.eval_table(pd.concat(qs), actuals)
    ev = pd.concat([pd.read_csv(EVAL / "arima182.csv"), pd.read_csv(EVAL / "kalman182.csv"),
                    ev_lat.assign(origin_q=ev_lat.origin_q.astype(str))])
    print("RMSFE total CPI (official) incl. latent-path aggregation:")
    print(evaluate.rmsfe_by_h(ev).to_string(float_format="%.3f"))

    # 2. by ARIMA(14) group -----------------------------------------------------------------------------------
    qk = pd.read_csv(FORECASTS / "kalman182_oos_quarterly.csv")
    qp = pd.read_csv(FORECASTS / "arima182_oos_quarterly.csv")
    qp = qp[qp.model == evaluate.MODEL_PLAIN]
    q = pd.concat([qk, qp])
    q = q[q["aggregate"].str.startswith("agg14:") | q["aggregate"].isin(["total", "excl_oil"])]
    w = inputs["weights"]
    rows = []
    for name, ids in aggregate.aggregate_groups(inputs["items"]).items():
        if name not in set(q["aggregate"]):
            continue
        act = aggregate.quarterly_yoy(aggregate.aggregate_index(inputs["index_wide"], w, ids))
        act.index = act.index.astype(str)
        g = q[q["aggregate"] == name].join(act.rename("act"), on="target_q").dropna(subset=["act"])
        r = g.assign(e2=(g.act - g.pi_hat) ** 2).groupby(["model", "h"]).e2.mean().pipe(np.sqrt).unstack("h")
        share = w[(w.year == 2010) & w.item_id.isin(ids)].weight.sum()
        for h in HORIZONS:
            rows.append({"aggregate": name, "weight_2010": share, "h": h, "kalman": r.loc[MODEL_KALMAN, h],
                         "arima": r.loc[evaluate.MODEL_PLAIN, h]})
    t = pd.DataFrame(rows)
    t["ratio_arima_over_kalman"] = t.arima / t.kalman
    pd.set_option("display.width", 200)
    print("\nRMSFE by sub-aggregate (own actual y-o-y), ratio > 1 = extended better:")
    print(t.pivot(index=["aggregate", "weight_2010"], columns="h", values="ratio_arima_over_kalman")
          .to_string(float_format="%.2f"))


def item_level(group: str = "Health", lead: int = 6) -> None:
    """Item-level RMSE (log points x100) of `lead`-month-ahead forecasts in one ARIMA(14) group: extended vs plain."""
    inputs = evaluate.load_inputs(with_crude=False)
    items = inputs["items"]
    ids = items.loc[items.agg14 == group, "item_id"]
    actual = inputs["panel"].set_index(["date", "item_id"]).log_p
    log = pd.read_csv(evaluate.OOS_CACHE.parent.parent.parent / "outputs" / "logs" / "oos_item_orders.csv")
    rows = []
    for o in evaluate.evaluation_origins():
        t = o + pd.DateOffset(months=lead)
        k = pd.read_csv(OOS_CACHE / f"{MODEL_KALMAN}_{o:%Y-%m}_items.csv", parse_dates=["target"])
        p = pd.read_csv(OOS_CACHE / f"arima182_{o:%Y-%m}_items.csv", parse_dates=["target"])
        for name, f in (("kalman", k), ("arima", p)):
            f = f[(f.target == t) & f.item_id.isin(ids)].set_index("item_id").log_p_hat
            for i, v in f.items():
                rows.append({"origin": o, "item_id": i, "model": name, "err": 100 * (actual.get((t, i), np.nan) - v)})
    e = pd.DataFrame(rows).dropna()
    r = e.groupby(["item_id", "model"]).err.apply(lambda x: np.sqrt((x ** 2).mean())).unstack("model")
    w = inputs["weights"]
    r["weight_2010"] = w[w.year == 2010].set_index("item_id").weight.reindex(r.index)
    r["name"] = items.set_index("item_id").name_en.reindex(r.index)
    r["plain_method"] = log[log.origin == "2008-05-01"].set_index("item_id").method.reindex(r.index)
    r["loss_contrib"] = r.weight_2010 * (r.kalman ** 2 - r.arima ** 2)
    print(f"\n{group}: item RMSE of {lead}-month-ahead log level (x100), sorted by weighted loss difference")
    print(r.sort_values("loss_contrib", ascending=False).to_string(float_format="%.2f"))



def hybrid_adhoc() -> None:
    """Sensitivity: extended model, but items on an ad-hoc fallback in T3.1 at that origin keep the fallback."""
    inputs = evaluate.load_inputs(with_crude=False)
    actuals = evaluate.quarterly_actuals(inputs, evaluate.official_cpi())
    qs, n = [], []
    for o in evaluate.evaluation_origins():
        k = pd.read_csv(OOS_CACHE / f"{MODEL_KALMAN}_{o:%Y-%m}_items.csv", parse_dates=["origin", "target"])
        p = pd.read_csv(OOS_CACHE / f"arima182_{o:%Y-%m}_items.csv", parse_dates=["origin", "target"])
        lg = pd.read_csv(OOS_CACHE / f"arima182_{o:%Y-%m}_log.csv")
        adhoc = lg.loc[lg.method.str.startswith("adhoc"), "item_id"]
        n.append(len(adhoc))
        fc = evaluate.swap_items(k[["origin", "target", "item_id", "log_p_hat"]],
                                 p[p.item_id.isin(adhoc)][["origin", "target", "item_id", "log_p_hat"]])
        _, q = evaluate.aggregate_origin(inputs, fc.assign(model="kalman182_hybrid"), o, "kalman182_hybrid")
        qs.append(q)
    ev = evaluate.eval_table(pd.concat(qs), actuals)
    print("\nhybrid " + f"(ad-hoc items kept, {min(n)}-{max(n)} items per origin), RMSFE vs official CPI:")
    print(evaluate.rmsfe_by_h(ev).to_string(float_format="%.3f"))
    ev_b = pd.read_csv(EVAL / "arima182.csv")
    from arima_snb.kalman_eval import comparison_table
    both = pd.concat([ev.assign(origin_q=ev.origin_q.astype(str)), ev_b])
    print(comparison_table(both, "kalman182_hybrid", ["arima182", "arima182_special"]).to_string(float_format="%.3f"))


if __name__ == "__main__":
    main()
    item_level()
    hybrid_adhoc()
