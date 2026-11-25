"""Reporting: tables in the paper's layout, paper-vs-replication comparison (T3.3), figures and text (T6.1).

Skills: snb-arima-evaluation (Tables 1-4), snb-arima-report.

The paper's results tables (pp. 9, 11, 12, 15) all have the same shape: the first row is the absolute RMSFE of the
reference model (percentage points of y-o-y inflation), every other row the RMSFE of a benchmark relative to the
reference with the DMW-HLN p-value in brackets; p < 0.10 is printed in bold. The functions here take the long
output of `evaluate.comparison_table` (columns row, h, value, p_value, T) and never type in a number themselves
(AGENTS.md rule 3); the paper's numbers come from `config.PAPER_TABLE*` (transcribed in docs/paper_spec.md §6).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from arima_snb.config import SIGNIFICANCE_LEVEL


# ---------------------------------------------------------------------------
# Paper layout (CSV) and LaTeX
# ---------------------------------------------------------------------------
def format_cell(value: float, p_value: float, digits: int = 2) -> str:
    """'0.36' for an absolute RMSFE, '1.25 (0.170)' for a relative one, '-' if there is no number."""
    if value is None or pd.isna(value):
        return "-"
    if p_value is None or pd.isna(p_value):
        return f"{value:.{digits}f}"
    return f"{value:.{digits}f} ({p_value:.3f})"


def paper_layout(tab: pd.DataFrame, labels: dict[str, str], col_prefix: str = "h=") -> pd.DataFrame:
    """Rows = models in the order of `labels` (missing rows shown as '–'), columns = horizons."""
    cells = tab.assign(cell=[format_cell(v, p) for v, p in zip(tab.value, tab.p_value)])
    out = cells.pivot(index="row", columns="h", values="cell").reindex(list(labels)).fillna("-")
    out.index = [labels[r] for r in out.index]
    out.columns = [f"{col_prefix}{h}" for h in out.columns]
    return out


def _latex_cell(value, p_value) -> str:
    """LaTeX cell: bold if the DMW-HLN p-value is below the 10 % level (paper p. 10)."""
    txt = "--" if pd.isna(value) else format_cell(value, p_value)
    if p_value is not None and not pd.isna(p_value) and p_value < SIGNIFICANCE_LEVEL:
        return rf"\textbf{{{txt}}}"
    return txt


def latex_block(tab: pd.DataFrame, labels: dict[str, str]) -> list[str]:
    """Body rows (one per model in `labels`) of a booktabs table."""
    lines = []
    for row, label in labels.items():
        g = tab[tab.row == row].set_index("h")
        cols = sorted(tab.h.unique())
        cells = [_latex_cell(g.value.get(h, np.nan), g.p_value.get(h, np.nan)) for h in cols]
        lines.append(f"{_latex_escape(label)} & " + " & ".join(cells) + r" \\")
    return lines


def _latex_escape(s: str) -> str:
    return s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def table_to_latex(blocks: list[tuple[str | None, pd.DataFrame, dict[str, str], list[str]]], caption: str,
                   label: str, notes: str = "") -> str:
    """Render one or more blocks (title, long table, row labels, column headers) as a booktabs LaTeX table.

    Every block can have its own column headers (Table 1's annual panel has two columns instead of five), so the
    tabular gets as many columns as the widest block.
    """
    ncol = max(len(b[3]) for b in blocks)
    lines = [r"\begin{table}[htbp]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             r"\begin{tabular}{l" + "c" * ncol + "}", r"\toprule"]
    for i, (title, tab, labels, headers) in enumerate(blocks):
        if i:
            lines.append(r"\midrule")
        if title:
            lines.append(rf"\multicolumn{{{ncol + 1}}}{{l}}{{\textit{{{_latex_escape(title)}}}}} \\")
        lines.append(" & " + " & ".join(headers) + r" \\")
        lines.append(r"\midrule")
        lines.extend(latex_block(tab, labels))
    lines += [r"\bottomrule", r"\end{tabular}"]
    if notes:
        lines.append(rf"\par\smallskip\begin{{minipage}}{{0.95\linewidth}}\footnotesize {_latex_escape(notes)}"
                     r"\end{minipage}")
    lines.append(r"\end{table}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Ours vs paper
# ---------------------------------------------------------------------------
def paper_frame(paper: dict) -> pd.DataFrame:
    """config.PAPER_TABLE* -> long frame row, h, paper_value, paper_p."""
    return pd.DataFrame([{"row": r, "h": h, "paper_value": v, "paper_p": p}
                         for r, cells in paper.items() for h, (v, p) in enumerate(cells, 1)]).astype(
        {"paper_value": float, "paper_p": float})


def compare_with_paper(tab: pd.DataFrame, paper: dict, references: list[str], row_map: dict | None = None
                       ) -> pd.DataFrame:
    """Cell-by-cell comparison: our value / p-value next to the paper's, difference, and two agreement flags.

    same_side_of_1          : a relative RMSFE is on the same side of 1 as in the paper (= same ranking against the
                              reference); always True for the absolute rows of the reference models.
    same_significance_10pct : the DMW-HLN test rejects at 10 % in both or in neither.
    row_map maps our row names to the paper's where they differ (e.g. kof_consensus -> consensus_economics).
    """
    ours = tab.assign(paper_row=tab.row.map(lambda r: (row_map or {}).get(r, r)))
    cmp = ours.merge(paper_frame(paper), left_on=["paper_row", "h"], right_on=["row", "h"], how="outer",
                     suffixes=("", "_paper"))
    cmp["row"] = cmp.row.fillna(cmp.row_paper)
    cmp = cmp.drop(columns=["row_paper"])
    cmp["diff"] = cmp.value - cmp.paper_value
    is_ref = cmp.row.isin(references)
    both = cmp.value.notna() & cmp.paper_value.notna()
    cmp["same_side_of_1"] = np.where(is_ref, True, np.where(both, (cmp.value > 1) == (cmp.paper_value > 1), np.nan))
    both_p = cmp.p_value.notna() & cmp.paper_p.notna()
    cmp["same_significance_10pct"] = np.where(
        both_p, (cmp.p_value < SIGNIFICANCE_LEVEL) == (cmp.paper_p < SIGNIFICANCE_LEVEL), np.nan)
    return cmp[["row", "paper_row", "h", "value", "p_value", "T", "paper_value", "paper_p", "diff",
                "same_side_of_1", "same_significance_10pct"]]


def agreement_summary(cmp: pd.DataFrame, references: list[str]) -> dict:
    """Counts for the paper-vs-ours note: ranking and significance agreement over the comparable cells."""
    rel = cmp[~cmp.row.isin(references)]
    side = rel.same_side_of_1.dropna().astype(bool)
    sig = rel.same_significance_10pct.dropna().astype(bool)
    return {"n_rel": int(len(side)), "same_side": int(side.sum()),
            "n_sig": int(len(sig)), "same_sig": int(sig.sum()),
            "sig_ours": int((rel.p_value < SIGNIFICANCE_LEVEL).sum()),
            "sig_paper": int((rel.paper_p < SIGNIFICANCE_LEVEL).sum()),
            "mismatch": rel[rel.same_significance_10pct.eq(False) | rel.same_side_of_1.eq(False)]}


def describe_agreement(cmp: pd.DataFrame, references: list[str]) -> str:
    """Two-line plain-text verdict: same ranking? same significance pattern? and which cells differ."""
    s = agreement_summary(cmp, references)
    lines = [f"Ranking vs the reference (relative RMSFE on the same side of 1 as the paper): "
             f"{s['same_side']} of {s['n_rel']} cells.",
             f"Significance at 10 % (DMW-HLN) agrees in {s['same_sig']} of {s['n_sig']} cells "
             f"(significant: ours {s['sig_ours']}, paper {s['sig_paper']})."]
    for r in s["mismatch"].itertuples(index=False):
        lines.append(f"  differs: {r.row} h={r.h}: ours {format_cell(r.value, r.p_value)}, "
                     f"paper {format_cell(r.paper_value, r.paper_p)}")
    return "\n".join(lines)
