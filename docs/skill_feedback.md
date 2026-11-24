# Skill feedback log

Maintained by the `skill-feedback-loop` skill. One row per finding; rows are never deleted, only their status changes.
Types: `wrong` · `missing` · `ambiguous` · `trigger` · `bloat` · `project-fact` · `one-off`.
Status: `open` · `proposed` · `applied` · `rejected` · `deferred`.

## Findings

| ID | Date | Skill | Task | Type | Finding | Evidence | Fix | Status |
|---|---|---|---|---|---|---|---|---|
| F-001 | 2026-11-24 | snb-arima-next-task | T0.0 | missing | T0.0 did not mention pytest, which is not in the old requirements; had to add it and re-freeze | improvised step | Add "install pytest, then `pip freeze --exclude-editable > requirements.txt`" to T0.0 | applied |
| F-002 | 2026-11-24 | snb-arima-next-task | T0.0 | missing | T0.0 assumed every raw file can be tracked; KOF licence unknown, so those files had to be gitignored | improvised step | Add "check each raw file's licence before tracking it (D-08)" to T0.0 | applied |
| F-003 | 2026-11-24 | snb-arima-next-task | T0.0 | ambiguous | T0.0 needed `config.py` (for RAW) before T0.1 creates it | improvised: created config.py paths in T0.0 | Say T0.0 creates the paths part of config.py | applied |
| F-004 | 2026-11-24 | snb-arima-next-task | T0.1 | one-off | Self-check test flagged its own docstring for containing the forbidden path pattern | failed check | Reworded the test; no skill change | applied |

## Summary per skill (updated at each macro retro)

| Skill | Uses | Findings | User corrections | Last retro |
|---|---|---|---|---|
| snb-arima-next-task | 0 | 0 | 0 | – |
| snb-arima-data | 0 | 0 | 0 | – |
| snb-arima-cpi-panel | 0 | 0 | 0 | – |
| snb-arima-item-diagnostics | 0 | 0 | 0 | – |
| snb-arima-item-models | 0 | 0 | 0 | – |
| snb-arima-oil-rent | 0 | 0 | 0 | – |
| snb-arima-aggregate | 0 | 0 | 0 | – |
| snb-arima-evaluation | 0 | 0 | 0 | – |
| snb-arima-kalman-extension | 0 | 0 | 0 | – |
| snb-arima-report | 0 | 0 | 0 | – |
| skill-feedback-loop | 0 | 0 | 0 | – |

## Ideas (not evidence yet; do not apply)

### Micro retro T0.2 (2026-11-24) — snb-arima-next-task
- Finding: skill lists G4 among the "important" gaps to confirm, but the ask tool fits 4 questions; G4 (origins) was left `proposed` since it follows directly from the paper. No skill edit needed.
- Added `tests/test_decisions.py` as the T0.2 check (skill did not name one) — candidate addition to the skill's T0.2 section.
