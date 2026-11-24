---
name: snb-arima-next-task
description: Orchestrator for the SNB disaggregate-ARIMA replication project. Use when the user says "next task", "what's next", "continue the replication", "plan the next step", "update the task board", or asks to work on a task ID like T2.2. Reads AGENTS.md's task board, picks the next unblocked task, loads the matching skill, and closes the loop (board, decisions log, checks). Also handles foundation tasks T0.1 (package skeleton) and T0.2 (resolving paper gaps into decisions).
---

# SNB ARIMA — next task / orchestration

## When to use
- Starting a work session on the replication ("let's continue", "next step").
- The user names a task ID (`T1.4`) or a phase (`P2`).
- Re-planning after a blocker or after the user changed a decision.

## Procedure
1. **Load context.** Read `AGENTS.md` (§5 task board, §8 definition of done), `docs/decisions.md`, and the section of
   `docs/paper_spec.md` relevant to the candidate task. Do not re-read the PDF unless the spec is unclear; if it is, fix
   the spec (transcription errors only) and say so.
2. **Pick the task.** If the user named one, use it. Otherwise choose the first `todo` task on the critical path whose
   dependencies are all `done`. Tell the user in one line which task and why. If several are independent, mention which
   could run in parallel.
3. **Check for open decisions.** If the task touches a gap (G1–G13) without a `confirmed` D-xx entry, present the
   proposed default and one alternative in two sentences, recommend one, and continue with the recommendation unless
   the user objects. Record it in `docs/decisions.md`.
4. **Set status** to `doing` in the board.
5. **Run the task's skill** (column "Skill"). Follow its procedure and its checks exactly.
6. **Verify against §8 Definition of done.** Run the checks; show the key sanity numbers to the user (counts, a plot path,
   a comparison against a paper number).
7. **Close.** Set status to `done` (or `blocked(<reason>)`), add a one-line note, add new decisions/data rows.
8. **Micro retro.** Run the `skill-feedback-loop` micro retro for the skill(s) used: log findings in
   `docs/skill_feedback.md`. If this task finished a phase, run the macro retro instead (it includes the review page).
9. **Commit and push.** Check that every command used in the task exists as code in the repo (AGENTS.md rule 7),
   then commit (`T<id>: <what>`, with the attribution line) and `git push origin main`.
10. Suggest the next task.

## Foundation tasks handled here

### T0.0 Make the repo standalone
The project must not depend on anything outside `Arima-model/`. Ask the user before each step that touches files outside it.
- Done 2026-11-24: repo lives at `HS26/Arima-model/` (moved out of `HS26/Bachelors-Thesis/`), `git init -b main`, `.gitignore`.
  The remote (e.g. GitHub) is created only when the user asks.
- Do the copying with a script, `scripts/00_import_from_thesis_repo.py` (AGENTS.md rule 7), that prints what it copied
  and skips files that already exist.
- **Copy** (never move or delete) from the thesis repo `../Bachelors-Thesis/`: raw files `Data/raw/*` → `data/raw/`;
  `codebook.csv` (header and rows) → `codebook.csv`; `requirements.txt` → `requirements.txt` re-saved as **UTF-8** (it was
  UTF-16); `read_snb_cube` from `src/snb.py` → `src/arima_snb/io.py` with paths changed to `data/raw`.
- Create a local virtual environment `.venv/`, `pip install -r requirements.txt pytest`, `pip install -e .`, then
  re-pin with `pip freeze --exclude-editable > requirements.txt` (F-001).
- `data/raw/` is not tracked in git (D-08); every raw file needs download steps in `docs/data_sources.md`.
- `io.py` needs the path constants, so T0.0 creates the paths section of `config.py`; T0.1 adds the rest (F-003).
- Check: `grep -rn "\.\./" src scripts tests` finds nothing; the SNB loader reads a file from `data/raw/`.

### T0.1 Package skeleton
- Create `src/arima_snb/` with the modules listed in AGENTS.md §3 (empty functions with docstrings are fine),
  `src/arima_snb/config.py`, `scripts/run_all.py`, `tests/test_smoke.py`, `pyproject.toml` (so `pip install -e .` works) and
  `.gitignore` entries for `data/interim`, `data/final`, `outputs/`.
- `config.py` holds: `ROOT` (repo root), `RAW = ROOT / "data" / "raw"`, `META`, `INTERIM`, `FINAL`, `OUTPUTS`, `CODEBOOK = ROOT / "codebook.csv"`,
  `EVAL_START = "2004Q1"`, `EVAL_END = "2011Q4"`, `HORIZONS = range(1, 6)`, `MONTHS_KNOWN_IN_QUARTER = 2`,
  SIC grid bounds (D-02), `KALMAN_SAMPLE_START = "1993-01"`, `NO_COLLECTION_TOL = 1e-3`.
- Check: `python -c "import arima_snb"` and `pytest -q` pass.

### T0.2 Gap resolution
- Walk through G1–G13 in `docs/paper_spec.md`. For each, ensure a D-xx row exists with a default, a reason citing the
  paper page, and a planned sensitivity check where the choice could change results. Mark all as `proposed`, then ask
  the user to confirm the important ones (G1, G2, G4, G5, G9) in one compact list.

## Rules
- One task at a time unless the user asks for parallel work.
- Never mark `done` without a passing check.
- If a task is bigger than expected, split it into sub-IDs (`T2.2a`, `T2.2b`) on the board rather than leaving it half-done.
