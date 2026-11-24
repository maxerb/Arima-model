"""Item panel: chain-linking across CPI bases, item mapping, weights and collection calendar (T1.4-T1.5).

Skill: snb-arima-cpi-panel.
"""

import numpy as np
import pandas as pd

from arima_snb.config import NO_COLLECTION_TOL


def chain_link(old: pd.Series, new: pd.Series, link_month: pd.Timestamp) -> pd.Series:
    """Join an item index across two CPI bases at the overlap month."""
    raise NotImplementedError("T1.4-T1.5")


def infer_collection(log_p: pd.Series, tol: float = NO_COLLECTION_TOL) -> pd.Series:
    """Flag months where the price was collected: |change in log price| >= tol (paper fn. 9)."""
    raise NotImplementedError("T1.4-T1.5")
