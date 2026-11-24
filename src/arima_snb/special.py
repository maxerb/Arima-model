"""Special models: oil-products error-correction model and rent model (T2.3-T2.4).

Skill: snb-arima-oil-rent.
"""

import numpy as np
import pandas as pd


def forecast_oil_item(log_p: pd.Series, crude_chf: pd.Series, origin: pd.Timestamp, steps: int) -> pd.DataFrame:
    """ECM forecast for heating oil, petrol or diesel (paper p. 7)."""
    raise NotImplementedError("T2.3-T2.4")


def forecast_rent(log_rent: pd.Series, mortgage_rate: pd.Series, origin: pd.Timestamp, steps: int) -> pd.DataFrame:
    """Quarterly rent model with lagged positive/negative mortgage-rate changes (paper pp. 7-8)."""
    raise NotImplementedError("T2.3-T2.4")
