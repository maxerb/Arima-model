"""Stage only T2.2's changes in files that the parallel T4.1 session edits too (config.py, decisions.md,
skill_feedback.md, review page), so that `git commit` records T2.2 alone (AGENTS.md rule 8, shared checkout).

Each shared file is rebuilt from its HEAD version plus the T2.2 edits and written to the git index with
`git hash-object` / `git update-index`; the working tree (with T4.1's uncommitted rows) is left untouched.
Files that only T2.2 touched are staged as they are. Run, check `git diff --cached`, then `git commit`.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "explore"))
from t22_feedback_rows import add_to  # noqa: E402

from arima_snb.review_page import build  # noqa: E402

OWN_FILES = ["AGENTS.md", "src/arima_snb/item_models.py", "scripts/06_item_models.py", "tests/test_item_models.py",
             "scripts/explore/t22_cls_options.py", "scripts/explore/t22_failed_fits.py",
             "scripts/explore/t22_fit_timing.py", "scripts/explore/t22_profile_fit.py",
             "scripts/explore/t22_profile_item.py", "scripts/explore/t22_sic_check.py",
             "scripts/explore/t22_time_candidates.py", "scripts/explore/t22_feedback_rows.py",
             "scripts/explore/t22_stage_own_changes.py"]
DECISION_IDS = ["| D-35 |", "| D-36 |", "| D-37 |"]


def git(*args, inp=None) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, input=inp, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def head(path: str) -> str:
    return git("show", f"HEAD:{path}")


def stage(path: str, content: str) -> None:
    sha = git("hash-object", "-w", f"--path={path}", "--stdin", inp=content).strip()
    git("update-index", "--add", "--cacheinfo", f"100644,{sha},{path}")


def config_text() -> str:
    work = (ROOT / "src/arima_snb/config.py").read_text(encoding="utf-8")
    anchor = "MIN_OBS_QUARTERLY = 12\n"
    block = work.split(anchor, 1)[1].split("\n\n", 1)[0] + "\n"   # T2.2 lines directly after the anchor
    assert "Q_MAX_QUARTERLY" in block and "ITEM_N_JOBS" in block and "KALMAN" not in block
    return head("src/arima_snb/config.py").replace(anchor, anchor + block, 1)


def decisions_text() -> str:
    work = (ROOT / "docs/decisions.md").read_text(encoding="utf-8").split("\n")
    mine = [l for l in work if any(l.startswith(i) for i in DECISION_IDS)]
    status = {l.split("|")[1].strip(): l for l in work if l.startswith(("| D-10 |", "| D-11 |"))}
    lines = head("docs/decisions.md").split("\n")
    lines = [status.get(l.split("|")[1].strip(), l) if l.startswith(("| D-10 |", "| D-11 |")) else l for l in lines]
    idx = max(i for i, l in enumerate(lines) if l.startswith("| D-34 |"))
    lines[idx + 1:idx + 1] = mine
    return "\n".join(lines)


def main() -> None:
    for f in OWN_FILES:
        stage(f, (ROOT / f).read_text(encoding="utf-8"))
    stage("src/arima_snb/config.py", config_text())
    dec = decisions_text()
    stage("docs/decisions.md", dec)
    stage("docs/skill_feedback.md", add_to(head("docs/skill_feedback.md")))
    with tempfile.TemporaryDirectory() as tmp:
        page, dmd = Path(tmp) / "index.html", Path(tmp) / "decisions.md"
        page.write_text(head("docs/review_page/index.html"), encoding="utf-8")
        dmd.write_text(dec, encoding="utf-8")
        build(page=page, agents=ROOT / "AGENTS.md", decisions_md=dmd)
        html = page.read_text(encoding="utf-8")
    stage("docs/review_page/index.html", html)
    print(git("diff", "--cached", "--stat"))


if __name__ == "__main__":
    main()
