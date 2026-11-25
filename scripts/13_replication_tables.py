"""T3.3: replicas of paper Tables 1-3 (pp. 9, 11, 12) from the pseudo-out-of-sample outputs in outputs/eval/.

Inputs (all written by earlier steps, nothing typed in):
    outputs/eval/arima182.csv     T3.1: arima182 (plain ARIMA for oil/rents) and arima182_special (D-50)
    outputs/eval/benchmarks.csv   T3.2: ar1, ar1_plain, arima1, arima6, arima14, snb_conditional
    outputs/eval/annual.csv       T3.2: annual-average target incl. kof_consensus (D-06 rev., D-57)
    outputs/eval/t23_oil.csv      T2.3: oil-products item, ECM vs plain ARIMA
    outputs/eval/t24_rent.csv     T2.4: rent item, mortgage-rate model vs plain ARIMA

Metrics (paper p. 10, D-52): RMSFE per h over the 32 origins 2004Q1-2011Q4 (D-04); relative RMSFE = benchmark /
reference on the origins both share; DMW test with HLN correction, p-values from t(T-1); bold if p < 0.10.

Writes outputs/tables/table{1,2,3}.csv          paper layout: absolute RMSFE row, then 'rel (p)'
       outputs/tables/table1_annual.csv         Table 1 panel B: annual-average target with the KOF consensus
       outputs/tables/table{1,2,3}_long.csv     the numbers behind (row, h, value, p_value, T)
       outputs/tables/table{1,2,3}.tex          LaTeX (booktabs), bold at 10 %
       outputs/tables/table{1,2,3}_compare_paper.csv  ours vs paper per cell
       outputs/tables/compare_paper.csv         all tables stacked (incl. Table 4 from T4.2 if present)
       outputs/tables/tables_paper_vs_ours.md   short generated note per table

    python scripts/13_replication_tables.py
"""

import pandas as pd

from arima_snb import evaluate, report
from arima_snb.config import EVAL, HORIZONS, PAPER_TABLE1, PAPER_TABLE2, PAPER_TABLE3, TABLES

H_HEAD = [f"$h={h}$" for h in HORIZONS]
RT = "Real-time ARIMA (analogue: ARIMA(182) + oil ECM + rent model, D-50)"

# Table 1 (p. 9) - reference real-time ARIMA. Consensus Economics is not available quarterly (D-06 rev.).
T1_LABELS = {"arima182_special": RT, "snb_conditional": "SNB conditional forecast",
             "consensus_economics": "Consensus (quarterly: not available, see panel B)", "ar1": "AR(1)"}
T1_SENSITIVITY = {"ar1_plain": "AR(1), one constant (sensitivity, D-05 rev.)",
                  "arima182": "ARIMA(182), plain ARIMA for oil and rents (sensitivity)"}
T1_ANNUAL = {"arima182_special": RT, "kof_consensus": "KOF consensus (replaces Consensus Economics, D-06 rev.)",
             "snb_conditional": "SNB conditional forecast", "ar1": "AR(1)"}
# Table 2 (p. 11) - reference ARIMA(182) with plain ARIMA for oil and rents
T2_LABELS = {"arima182": "ARIMA(182)", "arima14": "ARIMA(14)", "arima6": "ARIMA(6)", "arima1": "ARIMA(1)"}
# Table 3 (p. 12) - item-level y-o-y inflation of oil products and rents
T3_OIL = {"oil_ecm": "Oil products (ECM)", "oil_arima": "Oil products (ARIMA)",
          "oil_realtime": "Oil products (real-time; SNB vintages not public)"}
T3_RENT = {"rent_model": "Rents (ARIMA + mortgage rate)", "rent_arima": "Rents (ARIMA)",
           "rent_realtime": "Rents (real-time; SNB vintages not public)"}

# D-58: overlap of the annual-target errors. Current year (h_year 0): the same year is forecast from 4 consecutive
# quarterly origins -> errors correlated up to lag 3 -> kernel as for h = 4. Next year (h_year 1): only Q4 origins,
# one per target year -> no overlap -> h = 1.
ANNUAL_TEST_LAG = {1: 4, 2: 1}


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(EVAL / f"{name}.csv")


def check_counts(ev: pd.DataFrame, models: list[str], n_expected: int) -> None:
    """Every model has one forecast per origin and h (SNB: none for 2004Q1, D-56) and all actuals exist."""
    n_origins = len(evaluate.evaluation_origins())
    for m in models:
        g = ev[ev.model == m]
        assert len(g) == n_origins * n_expected, (m, len(g))
        assert g.pi_actual.notna().all(), m
        n_fc = g.dropna(subset=["pi_hat"]).groupby("h").size()
        assert n_fc.min() >= n_origins - 1, (m, n_fc.to_dict())


def table1() -> tuple[pd.DataFrame, pd.DataFrame]:
    ev = pd.concat([load("arima182"), load("benchmarks")], ignore_index=True)
    check_counts(ev, ["arima182_special", "arima182", "snb_conditional", "ar1", "ar1_plain"], len(HORIZONS))
    tab = evaluate.comparison_table(ev, "arima182_special", ["snb_conditional", "ar1", *T1_SENSITIVITY])
    an = load("annual").rename(columns={"h_year": "h"})
    an["h"] += 1                                            # 1 = current year, 2 = next year
    an = an[an.model.isin(T1_ANNUAL)]
    tab_a = evaluate.comparison_table(an, "arima182_special", ["kof_consensus", "snb_conditional", "ar1"],
                                      test_lag=ANNUAL_TEST_LAG)
    return tab, tab_a


def table2() -> pd.DataFrame:
    ev = pd.concat([load("arima182"), load("benchmarks")], ignore_index=True)
    check_counts(ev, list(T2_LABELS), len(HORIZONS))
    return evaluate.comparison_table(ev, "arima182", ["arima14", "arima6", "arima1"])


def table3() -> pd.DataFrame:
    oil = load("t23_oil").replace({"model": {"arima": "oil_arima"}})
    rent = load("t24_rent").replace({"model": {"arima": "rent_arima"}})
    check_counts(oil, ["oil_ecm", "oil_arima"], len(HORIZONS))
    check_counts(rent, ["rent_model", "rent_arima"], len(HORIZONS))
    return pd.concat([evaluate.comparison_table(oil, "oil_ecm", ["oil_arima"]),
                      evaluate.comparison_table(rent, "rent_model", ["rent_arima"])], ignore_index=True)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    note_lines = ["# Paper vs ours - Tables 1-3 (generated by scripts/13_replication_tables.py)", ""]
    all_cmp = []

    # --- Table 1 ---------------------------------------------------------------------------------------------
    t1, t1a = table1()
    lay1 = report.paper_layout(t1, {**T1_LABELS, **T1_SENSITIVITY})
    lay1a = report.paper_layout(t1a, T1_ANNUAL, col_prefix="year+")
    lay1a.columns = ["current year", "next year"]
    cmp1 = report.compare_with_paper(t1, PAPER_TABLE1, ["arima182_special"])
    cmp1 = cmp1[cmp1.row.isin(list(T1_LABELS))]
    tex1 = report.table_to_latex(
        [("A. Quarterly y-o-y inflation, h = 1..5 quarters", t1, T1_LABELS, H_HEAD),
         ("B. Annual-average inflation (target of the KOF consensus, D-57)", t1a, T1_ANNUAL,
          ["current year", "next year"])],
        caption="Real-time performance, 2004--2011 (replica of Huwiler \\& Kaufmann 2013, Table 1)",
        label="tab:table1",
        notes="First row: RMSFE in percentage points; other rows: RMSFE relative to the first row with the "
              "DMW-HLN p-value in brackets; bold = significant at 10 %. The real-time ARIMA is approximated by "
              "the pseudo-out-of-sample ARIMA(182) with the oil ECM and the rent model (SNB vintages are not "
              "public). Consensus Economics is replaced by the KOF consensus, which forecasts annual averages "
              "only (panel B; current year T = 32, next year T = 8 Q4 origins). SNB: T = 31 (no forecast 2004Q1).")
    # --- Table 2 ---------------------------------------------------------------------------------------------
    t2 = table2()
    lay2 = report.paper_layout(t2, T2_LABELS)
    cmp2 = report.compare_with_paper(t2, PAPER_TABLE2, ["arima182"])
    tex2 = report.table_to_latex(
        [(None, t2, T2_LABELS, H_HEAD)],
        caption="Optimal disaggregation, pseudo out-of-sample 2004--2011 (replica of Table 2)", label="tab:table2",
        notes="First row: RMSFE of ARIMA(182) (plain ARIMA also for oil products and rents) in percentage points; "
              "other rows: relative RMSFE (DMW-HLN p-value); bold = significant at 10 %. ARIMA(6)/(14) cover the "
              "182-item basket (about 93 % of the CPI, D-47); T = 32.")
    # --- Table 3 ---------------------------------------------------------------------------------------------
    t3 = table3()
    lay3 = report.paper_layout(t3, {**T3_OIL, **T3_RENT})
    cmp3 = report.compare_with_paper(t3, PAPER_TABLE3, ["oil_ecm", "rent_model"])
    tex3 = report.table_to_latex(
        [(None, t3, T3_OIL, H_HEAD), (None, t3, T3_RENT, H_HEAD)],
        caption="Oil products and rents, pseudo out-of-sample 2004--2011 (replica of Table 3)", label="tab:table3",
        notes="Item-level y-o-y inflation. First row of each block: RMSFE of the special model in percentage "
              "points; other rows: relative RMSFE (DMW-HLN p-value); bold = significant at 10 %. Rents are "
              "collected in the origin month, so the h = 1 error is zero. The paper's real-time rows use SNB "
              "vintages that are not public and are not replicated. T = 32.")

    for n, lay, tab, cmp, tex, refs in [(1, lay1, t1, cmp1, tex1, ["arima182_special"]),
                                        (2, lay2, t2, cmp2, tex2, ["arima182"]),
                                        (3, lay3, t3, cmp3, tex3, ["oil_ecm", "rent_model"])]:
        print(f"\nTable {n} replica (first row absolute RMSFE, then relative RMSFE (DMW-HLN p)):")
        print(lay.to_string())
        verdict = report.describe_agreement(cmp, refs)
        print(verdict)
        lay.to_csv(TABLES / f"table{n}.csv")
        tab.to_csv(TABLES / f"table{n}_long.csv", index=False)
        cmp.to_csv(TABLES / f"table{n}_compare_paper.csv", index=False)
        (TABLES / f"table{n}.tex").write_text(tex, encoding="utf-8")
        all_cmp.append(cmp.assign(table=n))
        paper_lay = report.paper_layout(report.paper_frame(
            {1: PAPER_TABLE1, 2: PAPER_TABLE2, 3: PAPER_TABLE3}[n]).rename(
            columns={"paper_value": "value", "paper_p": "p_value"}),
            {r: r for r in {1: PAPER_TABLE1, 2: PAPER_TABLE2, 3: PAPER_TABLE3}[n]})
        note_lines += [f"## Table {n}", "", "Ours:", "", "```", lay.to_string(), "```", "", "Paper:", "", "```",
                       paper_lay.to_string(), "```", "", verdict.replace("\n  ", "\n- ").replace("\n", "\n\n", 1),
                       ""]
    print("\nTable 1 panel B (annual-average target):")
    print(lay1a.to_string())
    lay1a.to_csv(TABLES / "table1_annual.csv")
    t1a.to_csv(TABLES / "table1_annual_long.csv", index=False)
    note_lines += ["## Table 1, panel B (annual target, KOF consensus; no paper counterpart)", "", "```",
                   lay1a.to_string(), "```", ""]

    if (TABLES / "table4_compare_paper.csv").exists():
        all_cmp.append(pd.read_csv(TABLES / "table4_compare_paper.csv").assign(table=4))
    pd.concat(all_cmp, ignore_index=True).to_csv(TABLES / "compare_paper.csv", index=False)
    (TABLES / "tables_paper_vs_ours.md").write_text("\n".join(note_lines), encoding="utf-8")
    print("\nwrote", *(f"table{n}.{{csv,tex}}" for n in (1, 2, 3)), "compare_paper.csv tables_paper_vs_ours.md",
          "in", TABLES)


if __name__ == "__main__":
    main()
