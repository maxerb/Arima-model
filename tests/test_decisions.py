"""T0.2 check: every paper gap G1-G13 has at least one decision row in docs/decisions.md."""
import re
from arima_snb.config import ROOT


def test_every_gap_has_a_decision():
    text = (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    gaps = set(re.findall(r"^\| D-\d+ \| (G\d+) \|", text, flags=re.M))
    missing = {f"G{i}" for i in range(1, 14)} - gaps
    assert not missing, f"gaps without a decision: {sorted(missing)}"
