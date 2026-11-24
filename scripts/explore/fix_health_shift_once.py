"""One-off fix (T1.5): paper Table 9 prints the weights of health items 119-124 one row off (the 0.046 of
'Medical products' = BFS Sanitaetsmaterial appears at 'Hospital services'). Remap these items by name in
item_mapping_overrides.csv and move their agg6 rule rows (keyed by German name) with the positions."""
import pandas as pd

o = pd.read_csv("data/meta/item_mapping_overrides.csv", dtype=str)
o = o[~(o.item_no.isin([str(n) for n in range(119, 125)]) & (o.base == "LIK05B05"))]
new = {119: (6070, "Sanitätsmaterial"), 120: (6016, "Medizinische Apparate und Geräte"),
       121: (6031, "Ärztliche Leistungen"), 122: (6036, "Zahnärztliche Leistungen"),
       123: (6051, "Andere Gesundheitsleistungen"), 124: (6059, "Spitalleistungen")}
rows = [dict(item_no=str(k), base="LIK05B05", pos_nos=str(p), note=f"{n}: paper Table 9 prints the health "
             "weights of items 119-124 one row off (p. 59); matched by name (T1.5)") for k, (p, n) in new.items()]
pd.concat([o, pd.DataFrame(rows)]).to_csv("data/meta/item_mapping_overrides.csv", index=False)

r = pd.read_csv("data/meta/agg6_rules.csv")
by_name = r.set_index("name_de")
for k, (_, n) in new.items():
    src = by_name.loc[n]
    r.loc[r.item_id == f"i{k:03d}", ["name_de", "type", "origin", "reason"]] = [n, src.type, src.origin, src.reason]
r.to_csv("data/meta/agg6_rules.csv", index=False)
