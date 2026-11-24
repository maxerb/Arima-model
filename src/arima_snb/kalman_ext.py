"""Collection-frequency extension: state-space model with missing monthly prices (T4.1).

Skill: snb-arima-kalman-extension.
"""

import numpy as np
import pandas as pd


def fit_collection_model(log_p: pd.Series, collected: pd.Series, p: int, seasonal: bool):
    """Fit the latent monthly AR model on log levels observed only in collection months."""
    raise NotImplementedError("T4.1")
