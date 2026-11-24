"""Pseudo-out-of-sample evaluation: forecast loop, benchmarks, RMSFE, DMW test (T3.x, T4.2, T5.x).

Skill: snb-arima-evaluation.
"""

import numpy as np
import pandas as pd


def rmsfe(errors: pd.Series) -> float:
    """Root mean squared forecast error (paper p. 10)."""
    return float(np.sqrt(np.mean(np.square(errors))))


def dmw_test(e_bench: pd.Series, e_ref: pd.Series, h: int) -> tuple[float, float]:
    """Diebold-Mariano-West test with the Harvey-Leybourne-Newbold correction; returns (statistic, p-value)."""
    raise NotImplementedError("T3.x, T4.2, T5.x")
