"""Explore (D-21): special series 111-119 in the 2010-2025 files and their weights in GEWICHTUNGEN."""
from arima_snb import panel
w = panel.load_weights()
for b, sh, _ in panel.BASKETS[3:]:
    wide, pos = panel.load_basket(b)
    sel = pos.index[(pos.index >= 111) & (pos.index <= 119)]
    print(b, pos.loc[sel, "name_de"].to_dict())
    print("  weights:", w[(w.basket == sh) & w.pos_no.isin(sel)].groupby("pos_no").weight.first().to_dict())
    print("  data from", wide[sel].dropna(how="all").index.min() if len(sel) else None)
