from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def _src(name: str) -> str:
    return (REPO / "static" / name).read_text(encoding="utf-8")


def test_composer_mic_uses_transcribe_and_message_textarea():
    index = _src("index.html")
    boot = _src("boot.js")

    assert 'id="btnMic"' in index
    assert "const ta=$('msg');" in boot
    assert "setComposerStatus('Transcribing…');" in boot
    assert "fetch('api/transcribe'" in boot


def test_memory_skills_kanban_mics_use_shared_textarea_helper():
    panels = _src("panels.js")
    index = _src("index.html")
    boot = _src("boot.js")

    assert 'id="btnMemMic"' in panels
    assert "window._startMicForTextarea(document.getElementById('memEditContent'),this)" in panels
    assert 'id="btnSkillMic"' in panels
    assert "window._startMicForTextarea(document.getElementById('skillFormContent'),this)" in panels
    assert 'id="btnKanbanCommentMic"' in panels
    assert "window._startMicForTextarea(document.getElementById('kanbanCommentInput'),this)" in panels
    assert 'id="btnKanbanTaskMic"' in index
    assert "window._startMicForTextarea(document.getElementById('kanbanTaskModalBody'),this)" in index
    assert "window._startMicForTextarea=(function()" in boot


def test_shared_helper_handles_accessible_button_state():
    boot = _src("boot.js")

    assert "setAttribute('aria-pressed'" in boot
    assert "btn.setAttribute('aria-label', label);" in boot
    assert "_setButtonTooltip(btn, label);" in boot
