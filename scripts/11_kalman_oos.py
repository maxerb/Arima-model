"""T4.2: pseudo-out-of-sample evaluation of the extended ARIMA(182) - replica of paper Table 4 (p. 15).

Decisions D-41 ... D-44 (extended model, T4.1), D-03/D-04 (expanding window, 32 origins), D-50/D-51 (benchmarks,
cache), D-52/D-53 (DMW-HLN, failed fits). Needs the outputs of scripts/09_kalman_extension.py (orders) and
scripts/10_pseudo_oos.py (outputs/eval/arima182.csv with the arima182 and arima182_special forecasts).

At each of the 32 origins all 182 extended item models are re-estimated on data from 1993 up to the origin
(cached per origin in data/interim/oos/kalman182_*.csv, so a stopped run resumes), aggregated to CPI and turned
into quarterly y-o-y inflation for h = 1..5.

Writes outputs/forecasts/kalman182.csv            items (log_p_hat, log_p_latent) + aggregates (index_hat)
       outputs/forecasts/kalman182_oos_quarterly.csv  quarterly y-o-y of every aggregate
       outputs/eval/kalman182.csv                  origin_q, h, target_q, model, pi_hat, pi_actual (+ 182)
       outputs/tables/table4.csv                   paper layout: absolute RMSFE row, relative RMSFE (p-value)
       outputs/tables/table4_compare_paper.csv     ours vs paper per cell
       outputs/logs/kalman_oos_item_log.csv        per item and origin: order used, drift, failures

    python scripts/11_kalman_oos.py                           # all 32 origins (~1 h first time, seconds cached)
    python scripts/11_kalman_oos.py --origins 2004-02 2011-11 # check run: prints only, writes no outputs
    python scripts/11_kalman_oos.py --force                   # refit cached origins
"""

import argparse

import pandas as pd

from arima_snb import evaluate, kalman_eval
from arima_snb.config import EVAL, FINAL, FORECASTS, HORIZONS, KALMAN_N_JOBS, LOGS, PAPER_TABLE4, TABLES

BENCHMARKS = [evaluate.MODEL_PLAIN, evaluate.MODEL_SPECIAL]
LABELS = {kalman_eval.MODEL_KALMAN: "Extended ARIMA(182)", evaluate.MODEL_PLAIN: "ARIMA(182)",
          evaluate.MODEL_SPECIAL: "Real-time ARIMA (analogue: ARIMA(182) + oil ECM + rent model, D-50)"}


def paper_layout(tab: pd.DataFrame) -> pd.DataFrame:
    """Rows = models, columns = h; first row absolute RMSFE, others 'rel (p)' as in the paper."""
    def cell(r):
        return f"{r.value:.2f}" if pd.isna(r.p_value) else f"{r.value:.2f} ({r.p_value:.3f})"
    out = tab.assign(cell=tab.apply(cell, axis=1)).pivot(index="row", columns="h", values="cell")
    out = out.reindex([kalman_eval.MODEL_KALMAN] + BENCHMARKS)
    out.index = [LABELS[i] for i in out.index]
    out.columns = [f"h={h}" for h in out.columns]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origins", nargs="*", help="subset of origins YYYY-MM (check run; no outputs written)")
    ap.add_argument("--force", action="store_true", help="refit cached origins")
    ap.add_argument("--n-jobs", type=int, default=KALMAN_N_JOBS)
    args = ap.parse_args()

    all_origins = evaluate.evaluation_origins()
    origins = [pd.Timestamp(o) for o in args.origins] if args.origins else all_origins
    assert all(o in all_origins for o in origins), "origins must be Feb/May/Aug/Nov 2004-2011 (D-04)"

    inputs = evaluate.load_inputs(with_crude=False)           # the extended model uses no exogenous data
    orders = pd.read_csv(FINAL / "kalman_orders.csv")
    res = kalman_eval.run_kalman_oos(inputs, orders, origins, n_jobs=args.n_jobs, force=args.force)
    actuals = evaluate.quarterly_actuals(inputs, evaluate.official_cpi())
    ev_k = evaluate.eval_table(res["quarterly"], actuals)

    # --- checks -----------------------------------------------------------------------------------------
    assert len(ev_k) == len(origins) * len(HORIZONS), len(ev_k)
    assert ev_k.pi_hat.notna().all() and ev_k.pi_actual.notna().all()
    n_items = res["items"].groupby("origin").item_id.nunique()
    assert n_items.ge(175).all(), n_items[n_items < 175]
    failed = res["log"][res["log"].note.str.startswith("failed", na=False)]
    print(f"\nitems per origin: min {n_items.min()}, max {n_items.max()}; failed fits: {len(failed)}")
    if len(failed):
        print(failed[["origin", "item_id", "note"]].to_string())
    fell_back = res["log"][(res["log"].p_used != res["log"].p_vintage) & res["log"].p_used.notna()]
    print(f"order stepped down at an origin (D-42 fallback): {len(fell_back)} item-origins")

    # benchmarks from T3.1 on the same origins
    ev_b = pd.read_csv(EVAL / "arima182.csv")
    ev_b = ev_b[ev_b.model.isin(BENCHMARKS) & ev_b.origin_q.isin(ev_k.origin_q.astype(str).unique())]
    ev_k = ev_k.assign(origin_q=ev_k.origin_q.astype(str))
    ev = pd.concat([ev_k, ev_b], ignore_index=True)
    assert ev.groupby(["model", "h"]).size().nunique() == 1, "benchmarks must cover the same origins"

    # --- Table 4 ------------------------------------------------------------------------------------------
    pd.set_option("display.width", 220)
    print("\nRMSFE (pp) vs official CPI:")
    print(evaluate.rmsfe_by_h(ev).to_string(float_format="%.3f"))
    print("\nRMSFE (pp) vs 182-item re-aggregation:")
    print(evaluate.rmsfe_by_h(ev, "pi_actual_182").to_string(float_format="%.3f"))
    tab = kalman_eval.comparison_table(ev, kalman_eval.MODEL_KALMAN, BENCHMARKS)
    layout = paper_layout(tab)
    print("\nTable 4 replica (first row absolute RMSFE; then relative RMSFE (DMW-HLN p-value)):")
    print(layout.to_string())
    paper = pd.DataFrame([{"row": r, "h": h, "paper_value": v, "paper_p": p}
                          for r, cells in PAPER_TABLE4.items() for h, (v, p) in enumerate(cells, 1)])
    cmp = tab.merge(paper, on=["row", "h"])
    cmp["diff"] = cmp.value - cmp.paper_value
    cmp["same_side_of_1"] = (cmp.row == kalman_eval.MODEL_KALMAN) | ((cmp.value > 1) == (cmp.paper_value > 1))
    cmp["same_significance_10pct"] = cmp.p_value.isna() | ((cmp.p_value < 0.10) == (cmp.paper_p < 0.10))
    print("\nours vs paper:")
    print(cmp.to_string(float_format="%.3f", index=False))
    in_window = ev[pd.PeriodIndex(ev.target_q, freq="Q") <= pd.Period(all_origins[-1], freq="Q")]
    print("\nRMSFE (pp), targets 2004Q1-2011Q4 only (D-04 robustness):")
    print(evaluate.rmsfe_by_h(in_window).to_string(float_format="%.3f"))

    if args.origins:
        print("\ncheck run on a subset of origins: no outputs written")
        return

    # --- outputs (complete rewrite = idempotent) ----------------------------------------------------------
    for d in (FORECASTS, EVAL, LOGS, TABLES):
        d.mkdir(parents=True, exist_ok=True)
    it = res["items"].assign(aggregate=pd.NA, index_hat=float("nan"))
    ag = res["monthly"].assign(item_id=pd.NA, log_p_hat=float("nan"), log_p_latent=float("nan"))
    cols = ["origin", "target", "item_id", "aggregate", "model", "log_p_hat", "log_p_latent", "index_hat"]
    pd.concat([it[cols], ag[cols]], ignore_index=True).to_csv(FORECASTS / "kalman182.csv", index=False)
    res["quarterly"].to_csv(FORECASTS / "kalman182_oos_quarterly.csv", index=False)
    ev_k.to_csv(EVAL / "kalman182.csv", index=False)
    res["log"].to_csv(LOGS / "kalman_oos_item_log.csv", index=False)
    layout.to_csv(TABLES / "table4.csv")
    cmp.to_csv(TABLES / "table4_compare_paper.csv", index=False)
    print("\nwrote", EVAL / "kalman182.csv", TABLES / "table4.csv", TABLES / "table4_compare_paper.csv")


if __name__ == "__main__":   # needed on Windows: the item fits run in worker processes
    main()
