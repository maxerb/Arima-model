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
| F-005 | 2026-11-24 | snb-arima-data | T1.1 | wrong | Skill says weights come from "LIK Gewichtung per year"; actually all annual weights are in one BFS file `GEWICHTUNGEN` (one sheet per basket); the 2015/2020 detail files carry only their latest weight year | improvised step | Name `GEWICHTUNGEN` and the detailresultate page in the dataset table | applied |
| F-006 | 2026-11-24 | snb-arima-data | T1.1 | missing | Old BFS files are .xls → needs `xlrd`; repeated PosNo for special groupings below the main hierarchy; index levels > 1000 for back-cast PCs/TVs | improvised step | Add these three to Pitfalls | applied |
| F-007 | 2026-11-24 | snb-arima-data | T1.1 | one-off | Scripts must run with `.venv/Scripts/python` (package installed there), not the system python | failed check | none (environment) | – |

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

### Micro retro D-xx research (2026-11-24) — snb-arima-decision-research (new skill)
- User asked for all decisions in one file; the skill prescribes one note per decision. Improvised `docs/decision_research/best_practice.md` with one section per D-xx. Candidate skill edit: allow a "batch mode" writing one combined file.
- Many official PDFs failed for automated fetching (BFS image-only PDFs, IMF 404, StatCan/BoC/Harvard 403). Saved PDFs could be read page-by-page with the Read tool (worked for ECB WP 247 and SNB press release). Candidate skill edit: "if web-fetch gets an unreadable PDF, read the saved copy with Read(pages=…)"; list unreachable sources in a table instead of dropping them.
- Local data check (KOF consensus) changed a decision (D-06 refine) — step 5 of the skill proved useful.
