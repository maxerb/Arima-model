# Regression scenarios — snb-arima-next-task

| # | Prompt | Expected behaviour |
|---|---|---|
| S-1 (F-022) | "Run the T2.2 script and add a column to decisions.md." | Runs with `.venv/Scripts/python`; edits the table with Python/Edit, not `sed`. |
| S-2 (F-008) | "T2.1 is done, close it." | Runs `build_review_page.py`, republishes the review page, then commits and pushes. |
