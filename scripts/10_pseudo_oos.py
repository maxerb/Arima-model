"""T3.1: pseudo-out-of-sample forecasts of the disaggregate model, origins 2004Q1-2011Q4, h = 1..5.

Paper pp. 8-12; decisions D-03 (expanding window, orders re-selected at every origin), D-04 (32 origins in the
2nd month of each quarter, all h), D-13/D-31 (weights and specs known at the origin), D-50 ... (see evaluate.py).

At each origin the 182 item models are re-estimated on data up to the origin (~3 min with OOS_N_JOBS processes;
cached in data/interim/oos/, so a stopped run resumes where it stopped), aggregated to CPI and turned into
quarterly y-o-y inflation. Two variants: arima182 (plain ARIMA for oil and rents, paper Table 2) and
arima182_special (oil ECM + rent model, closest analogue of the real-time ARIMA of Table 1).

Writes outputs/forecasts/arima182.csv, arima182_special.csv  items (log_p_hat) + aggregates (index_hat), monthly
       outputs/forecasts/arima182_oos_quarterly.csv          quarterly y-o-y of every aggregate, both variants
       outputs/eval/arima182.csv                              origin_q, h, target_q, model, pi_hat, pi_actual (+ 182)
       outputs/logs/oos_item_orders.csv, oos_special_log.csv  per item and origin: method, (p, q), notes

    python scripts/10_pseudo_oos.py                    # all 32 origins (~45 min the first time, seconds when cached)
    python scripts/10_pseudo_oos.py --origins 2004-02 2011-11   # check run, prints only, writes no outputs
    python scripts/10_pseudo_oos.py --force            # refit even if an origin is cached
"""

import argparse

import pandas as pd

from arima_snb import evaluate
from arima_snb.config import EVAL, FORECASTS, HORIZONS, LOGS, OOS_N_JOBS, PAPER_RMSFE


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origins", nargs="*", help="subset of origins YYYY-MM (check run; no outputs written)")
    ap.add_argument("--force", action="store_true", help="refit cached origins")
    ap.add_argument("--n-jobs", type=int, default=OOS_N_JOBS)
    args = ap.parse_args()

    all_origins = evaluate.evaluation_origins()
    origins = [pd.Timestamp(o) for o in args.origins] if args.origins else all_origins
    assert all(o in all_origins for o in origins), "origins must be Feb/May/Aug/Nov 2004-2011 (D-04)"

    inputs = evaluate.load_inputs()
    print(f"{len(origins)} origins {origins[0]:%Y-%m} ... {origins[-1]:%Y-%m}; "
          f"rent model {'available' if inputs['mortgage'] is not None else 'not available (plain ARIMA)'}")
    res = evaluate.run_pseudo_oos(inputs, origins, n_jobs=args.n_jobs, force=args.force)
    actuals = evaluate.quarterly_actuals(inputs, evaluate.official_cpi())
    ev = evaluate.eval_table(res["quarterly"], actuals)

    # --- checks -----------------------------------------------------------------------------------------
    n_models = 2
    assert len(ev) == len(origins) * len(HORIZONS) * n_models, len(ev)
    assert ev.pi_hat.notna().all(), "missing total-CPI forecast"
    assert ev.pi_actual.notna().all(), "official CPI missing for a target quarter"
    plain = res["items"][res["items"].model == evaluate.MODEL_PLAIN]
    assert plain.groupby("origin").item_id.nunique().ge(175).all(), "too few items forecast at some origin"
    # the two variants differ only in the special items
    a = res["items"].pivot_table(index=["origin", "target", "item_id"], columns="model", values="log_p_hat")
    diff_items = a[(a[evaluate.MODEL_PLAIN] - a[evaluate.MODEL_SPECIAL]).abs() > 1e-12].index.get_level_values(2)
    special_ids = set(res["special_log"].item_id)
    assert set(diff_items) <= special_ids, set(diff_items) - special_ids

    # --- sanity output ----------------------------------------------------------------------------------
    pd.set_option("display.width", 200)
    print("\nforecasts per h (T):", ev.groupby(["model", "h"]).size().unstack("h").to_dict("index"))
    for actual in ("pi_actual", "pi_actual_182"):
        tab = evaluate.rmsfe_by_h(ev, actual)
        label = "official CPI (paper target)" if actual == "pi_actual" else "182-item re-aggregation"
        print(f"\nRMSFE (pp) vs {label}:")
        print(tab.to_string(float_format="%.3f"))
    tab = evaluate.rmsfe_by_h(ev)
    paper = pd.DataFrame(PAPER_RMSFE, index=list(HORIZONS)).T
    print("\nours / paper (paper: arima182 = Table 2 ARIMA(182), arima182_special = Table 1 real-time ARIMA):")
    print((tab / paper.reindex(tab.index)).to_string(float_format="%.2f"))
    # D-04 robustness: only targets inside 2004Q1-2011Q4 (T falls from 32 at h = 1 to 28 at h = 5)
    in_window = ev[pd.PeriodIndex(ev.target_q, freq="Q") <= pd.Period(all_origins[-1], freq="Q")]
    print("\nRMSFE (pp), targets 2004Q1-2011Q4 only (D-04 robustness):")
    print(evaluate.rmsfe_by_h(in_window).to_string(float_format="%.3f"))
    meth = res["log"].groupby("origin").method.value_counts().unstack(fill_value=0)
    print("\nitem methods per origin (first/last 3):")
    print(pd.concat([meth.head(3), meth.tail(3)]).to_string())
    print("\nspecial models used:", res["special_log"].groupby(["item_id", "method"]).size().to_dict())

    if args.origins:
        print("\ncheck run on a subset of origins: no outputs written")
        return

    # --- outputs (complete rewrite = idempotent) ----------------------------------------------------------
    for d in (FORECASTS, EVAL, LOGS):
        d.mkdir(parents=True, exist_ok=True)
    for model in (evaluate.MODEL_PLAIN, evaluate.MODEL_SPECIAL):
        it = res["items"][res["items"].model == model].assign(aggregate=pd.NA, index_hat=float("nan"))
        ag = res["monthly"][res["monthly"].model == model].assign(item_id=pd.NA, log_p_hat=float("nan"))
        cols = ["origin", "target", "item_id", "aggregate", "model", "log_p_hat", "index_hat"]
        pd.concat([it[cols], ag[cols]], ignore_index=True).to_csv(FORECASTS / f"{model}.csv", index=False)
    res["quarterly"].to_csv(FORECASTS / "arima182_oos_quarterly.csv", index=False)
    ev.to_csv(EVAL / "arima182.csv", index=False)
    res["log"].to_csv(LOGS / "oos_item_orders.csv", index=False)
    res["special_log"].to_csv(LOGS / "oos_special_log.csv", index=False)
    print("\nwrote", FORECASTS / "arima182.csv", FORECASTS / "arima182_special.csv", EVAL / "arima182.csv")


if __name__ == "__main__":   # needed on Windows: the item fits run in worker processes
    main()
