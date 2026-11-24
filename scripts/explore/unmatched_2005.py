"""Explore (T1.4): LIK2005 positions around the Table 9 items not matched by weight."""
from arima_snb import panel
w = panel.load_weights(); w05 = w[(w.basket=="LIK2005")&(w.year==2010)].set_index("pos_no").weight
_, p = panel.load_basket("LIK05B05"); p = p.join(w05)
for lo, hi in [(3060, 3110), (3180, 3240), (6000, 6080), (1060, 1080), (12120, 12135), (9470, 9495), (7200, 7225)]:
    print(p[(p.index>=lo)&(p.index<=hi)][["level","name_de","weight"]].to_string(header=False)); print("--")
_, p0 = panel.load_basket("LIK00B00"); print(p0.loc[[1076,1170,1218,1530,2003,7210,9475,9490,12129]].to_string())
