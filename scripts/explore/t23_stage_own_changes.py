"""Stage only T2.3's changes in files that parallel sessions (T4.1, T2.5) edit too (config.py, decisions.md,
skill_feedback.md, AGENTS.md, review page), so that `git commit` records T2.3 alone (AGENTS.md rule 8, shared checkout).

Each shared file is rebuilt from its HEAD version plus the T2.3 edits and written to the git index with
`git hash-object` / `git update-index`; the working tree (with the siblings' uncommitted edits) stays untouched.
Files that only T2.3 touched are staged as they are. Run, check `git diff --cached`, then `git commit`.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "explore"))
from t23_feedback_rows import add_to  # noqa: E402

from arima_snb.review_page import build  # noqa: E402

OWN_FILES = ["src/arima_snb/special.py", "src/arima_snb/item_models.py", "scripts/07_oil_ecm.py",
             "tests/test_oil_ecm.py", "scripts/explore/t23_oil_timing.py", "scripts/explore/t23_feedback_rows.py",
             "scripts/explore/t23_stage_own_changes.py"]
NEW_DECISIONS = ["| D-14 rev. ", "| D-38 |", "| D-39 |"]
BOARD_ROW = "| T2.3 | Oil-products ECM |"


def git(*args, inp=None) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, input=inp, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def head(path: str) -> str:
    return git("show", f"HEAD:{path}")


def work(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def stage(path: str, content: str) -> None:
    sha = git("hash-object", "-w", f"--path={path}", "--stdin", inp=content).strip()
    git("update-index", "--add", "--cacheinfo", f"100644,{sha},{path}")


def config_text() -> str:
    start = "# ---------------------------------------------------------------------------\n# Oil-products ECM"
    w = work("src/arima_snb/config.py")
    block = w[w.index(start):].split("\n\n", 1)[0] + "\n"
    anchor = "ITEM_N_JOBS = 4                    # parallel worker processes for the item models (T2.2)\n"
    assert "OIL_K_MAX" in block and "KALMAN" not in block
    return head("src/arima_snb/config.py").replace(anchor, anchor + "\n" + block, 1)


def replace_rows(head_text: str, work_text: str, prefixes) -> str:
    """Take the working-tree version of every line starting with one of `prefixes` into the HEAD text."""
    w = {l.split("|")[1].strip(): l for l in work_text.split("\n") if l.startswith(tuple(prefixes))}
    out = [w.get(l.split("|")[1].strip(), l) if l.startswith(tuple(prefixes)) else l for l in head_text.split("\n")]
    return "\n".join(out)


def decisions_text() -> str:
    w = work("docs/decisions.md")
    lines = replace_rows(head("docs/decisions.md"), w, ["| D-14 |"]).split("\n")
    mine = [l for l in w.split("\n") if l.startswith(tuple(NEW_DECISIONS))]
    assert len(mine) == 3
    idx = max(i for i, l in enumerate(lines) if l.startswith("| D-37 |"))
    lines[idx + 1:idx + 1] = mine
    return "\n".join(lines)


def main() -> None:
    for f in OWN_FILES:
        stage(f, work(f))
    stage("src/arima_snb/config.py", config_text())
    dec = decisions_text()
    stage("docs/decisions.md", dec)
    agents = replace_rows(head("AGENTS.md"), work("AGENTS.md"), [BOARD_ROW])
    stage("AGENTS.md", agents)
    stage("docs/skill_feedback.md", add_to(head("docs/skill_feedback.md")))
    with tempfile.TemporaryDirectory() as tmp:
        page, dmd, amd = Path(tmp) / "index.html", Path(tmp) / "decisions.md", Path(tmp) / "AGENTS.md"
        page.write_text(head("docs/review_page/index.html"), encoding="utf-8")
        dmd.write_text(dec, encoding="utf-8")
        amd.write_text(agents, encoding="utf-8")
        build(page=page, agents=amd, decisions_md=dmd)
        html = page.read_text(encoding="utf-8")
    stage("docs/review_page/index.html", html)
    print(git("diff", "--cached", "--stat"))


if __name__ == "__main__":
    main()
