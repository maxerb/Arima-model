# Regression scenarios — snb-arima-next-task

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-022) | "Run the T2.2 script and add a column to decisions.md." | Runs with `.venv/Scripts/python`; edits the table with Python/Edit, not `sed`. |
| S-2 (F-008) | "T2.1 is done, close it." | Runs `build_review_page.py`, republishes the review page, then commits and pushes. |
| S-3 (F-031, F-072) | "Run T5.1 while T5.2 runs in another session." | Reserves D-/F-ID blocks and owned files in the shared notes; commits with `git commit -- <paths>`, stages only own hunks of shared files; pulls with rebase before push; builds the review page after committing. |
| S-4 (F-073) | "T3.2 is done, close it." | Lists the task's `proposed` decisions and asks the user to confirm them; marks superseded rows `revised`. |
