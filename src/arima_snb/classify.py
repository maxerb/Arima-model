"""Recover which CPI positions belong to the BFS special groupings (domestic/imported, goods/services types).

Why (D-21, revised): the paper's ARIMA(6) splits the CPI by origin and product type, but BFS publishes these
groupings only as aggregate index series, not as a membership list. Since a chained Laspeyres aggregate is a
weighted mean of its members, membership can be estimated from the data:

    within weight year y (price base Dec y-1):   A_t = sum_i s_i w_i r_it / sum_i s_i w_i
    <=>  sum_i s_i * w_i * (r_it - A_t) = 0          for every month t of the year,

with r_it = I_it / I_i,Dec(y-1) the leaf's price relative, A_t the same for the aggregate, w_i the leaf's weight
and s_i in [0, 1] its membership. Each leaf belongs to exactly one category of a classification
(sum_c s_ic = 1). We stack these equations over all months of the 2010, 2015, 2020 and 2025 basket files (only
these contain the grouping series), share s across baskets for positions whose number and name stay the same,
and solve a bounded least-squares problem. Memberships come out (close to) 0/1; we round and then check that the
rebuilt aggregates reproduce the BFS series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import nnls

from arima_snb import panel

# Classification -> BFS position numbers of its categories (same numbers in the 2010-2025 files)
CLASSIFICATIONS = {
    "origin": {118: "domestic", 119: "imported"},
    "type": {111: "non-durable goods", 112: "semi-durable goods", 113: "durable goods",
             116: "private services", 117: "public services"},
}
GROUPING_BASKETS = panel.BASKETS[3:]      # LIK10B10 ... LIK25B25 (own periods, D-24)
SUM_TO_ONE_WEIGHT = 10.0                   # weight of the "sum of memberships = 1" rows (relative to data rows);
                                           # large, so it acts as a constraint and keeps every s <= 1


def leaves(pos: pd.DataFrame) -> pd.Index:
    """Lowest-level positions of a basket (next row is not deeper), excluding special groupings (100-199)."""
    p = pos[(pos.index < 100) | (pos.index >= 200)]
    lvl = p["level"].astype(float)
    is_leaf = lvl.shift(-1).fillna(0).values <= lvl.values
    return p.index[is_leaf]


def descendants(pos: pd.DataFrame, pos_no: int) -> list[int]:
    """Leaf positions below `pos_no` in the basket's outline (the position itself if it is a leaf)."""
    order = list(pos.index)
    k = order.index(pos_no)
    lvl = pos["level"].astype(float).values
    out = [pos_no]
    for j in range(k + 1, len(order)):
        if lvl[j] <= lvl[k]:
            break
        out.append(order[j])
    leaf = set(leaves(pos))
    return [p for p in out if p in leaf]


def leaf_keys() -> pd.DataFrame:
    """One row per (basket, leaf) with the key of its membership unknown.

    Positions keep one key across baskets when the number is unchanged and the name similar (as in D-23);
    otherwise the leaf gets its own key.
    """
    rows, prev = [], {}
    for code, _sheet, _start in GROUPING_BASKETS:
        _, pos = panel.load_basket(code)
        cur = {}
        for p in leaves(pos):
            name = pos.loc[p, "name_de"]
            if p in prev and (panel.name_similarity(name, prev[p][1]) >= 0.5 or panel.words_contained(name, prev[p][1])):
                key = prev[p][0]
            else:
                key = f"{code}_{p}"
            cur[p] = (key, name)
            rows.append({"base": code, "pos_no": p, "key": key, "name_de": name})
        prev = cur
    return pd.DataFrame(rows)


def build_system(classification: str, keys: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list, list]:
    """Stack the aggregation equations of all months, categories and baskets: A @ s = b (columns key*K + cat)."""
    cats = list(CLASSIFICATIONS[classification])
    ukeys = list(dict.fromkeys(keys["key"]))
    col = {(k, c): j for j, (k, c) in enumerate((k, c) for k in ukeys for c in cats)}  # j = key*K + cat
    w_all = panel.load_weights()
    A, b = [], []
    for code, sheet, start in GROUPING_BASKETS:
        wide, _ = panel.load_basket(code)
        kb = keys[keys.base == code].set_index("pos_no")["key"]
        own = wide[wide.index >= pd.Timestamp(start)]
        for year, s0, s1 in panel.weight_segments(sheet, start, own.index.max()):
            if s0 not in own.index:
                continue
            w = (w_all[(w_all.basket == sheet) & (w_all.year == year)].drop_duplicates("pos_no")
                 .set_index("pos_no")["weight"].reindex(kb.index).fillna(0.0))
            seg = own.loc[(own.index > s0) & (own.index <= s1)]
            rel = seg[kb.index] / own.loc[s0, kb.index]
            # map leaves to unknown columns once: M[i, j] = 1 if leaf i uses key j
            kidx = np.array([ukeys.index(k) for k in kb.values])
            for c in cats:
                agg = seg[c] / own.loc[s0, c]
                dev = rel.sub(agg, axis=0).mul(w, axis=1).fillna(0.0).values   # w_i (r_it - A_t)
                rows = np.zeros((dev.shape[0], len(col)))
                cidx = kidx * len(cats) + cats.index(c)
                np.add.at(rows, (slice(None), cidx), dev)
                A.extend(rows)
                b.extend([0.0] * dev.shape[0])
    # every leaf belongs to exactly one category
    for k in ukeys:
        row = np.zeros(len(col))
        for c in cats:
            row[col[(k, c)]] = SUM_TO_ONE_WEIGHT
        A.append(row)
        b.append(SUM_TO_ONE_WEIGHT)
    return np.array(A), np.array(b), ukeys, cats


def estimate_membership(classification: str, keys: pd.DataFrame | None = None,
                        allowed: dict | None = None) -> pd.DataFrame:
    """Non-negative least squares for the memberships; returns one row per key with s per category and the label.

    `allowed` maps a key to the category names it may belong to (from the hand rules, D-21 rev.); the other
    categories of that key are fixed at 0. Fixing the clear cases is what makes the unclear ones identified.
    """
    keys = leaf_keys() if keys is None else keys
    A, b, ukeys, cats = build_system(classification, keys)
    names = [CLASSIFICATIONS[classification][c] for c in cats]
    if allowed:
        keep = np.ones(A.shape[1], dtype=bool)
        for k, ok in allowed.items():
            if k in ukeys:
                for j, nm in enumerate(names):
                    if nm not in ok:
                        keep[ukeys.index(k) * len(cats) + j] = False
        A = np.where(keep, A, 0.0)          # a dropped column can only take the value 0 in nnls
    # Scale the data rows so that they are comparable to the sum-to-one rows
    n_data = len(b) - len(ukeys)
    scale = np.abs(A[:n_data]).max() or 1.0
    A[:n_data] /= scale
    # Non-negative least squares (fast, exact active-set solver); s <= 1 follows from the sum-to-one rows
    x, _ = nnls(A, b, maxiter=50 * A.shape[1])
    s = pd.DataFrame(x.reshape(len(ukeys), len(cats)), index=ukeys,
                     columns=[CLASSIFICATIONS[classification][c] for c in cats])
    s["label"] = s.idxmax(axis=1)
    s["max_share"] = s[[CLASSIFICATIONS[classification][c] for c in cats]].max(axis=1)
    return s


def rebuild_check(classification: str, keys: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    """Rebuild each category index from the rounded labels and compare its monthly changes with BFS's series.

    Returns per basket and category: max and mean absolute difference of month-on-month % changes.
    """
    out = []
    cats = CLASSIFICATIONS[classification]
    for code, sheet, start in GROUPING_BASKETS:
        wide, _ = panel.load_basket(code)
        kb = keys[keys.base == code].set_index("pos_no")["key"]
        own = wide[wide.index >= pd.Timestamp(start)]
        for c, name in cats.items():
            members = [p for p, k in kb.items() if labels.get(k) == name]
            if not members:
                continue
            ours = panel.combine_children(own, members, sheet, start)
            d = pd.concat([ours.pct_change(), own[c].pct_change()], axis=1).dropna() * 100
            diff = (d.iloc[:, 0] - d.iloc[:, 1]).abs()
            out.append({"base": code, "category": name, "n_members": len(members),
                        "max_abs_diff_pp": round(diff.max(), 3), "mean_abs_diff_pp": round(diff.mean(), 4)})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# ARIMA(6) labels for the paper items: hand rules + data check (D-21 rev.)
# ---------------------------------------------------------------------------
AGG6_NAMES = {
    "goods": "Domestic durable goods",          # paper's label; it contains all domestic goods (D-21)
    "private": "Domestic private services",
    "public": "Public services",
    "imported": "Imported goods and services excl. oil products",
    "rent": "Rents",
    "oil": "Oil products",
}
GOODS = ["non-durable goods", "semi-durable goods", "durable goods"]
TYPE_ALLOWED = {"goods": set(GOODS), "private": {"private services"}, "public": {"public services"}}


def item_leaf_keys(mapping: pd.DataFrame, keys: pd.DataFrame, base: str = "LIK10B10") -> dict[str, list]:
    """Item -> membership keys of its leaf positions in the 2010 basket (first basket with group series)."""
    _, pos = panel.load_basket(base)
    kb = keys[keys.base == base].set_index("pos_no")["key"]
    out = {}
    for item, p in mapping[mapping.base == base].set_index("item_id")["pos_nos"].items():
        out[item] = [kb[leaf] for x in str(p).split(";") for leaf in descendants(pos, int(x))]
    return out


def item_agg6(mapping: pd.DataFrame, items: pd.DataFrame, rules: pd.DataFrame,
              keys: pd.DataFrame | None = None, weight_year: int = 2011) -> tuple[pd.DataFrame, dict]:
    """ARIMA(6) label per item from the hand rules (data/meta/agg6_rules.csv), origin 'data' -> regression.

    Steps: (1) the rules fix the product type of every item and the origin of the clear items; these are imposed
    on the item's leaf positions; (2) the origin regression (estimate_membership with `allowed`) then estimates
    the domestic share of the remaining leaves; (3) an item with origin 'data' is domestic if its weighted
    domestic share > 0.5. Returns the item table and the leaf labels (for the rebuild check).
    """
    keys = leaf_keys() if keys is None else keys
    ikeys = item_leaf_keys(mapping, keys)
    r = rules.set_index("item_id")
    allowed_o, allowed_t = {}, {}
    for item, ks in ikeys.items():
        for k in ks:
            allowed_t[k] = TYPE_ALLOWED[r.at[item, "type"]]
            if r.at[item, "origin"] in ("domestic", "imported"):
                allowed_o[k] = {r.at[item, "origin"]}
    so = estimate_membership("origin", keys, allowed_o)
    st = estimate_membership("type", keys, allowed_t)

    w_all = panel.load_weights()
    w = w_all[(w_all.basket == "LIK2010") & (w_all.year == weight_year)].drop_duplicates("pos_no")
    kb = keys[keys.base == "LIK10B10"].set_index("key")["pos_no"]
    wk = kb.map(w.set_index("pos_no")["weight"]).fillna(0.0)
    rows = []
    for item, ks in ikeys.items():
        ww = wk.reindex(ks).fillna(0.0)
        ww = ww / ww.sum() if ww.sum() > 0 else pd.Series(1 / len(ks), index=ks)
        dom = float((ww.values * so.loc[ks, "domestic"].values).sum())
        rows.append({"item_id": item, "type": r.at[item, "type"], "origin_rule": r.at[item, "origin"],
                     "domestic_share": round(dom, 3)})
    d = pd.DataFrame(rows)
    d["domestic"] = np.where(d.origin_rule == "data", d.domestic_share > 0.5, d.origin_rule == "domestic")
    special = items.set_index("item_id")["special"].fillna("")

    def label(x):
        sp = special.get(x.item_id, "")
        if sp in ("oil", "rent"):
            return AGG6_NAMES[sp]
        return AGG6_NAMES[x.type] if x.domestic else AGG6_NAMES["imported"]

    d["agg6"] = d.apply(label, axis=1)
    # leaf labels for the rebuild check: item leaves get the item's final labels, other leaves the regression's
    leaf_origin, leaf_type = so["label"].copy(), st["label"].copy()
    for x in d.itertuples():
        for k in ikeys[x.item_id]:
            leaf_origin[k] = "domestic" if x.domestic else "imported"
            if x.type != "goods":
                leaf_type[k] = f"{x.type} services"
    return d, {"origin": leaf_origin, "type": leaf_type}
