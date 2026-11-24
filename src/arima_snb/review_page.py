"""Keep the review page (docs/review_page/index.html) in sync with the planning files.

The review page is a static HTML file published as a claude.ai artifact (AGENTS.md §10). Its task statuses and
decisions used to be typed into the HTML by hand, so the page fell behind the repo. This module reads the two
sources of truth and writes them into a marked block of the page's <script>:

- the task board in AGENTS.md §5   -> BOARD     (id, phase, title, skill, deps, status, note)
- the decision log docs/decisions.md -> DECISIONS (id, gap, title, why, alt, status, rev)

Everything else on the page (paper claims, skills, open items) is still written by hand. The block between the
markers is overwritten on every run, so never edit it by hand: change AGENTS.md / decisions.md and re-run
`scripts/build_review_page.py`.
"""

import datetime as dt
import json
import re
from pathlib import Path

from arima_snb.config import ROOT

AGENTS_MD = ROOT / "AGENTS.md"
DECISIONS_MD = ROOT / "docs" / "decisions.md"
PAGE = ROOT / "docs" / "review_page" / "index.html"

BEGIN = "/* @generated-begin: scripts/build_review_page.py writes this block, do not edit by hand */"
END = "/* @generated-end */"

STATUSES = ("todo", "doing", "done", "blocked")

_PHASE_ROW = re.compile(r"^\|\s*\*\*(P\d+)\*\*\s*\|")
_TASK_ID = re.compile(r"^T\d+\.\d+[a-z]?$")
_DEC_ID = re.compile(r"^(D-\d+)\b(.*)$")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _clean(text):
    """Strip the Markdown the page cannot render (code ticks, bold) and surrounding spaces."""
    return text.replace("`", "").replace("**", "").strip()


def _cells(line):
    """Split one Markdown table row into its cells (the outer pipes are dropped)."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_status(raw):
    """'done (2026-11-24; 16 tests pass)' -> ('done', '2026-11-24; 16 tests pass').

    'blocked(<reason>)' keeps the reason as the note. Anything unknown is an error, so a typo on the board
    does not silently show up as 'to do' on the page.
    """
    raw = _clean(raw)
    m = re.match(r"^([a-z]+)\s*(?:\((.*)\))?\s*$", raw, flags=re.S)
    if not m or m.group(1) not in STATUSES:
        raise ValueError(f"Unknown task status on the board: {raw!r} (allowed: {', '.join(STATUSES)})")
    return m.group(1), (m.group(2) or "").strip()


def parse_board(path=AGENTS_MD):
    """Read the task board table of AGENTS.md §5 into a list of dicts, in board order."""
    tasks, phase = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        m = _PHASE_ROW.match(line)
        if m:
            phase = m.group(1)
            continue
        cells = _cells(line)
        if len(cells) != 5 or not _TASK_ID.match(cells[0]):
            continue
        task_id, title, skill, deps, status = cells
        status, note = parse_status(status)
        tasks.append({
            "id": task_id,
            "ph": phase,
            "title": _clean(title),
            "skill": _clean(skill),
            "deps": [d.strip() for d in deps.split(",") if _TASK_ID.match(d.strip())],
            "status": status,
            "note": note,
        })
    if not tasks:
        raise ValueError(f"No task rows found in {path}")
    return tasks


def parse_decisions(path=DECISIONS_MD):
    """Read docs/decisions.md into one dict per decision ID.

    A revision row 'D-06 (rev. 2026-11-24)' replaces the earlier row of the same ID, so the page shows the
    decision that is in force. Review marks on the page are keyed by the plain ID and stay attached.
    """
    latest = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| D-"):
            continue
        cells = _cells(line)
        if len(cells) != 6:
            raise ValueError(f"Decision row does not have 6 cells: {line[:80]}…")
        m = _DEC_ID.match(cells[0])
        if not m:
            raise ValueError(f"Cannot read decision ID {cells[0]!r}")
        # Revision rows are written as 'D-06 (rev. 2026-11-24)' or 'D-21 rev. (2026-11-24)'.
        dec_id, suffix = m.group(1), m.group(2)
        if suffix.strip() and "rev" not in suffix:
            raise ValueError(f"Cannot read decision ID {cells[0]!r}")
        date = _DATE.search(suffix)
        rev = (date.group(0) if date else "yes") if "rev" in suffix else ""
        latest[dec_id] = {
            "id": dec_id,
            "gap": _clean(cells[1]),
            "title": _clean(cells[2]),
            "why": _clean(cells[3]),
            "alt": _clean(cells[4]),
            "status": _clean(cells[5]),
            "rev": rev,
        }
    return sorted(latest.values(), key=lambda d: int(d["id"][2:]))


def _js_array(rows):
    """One JSON object per line; '</' is escaped so text can never close the <script> tag."""
    body = ",\n".join("  " + json.dumps(r, ensure_ascii=False) for r in rows)
    return "[\n" + body.replace("</", "<\\/") + "\n]"


def generated_block(tasks, decisions, updated):
    """The JavaScript that goes between the BEGIN and END markers."""
    return "\n".join([
        BEGIN,
        f'const UPDATED = "{updated}";',
        f"const BOARD = {_js_array(tasks)};",
        f"const DECISIONS = {_js_array(decisions)};",
        END,
    ])


def render_page(html, tasks, decisions, updated):
    """Return the page HTML with the generated block replaced."""
    start, stop = html.find(BEGIN), html.find(END)
    if start < 0 or stop < start:
        raise ValueError("Generated-block markers not found in the review page")
    return html[:start] + generated_block(tasks, decisions, updated) + html[stop + len(END):]


def build(page=PAGE, agents=AGENTS_MD, decisions_md=DECISIONS_MD, today=None):
    """Regenerate the block in the page file. Returns (tasks, decisions, changed)."""
    tasks = parse_board(agents)
    decisions = parse_decisions(decisions_md)
    updated = (today or dt.date.today()).isoformat()
    page = Path(page)
    old = page.read_text(encoding="utf-8")
    new = render_page(old, tasks, decisions, updated)
    if new != old:
        page.write_text(new, encoding="utf-8", newline="\n")
    return tasks, decisions, new != old
