"""T1.3: build data/meta/ tables from the paper's appendix (Huwiler & Kaufmann 2013, PDF pp. 19-27).

1. Table 9 (App. B, PDF pp. 23-27): the ARIMA(6), ARIMA(14) sub-aggregates and the 182 model items with 2010
   weights are read from the PDF text layer (no hand-typing of 200 numbers) and written to
   - data/meta/paper_table9_subaggregates.csv  (model, subaggregate, weight_2010)
   - data/meta/items_paper_table9.csv          (item_no, item_en, weight_2010, agg6, agg14)
   agg14 follows from the item order (the list runs through the COICOP main groups, oil products and rents are
   split out as in the ARIMA(14) rows). agg6 cannot be derived from the paper (it lists no item -> agg6 map) and
   is left empty; it is filled from BFS codes in T1.4 (decision D-21).
2. Tables 5-8 (App. A): the collection calendars were transcribed by hand from rendered page images
   (scripts/explore/render_paper_pages.py) into data/meta/collection_calendar_paper.csv, because the 'x' marks
   have no usable column position in the text layer. This script cross-checks that file: per table, the number
   of collection months must equal the number of 'x' marks in the PDF text layer.

Checks (paper p. 21-25): 182 items, item weights sum to 92.788, ARIMA(6) and ARIMA(14) weights sum to 100.000.
"""

import re

import pandas as pd
import pypdf

from arima_snb.config import META, RAW

NUM = re.compile(r"^(.*\S)\s+(\d+\.\d{3})$")

# First item of each ARIMA(14) group in Table 9 order; oil products and rents are single items placed inside
# their COICOP group, so they are mapped explicitly below.
AGG14_START = {
    "Rice": "Food and non-alcoholic beverages",
    "Spirits and brandies": "Alcoholic beverages and tobacco",
    "Coats and jackets (Men)": "Clothing and footwear",
    "Rental of garages and parking spaces": "Housing and energy (excl. oil products and rents)",
    "Furniture for living room": "Furnishings, household equipment and routine maintenance of the house",
    "Medicines": "Health",
    "New cars": "Transport (excl. oil products)",
    "Postal services": "Communication",
    "TV and audiovisual appliances": "Recreation and culture",
    "Education": "Education",
    "Meals taken in restaurants and cafés": "Restaurants and hotels",
    "Hairdressing establishments": "Miscellaneous goods and services",
}
AGG14_SPECIAL = {"Rents": "Rents", "Heating oil": "Oil products", "Fuels": "Oil products"}


def paper_pdf():
    files = sorted(RAW.glob("economic_studies_2013_07_*.pdf"))
    assert files, "paper PDF missing: run scripts/00_download_paper.py"
    return pypdf.PdfReader(files[-1])


def table9_lines(reader) -> list[str]:
    """Text lines of Table 9 (PDF pp. 23-27), wrapped names re-joined, headers/footers dropped."""
    text = "\n".join(reader.pages[i].extract_text() for i in range(22, 27))
    text = text.split("Table 9: ")[1].split("Source: SFSO, authors")[0]
    out, carry = [], ""
    for raw in text.splitlines():
        line = raw.replace("ﬁ", "fi").replace("mainte -", "mainte-").strip()
        if not line or line.startswith(("Model Sub-aggregates", "Table 9 continued", "Table 8 continued")) or line.isdigit():
            continue
        line = (carry + " " + line).strip() if carry else line
        if NUM.match(line) or re.fullmatch(r"\d+\.\d{3}", line):
            out.append(line.replace("mainte- nance", "maintenance"))
            carry = ""
        else:
            carry = line
    return out


def parse_table9(lines):
    subagg, items, model = [], [], None
    for line in lines:
        m = re.match(r"^ARIMA \((\d+)\)\s+(.*)$", line)
        if m:
            model, line = f"ARIMA({m.group(1)})", m.group(2)
        nm = NUM.match(line)
        if nm is None:  # bare total line, e.g. '100.000' or '92.788'
            subagg.append((model, "TOTAL", float(line)))
            continue
        name, w = nm.group(1), float(nm.group(2))
        (items.append((name, w)) if model == "ARIMA(182)" else subagg.append((model, name, w)))
    sub = pd.DataFrame(subagg, columns=["model", "subaggregate", "weight_2010"])
    it = pd.DataFrame(items, columns=["item_en", "weight_2010"])
    it.insert(0, "item_no", range(1, len(it) + 1))
    group = it["item_en"].map(AGG14_START).ffill()
    it["agg6"] = ""  # D-21: not in the paper, filled in T1.4 from BFS codes
    it["agg14"] = it["item_en"].map(AGG14_SPECIAL).fillna(group)
    return sub, it


def check_table9(sub, it):
    assert len(it) == 182, len(it)
    assert round(it["weight_2010"].sum(), 3) == 92.788, it["weight_2010"].sum()
    for model in ["ARIMA(6)", "ARIMA(14)"]:
        s = sub[(sub.model == model) & (sub.subaggregate != "TOTAL")]["weight_2010"].sum()
        assert round(s, 3) == 100.000, (model, s)
    assert round(sub.query("subaggregate == 'TOTAL' and model == 'ARIMA(182)'")["weight_2010"].iloc[0], 3) == 92.788
    # item weights per ARIMA(14) group can never exceed the group's total weight (182 items cover 92.8 %)
    tot = sub[sub.model == "ARIMA(14)"].set_index("subaggregate")["weight_2010"]
    by = it.groupby("agg14")["weight_2010"].sum()
    assert set(by.index) <= set(tot.index), set(by.index) - set(tot.index)
    assert (by <= tot[by.index] + 1e-9).all(), pd.concat([by, tot], axis=1)
    # Rents and oil products are complete in the 182 items
    for g in ["Rents", "Oil products"]:
        assert round(by[g], 3) == round(tot[g], 3), g
    print("Table 9 coverage per ARIMA(14) group (items / group weight):")
    print((by / tot[by.index]).round(3).to_string())


def check_calendar(reader):
    cal = pd.read_csv(META / "collection_calendar_paper.csv")
    pages = {5: [18], 6: [19], 7: [20], 8: [21, 22]}
    for table, idx in pages.items():
        text = "\n".join(reader.pages[i].extract_text() for i in idx)
        if table == 8:
            text = text.split("B Sub-aggregates")[0]
        n_pdf = len(re.findall(r"(?<![A-Za-z])x(?![A-Za-z])", text))
        m = cal.loc[cal.table == table, "months"]
        n_csv = int(m[~m.isin(["aperiodic", "seasonal"])].str.count(";").add(1).sum())
        assert n_pdf == n_csv, f"Table {table}: {n_pdf} x-marks in PDF vs {n_csv} months in CSV"
        print(f"Table {table}: {n_csv} collection marks match the PDF")


def main() -> None:
    reader = paper_pdf()
    sub, it = parse_table9(table9_lines(reader))
    check_table9(sub, it)
    sub.to_csv(META / "paper_table9_subaggregates.csv", index=False)
    it.to_csv(META / "items_paper_table9.csv", index=False)
    print(f"wrote {len(it)} items, sum {it.weight_2010.sum():.3f}")
    check_calendar(reader)


if __name__ == "__main__":
    main()
