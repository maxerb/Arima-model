"""T3.2: benchmark forecasts AR(1), ARIMA(1), ARIMA(6), ARIMA(14), SNB conditional, KOF consensus.

Paper pp. 8-11, Tables 1-2; decisions D-05 rev. (AR(1) with month intercepts), D-06 rev. + D-56 (KOF), D-20 (SNB), D-47 (inputs),
D-55 (sub-aggregate ARIMA spec), D-57 (annual target). Same 32 origins as T3.1 (D-04). Needs
scripts/10_pseudo_oos.py to have run (outputs/eval/arima182.csv) for the comparison with the disaggregate model.

Writes data/final/subaggregate_specs.csv               spec vintages of the 21 sub-aggregate series
       outputs/forecasts/benchmarks.csv                 origin, target, aggregate, model, index_hat (monthly paths)
       outputs/forecasts/benchmarks_subaggregates.csv   origin, target, item_id (group), model, log_p_hat
       outputs/eval/benchmarks.csv                      origin_q, h, target_q, model, pi_hat, pi_actual, pi_actual_182
       outputs/eval/annual.csv                          origin_q, h_year, target_y, model, pi_hat, pi_actual (all models)
       outputs/logs/benchmark_orders.csv                per group and origin: method, (p, q), notes

    python scripts/12_benchmarks.py            # ~10 min the first time, seconds when the fits are cached
    python scripts/12_benchmarks.py --force    # refit the sub-aggregate ARIMAs
"""

import argparse

import numpy as np
import pandas as pd

from arima_snb import benchmarks as bm
from arima_snb import evaluate
from arima_snb.config import EVAL, FINAL, FORECASTS, HORIZONS, LOGS, OOS_N_JOBS, PAPER_RELATIVE, SPEC_VINTAGES


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="refit cached origins")
    ap.add_argument("--n-jobs", type=int, default=OOS_N_JOBS)
    args = ap.parse_args()

    # --- specs of the sub-aggregates (D-55), written first so load_inputs() reads them -----------------
    panel = bm.subaggregate_panel()
    coll = bm.group_collection(panel)
    specs = bm.subaggregate_specs(panel, coll, SPEC_VINTAGES)
    specs.to_csv(FINAL / "subaggregate_specs.csv", index=False)
    print("sub-aggregate specs (vintage 2003 / 2010):")
    print(specs[specs.vintage.isin([2003, 2010])].pivot(index="item_id", columns="vintage",
                                                        values=["collection_freq", "seasonal", "method"]).to_string())

    inputs = bm.load_inputs()
    origins = evaluate.evaluation_origins()
    parts = {k: [] for k in ("quarterly", "monthly", "items", "log")}
    for i, origin in enumerate(origins, 1):
        res = bm.forecast_origin(inputs, origin, args.n_jobs, force=args.force)
        for k in parts:
            parts[k].append(res[k].assign(origin=origin) if k == "log" else res[k])
        tot = res["quarterly"].pivot(index="model", columns="h", values="pi_hat").round(2)
        print(f"[{i:2d}/{len(origins)}] {origin:%Y-%m}", tot.to_dict("index"), flush=True)
    res = {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}

    # SNB conditional forecast (D-20)
    snb_paths = bm.snb_conditional_paths()
    snb = pd.concat([bm.snb_forecast_origin(snb_paths, o) for o in origins], ignore_index=True).assign(model=bm.SNB)
    q = pd.concat([res["quarterly"], snb], ignore_index=True)

    eval_inputs = evaluate.load_inputs(with_crude=False)
    actuals = evaluate.quarterly_actuals(eval_inputs, inputs["cpi"])
    ev = q.assign(aggregate="total", origin_q=q.origin_q.astype(str))
    ev = evaluate.eval_table(ev, actuals)

    # --- checks -----------------------------------------------------------------------------------------
    n_quarterly_models = 5   # ar1, ar1_plain, arima1, arima6, arima14
    assert len(ev) == len(origins) * len(HORIZONS) * (n_quarterly_models + 1), len(ev)
    assert ev[ev.model != bm.SNB].pi_hat.notna().all(), "missing benchmark forecast"
    snb_missing = ev[(ev.model == bm.SNB) & ev.pi_hat.isna()].origin_q.unique().tolist()
    assert snb_missing == ["2004Q1"], snb_missing   # the cube starts with the June 2004 assessment
    # ARIMA(1) works on official CPI: its h = 1 forecast shares two actual months, so errors must be small
    assert evaluate.rmsfe_by_h(ev).loc["arima1", 1] < 0.3

    # --- annual-average target (D-06 rev., D-57): every model incl. arima182 and KOF -------------------
    a182 = pd.read_csv(EVAL / "arima182.csv")
    q_all = pd.concat([ev, a182], ignore_index=True)[["origin_q", "h", "target_q", "model", "pi_hat"]]
    act_q = actuals.pi_actual
    annual = bm.annual_from_quarterly(q_all, act_q)
    kof = bm.kof_consensus()
    kof_rows = []
    for o in origins:
        s = bm.kof_for_origin(kof, o)
        oq = pd.Timestamp(o).to_period("Q")
        for h_year, col in ((0, "prices_cy"), (1, "prices_ny")):
            kof_rows.append({"origin_q": str(oq), "h_year": h_year, "target_y": oq.year + h_year, "model": bm.KOF,
                             "pi_hat": np.nan if s is None else s[col]})
    annual = pd.concat([annual, pd.DataFrame(kof_rows)], ignore_index=True)
    annual["pi_actual"] = annual.target_y.map(bm.annual_actuals(act_q))
    # exact BFS definition (change of the annual-average index) only as a check of the D-57 approximation
    cpi_y = inputs["cpi"].groupby(inputs["cpi"].index.year).mean()
    exact = 100 * (cpi_y / cpi_y.shift(1) - 1)
    gap = (annual.drop_duplicates("target_y").set_index("target_y").pi_actual - exact).dropna()
    print(f"\nannual target: mean of quarterly y-o-y vs change of annual average, max |gap| = {gap.abs().max():.3f} pp")
    assert gap.abs().max() < 0.1

    # --- sanity output ----------------------------------------------------------------------------------
    pd.set_option("display.width", 200)
    full = pd.concat([ev, a182], ignore_index=True)
    tab = evaluate.rmsfe_by_h(full)
    print("\nforecasts per h (T):", full.dropna(subset=["pi_hat"]).groupby(["model", "h"]).size()
          .unstack("h").to_dict("index"))
    print("\nRMSFE (pp) vs official CPI y-o-y, 2004Q1-2011Q4 origins:")
    print(tab.to_string(float_format="%.3f"))
    # SNB: common sample without 2004Q1 for its relative RMSFE
    no04 = full[full.origin_q != "2004Q1"]
    tab31 = evaluate.rmsfe_by_h(no04)
    print("\nrelative RMSFE, ours vs paper (preliminary; DMW tests are T3.3):")
    for (ref, bench), paper in PAPER_RELATIVE.items():
        if bench == bm.KOF:
            continue
        t = tab31 if bench == bm.SNB else tab
        ours = (t.loc[bench] / t.loc[ref]).round(2).tolist()
        print(f"  {bench:16s} / {ref:16s} ours {ours}  paper {list(paper)}")
    print("  (snb_conditional on 31 origins 2004Q2-2011Q4; KOF only on the annual target below)")

    sc = annual[annual.pi_hat.notna()]
    sc = sc[sc.groupby(["origin_q", "h_year"]).model.transform("nunique") == sc.model.nunique()]
    ann = sc.assign(err=sc.pi_actual - sc.pi_hat).groupby(["model", "h_year"]).err.agg(
        rmsfe=evaluate.rmsfe, T="size").unstack("h_year")
    print("\nannual-average inflation (current year h_year=0: all origins; next year h_year=1: Q4 origins), "
          "common sample of all models:")
    print(ann.to_string(float_format="%.3f"))

    # --- outputs ----------------------------------------------------------------------------------------
    for d in (FORECASTS, EVAL, LOGS):
        d.mkdir(parents=True, exist_ok=True)
    res["monthly"].to_csv(FORECASTS / "benchmarks.csv", index=False)
    res["items"].assign(model=res["items"].item_id.str.split(":").str[0].map(bm.LEVEL_MODEL)).to_csv(
        FORECASTS / "benchmarks_subaggregates.csv", index=False)
    ev.to_csv(EVAL / "benchmarks.csv", index=False)
    annual.to_csv(EVAL / "annual.csv", index=False)
    res["log"].to_csv(LOGS / "benchmark_orders.csv", index=False)
    print("\nwrote", EVAL / "benchmarks.csv", EVAL / "annual.csv", FORECASTS / "benchmarks.csv")


if __name__ == "__main__":   # needed on Windows: the sub-aggregate fits run in worker processes
    main()
