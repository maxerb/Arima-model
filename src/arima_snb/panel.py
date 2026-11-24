"""Item panel: chain-linking across CPI bases, item mapping, weights and collection calendar (T1.4-T1.5).

Skill: snb-arima-cpi-panel.

How the panel is built (T1.4, decisions D-22 ... D-25):

1. The paper's 182 model items (Table 9) are positions of the **2005 basket**: their 2010 weights equal the BFS
   LIK2005 weights for 2010. We find each item's 2005 position by its weight (D-22).
2. Every other basket (1993, 2000, 2010, 2015, 2020, 2025) gets a crosswalk 2005-position -> position(s) in that
   basket: same position number with a similar name, else the best name match; hand corrections live in
   `data/meta/item_mapping_overrides.csv` (reviewable, tracked in git). If an item is split in a later basket, the
   override lists the children and we rebuild the parent from them with the basket's weights (D-23, paper p. 11).
3. Each basket's **own file** is used only for its own period, and successive baskets are chain-linked at the
   overlap month (May 2000, Dec 2005, Dec 2010, ...) (D-24). BFS back-casts inside newer files are not used.
"""

from __future__ import annotations

import difflib
import re

import numpy as np
import pandas as pd

from arima_snb import io
from arima_snb.config import META, NO_COLLECTION_TOL

# Baskets in time order: (file code, weight sheet, first month of the basket's own period).
# The first month is the basket's base month; the overlap with the previous basket is that month (D-24).
BASKETS = [
    ("LIK93B93", "LIK1993", "1993-05-01"),
    ("LIK00B00", "LIK2000", "2000-05-01"),
    ("LIK05B05", "LIK2005", "2005-12-01"),
    ("LIK10B10", "LIK2010", "2010-12-01"),
    ("LIK15B15", "LIK2015", "2015-12-01"),
    ("LIK20B20", "LIK2020", "2020-12-01"),
    ("LIK25B25", "LIK2025", "2025-12-01"),
]
PAPER_BASKET = "LIK05B05"      # Table 9 weights = LIK2005 weights of 2010 (D-22)
PAPER_WEIGHT_YEAR = 2010
REFERENCE_MONTH = "2010-12-01"  # linked index = 100 in this month (any month works, logs differ by a constant)

# Oil products and rents get special models (paper p. 7)
SPECIAL = {"Heating oil": "oil", "Fuels": "oil", "Rents": "rent"}


# ---------------------------------------------------------------------------
# Raw data access (cached, the BFS files are slow to read)
# ---------------------------------------------------------------------------
_CACHE: dict = {}


def load_basket(code: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Index values (wide: date x pos_no) and position table of one basket file."""
    if code not in _CACHE:
        long, pos = io.read_bfs_cpi_items(io.find_raw(f"{code}_*"), code)
        long["pos_no"] = long["variable"].str.split("_").str[1].astype(int)
        wide = long.pivot(index="date", columns="pos_no", values="value").sort_index()
        _CACHE[code] = (wide, pos.set_index("pos_no"))
    return _CACHE[code]


def load_weights() -> pd.DataFrame:
    """All BFS weights in long format (basket, pos_no, year, weight)."""
    if "weights" not in _CACHE:
        _CACHE["weights"] = io.read_bfs_weights(io.find_raw("GEWICHTUNGEN_*"))
    return _CACHE["weights"]


# ---------------------------------------------------------------------------
# Step 1: Table 9 item -> 2005-basket position (by weight)
# ---------------------------------------------------------------------------
def match_table9_to_basket(t9: pd.DataFrame, pos: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Assign each Table 9 item the position whose weight equals the Table 9 weight (3 decimals).

    Weights are not unique (e.g. 0.143 occurs twice), but Table 9 lists the items in BFS position order.
    We therefore choose the largest set of matches that keeps that order (a longest-increasing-subsequence
    problem, solved by dynamic programming). Items left over go to the hand overrides (D-22).
    Returns pos_no per Table 9 row (NaN if not matched).
    """
    rows = pos.reset_index()
    rows["w"] = rows["pos_no"].map(weights).round(3)
    rows["row"] = np.arange(len(rows))
    cand = [rows.loc[rows["w"] == round(w, 3), "row"].tolist() for w in t9["weight_2010"]]

    # DP over (item, candidate row): best[i][r] = most matches among items <= i ending with item i at row r.
    best: list[dict] = []
    for i, rs in enumerate(cand):
        cur = {}
        for r in rs:
            prev = [(v[0], (j, pr)) for j in range(i) for pr, v in best[j].items() if pr < r]
            top = max(prev, default=(0, None))
            cur[r] = (top[0] + 1, top[1])
        best.append(cur)
    end = max(((v[0], (i, r)) for i, d in enumerate(best) for r, v in d.items()), default=(0, None))[1]
    out = pd.Series(np.nan, index=t9.index)
    while end is not None:
        i, r = end
        out.iloc[i] = rows.loc[r, "pos_no"]
        end = best[i][r][1]
    return out


# ---------------------------------------------------------------------------
# Step 2: crosswalk 2005 position -> other baskets
# ---------------------------------------------------------------------------
def _norm(name: str) -> str:
    """Lower-case name without punctuation and without BFS qualifiers added in later baskets, for comparison."""
    s = str(name).lower()
    s = re.sub(r"\((detailhandel|commerce de détail)\)", " ", s)
    s = re.sub(r"[^a-z0-9äöüéèàß ]", " ", s)
    return " ".join(s.split())


def name_similarity(a: str, b: str) -> float:
    """Similarity of two position names in [0, 1] (difflib ratio on normalised names)."""
    na, nb = _norm(a), _norm(b)
    if not na or na == "nan" or not nb or nb == "nan":
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def words_contained(a: str, b: str) -> bool:
    """True if all words of one name appear in the other ("Bier" vs "Bier (Detailhandel)")."""
    wa, wb = set(_norm(a).split()), set(_norm(b).split())
    return bool(wa) and bool(wb) and (wa <= wb or wb <= wa)


def weight_close(w_old: float, w_new: float, factor: float = 2.0) -> bool:
    """Plausibility check: an item's basket weight rarely changes by more than `factor` between baskets."""
    if pd.isna(w_old) or pd.isna(w_new) or w_old <= 0 or w_new <= 0:
        return False
    return 1 / factor <= w_new / w_old <= factor


def crosswalk_position(pos_no: int, name: str, weight: float, target: pd.DataFrame,
                       same_no_min: float = 0.5, name_min: float = 0.85) -> tuple[str, str, float]:
    """Find the position in another basket for one 2005-basket position.

    Rule (D-23):
    1. same position number, if the name is similar (ratio >= 0.5 or one name's words contain the other's)
       or, when the old file has no name, the weight is close (BFS kept numbers stable 2000-2020);
    2. else the best name match in the basket with ratio >= 0.85, or with contained words and a close weight.
    `target` needs columns name_de and weight (weight of the year next to the link). Returns
    (pos_nos as text, rule, similarity); pos_nos = "" -> resolve in data/meta/item_mapping_overrides.csv.
    """
    if pos_no in target.index:
        t = target.loc[pos_no]
        s = name_similarity(name, t.name_de)
        if s >= same_no_min or words_contained(name, t.name_de) or (s == 0 and weight_close(weight, t.weight)):
            return str(pos_no), "same_no", round(s, 2)
    sims = target["name_de"].map(lambda n: name_similarity(name, n))
    ok = (sims >= name_min) | (target["name_de"].map(lambda n: words_contained(name, n))
                               & target["weight"].map(lambda w: weight_close(weight, w)))
    if ok.any():
        best = sims[ok].idxmax()
        return str(int(best)), "name", round(float(sims[best]), 2)
    return "", "unmatched", round(float(sims.max()) if len(sims) else 0.0, 2)


def basket_weight(sheet: str, newer_than_paper: bool) -> pd.Series:
    """Weights of one basket in the year next to the paper basket: first year if newer, last year if older."""
    w = load_weights().query("basket == @sheet")
    year = w.year.min() if newer_than_paper else w.year.max()
    w = w[w.year == year].drop_duplicates("pos_no")  # first occurrence = basket position (D-18)
    return w.set_index("pos_no")["weight"]


def build_mapping(overrides: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build items table (one row per paper item) and the long mapping item x basket -> positions.

    `overrides` (columns item_no, base, pos_nos, note) replaces the automatic choice; pos_nos may list several
    children separated by ';' (rebuilt with weights) or be 'none' (item not in that basket).
    """
    if overrides is None:
        overrides = pd.read_csv(META / "item_mapping_overrides.csv", dtype={"pos_nos": str})
    t9 = pd.read_csv(META / "items_paper_table9.csv")
    w = load_weights()
    w05 = w[(w.basket == "LIK2005") & (w.year == PAPER_WEIGHT_YEAR)].set_index("pos_no")["weight"]
    _, pos05 = load_basket(PAPER_BASKET)
    t9["pos05"] = match_table9_to_basket(t9, pos05, w05)
    t9["rule05"] = np.where(t9["pos05"].notna(), "weight", "unmatched")
    # Overrides of the 2005 position fix the item's identity, so apply them before the crosswalk
    ov05 = overrides[overrides.base == PAPER_BASKET].set_index("item_no")["pos_nos"]
    t9.loc[t9.item_no.isin(ov05.index), "pos05"] = t9["item_no"].map(ov05).astype(float)
    w_old = load_weights().query("basket == 'LIK2005'")
    w05_first = basket_weight("LIK2005", newer_than_paper=True)
    paper_i = [c for c, _, _ in BASKETS].index(PAPER_BASKET)

    rows = []
    for _, it in t9.iterrows():
        for k, (code, sheet, _start) in enumerate(BASKETS):
            _, pos = load_basket(code)
            if code == PAPER_BASKET:
                p, rule, sim = ("" if pd.isna(it.pos05) else str(int(it.pos05))), it.rule05, 1.0
            elif pd.isna(it.pos05):
                p, rule, sim = "", "unmatched", 0.0
            else:
                newer = k > paper_i
                target = pos.join(basket_weight(sheet, newer).rename("weight"))
                w_item = (w05 if newer else w05_first).get(int(it.pos05), np.nan)
                p, rule, sim = crosswalk_position(int(it.pos05), pos05.loc[int(it.pos05), "name_de"], w_item, target)
            rows.append({"item_no": it.item_no, "base": code, "pos_nos": p, "rule": rule, "similarity": sim})
    m = pd.DataFrame(rows)

    # Hand overrides win (reviewed in data/meta/item_mapping_overrides.csv)
    ov = overrides.set_index(["item_no", "base"])
    for k, r in ov.iterrows():
        sel = (m.item_no == k[0]) & (m.base == k[1])
        m.loc[sel, ["pos_nos", "rule"]] = ["" if r.pos_nos == "none" else r.pos_nos, "override"]
    # The 2005 position fixes the item's identity: refresh it after overrides
    p05 = m[m.base == PAPER_BASKET].set_index("item_no")["pos_nos"]
    t9["pos05"] = t9["item_no"].map(p05)

    # Add names of the mapped positions for review
    def names(r):
        _, pos = load_basket(r.base)
        return " + ".join(pos.loc[int(p), "name_de"] for p in r.pos_nos.split(";") if p and int(p) in pos.index)
    m["name_de"] = m.apply(names, axis=1)
    m["item_id"] = m["item_no"].map(lambda n: f"i{n:03d}")
    t9["item_id"] = t9["item_no"].map(lambda n: f"i{n:03d}")
    return t9, m


# ---------------------------------------------------------------------------
# Step 3: item index per basket (own period) and chain-linking
# ---------------------------------------------------------------------------
def weight_segments(sheet: str, start: str, end: pd.Timestamp) -> list[tuple[int, pd.Timestamp, pd.Timestamp]]:
    """Weight periods of one basket: (weight year, segment start month, segment end month).

    Chained Laspeyres: weight of year y applies from the December of y-1 (the price base) to December of y.
    The first weight year starts at the basket's base month (e.g. May 2000 for weight "2000/01") and the last
    one runs to the end of the basket's own period.
    """
    years = sorted(load_weights().query("basket == @sheet")["year"].unique())
    starts = [pd.Timestamp(start)] + [pd.Timestamp(f"{y - 1}-12-01") for y in years[1:]]
    ends = starts[1:] + [end]
    return list(zip(years, starts, ends))


def combine_children(wide: pd.DataFrame, children: list[int], sheet: str, start: str) -> pd.Series:
    """Rebuild a parent index from child indices with the basket's annual weights (chained Laspeyres, D-23).

    Within each weight year: parent_t / parent_link = sum_i w_i (I_i,t / I_i,link) / sum_i w_i.
    """
    w = load_weights().query("basket == @sheet")
    sub = wide[children].dropna(how="all")
    out = pd.Series(np.nan, index=sub.index)
    level = 1.0
    for year, s0, s1 in weight_segments(sheet, start, sub.index.max()):
        wy = w[(w.year == year) & w.pos_no.isin(children)].set_index("pos_no")["weight"].reindex(children)
        seg = sub.loc[(sub.index >= s0) & (sub.index <= s1)]
        if seg.empty or s0 not in sub.index:
            continue
        rel = seg / sub.loc[s0]
        ok = wy.notna() & rel.loc[s0].notna()
        val = level * (rel.loc[:, ok] * wy[ok]).sum(axis=1) / wy[ok].sum()
        out.loc[seg.index] = val
        level = val.iloc[-1]
    return out


def basket_series(code: str, pos_nos: str, sheet: str, start: str) -> pd.Series:
    """Index of one item within one basket file, restricted to the basket's own period (from its base month)."""
    wide, _ = load_basket(code)
    nos = [int(p) for p in pos_nos.split(";") if p]
    nos = [p for p in nos if p in wide.columns]
    if not nos:
        return pd.Series(dtype=float)
    s = wide[nos[0]] if len(nos) == 1 else combine_children(wide, nos, sheet, start)
    return s[s.index >= pd.Timestamp(start)].dropna()


def chain_link(old: pd.Series, new: pd.Series, link_month: pd.Timestamp) -> pd.Series:
    """Join an item index across two CPI bases at the overlap month (D-24).

    I_linked_t = I_new_t * (I_old_link / I_new_link) for t after the link month; before it the old series.
    If the old series is empty (item new in this basket), the new series is returned unchanged.
    """
    link_month = pd.Timestamp(link_month)
    if old.empty:
        return new.copy()
    if new.empty:
        return old.copy()
    if link_month not in old.index or link_month not in new.index:
        raise ValueError(f"link month {link_month:%Y-%m} missing in one of the series")
    factor = old.loc[link_month] / new.loc[link_month]
    return pd.concat([old[old.index <= link_month], new[new.index > link_month] * factor])


def link_item(mapping_item: pd.DataFrame) -> tuple[pd.Series, list[str]]:
    """Chain-link one item over all baskets. Returns the linked index and notes (breaks, gaps).

    If an item is missing in a basket, the history stops (an item cannot be linked over a gap): we keep the
    longest stretch that reaches the paper basket (2005) and note the break.
    """
    by_base = mapping_item.set_index("base")["pos_nos"]
    pieces, notes = [], []
    for code, sheet, start in BASKETS:
        p = by_base.get(code, "")
        pieces.append((code, start, basket_series(code, p, sheet, start) if p else pd.Series(dtype=float)))

    i05 = [c for c, _, _ in pieces].index(PAPER_BASKET)
    linked = pieces[i05][2]
    for code, start, s in pieces[i05 + 1:]:          # forwards
        if s.empty:
            notes.append(f"ends before {code}")
            break
        linked = chain_link(linked, s, pd.Timestamp(start))
    first_start = pd.Timestamp(pieces[i05][1])
    for k in range(i05 - 1, -1, -1):                  # backwards: link older basket at the newer basket's start
        code, start, s = pieces[k]
        if s.empty or first_start not in s.index:
            notes.append(f"starts at {first_start:%Y-%m} (no link to {code})")
            break
        factor = linked.loc[first_start] / s.loc[first_start]
        linked = pd.concat([s[s.index < first_start] * factor, linked[linked.index >= first_start]])
        first_start = pd.Timestamp(start)
    return linked.sort_index(), notes


def build_panel(mapping: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Linked index per item, rescaled to 100 in REFERENCE_MONTH, plus a link report (one row per item)."""
    out, report = [], []
    ref = pd.Timestamp(REFERENCE_MONTH)
    for item_id, g in mapping.groupby("item_id"):
        s, notes = link_item(g)
        if s.empty:
            report.append({"item_id": item_id, "first_obs": pd.NaT, "last_obs": pd.NaT, "notes": "no data"})
            continue
        if ref in s.index:
            s = 100 * s / s.loc[ref]
        out.append(pd.DataFrame({"date": s.index, "item_id": item_id, "index": s.values}))
        report.append({"item_id": item_id, "first_obs": s.index.min(), "last_obs": s.index.max(),
                       "notes": "; ".join(notes)})
    panel = pd.concat(out, ignore_index=True)
    panel["log_p"] = np.log(panel["index"])
    return panel, pd.DataFrame(report)


def link_jumps(panel: pd.DataFrame, threshold: float = 0.20) -> pd.DataFrame:
    """Suspicious changes in the month after a basket link (check for wrong links).

    Clothing sales (January) and fresh fruit/vegetables move by more than 20 % every year, so we compare the
    change after the link with the item's median change in the same calendar month of all years and flag the
    link if the difference exceeds `threshold` (log points).
    """
    months = [pd.Timestamp(s) for _, _, s in BASKETS[1:]]
    after = {m + pd.offsets.MonthBegin(1) for m in months}
    p = panel.sort_values(["item_id", "date"]).copy()
    p["dlog"] = p.groupby("item_id")["log_p"].diff()
    p["typical"] = p.groupby(["item_id", p["date"].dt.month])["dlog"].transform("median")
    p["excess"] = p["dlog"] - p["typical"]
    return p[p["date"].isin(after) & (p["excess"].abs() > threshold)]


RENUMBERED = {"LIK93B93": ("LIK15B15", "2000-05-01"), "LIK25B25": (None, "2025-12-01")}
MIN_DYNAMICS_CORR = 0.9


def refine_renumbered(mapping: pd.DataFrame, panel_wo: pd.DataFrame, months: int = 24) -> pd.DataFrame:
    """Choose links into the renumbered baskets (1993, 2025) by name AND price dynamics (D-25).

    Position numbers of these baskets differ from 2000-2020, and names repeat (wine in shops vs restaurants),
    so a name alone is not enough. Candidates are positions whose name is similar (ratio >= 0.85 or contained
    words); among them we keep the one whose monthly log changes over the `months` before the link correlate
    best with the item's own changes, and only if that correlation is >= MIN_DYNAMICS_CORR. Otherwise the item
    is not linked into that basket (it starts May 2000, or ends Dec 2025): "1:1 matches only".

    Reference dynamics: 2025 -> our linked series (panel built without the 2025 basket);
    1993 -> the BFS 2015 file's back-cast of the item's 2015 position (the only source covering 1998-2000).
    Hand overrides (rule == "override") are kept.
    """
    m = mapping.copy()
    names05 = m[m.base == PAPER_BASKET].set_index("item_id")["name_de"]
    ours = panel_wo.pivot(index="date", columns="item_id", values="log_p")
    for code, (ref_code, link) in RENUMBERED.items():
        t1 = pd.Timestamp(link)
        t0 = t1 - pd.DateOffset(months=months)
        wide, pos = load_basket(code)
        ref_wide = load_basket(ref_code)[0] if ref_code else None
        for i in m.index[(m.base == code) & (m.rule != "override")]:
            item = m.at[i, "item_id"]
            if ref_code:
                p15 = m[(m.item_id == item) & (m.base == ref_code)]["pos_nos"].iloc[0]
                nos = [int(x) for x in str(p15).split(";") if x and x != "nan"]
                if len(nos) != 1 or nos[0] not in ref_wide.columns:
                    m.loc[i, ["pos_nos", "rule", "similarity"]] = ["", "unmatched", 0.0]
                    continue
                ref = np.log(ref_wide[nos[0]]).loc[t0:t1].diff()
            else:
                if item not in ours.columns:
                    continue
                ref = ours[item].loc[t0:t1].diff()
            name = names05.get(item, "")
            cand = [n for n, nm in pos["name_de"].items()
                    if name_similarity(name, nm) >= 0.85 or words_contained(name, nm)]
            best, best_c = "", -1.0
            for n in cand:
                if n not in wide.columns:
                    continue
                x = np.log(wide[n]).loc[t0:t1].diff()
                both = pd.concat([ref, x], axis=1).dropna()
                if len(both) < months // 2 or both.std().min() == 0:
                    continue
                c = both.iloc[:, 0].corr(both.iloc[:, 1])
                if c > best_c:
                    best, best_c = str(n), c
            if best and best_c >= MIN_DYNAMICS_CORR:
                m.loc[i, ["pos_nos", "rule", "similarity"]] = [best, "name+dynamics", round(best_c, 3)]
            else:
                m.loc[i, ["pos_nos", "rule", "similarity"]] = ["", "unmatched", round(max(best_c, 0), 3)]
        _, pos = load_basket(code)
        sel = m.base == code
        m.loc[sel, "name_de"] = m.loc[sel, "pos_nos"].map(
            lambda v: " + ".join(pos.loc[int(x), "name_de"] for x in str(v).split(";") if x and x != "nan"))
    return m


def backcast_agreement(mapping: pd.DataFrame, panel: pd.DataFrame, months: int = 24) -> pd.DataFrame:
    """Check the item mapping against BFS back-casts (validation only, not used for the panel, D-24).

    Ratio-linking never creates a level jump, so a wrong link shows up as different *dynamics*. Newer BFS files
    (2010 basket on) also contain their positions back in time. For each item and link month we compare our
    linked monthly log changes over the `months` before the link with the newer file's back-cast of the mapped
    position(s): correlation and mean absolute difference (in log points). For the 1993 link the 2015 file's
    back-cast is used. Single-position mappings only; merged items are skipped.
    """
    rows = []
    p = panel.pivot(index="date", columns="item_id", values="log_p")
    checks = [(code, start, code) for code, _, start in BASKETS[3:]] + [("LIK93B93", "2000-05-01", "LIK15B15")]
    for code, start, ref_code in checks:
        wide, _ = load_basket(ref_code)
        t1 = pd.Timestamp(start)
        t0 = t1 - pd.DateOffset(months=months)
        sub = mapping[mapping.base == (code if code != "LIK93B93" else "LIK15B15")]
        for _, r in sub.iterrows():
            nos = [int(x) for x in str(r.pos_nos).split(";") if x and x != "nan"]
            if len(nos) != 1 or nos[0] not in wide.columns or r.item_id not in p.columns:
                continue
            ours = p[r.item_id].loc[t0:t1].diff().dropna()
            ref = np.log(wide[nos[0]]).loc[t0:t1].diff().dropna()
            both = pd.concat([ours, ref], axis=1, keys=["ours", "ref"]).dropna()
            if len(both) < months // 2:
                continue
            same = (both.ours - both.ref).abs()
            corr = both.ours.corr(both.ref) if both.std().min() > 0 else np.nan
            rows.append({"item_id": r.item_id, "link": start, "ref_file": ref_code, "n": len(both),
                         "corr": round(corr, 3), "mad": round(same.mean(), 4)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Step 4 (T1.5): annual weights per model item
# ---------------------------------------------------------------------------
def weight_years(sheet: str) -> dict[int, list[int]]:
    """Calendar years for which each BFS weight column of a basket is valid (D-26).

    Weights of year y hold from December of y-1 (the price base) through December of y, i.e. they steer
    the index in Jan-Dec of y. Exceptions: the 1993 basket has one weight column for 1993-1999, and the
    2000 basket's column "2000/01" (stored as 2000) covers 2000 and 2001 (link month May 2000).
    """
    years = sorted(load_weights().query("basket == @sheet")["year"].unique())
    if sheet == "LIK1993":
        return {1993: list(range(1993, 2000))}
    if sheet == "LIK2000":
        return {y: ([2000, 2001] if y == 2000 else [y]) for y in years}
    return {y: [y] for y in years}


def item_weights(mapping: pd.DataFrame) -> pd.DataFrame:
    """Weights per model item and calendar year from the BFS GEWICHTUNGEN file (D-26).

    Item weight = sum of the weights of its BFS position(s) in that basket (split items: children summed).
    If one position carries several model items (women's coats + jackets from 2016), its weight is split
    by the items' shares in the last year with separate weights (D-27).
    Items without a position in a basket get no row for those years (coverage then falls below 2010's 92.8).
    Returns long frame: year, item_id, weight (BFS units, full basket = 100; not normalised).
    """
    w = load_weights().drop_duplicates(["basket", "pos_no", "year"])  # first occurrence = basket position (D-18)
    code_to_sheet = {c: s for c, s, _ in BASKETS}
    rows = []
    for _, r in mapping.iterrows():
        if pd.isna(r.pos_nos) or str(r.pos_nos) == "":
            continue
        sheet = code_to_sheet[r.base]
        nos = [int(float(p)) for p in str(r.pos_nos).split(";")]
        wb = w[(w.basket == sheet) & w.pos_no.isin(nos)]
        for wy, g in wb.groupby("year"):
            for y in weight_years(sheet)[wy]:
                rows.append({"year": y, "item_id": r.item_id, "pos_key": f"{sheet}:{r.pos_nos}",
                             "weight": g["weight"].sum()})
    out = pd.DataFrame(rows)

    # D-27: a position shared by several items -> split by the items' last separate weights
    n_items = out.groupby(["year", "pos_key"])["item_id"].transform("nunique")
    for (year, _key), g in out[n_items > 1].groupby(["year", "pos_key"]):
        ids = g["item_id"].tolist()
        sep = out[out.item_id.isin(ids) & (n_items == 1) & (out.year < year)]
        last = sep[sep.year == sep.year.max()].set_index("item_id")["weight"].reindex(ids)
        share = last / last.sum()
        out.loc[g.index, "weight"] = g["weight"] * g["item_id"].map(share)
    return out.drop(columns="pos_key").sort_values(["year", "item_id"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 5 (T1.5): collection calendar (official from the paper + inferred from the data)
# ---------------------------------------------------------------------------
def infer_collection(log_p: pd.Series, tol: float = NO_COLLECTION_TOL) -> pd.Series:
    """Flag months where the price was collected: |change in log price| >= tol (paper fn. 9).

    A flat month is read as "not collected" (price carried forward, AGENTS.md §7). The first observation has
    no change and is returned as NaN (unknown).
    """
    d = log_p.diff().abs()
    return (d >= tol).where(d.notna())


def _calendar_years(period: str, last_year: int) -> list[int]:
    """Years covered by a paper calendar table ("2000-2005", ..., "2011-" = 2011..last_year, D-28)."""
    a, _, b = period.partition("-")
    return list(range(int(a), (int(b) if b else last_year) + 1))


def _division(items: pd.DataFrame) -> pd.Series:
    """COICOP division (group label of the paper's calendar tables) per item, derived from agg14."""
    div = items["agg14"].str.replace(r" \(excl\..*\)$", "", regex=True).replace({"Rents": "Housing and energy"})
    div[items["item_id"] == "i100"] = "Housing and energy"   # heating oil
    div[items["item_id"] == "i130"] = "Transport"            # fuels
    return div.str[:20]   # the Furnishings label is worded differently after 20 characters


def official_calendar(items: pd.DataFrame, last_year: int) -> pd.DataFrame:
    """Official collection months per item and month from paper Tables 5-8 (D-28).

    Item rows (mapped to model items in data/meta/collection_calendar_items.csv) override the group row of
    the item's COICOP division; several item rows for one item are combined (union of months).
    'aperiodic'/'seasonal' have no fixed months: collected = NaN and `pattern` keeps the label.
    Starts May 2000 (Table 5 belongs to the May 2000 basket). Returns: date, item_id, collected, pattern.
    """
    cal = pd.read_csv(META / "collection_calendar_paper.csv")
    cal["group"] = cal["group"].str.replace("\n", " ").str[:20]
    cal["item"] = cal["item"].str.replace("\n", " ")
    cmap = pd.read_csv(META / "collection_calendar_items.csv").dropna(subset=["item_ids"])
    cmap = {r.calendar_item: r.item_ids.split(";") for r in cmap.itertuples()}
    div = dict(zip(items["item_id"], _division(items)))

    spec: dict[tuple[str, int], tuple[str, str]] = {}   # (item_id, year) -> (months, "group"/"item")
    for r in cal[cal.level == "group"].itertuples():
        for y in _calendar_years(r.period, last_year):
            for i, d in div.items():
                if d == r.group:
                    spec[(i, y)] = (r.months, "group")
    for r in cal[cal.level == "item"].itertuples():
        for y in _calendar_years(r.period, last_year):
            for i in cmap.get(r.item, []):
                old, lvl = spec.get((i, y), ("", ""))
                months = r.months
                if lvl == "item" and old[:1].isdigit() and months[:1].isdigit():
                    months = ";".join(sorted(set(old.split(";")) | set(months.split(";")), key=int))
                spec[(i, y)] = (months, "item")

    rows = []
    for (i, y), (m, _lvl) in spec.items():
        fixed = m[:1].isdigit()
        months = {int(x) for x in m.split(";")} if fixed else set()
        for mo in range(1, 13):
            date = pd.Timestamp(year=y, month=mo, day=1)
            if date >= pd.Timestamp("2000-05-01"):
                rows.append({"date": date, "item_id": i,
                             "collected": (mo in months) if fixed else np.nan, "pattern": m})
    return pd.DataFrame(rows).sort_values(["item_id", "date"]).reset_index(drop=True)


def collection_pattern(collection: pd.DataFrame, item_id: str, origin) -> list[int]:
    """Months (1-12) in which an item was collected in the calendar year BEFORE the origin's year.

    Real-time rule of the paper (pp. 14-15): at `origin` the forecaster knows the collection pattern only from
    the previous complete year. Uses the inferred flags (source 'inferred').
    """
    origin = pd.Timestamp(origin)
    c = collection[(collection.item_id == item_id) & (collection.source == "inferred")]
    prev = c[pd.to_datetime(c.date).dt.year == origin.year - 1]
    return sorted(pd.to_datetime(prev.loc[prev.collected == True, "date"]).dt.month.tolist())  # noqa: E712
