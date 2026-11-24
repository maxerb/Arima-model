"""T2.3 micro retro: add the skill-feedback rows F-039 ... F-042 and the retro note to docs/skill_feedback.md.

Kept as code (AGENTS.md rule 7); `add_to(text)` is also used by t23_stage_own_changes.py to stage only these
lines while sibling sessions edit the same file. Idempotent.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROWS = [
    "| F-039 | 2026-11-24 | snb-arima-oil-rent | T2.3 | wrong | Part A says 'heating oil, petrol, diesel - each separately', but the model panel (Table 9) has two oil items: heating oil i100 and fuels i130 (petrol and diesel in one position) | items.csv special == 'oil' | Replace with 'each oil item of items.csv (special == oil): i100 heating oil, i130 fuels' | proposed |",
    "| F-040 | 2026-11-24 | snb-arima-oil-rent | T2.3 | ambiguous | Step 1 offers 'first ~5 business days of the month, or previous month's average' for x_t; user chose the last 10 daily prices before the 1st of month t (D-14 rev.), which also makes the step-4 'constant at last 10 days' rule consistent; the first-5-days variant was tested and is slightly worse out of sample | decisions D-14 rev., scripts/explore/t23_oil_timing.py | Step 1: state D-14 rev. timing; list first-days as the tested alternative (OIL_X_RULE) | proposed |",
    "| F-041 | 2026-11-24 | snb-arima-oil-rent | T2.3 | missing | Estimation sample start for the ECM not mentioned; item models start May 2000, which leaves ~45 months at the 2004 origin; user chose May 1993 (D-38) | decision D-38 | Add to step 2: 'sample from OIL_SAMPLE_START (1993-05, D-38)' | proposed |",
    "| F-042 | 2026-11-24 | snb-arima-oil-rent | T2.3 | missing | Interface: skill says 'same interface as forecast_item' but not how the exogenous series reaches it; implemented as optional `crude_chf_daily` argument of forecast_item / forecast_items (None = plain ARIMA benchmark, D-39). Table 3 check also needs the oil sub-index aggregation; 32 origins with ARIMA benchmark take ~4 min (run in background) | item_models.py diff, scripts/07_oil_ecm.py | Add one line on the crude_chf_daily switch and the runtime | proposed |",
]
NOTE = """
### Micro retro T2.3 (snb-arima-oil-rent, oil ECM), 2026-11-24
- No user corrections; four choices put to the user (timing of x_t, Brent vs WTI, sample start, lags), all recommended options taken (D-14 rev., D-38).
- Skill wrong on the oil item list (F-039), ambiguous on the crude timing (F-040), silent on sample start and on the exogenous-data interface (F-041, F-042). All queued as `proposed` for the P2 retro.
- Improvised: an in-sample timing check (heating oil fits the first 5 days of month t better) was overturned by the out-of-sample RMSFE; logged in D-14 rev. as a sensitivity result.
- Checks passed: parameter recovery on simulated ECM, no-look-ahead for item prices and crude (both timing rules), crude just before the cut-off does move the nowcast, convergence to the long run, routing through forecast_item / forecast_items; Table 3 oil RMSFE 1.15/7.70/12.85/15.45/16.94 vs paper 1.14/6.72/12.49/15.25/17.10.
"""


def add_to(text: str) -> str:
    if "| F-039 |" in text:
        return text
    lines = text.split("\n")
    i = max(k for k, l in enumerate(lines) if l.startswith("| F-0"))
    lines[i + 1:i + 1] = ROWS
    return "\n".join(lines).rstrip("\n") + "\n" + NOTE


if __name__ == "__main__":
    p = ROOT / "docs" / "skill_feedback.md"
    p.write_text(add_to(p.read_text(encoding="utf-8")), encoding="utf-8")
