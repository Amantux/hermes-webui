"""Todo panel should render `done` statuses as completed/struck-through."""

from pathlib import Path


REPO = Path(__file__).parent.parent
PANELS_JS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")


def test_done_status_normalized_to_completed_in_todo_panel():
    # normStatus variable normalizes 'done' to 'completed'
    assert "normStatus = t.status === 'done' ? 'completed' : t.status" in PANELS_JS


def test_done_status_uses_completed_visual_state():
    assert "done:li('check',14)" in PANELS_JS
    assert "done:'rgba(100,200,100,.8)'" in PANELS_JS
    assert "text-decoration:line-through" in PANELS_JS


def test_blocked_status_has_icon():
    assert "blocked:li('alert-circle'" in PANELS_JS
