"""Rebuild everything from the raw data: run the numbered scripts in order (AGENTS.md rule 5).

    python scripts/run_all.py            # run every step
    python scripts/run_all.py --list     # only show which steps would run

Steps are the files scripts/NN_*.py with NN from 01 upwards. Step 00 (one-time import
from the old thesis repository) and the exploratory scripts in scripts/explore/ are not part of the rebuild.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def pipeline_steps() -> list[Path]:
    """Numbered scripts 01_*.py, 02_*.py, ... in order."""
    steps = sorted(SCRIPTS.glob("[0-9][0-9]_*.py"))
    return [s for s in steps if not s.name.startswith("00_")]


def main() -> None:
    steps = pipeline_steps()
    if not steps:
        print("No pipeline steps yet (scripts/01_*.py ...). Nothing to run.")
        return
    for step in steps:
        print(f"\n=== {step.name} ===")
        if "--list" in sys.argv:
            continue
        # Each step runs in its own Python process, like running it by hand.
        result = subprocess.run([sys.executable, str(step)], cwd=SCRIPTS.parent)
        if result.returncode != 0:
            sys.exit(f"{step.name} failed (exit code {result.returncode}); later steps were not run.")
    print("\nAll steps finished.")


if __name__ == "__main__":
    main()
