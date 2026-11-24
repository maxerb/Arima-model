"""Item diagnostics: unit-root tests, seasonality, collection frequency -> item_specs.csv (T2.1).

Skill: snb-arima-item-diagnostics.
"""

import numpy as np
import pandas as pd


def diagnose_item(log_p: pd.Series, vintage: pd.Timestamp) -> dict:
    """ADF/KPSS, lag-12 seasonality and collection frequency for one item, using data up to `vintage` only."""
    raise NotImplementedError("T2.1")
