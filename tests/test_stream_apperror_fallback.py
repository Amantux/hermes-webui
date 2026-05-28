"""Regression coverage for app-level stream error fallback rendering."""

from pathlib import Path


MESSAGES_JS = (Path(__file__).resolve().parents[1] / "static" / "messages.js").read_text(
    encoding="utf-8"
)


def test_apperror_fallback_surfaces_raw_server_payload_when_json_parse_fails():
    """The apperror catch path should use EventSource payload instead of a generic-only message."""
    assert "const rawAppError=(typeof e?.data==='string'?e.data.trim():'');" in MESSAGES_JS
    assert "content:safeRaw?`**Error:** ${safeRaw}`:'**Error:** An error occurred. Check server logs.'" in MESSAGES_JS

