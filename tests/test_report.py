"""T3.3: replication tables in the paper's layout - formatting, bold at 10 %, paper comparison, generated outputs."""

import numpy as np
import pandas as pd
import pytest

from arima_snb import report
from arima_snb.config import EVAL, PAPER_TABLE2, TABLES

TAB = pd.DataFrame({"row": ["ref", "ref", "b", "b"], "h": [1, 2, 1, 2], "value": [0.081, 0.4, 1.25, 0.97],
                    "p_value": [np.nan, np.nan, 0.034, 0.5], "T": 32})
LABELS = {"ref": "Reference", "b": "Bench & co", "missing": "Not available"}


def test_paper_layout_cells_and_missing_rows():
    lay = report.paper_layout(TAB, LABELS)
    assert list(lay.columns) == ["h=1", "h=2"]
    assert lay.loc["Reference", "h=1"] == "0.08" and lay.loc["Bench & co", "h=1"] == "1.25 (0.034)"
    assert (lay.loc["Not available"] == "-").all()


def test_latex_bold_only_below_10_percent_and_escaped():
    tex = report.table_to_latex([(None, TAB, LABELS, ["$h=1$", "$h=2$"])], "cap", "tab:x", notes="10 % level")
    assert r"\textbf{1.25 (0.034)}" in tex and r"\textbf{0.97" not in tex and "0.97 (0.500)" in tex
    assert r"Bench \& co" in tex and r"10 \% level" in tex and tex.count(r"\\") >= 4
    assert "Not available & -- & --" in tex


def test_compare_with_paper_flags():
    paper = {"ref": ((0.08, None), (0.41, None)), "b": ((1.20, 0.30), (1.10, 0.40))}
    cmp = report.compare_with_paper(TAB, paper, ["ref"]).set_index(["row", "h"])
    assert cmp.loc[("b", 1), "same_side_of_1"] == 1 and cmp.loc[("b", 1), "same_significance_10pct"] == 0
    assert cmp.loc[("b", 2), "same_side_of_1"] == 0 and cmp.loc[("b", 2), "same_significance_10pct"] == 1
    assert cmp.loc[("b", 1), "diff"] == pytest.approx(0.05)
    s = report.agreement_summary(cmp.reset_index(), ["ref"])
    assert (s["n_rel"], s["same_side"], s["n_sig"], s["same_sig"]) == (2, 1, 2, 1)


@pytest.mark.skipif(not (EVAL / "benchmarks.csv").exists(), reason="run scripts/10 and 12 first")
def test_generated_tables_come_from_outputs(tmp_path, monkeypatch):
    """Regenerate Table 2 from outputs/eval and check it against the eval file (nothing hard-coded)."""
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "rep_tables", Path(__file__).parents[1] / "scripts" / "13_replication_tables.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    t2 = mod.table2()
    ev = pd.read_csv(EVAL / "arima182.csv")
    ev = ev[ev.model == "arima182"]
    r = np.sqrt(((ev.pi_actual - ev.pi_hat) ** 2).groupby(ev.h).mean())
    ours = t2[t2.row == "arima182"].set_index("h").value
    assert np.allclose(ours.values, r.values)
    assert set(t2.row) == set(PAPER_TABLE2) and (t2["T"] == 32).all()
    assert t2[t2.row != "arima182"].p_value.between(0, 1).all()
