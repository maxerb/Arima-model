"""Stage only T2.5's changes (shared checkout, AGENTS.md rule 8), like t22_stage_own_changes.py.

Shared files (decisions.md, skill_feedback.md, review page) are rebuilt from their HEAD version plus the T2.5 rows
and written to the git index; the working tree, which also holds other sessions' uncommitted rows, is untouched.
Files only T2.5 touched are staged as they are. Run, check `git diff --cached`, then `git commit`.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "explore"))
from t25_rows import DECISIONS, add_to  # noqa: E402

from arima_snb.review_page import build  # noqa: E402

OWN_FILES = ["AGENTS.md", "src/arima_snb/aggregate.py", "scripts/08_aggregate_forecasts.py", "tests/test_aggregate.py",
             "scripts/06_item_models.py", "scripts/explore/t25_agg14_gap.py",
             "scripts/explore/t25_forecast_by_group.py", "scripts/explore/t25_rows.py",
             "scripts/explore/t25_stage_own_changes.py"]


def git(*args, inp=None) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, input=inp, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def head(path: str) -> str:
    """HEAD version with its original line endings (git show returns the blob; no newline translation)."""
    out = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    return out.decode("utf-8")


def stage(path: str, content: str) -> None:
    tmp = ROOT / ".git" / "t25_stage.tmp"
    tmp.write_bytes(content.encode("utf-8"))
    sha = git("hash-object", "-w", f"--path={path}", str(tmp)).strip()   # applies the repo's eol filter
    tmp.unlink()
    git("update-index", "--add", "--cacheinfo", f"100644,{sha},{path}")


def decisions_text() -> str:
    text = head("docs/decisions.md")
    if "| D-45 |" in text:
        return text
    nl = "\r\n" if "\r\n" in text else "\n"
    return text.rstrip("\r\n") + nl + nl.join(DECISIONS) + nl


def main() -> None:
    for f in OWN_FILES:
        stage(f, (ROOT / f).read_bytes().decode("utf-8"))
    dec = decisions_text()
    stage("docs/decisions.md", dec)
    stage("docs/skill_feedback.md", add_to(head("docs/skill_feedback.md")))
    with tempfile.TemporaryDirectory() as tmp:
        page, dmd = Path(tmp) / "index.html", Path(tmp) / "decisions.md"
        page.write_bytes(head("docs/review_page/index.html").encode("utf-8"))
        dmd.write_bytes(dec.encode("utf-8"))
        build(page=page, agents=ROOT / "AGENTS.md", decisions_md=dmd)
        html = page.read_bytes().decode("utf-8")
    stage("docs/review_page/index.html", html)
    print(git("diff", "--cached", "--stat"))


if __name__ == "__main__":
    main()
