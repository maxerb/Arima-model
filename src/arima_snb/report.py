"""Reporting: LaTeX tables in the paper's layout, figures, paper-vs-replication comparison (T6.1).

Skill: snb-arima-report.
"""

import numpy as np
import pandas as pd


def table_to_latex(table: pd.DataFrame, caption: str) -> str:
    """Render a results table (absolute RMSFE row, relative RMSFE with p-values) as booktabs LaTeX."""
    raise NotImplementedError("T6.1")
