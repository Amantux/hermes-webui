from pathlib import Path


def test_memory_editor_mic_uses_shared_whisperx_fallback():
    repo = Path(__file__).resolve().parents[1]
    panels = (repo / "static" / "panels.js").read_text(encoding="utf-8")
    boot = (repo / "static" / "boot.js").read_text(encoding="utf-8")

    assert 'id="btnMemMic"' in panels
    assert "window._startMicForTextarea(document.getElementById('memEditContent'),this)" in panels
    assert "window._startMicForTextarea=(function()" in boot
    assert "fetch('api/transcribe'" in boot
