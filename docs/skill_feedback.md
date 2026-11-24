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
| F-008 | 2026-11-24 | snb-arima-next-task | T0.0–T1.4 | missing | Review page never updated after tasks: statuses and decisions were typed into the HTML and no step refreshed it (showed 0/22 done and D-01…D-08 after 7 tasks and 25 decisions) | user question "does the page update when tasks are done?" | `scripts/build_review_page.py` generates both from AGENTS.md / decisions.md; new step 9 "Refresh the review page" in the skill; `tests/test_review_page.py` fails when stale (user approved) | applied |

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

### Micro retro T1.2 (2026-11-24) — snb-arima-data
- Skill says SNB conditional forecasts must be hand-collected; they exist as SNB cube `snbiprogq`. Candidate edit: name the cube in the datasets table.
- Skill suggests BWO for mortgage rates after 2008; BWO page is JS-only (no file). SNB `zikrepro` `M_MV` covers 1976–today. Candidate edit: list `zikrepro` first.
- `read_snb_cube` only handled one dimension and monthly dates; extended for D0/D1 and quarterly cubes (no skill change needed).
- Scripts need the project venv (`.venv/Scripts/python`); plain `python` lacked the package. Candidate edit: mention in next-task skill.
- 2026-11-24: user confirmed D-06 revision (KOF evaluated on annual-average inflation, cy/ny). Pending skill edit (needs approval): `snb-arima-evaluation` consensus row should say "annual-average target per D-06 rev." instead of the open "convert … only if defensible". → applied 2026-11-24 with user approval.

### Micro retro T1.3 (2026-11-24) — snb-arima-data
- Skill implies Table 9 gives `agg6, agg14` per item; it does not (only sub-aggregate totals). agg14 derived from item order, agg6 deferred to T1.4 (D-21). Candidate edit: say so in step 5.
- Skill says PDF pp. 21-25 for Table 9; those are printed page numbers (PDF pages 23-27). Calendars are PDF pp. 19-23. Candidate edit: give both.
- Improvised: the calendar 'x' marks have no column position in the text layer; rendered pages to PNG and transcribed visually, then cross-checked mark counts against the text layer. Candidate edit: describe this method.

### Micro retro T1.4 (2026-11-24) — snb-arima-cpi-panel
- Skill assumes the item list comes from Table 9 names; matching works only via weights, and the weights are those of the **2005 basket for 2010** (not the 2010 basket). Candidate edit: step 1 "match Table 9 by LIK2005 weights of 2010, then by order".
- Skill check "no jump > 20 % at a link month" cannot detect wrong links (ratio-linking never creates a level jump; seasonal items jump anyway). Improvised a better check: compare linked monthly changes with BFS back-casts in newer files. Candidate edit: replace the check.
- Skill does not mention that the 1993 and 2025 baskets use different position numbers, and that names repeat (retail vs restaurant wine/beer). Improvised name + dynamics rule (D-25). Candidate edit: add pitfall.
- D-21 plan (agg6 from BFS special groupings) does not work: groupings are aggregate series without membership lists. Candidate edit to snb-arima-data/cpi-panel once a source is found.
- Transcription bug from T1.3 fixed (item 9 "Table 8 continued Beef" -> "Beef"; page header was not skipped).
- agg6 follow-up (2026-11-24): BFS methods PDFs (2005, 2010 bases) publish domestic/imported and goods/services only as totals (Anhang 2), no per-position list. Membership regression on BFS grouping series (`src/arima_snb/classify.py`) reproduces the paper's ARIMA(6) totals on the full basket (16.3/28.2/18.9/8.6/23.9 vs 16.9/27.8/19.5/8.7/23.4) but item-level labels are not identified (e.g. margarine -> public services). Not wired into the pipeline; awaiting user decision.

- agg6 resolved with user (rules + data check, D-21 rev.). Candidate skill edit (snb-arima-cpi-panel step 4): agg6 is not in Table 9 nor in BFS files; use data/meta/agg6_rules.csv + classify.item_agg6.

## T1.5 micro retro (2026-11-24, snb-arima-cpi-panel)
- Wrong input found: paper Table 9 prints weights one row off in two blocks (items 85–93, 119–124); T1.4's weight matching inherited it (shoe repairs mapped twice). Fixed by name overrides (D-22 rev.). Candidate edit (step 1 / checks): "after weight matching, read the English↔German name pairs once and assert no BFS position is used by two items unless a documented merge".
- Skill step 3 says "before annual updating the weight is constant between revisions" — wrong for BFS: GEWICHTUNGEN has a new weight column every year from 2002 (2000/01 for 2000–01, one 1993 column). Candidate edit: replace with "use the GEWICHTUNGEN column of each year; 1993 column covers 1993–99, 2000/01 covers 2000–01 (D-26)".
- Skill step 3 does not cover one position carrying several items (merge in a later basket); asked user (D-27: split by last separate shares). Candidate edit: add the rule.
- Skill step 5 assumes calendar rows name model items; in fact they are BFS sub-groups. Improvised `data/meta/collection_calendar_items.csv`. Candidate edit: mention the hand map.
- Check "2010 coverage ≈ 92.8 %" is 92.70 with true BFS weights (paper's skirts weight 0.230 vs BFS 0.143). Candidate edit to the check value.
- Tooling: Bash `sed 's/\|...\|/'` (escaped pipes) matched the empty string and corrupted every line of decisions.md; reverted. Use Python for edits containing `|`.
- Observation for T5.1: coverage drops to 86–88 % from 2016 and 60 % in 2026 (2015 splits such as package holidays abroad/domestic and hospital in/outpatient map to one child only; 54 items without 2025 link, D-25).

### T1.6 micro retro (2026-11-24, snb-arima-aggregate)
- Skill interface `aggregate_index(item_log_p, ...)` takes log prices, but the Laspeyres formula needs index levels; implemented with levels (`item_index`). Candidate edit: rename the argument in the skill.
- Skill says "verify the base month for 2000–2007 bases": answer is basket periods May 1993→May 2000 and May 2000→Dec 2001, then Dec-chaining yearly (D-29). Off-by-one: the old basket period must include the overlap month (May 2000) or the chain breaks — candidate edit: state this.
- `build_subaggregate_series` needs the `items` table for groupings (signature in skill lacks it).
- Tooling: matplotlib was not in requirements/venv; `pip install matplotlib==3.9.2` tried to build from source on this Python → use `--only-binary=:all:` (pinned 3.11.2).
- Check passed: monthly y-o-y RMSE 0.067 pp (2001–2011); gaps > 0.2 pp only around the 2000 basket switch and 4 months 2018–2026.
