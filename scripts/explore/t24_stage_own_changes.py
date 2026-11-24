"""Stage only T2.4's changes, so that `git commit` records T2.4 alone (AGENTS.md rule 8, shared checkout).

config.py also carries T3.1's uncommitted block; it is staged as HEAD + the rent block only, with
`git hash-object` / `git update-index`, leaving the working tree untouched. The other shared files
(decisions.md, skill_feedback.md, AGENTS.md, review page) held only T2.4 edits when this was run and are
checked for that. Run, check `git diff --cached`, then `git commit`.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWN_FILES = ["src/arima_snb/special.py", "src/arima_snb/item_models.py", "scripts/07_rent_model.py",
             "tests/test_rent.py", "scripts/explore/t24_rent_data.py", "scripts/explore/t24_feedback_rows.py",
             "scripts/explore/t24_stage_own_changes.py", "docs/decisions.md", "docs/skill_feedback.md",
             "AGENTS.md", "docs/review_page/index.html"]


def git(*args, inp=None) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, input=inp, capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def config_text() -> str:
    start = "# ---------------------------------------------------------------------------\n# Rent model"
    w = (ROOT / "src/arima_snb/config.py").read_text(encoding="utf-8")
    block = w[w.index(start):].split("\n\n", 1)[0] + "\n"
    anchor = "OIL_M_MAX = 3                      # D-14: Δp lags 0..3, chosen by SIC\n"
    assert "RENT_P_MAX" in block and "OOS" not in block
    return git("show", "HEAD:src/arima_snb/config.py").replace(anchor, anchor + "\n" + block, 1)


def main() -> None:
    for f in ["docs/decisions.md", "docs/skill_feedback.md", "AGENTS.md"]:
        added = [l for l in git("diff", "-U0", "--", f).split("\n") if l.startswith("+") and not l.startswith("+++")]
        assert not any(l.startswith(("+| D-5", "+| F-051", "+| F-052")) for l in added), f"foreign edits in {f}"
    git("add", "--", *OWN_FILES)
    sha = git("hash-object", "-w", "--path=src/arima_snb/config.py", "--stdin", inp=config_text()).strip()
    git("update-index", "--add", "--cacheinfo", f"100644,{sha},src/arima_snb/config.py")
    print(git("diff", "--cached", "--stat"))


if __name__ == "__main__":
    main()
