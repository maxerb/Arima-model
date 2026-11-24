"""T1.4: build the consistent CPI item panel (182 paper items, chain-linked over all BFS baskets).

Writes
  data/interim/item_mapping.csv   item x basket -> BFS position(s), rule used, names (for review)
  data/interim/item_link_report.csv  first/last observation and link notes per item
  data/final/items.csv            one row per model item (AGENTS.md §4)
  data/final/cpi_items_long.csv   date, item_id, index (=100 in Dec 2010), log_p

Decisions: D-22 (Table 9 -> 2005 basket by weight), D-23 (crosswalk + merging split items),
D-24 (chain own basket files at the overlap month), D-25 (1993 basket only for 1:1 name matches).
"""

import sys

import pandas as pd

from arima_snb import panel
from arima_snb.config import FINAL, INTERIM


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)

    t9, mapping = panel.build_mapping()
    # Pass 1 without the renumbered baskets (1993, 2025), pass 2 links them by name + dynamics (D-25)
    core = mapping.assign(pos_nos=mapping.pos_nos.where(~mapping.base.isin(panel.RENUMBERED), ""))
    long_core, _ = panel.build_panel(core)
    mapping = panel.refine_renumbered(mapping, long_core)
    mapping.to_csv(INTERIM / "item_mapping.csv", index=False)

    long, report = panel.build_panel(mapping)
    report.to_csv(INTERIM / "item_link_report.csv", index=False)
    long.to_csv(FINAL / "cpi_items_long.csv", index=False)

    # items.csv: one row per model item. agg6 is not yet assigned (see decisions D-21 / follow-up).
    names_de = mapping[mapping.base == panel.PAPER_BASKET].set_index("item_id")["name_de"]
    items = pd.DataFrame({
        "item_id": t9["item_id"],
        "name_de": t9["item_id"].map(names_de),
        "name_en": t9["item_en"],
        "bfs_codes": t9["pos05"],
        "agg6": t9["agg6"],
        "agg14": t9["agg14"],
        "special": t9["item_en"].map(panel.SPECIAL).fillna(""),
        "weight_2010": t9["weight_2010"],
        "first_obs": t9["item_id"].map(report.set_index("item_id")["first_obs"]),
        "last_obs": t9["item_id"].map(report.set_index("item_id")["last_obs"]),
    })
    items.to_csv(FINAL / "items.csv", index=False)

    # ---------------- checks and sanity output ----------------
    assert len(items) == 182 and items["bfs_codes"].notna().all(), "every paper item needs a 2005 position"
    assert mapping.loc[mapping.base.isin(["LIK00B00", "LIK05B05", "LIK10B10"]), "pos_nos"].ne("").all(), \
        "replication period 2000-2015 must be fully mapped"
    start = pd.to_datetime(items["first_obs"])
    assert (start <= "2000-05-01").all(), "all paper items must start by May 2000 (paper p. 5)"

    print(f"items: {len(items)}, 2010 weight covered: {items.weight_2010.sum():.3f} (paper 92.788)")
    print("mapping rules per basket:")
    print(mapping.groupby(["base", "rule"]).size().unstack(fill_value=0).to_string())
    print("first observation:", start.value_counts().sort_index().to_string(), sep="\n")
    print("last observation:", pd.to_datetime(items.last_obs).value_counts().sort_index().to_string(), sep="\n")
    jumps = panel.link_jumps(long)
    print(f"links with an unusual change (> 20 log pts vs same month other years): {len(jumps)}")
    if len(jumps):
        print(jumps[["date", "item_id", "dlog", "typical", "excess"]].to_string(index=False))
    agree = panel.backcast_agreement(mapping, long)
    agree.to_csv(INTERIM / "item_backcast_check.csv", index=False)
    bad = agree[(agree["corr"] < 0.5) & (agree["mad"] > 0.005)]
    print(f"back-cast check: {len(agree)} item-links compared, median corr {agree['corr'].median():.2f}, "
          f"{len(bad)} with corr < 0.5 and mean abs. difference > 0.5 log pts:")
    print(bad.to_string(index=False))
    if "--strict" in sys.argv:
        assert jumps.empty


if __name__ == "__main__":
    main()
