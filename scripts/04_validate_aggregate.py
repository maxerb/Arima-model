"""T1.6: re-aggregate the 182-item panel and compare with official headline CPI (paper Chart 4).

Writes
  data/interim/cpi_reaggregated.csv           date, index_ours, index_official, yoy_ours, yoy_official, gap
  outputs/tables/t16_reaggregation_gap.csv    gap statistics by period (monthly and quarterly y-o-y)
  outputs/figures/chart4_reaggregated_vs_official.png
Decisions: D-29 (chaining periods), D-30 (normalise weights over covered items).
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from arima_snb import aggregate, io
from arima_snb.config import FIGURES, FINAL, INTERIM, RAW, TABLES

PERIODS = [("1994-05", "2000-05"), ("2001-05", "2011-12"), ("2004-01", "2011-12"),
           ("2012-01", "2015-12"), ("2016-01", "2025-12"), ("2026-01", "2026-12")]


def official_cpi() -> pd.Series:
    df = io.read_snb_cube(io.find_raw("snb-data-plkopr-*.csv"), "plkopr")
    s = df[df.variable == "plkopr_LD2010100"].set_index("date")["value"]
    return s.astype(float).sort_index()


def gap_stats(d: pd.Series) -> dict:
    d = d.dropna()
    return dict(n=len(d), mean=d.mean(), mae=d.abs().mean(), rmse=np.sqrt((d ** 2).mean()), max_abs=d.abs().max())


def main() -> None:
    long = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
    weights = pd.read_csv(FINAL / "weights.csv")
    wide = long.pivot(index="date", columns="item_id", values="index").asfreq("MS")

    ours = aggregate.aggregate_index(wide, weights)
    off = official_cpi().reindex(ours.index)
    m = pd.DataFrame({"index_ours": ours, "index_official": off,
                      "yoy_ours": aggregate.monthly_yoy(ours), "yoy_official": aggregate.monthly_yoy(off)})
    m["gap"] = m.yoy_ours - m.yoy_official
    m.index.name = "date"
    m.to_csv(INTERIM / "cpi_reaggregated.csv")

    q = pd.DataFrame({"ours": aggregate.quarterly_yoy(ours), "official": aggregate.quarterly_yoy(off)})
    q["gap"] = q.ours - q.official

    rows = []
    for a, b in PERIODS:
        rows.append(dict(period=f"{a}..{b}", freq="monthly", **gap_stats(m.gap[a:b])))
        qa, qb = pd.Period(a, "M").asfreq("Q"), pd.Period(b, "M").asfreq("Q")
        rows.append(dict(period=f"{a}..{b}", freq="quarterly", **gap_stats(q.gap[qa:qb])))
    tab = pd.DataFrame(rows)
    tab.to_csv(TABLES / "t16_reaggregation_gap.csv", index=False, float_format="%.3f")
    print(tab.round(3).to_string(index=False))
    big = m.gap[m.gap.abs() > 0.2].dropna()
    print(f"\nmonths with |gap| > 0.2 pp: {len(big)} of {m.gap.notna().sum()}")
    print(big.groupby(big.index.year).agg(["count", "mean"]).round(2).to_string())

    # Sanity: gap over the paper's sample must be small, otherwise something is mislinked.
    assert gap_stats(m.gap["2001-05":"2011-12"])["rmse"] < 0.3, "re-aggregation far from official CPI"

    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax[0].plot(m.index, m.yoy_official, color="black", lw=1.4, label="Official CPI")
    ax[0].plot(m.index, m.yoy_ours, color="tab:red", lw=1, ls="--", label="Re-aggregated (182 items)")
    ax[0].axhline(0, color="grey", lw=0.5)
    ax[0].set_ylabel("y-o-y inflation, %")
    ax[0].legend(frameon=False)
    ax[0].set_title("Re-aggregated vs official CPI inflation (cf. paper Chart 4)")
    ax[1].bar(m.index, m.gap, width=25, color="tab:grey")
    ax[1].set_ylabel("gap, pp")
    fig.tight_layout()
    fig.savefig(FIGURES / "chart4_reaggregated_vs_official.png", dpi=150)
    print("saved figure")


if __name__ == "__main__":
    main()
