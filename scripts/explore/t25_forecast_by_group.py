"""T2.5 exploration: aggregated forecast vs re-aggregated actual by ARIMA(6) group and horizon, one origin."""
import sys
import pandas as pd
from arima_snb import aggregate
from arima_snb.config import FINAL, FORECASTS

origin = pd.Timestamp(sys.argv[1] if len(sys.argv) > 1 else "2004-02-01")
long = pd.read_csv(FINAL / "cpi_items_long.csv", parse_dates=["date"])
weights = pd.read_csv(FINAL / "weights.csv")
items = pd.read_csv(FINAL / "items.csv")
wide = long.pivot(index="date", columns="item_id", values="index").asfreq("MS")
q = pd.read_csv(FORECASTS / "arima182_quarterly.csv")
q = q[pd.to_datetime(q.origin) == origin]
groups = aggregate.aggregate_groups(items)
rows = []
for name in ["total", "excl_oil"] + [g for g in groups if g.startswith("agg6")]:
    act = aggregate.quarterly_yoy(aggregate.aggregate_index(wide, weights, groups[name]))
    f = q[q["aggregate"] == name].set_index("h").pi_hat
    rows.append(dict(aggregate=name[:40], **{f"h{h}": f"{f[h]:5.2f}/{act[pd.Period(t)]:5.2f}"
                                             for h, t in zip(q[q['aggregate'] == name].h, q[q['aggregate'] == name].target_q)}))
print("forecast/actual quarterly y-o-y, origin", origin.date())
print(pd.DataFrame(rows).to_string(index=False))
