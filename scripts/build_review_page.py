"""Refresh the review page from the task board (AGENTS.md §5) and the decision log (docs/decisions.md).

Run after every task, before publishing the page (snb-arima-next-task, step 8):

    .venv/Scripts/python scripts/build_review_page.py

The script only rewrites the generated block in docs/review_page/index.html. Publishing the page to its
claude.ai URL (AGENTS.md §10) needs Claude's Artifact tool, so Claude does that step after running this script.
"""

from collections import Counter

from arima_snb.review_page import PAGE, build


def main():
    tasks, decisions, changed = build()
    by_status = Counter(t["status"] for t in tasks)
    dec_status = Counter("confirmed" if d["status"].startswith("confirmed") else "proposed" for d in decisions)
    print(f"Tasks: {len(tasks)} ({', '.join(f'{k} {v}' for k, v in sorted(by_status.items()))})")
    print(f"Decisions: {len(decisions)} ({', '.join(f'{k} {v}' for k, v in sorted(dec_status.items()))})")
    print(f"{PAGE.relative_to(PAGE.parents[2])}: {'updated' if changed else 'already up to date'}")


if __name__ == "__main__":
    main()
