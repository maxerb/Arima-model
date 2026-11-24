"""Aggregation of item indices to CPI and sub-aggregates; quarterly y-o-y inflation (T1.6, T2.5).

Skill: snb-arima-aggregate.
"""

import numpy as np
import pandas as pd


def aggregate_index(item_log_p: pd.DataFrame, weights: pd.DataFrame) -> pd.Series:
    """Chained Laspeyres aggregate with base December of the previous year (AGENTS.md §7)."""
    raise NotImplementedError("T1.6, T2.5")


def quarterly_yoy(index_m: pd.Series) -> pd.Series:
    """Year-on-year % change of the quarterly average of a monthly index."""
    q = index_m.resample("QS").mean()
    q.index = q.index.to_period("Q")
    return 100 * (q / q.shift(4) - 1)
