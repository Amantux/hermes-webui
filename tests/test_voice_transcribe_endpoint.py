import io
import json
import builtins
import sys
import types

import api.upload as upload


def _multipart_body(fields=None, files=None, boundary=b"voiceboundary"):
    fields = fields or {}
    files = files or {}
    body = b""
    for name, value in fields.items():
        body += b"--" + boundary + b"\r\n"
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += str(value).encode() + b"\r\n"
    for name, (filename, data, content_type) in files.items():
        body += b"--" + boundary + b"\r\n"
        body += (
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f'Content-Type: {content_type}\r\n\r\n'
        ).encode()
        body += data + b"\r\n"
    body += b"--" + boundary + b"--\r\n"
    return body, f"multipart/form-data; boundary={boundary.decode()}"


class _FakeHandler:
    def __init__(self, body: bytes, content_type: str):
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }
        self.status = None
        self.sent_headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.sent_headers[key] = value

    def end_headers(self):
        pass

    def payload(self):
        return json.loads(self.wfile.getvalue().decode("utf-8"))


def test_handle_transcribe_requires_file_field():
    body, content_type = _multipart_body(fields={"note": "missing file"})
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)
    assert handler.status == 400
    assert handler.payload()["error"] == "No file field in request"


def test_handle_transcribe_returns_transcript(monkeypatch):
    fake_mod = types.ModuleType("tools.transcription_tools")
    fake_mod.transcribe_audio = lambda path: {"success": True, "transcript": "hello from audio"}
    monkeypatch.setitem(sys.modules, "tools.transcription_tools", fake_mod)

    body, content_type = _multipart_body(
        files={"file": ("voice.webm", b"RIFFfakeaudio", "audio/webm")}
    )
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)

    assert handler.status == 200
    assert handler.payload() == {"ok": True, "transcript": "hello from audio"}


def test_handle_transcribe_surfaces_provider_error(monkeypatch):
    fake_mod = types.ModuleType("tools.transcription_tools")
    fake_mod.transcribe_audio = lambda path: {"success": False, "error": "STT not configured"}
    monkeypatch.setitem(sys.modules, "tools.transcription_tools", fake_mod)

    body, content_type = _multipart_body(
        files={"file": ("voice.webm", b"RIFFfakeaudio", "audio/webm")}
    )
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)

    assert handler.status == 503
    assert handler.payload()["error"] == "STT not configured"


def test_handle_transcribe_returns_503_when_transcription_module_missing(monkeypatch):
    real_import = builtins.__import__

    def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tools.transcription_tools":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _patched_import)

    body, content_type = _multipart_body(
        files={"file": ("voice.webm", b"RIFFfakeaudio", "audio/webm")}
    )
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)

    assert handler.status == 503
    assert "unavailable" in handler.payload()["error"].lower()


def test_handle_transcribe_non_config_failure_is_400(monkeypatch):
    fake_mod = types.ModuleType("tools.transcription_tools")
    fake_mod.transcribe_audio = lambda path: {"success": False, "error": "decoder crashed"}
    monkeypatch.setitem(sys.modules, "tools.transcription_tools", fake_mod)

    body, content_type = _multipart_body(
        files={"file": ("voice.webm", b"RIFFfakeaudio", "audio/webm")}
    )
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)

    assert handler.status == 400
    assert handler.payload()["error"] == "decoder crashed"


def test_handle_transcribe_uses_whisperx_when_selected(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_TRANSCRIPTION_PROVIDER", "whisperx")
    monkeypatch.setattr(
        upload,
        "_transcribe_with_whisperx",
        lambda _path: {"success": True, "transcript": "hello from whisperx"},
    )
    monkeypatch.setattr(
        upload,
        "_transcribe_with_legacy_provider",
        lambda _path: {"success": True, "transcript": "legacy transcript"},
    )

    body, content_type = _multipart_body(
        files={"file": ("voice.webm", b"RIFFfakeaudio", "audio/webm")}
    )
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)

    assert handler.status == 200
    assert handler.payload() == {"ok": True, "transcript": "hello from whisperx"}


def test_handle_transcribe_whisperx_unavailable_falls_back_to_legacy(monkeypatch):
    monkeypatch.setenv("HERMES_WEBUI_TRANSCRIPTION_PROVIDER", "whisperx")
    monkeypatch.setattr(
        upload,
        "_transcribe_with_whisperx",
        lambda _path: {
            "success": False,
            "error": "WhisperX unavailable: missing dependency",
            "unavailable": True,
        },
    )
    monkeypatch.setattr(
        upload,
        "_transcribe_with_legacy_provider",
        lambda _path: {"success": True, "transcript": "legacy fallback transcript"},
    )

    body, content_type = _multipart_body(
        files={"file": ("voice.webm", b"RIFFfakeaudio", "audio/webm")}
    )
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)

    assert handler.status == 200
    assert handler.payload() == {"ok": True, "transcript": "legacy fallback transcript"}


def test_handle_transcribe_reads_provider_from_settings_when_env_unset(monkeypatch):
    monkeypatch.delenv("HERMES_WEBUI_TRANSCRIPTION_PROVIDER", raising=False)
    monkeypatch.setattr(upload, "load_settings", lambda: {"transcription_provider": "whisperx"})
    monkeypatch.setattr(
        upload,
        "_transcribe_with_whisperx",
        lambda _path: {"success": True, "transcript": "settings whisperx transcript"},
    )
    monkeypatch.setattr(
        upload,
        "_transcribe_with_legacy_provider",
        lambda _path: {"success": True, "transcript": "legacy transcript"},
    )

    body, content_type = _multipart_body(
        files={"file": ("voice.webm", b"RIFFfakeaudio", "audio/webm")}
    )
    handler = _FakeHandler(body, content_type)
    upload.handle_transcribe(handler)

    assert handler.status == 200
    assert handler.payload() == {"ok": True, "transcript": "settings whisperx transcript"}
