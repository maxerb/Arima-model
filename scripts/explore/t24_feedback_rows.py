"""T2.4 micro retro: add the skill-feedback rows F-047 ... F-050 and the retro note to docs/skill_feedback.md.

Kept as code (AGENTS.md rule 7); `add_to(text)` is also used by t24_stage_own_changes.py to stage only these
lines while sibling sessions edit the same file. Idempotent.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROWS = [
    "| F-047 | 2026-11-24 | snb-arima-oil-rent | T2.4 | wrong | Part B step 1 says the mortgage rate is the cantonal-bank average linked to the BWO rate in 2008Q2; the confirmed decision D-19 uses the continuous SNB series zikrepro M_MV instead | decisions D-19 | Step 1: 'mortgage rate = SNB M_MV (D-19), quarterly average (D-15 rev.)'; keep fn. 3 splice as the paper's original | proposed |",
    "| F-048 | 2026-11-24 | snb-arima-oil-rent | T2.4 | project-fact | Step 5 says rents are collected in the 2nd month of the quarter 'since 2008'; the linked rent index changes only in Feb/May/Aug/Nov from 1993 on (scripts/explore/t24_rent_data.py) | data check | Step 5: 'since 1993 (D-48)'; AGENTS.md §7 'check earlier' can be answered | proposed |",
    "| F-049 | 2026-11-24 | snb-arima-oil-rent | T2.4 | missing | Rent part silent on sample start, AR grid, information set for the current quarter's mortgage rate and the interface switch; user chose 1993Q2 and p = 0..4 (D-48); implemented `mortgage_rate` argument of forecast_item(s) (None = ARIMA benchmark, D-49); run takes ~25 s for 32 origins | decisions D-15 rev., D-48, D-49 | Add one line each to Part B (sample, grid, info set = months <= origin, mortgage_rate switch) | proposed |",
    "| F-050 | 2026-11-24 | snb-arima-oil-rent | T2.4 | one-off | Script number 10_ clashed with T3.1's 10_pseudo_oos.py running in parallel; renamed to 07_rent_model.py (next to 07_oil_ecm.py) | sibling notes | none | applied |",
]
NOTE = """
### Micro retro T2.4 (snb-arima-oil-rent, rent model), 2026-11-24
- No user corrections; three choices put to the user (sample start, quarterly mortgage measure, AR grid), all recommended options taken (D-48, D-15 rev.).
- Skill wrong on the mortgage series (F-047, superseded by D-19) and on the start of quarterly rent collection (F-048); silent on sample, grid, info set and interface (F-049). Queued as `proposed` for the P2 retro.
- Checks passed: parameter recovery (β⁺, β⁻), no-look-ahead for rents and mortgage rate (origin-month rate does move the forecast, origin+1 does not), changes only in collection months, h = 1 error 0, routing through forecast_item / forecast_items; Table 3 rent RMSFE 0.00/0.26/0.51/0.64/0.76 vs paper 0.00/0.24/0.46/0.56/0.61, ARIMA/rent 1.01/1.12/1.20/1.20 vs paper 1.18/1.44/1.72/1.90.
"""


def add_to(text: str) -> str:
    if "| F-047 |" in text:
        return text
    lines = text.split("\n")
    i = max(k for k, l in enumerate(lines) if l.startswith("| F-0"))
    lines[i + 1:i + 1] = ROWS
    return "\n".join(lines).rstrip("\n") + "\n" + NOTE


if __name__ == "__main__":
    p = ROOT / "docs" / "skill_feedback.md"
    p.write_text(add_to(p.read_text(encoding="utf-8")), encoding="utf-8")
