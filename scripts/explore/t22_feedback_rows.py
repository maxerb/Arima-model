"""T2.2 micro retro: the skill-feedback rows and retro notes of task T2.2 (inserted by t22_stage_own_changes.py).

Kept as code because two sessions edit docs/skill_feedback.md at the same time (rule 7): the T2.2 rows are
added to whichever version of the file is given.
"""

ROWS = [
    "| F-032 | 2026-11-24 | snb-arima-item-models | T2.2 | wrong | Estimation prescribes SARIMAX ML with powell/lbfgs retries: 0.1-0.8 s per fit, ~30 CPU h for 32 origins, and eq. (3) is an SSE criterion anyway; user chose conditional least squares (D-35) | scripts/explore/t22_fit_timing.py | Replace the Estimation bullet by CLS with PACF transform (stationary/invertible), nfev cap, failed = dropped | proposed |",
    "| F-033 | 2026-11-24 | snb-arima-item-models | T2.2 | missing | Seasonal AR(12) with p = 12 is not identified (lag 12 in both factors; SARIMAX raises ValueError) - same as F-027 | ValueError in timing script | Add: p <= s - 1 when seasonal | proposed |",
    "| F-034 | 2026-11-24 | snb-arima-item-models | T2.2 | missing | No rule for short samples: at origin 2004-02 the common SIC sample has 21 obs for up to 16 parameters; user chose a grid guard (D-37) | asked user | Add the guard (>= 24 monthly / 12 quarterly obs in the common sample, drop seasonal if needed) | proposed |",
    "| F-035 | 2026-11-24 | snb-arima-item-models | T2.2 | wrong | Fallback table says plausibility band 'e.g. +-3 SD'; decision D-11 (now confirmed) uses the [1st, 99th] percentile of the item's own 12-month changes | decisions.md D-11 | Point the plausibility row to D-11 | proposed |",
    "| F-036 | 2026-11-24 | snb-arima-item-models | T2.2 | ambiguous | Quarterly items: skill said quarterly-sampled series, D-10 said monthly series with lag lists; user chose quarterly sampling (D-36, D-10 revised). Interface: `collection` argument is really last year's pattern; function also returns a log dict | conflicting texts | Align the Model section with D-36; update the interface signature | proposed |",
    "| F-037 | 2026-11-24 | snb-arima-item-models | T2.2 | missing | Runtime: joblib is not installed (stdlib ProcessPoolExecutor + __main__ guard on Windows used); MA candidates drifting to a unit root took 25 s each until the optimiser budget was capped (100 nfev, a 10x budget rescues none); 2.5-4 min per origin with 4 processes | scripts/explore/t22_profile_fit.py, t22_failed_fits.py | Replace the joblib hint; add budget cap and per-origin timing | proposed |",
    "| F-038 | 2026-11-24 | snb-arima-item-models | T2.2 | one-off | Check 'SIC picks the true AR(2) order' failed with phi = (0.5, -0.3): MA(1) mimics it with one parameter less and wins legitimately; test uses phi = (0.3, 0.4) | test failure, scripts/explore/t22_sic_check.py | Mention a non-MA-like AR(2) in the check | proposed |",
]

RETRO = """
### Micro retro T2.2 (snb-arima-item-models), 2026-11-24
- No user corrections; four choices put to the user (estimation, quarterly items, short samples, fallbacks), all recommended options taken (D-35, D-36, D-37, D-11 confirmed).
- Skill wrong/outdated on estimation and plausibility band (F-032, F-035), ambiguous on quarterly items (F-036), missing seasonal p cap, short-sample guard and runtime notes (F-033, F-034, F-037). All queued as `proposed` for the P2 retro.
- Checks passed: no-look-ahead (single item and all items, prices and collection flags perturbed), SIC picks true AR(2), CLS vs SARIMAX ML, MA invertibility, quarterly steps only in collection months, ad-hoc rules. Single-origin runs 2004-02 and 2011-02: all 182 items forecast, 1-2 plausibility fallbacks.
"""


def add_to(text: str) -> str:
    """Insert the T2.2 rows after the last F-row and append the retro notes (idempotent)."""
    if "| F-032 |" in text:
        return text
    lines = text.split("\n")
    last = max(i for i, l in enumerate(lines) if l.startswith("| F-"))
    lines[last + 1:last + 1] = ROWS
    return "\n".join(lines).rstrip("\n") + "\n" + RETRO
