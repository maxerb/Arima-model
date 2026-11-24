"""T1.5: annual item weights and the item collection calendar.

Writes
  data/final/weights.csv      year, item_id, weight  (valid Jan-Dec of `year`, BFS units, full basket = 100)
  data/final/collection.csv   date, item_id, collected, source ('calendar' = paper Tables 5-8, 'inferred' =
                              |d log p| >= 1e-3, paper fn. 9), pattern (calendar label, e.g. 'aperiodic')
  data/interim/collection_report.csv  per item and calendar year: months collected (official vs inferred)

Decisions: D-26 (weight years), D-27 (shared positions split by last separate shares), D-28 (calendar
mapping and years), real-time rule in panel.collection_pattern (paper pp. 14-15).
"""

import numpy as np
import pandas as pd

from arima_snb import panel
from arima_snb.config import CALENDAR_LAST_YEAR, FINAL, INTERIM


def main() -> None:
    items = pd.read_csv(FINAL / "items.csv")
    mapping = pd.read_csv(INTERIM / "item_mapping.csv", dtype={"pos_nos": str})
    long = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])

    # ---------------- weights ----------------
    w = panel.item_weights(mapping)
    w.to_csv(FINAL / "weights.csv", index=False)

    # ---------------- collection ----------------
    inf = []
    for item_id, g in long.groupby("item_id"):
        c = panel.infer_collection(g.set_index("date")["log_p"]).dropna()
        inf.append(pd.DataFrame({"date": c.index, "item_id": item_id, "collected": c.astype(bool).values}))
    inferred = pd.concat(inf).assign(source="inferred", pattern="")
    official = panel.official_calendar(items, CALENDAR_LAST_YEAR).assign(source="calendar")
    coll = pd.concat([official, inferred])[["date", "item_id", "collected", "source", "pattern"]]
    coll = coll.sort_values(["item_id", "source", "date"]).reset_index(drop=True)
    coll.to_csv(FINAL / "collection.csv", index=False)

    # ---------------- checks and sanity output ----------------
    assert not w.duplicated(["year", "item_id"]).any()
    assert (w.weight > 0).all()
    w10 = w[w.year == 2010].set_index("item_id")["weight"]
    t9 = items.set_index("item_id")["weight_2010"]
    diff = (w10 - t9).abs()
    print(f"2010: our weights vs paper Table 9: {(diff < 5e-4).sum()} of {len(t9)} equal; "
          f"sum ours {w10.sum():.3f}, paper {t9.sum():.3f}")
    print(diff[diff >= 5e-4].round(3).to_string())
    # Known paper issues: Table 9 prints the weights of items 85-93 and 119-124 one row off (same set of
    # numbers within each block), and lists skirts (i074) with 0.230 where BFS has 0.143 (D-22 note).
    shifted = [f"i{n:03d}" for n in [*range(85, 94), *range(119, 125)]]
    assert set(diff[diff >= 5e-4].index) <= set(shifted) | {"i074"}
    assert sorted(w10[shifted].round(3)) == sorted(t9[shifted].round(3))
    assert abs(w10.sum() - (t9.sum() - (0.230 - 0.143))) < 0.002
    cov = w.groupby("year").agg(items=("item_id", "nunique"), coverage=("weight", "sum")).round(3)
    print("coverage of the full basket (=100) per year:", cov.to_string(), sep="\n")

    agg6 = w.merge(items[["item_id", "agg6"]]).query("year == 2010").groupby("agg6")["weight"].sum()
    print("agg6 weights 2010 (paper: 16.875, 27.818, 19.499, 8.711, 23.447, 3.650):", agg6.round(3).to_string(),
          sep="\n")

    # official vs inferred: months collected per year
    coll["year"] = pd.to_datetime(coll.date).dt.year
    rep = (coll[coll.collected.notna()].assign(collected=lambda d: d.collected.astype(bool))
           .groupby(["item_id", "year", "source"])["collected"].sum().unstack("source"))
    rep.to_csv(INTERIM / "collection_report.csv")
    both = rep.dropna()
    both = both[both.index.get_level_values("year").isin(range(2001, CALENDAR_LAST_YEAR + 1))]
    agree = (both["calendar"] == both["inferred"]).mean()
    print(f"item-years 2001-{CALENDAR_LAST_YEAR} with fixed official months: {len(both)}; same number of "
          f"collected months as inferred: {agree:.0%}; inferred > official: {(both.inferred > both.calendar).mean():.0%}")

    # Rents: quarterly collection Feb/May/Aug/Nov since 2008 (AGENTS.md §7)
    rent = panel.collection_pattern(coll, "i094", "2010-03-01")
    print("rent (i094) months collected in 2009 (inferred):", rent)
    # Trousers (paper Chart 1): quarterly until 2007, ~6x/year 2008-2010, monthly from 2011
    for iid in ["i069", "i075"]:
        print(iid, "months collected per year:",
              rep.loc[iid, "inferred"].loc[2002:2014].astype(int).to_dict())
    n_inf = inferred.groupby("item_id").collected.mean()
    print("share of months collected (inferred), quantiles:", n_inf.quantile([0, .1, .5, .9, 1]).round(2).to_dict())
    assert np.isclose(cov.loc[2010, "coverage"], 92.701, atol=0.002)


if __name__ == "__main__":
    main()
