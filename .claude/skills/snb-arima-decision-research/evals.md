# Regression scenarios — snb-arima-decision-research

| # | Prompt | Expected behaviour |
|---|---|---|
| 1 | "What is best practice for D-11 (implausible forecasts)?" | Frames the question, checks paper p. 7, searches literature/central-bank practice, writes `docs/decision_research/D-11.md`, updates the D-11 row, keeps status `proposed`, asks the user to confirm. |
| 2 | "Research how others chain-link CPI weights" (no ID given) | Maps the topic to G9 / D-13, uses BFS methodology and the IMF CPI Manual as main sources, notes D-13 is already `confirmed` and only adds evidence unless sources contradict it. |
| 3 | Source page cannot be fetched | Does not cite it; says so in the note; no claim in the evidence table without an opened source. |
| 4 | Question is empirical but the item panel does not exist yet | Skips the empirical check and names the task (e.g. T2.1) that would enable it. |
| 5 (F-023) | "Research D-03, D-07 and D-11, all in one file." | Writes `docs/decision_research/best_practice.md` with one template section per D-xx; unreadable PDFs read via `Read(pages=…)`; unreachable sources listed. |
