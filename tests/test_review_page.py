"""Checks for the review-page generator (src/arima_snb/review_page.py)."""

import datetime as dt

import pytest

from arima_snb import review_page as rp


def test_board_is_read_completely():
    tasks = rp.parse_board()
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)) >= 22
    assert {t["status"] for t in tasks} <= set(rp.STATUSES)
    assert all(t["ph"] for t in tasks)
    t11 = next(t for t in tasks if t["id"] == "T1.1")
    assert t11["deps"] == ["T0.1"] and t11["skill"] == "snb-arima-data"
    # Every dependency points to a task on the board.
    assert all(d in ids for t in tasks for d in t["deps"])


@pytest.mark.parametrize("raw, expected", [
    ("todo", ("todo", "")),
    ("done (2026-11-24; 16 tests pass)", ("done", "2026-11-24; 16 tests pass")),
    ("blocked(no data)", ("blocked", "no data")),
])
def test_parse_status(raw, expected):
    assert rp.parse_status(raw) == expected


def test_unknown_status_is_an_error():
    with pytest.raises(ValueError):
        rp.parse_status("finished")


def test_decision_revision_replaces_original():
    decisions = rp.parse_decisions()
    ids = [d["id"] for d in decisions]
    assert len(ids) == len(set(ids))
    d06 = next(d for d in decisions if d["id"] == "D-06")
    assert d06["rev"] and d06["status"] == "confirmed"
    assert "`" not in d06["title"] and "**" not in d06["title"]


def test_text_cannot_close_the_script_tag():
    block = rp.generated_block([{"id": "T9.9", "note": "</script>"}], [], "2026-01-01")
    assert "</script>" not in block


def test_page_is_in_sync_with_board_and_decision_log():
    """Fails when AGENTS.md or decisions.md changed but scripts/build_review_page.py was not re-run."""
    html = rp.PAGE.read_text(encoding="utf-8")
    start = html.index(rp.BEGIN)
    updated = html[start:].split('const UPDATED = "', 1)[1][:10]
    expected = rp.render_page(html, rp.parse_board(), rp.parse_decisions(), updated)
    assert html == expected, "Review page is stale: run scripts/build_review_page.py"
    dt.date.fromisoformat(updated)
