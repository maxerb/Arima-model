"""Per-item ARIMA models with SIC lag selection and ad-hoc fallbacks (T2.2).

Skill: snb-arima-item-models.
"""

import numpy as np
import pandas as pd


def sic(sse: float, n_obs: int, n_params: int) -> float:
    """Schwarz criterion as in the paper, eq. (3): log(SSE/T) + k*log(T)/T."""
    return float(np.log(sse / n_obs) + n_params * np.log(n_obs) / n_obs)


def forecast_item(log_p: pd.Series, spec: pd.Series, origin: pd.Timestamp, steps: int) -> pd.DataFrame:
    """Forecast one item's log price `steps` months after `origin`, using data up to `origin` only."""
    raise NotImplementedError("T2.2")
