"""One-off generator of data/meta/agg6_rules.csv (D-21 rev.): hand rules for product type and origin per item.

Kept as code so the rules are reviewable; the CSV is the tracked, hand-maintained source afterwards.
type: goods / private / public (services). origin: domestic / imported / data (= decided by the regression).
"""
import pandas as pd
items = pd.read_csv("data/final/items.csv")
n = lambda *ids: set(ids)

PRIVATE = n(88, 89, 93, 95, 97, 120, 121, 122, 131, 132, 135, 138, 144, *range(149, 154), 155, 156, 161,
            *range(163, 175))
PUBLIC = n(123, 133, 134, 136, 154, 162)   # hospitals, public transport, post, licences, education
IMPORTED = n(1, 32, 29, 51, 52, 53, 60, 62, 63, 98, 125, 126, 127, 128, 129, 137, 139, 140, 141, 142, 143, 161,
             *range(67, 88), 90, 91, 92, 109, 110, 113, 180)
DOMESTIC = n(3, 4, 5, 9, 10, 11, 12, 13, 15, 20, 21, 22, 23, 24, 25, 26, 27, 41, 59, 61, 64, 65, 99, 101,
             158, 159, 181) | PRIVATE - {161} | PUBLIC
WHY = {
    "type_private": "service (COICOP), market price",
    "type_public": "service with public/administered provider (hospital, public transport, post, licence, education)",
    "type_goods": "good (COICOP)",
    "imported": "mostly imported in Switzerland (no or little domestic production: tropical products, foreign wine, "
                "vehicles, electronics, clothing/footwear, natural gas, package holidays abroad)",
    "domestic": "domestic production or domestic service (Swiss agriculture under border protection, Swiss wine, "
                "beer, cigarettes, electricity, newspapers, watches; all services except package holidays)",
    "data": "mixed or unclear origin -> decided by the regression on BFS group series",
}
rows = []
for r in items.itertuples():
    i = int(r.item_id[1:])
    t = "public" if i in PUBLIC else "private" if i in PRIVATE else "goods"
    o = "imported" if i in IMPORTED else "domestic" if i in DOMESTIC else "data"
    if r.special in ("oil", "rent"):
        t, o = ("goods", "imported") if r.special == "oil" else ("private", "domestic")
    rows.append({"item_id": r.item_id, "name_de": r.name_de, "type": t, "origin": o,
                 "reason": f"{WHY['type_' + t]}; {WHY[o]}"})
out = pd.DataFrame(rows)
out.to_csv("data/meta/agg6_rules.csv", index=False)
print(out.groupby(["type", "origin"]).size())
