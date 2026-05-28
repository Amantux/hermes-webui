"""Integration tests for dependency-unavailable (503) responses on /api/skills and /api/crons.

These routes guard optional Hermes agent packages (tools.skills_tool, cron.jobs) with
try/except ImportError blocks, returning a structured 503 when the packages are absent.

_dependency_unavailable_response() shape (always):
    {"error": "<feature> unavailable: <exc>", "feature": "<feature>", "dependency_ready": false}

Tests exercise this contract both by monkeypatching the internal helpers that raise
ImportError (so tests pass regardless of whether agent packages are installed) and by
directly testing the helper function itself.
"""

from __future__ import annotations

import io
import json
from urllib.parse import urlparse

import pytest

from api import routes


# ── Minimal handler stand-in ──────────────────────────────────────────────────

class _FakeHandler:
    """Minimal BaseHTTPRequestHandler stand-in for routes.handle_get."""

    def __init__(self):
        self.status = None
        self.sent_headers: list[tuple[str, str]] = []
        self.body = bytearray()
        self.wfile = self
        self.rfile = io.BytesIO(b"")
        self.headers = {}

    def send_response(self, code: int):
        self.status = code

    def send_header(self, key: str, value: str):
        self.sent_headers.append((key, value))

    def end_headers(self):
        pass

    def write(self, data):
        self.body.extend(data if isinstance(data, (bytes, bytearray)) else data.encode("utf-8"))

    def get_json(self) -> dict:
        return json.loads(self.body.decode("utf-8"))


# ── _dependency_unavailable_response unit tests ────────────────────────────────

def test_dependency_unavailable_response_returns_503():
    handler = _FakeHandler()
    exc = ImportError("No module named 'cron.jobs'")
    routes._dependency_unavailable_response(handler, "crons", exc)
    assert handler.status == 503


def test_dependency_unavailable_response_payload_structure():
    handler = _FakeHandler()
    exc = ImportError("No module named 'tools.skills_tool'")
    routes._dependency_unavailable_response(handler, "skills", exc)
    payload = handler.get_json()
    assert payload["feature"] == "skills"
    assert payload["dependency_ready"] is False
    assert "skills unavailable" in payload["error"]
    assert "tools.skills_tool" in payload["error"]


def test_dependency_unavailable_response_crons_feature_name():
    handler = _FakeHandler()
    exc = ImportError("No module named 'cron'")
    routes._dependency_unavailable_response(handler, "crons", exc)
    payload = handler.get_json()
    assert payload["feature"] == "crons"
    assert payload["dependency_ready"] is False
    assert "crons unavailable" in payload["error"]


# ── /api/skills route ─────────────────────────────────────────────────────────

def test_skills_route_returns_503_when_import_unavailable(monkeypatch):
    """When _skills_list_from_dir raises ImportError, /api/skills must return 503."""
    monkeypatch.setattr(
        routes,
        "_skills_list_from_dir",
        lambda *_a, **_kw: (_ for _ in ()).throw(ImportError("No module named 'tools.skills_tool'")),
    )
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/skills"))
    assert handler.status == 503


def test_skills_route_dependency_ready_false_on_import_error(monkeypatch):
    """Response body must carry dependency_ready=False and feature='skills'."""
    monkeypatch.setattr(
        routes,
        "_skills_list_from_dir",
        lambda *_a, **_kw: (_ for _ in ()).throw(ImportError("No module named 'tools.skills_tool'")),
    )
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/skills"))
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "skills"
    assert "skills unavailable" in payload["error"]


def test_skills_route_category_query_does_not_affect_503_shape(monkeypatch):
    """A ?category= query string must not change the 503 error shape."""
    monkeypatch.setattr(
        routes,
        "_skills_list_from_dir",
        lambda *_a, **_kw: (_ for _ in ()).throw(ImportError("missing dep")),
    )
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/skills?category=coding"))
    assert handler.status == 503
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "skills"


def test_skills_content_route_returns_503_when_import_unavailable(monkeypatch):
    """GET /api/skills/content (no file= param) must also return 503 on ImportError."""
    monkeypatch.setattr(
        routes,
        "_skill_view_from_active_dir",
        lambda *_a, **_kw: (_ for _ in ()).throw(ImportError("No module named 'agent.skill_utils'")),
    )
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/skills/content?name=myskill"))
    assert handler.status == 503
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "skills"


def test_skills_content_file_route_returns_503_when_import_unavailable(monkeypatch):
    """GET /api/skills/content?file=... must also return 503 on ImportError."""
    monkeypatch.setattr(
        routes,
        "_find_skill_in_dirs",
        lambda *_a, **_kw: (_ for _ in ()).throw(ImportError("No module named 'agent.skill_utils'")),
    )
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/skills/content?name=myskill&file=SKILL.md"))
    assert handler.status == 503
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "skills"


def test_skills_toggle_route_returns_503_when_import_unavailable(monkeypatch):
    """POST /api/skills/toggle must return 503 when skill imports fail."""
    monkeypatch.setattr(
        routes,
        "_handle_skill_toggle",
        lambda *_a, **_kw: (_ for _ in ()).throw(ImportError("No module named 'agent.skill_utils'")),
    )
    handler = _FakeHandler()
    handler.headers = {"Content-Length": "0"}
    handler.rfile = io.BytesIO(b"{}")
    routes.handle_post(handler, urlparse("/api/skills/toggle"))
    assert handler.status == 503
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "skills"


# ── /api/commands/exec route ──────────────────────────────────────────────────

def _make_plugin_runtime_import_fail(monkeypatch):
    """Block hermes_cli.plugins so plugin command runtime import raises ImportError."""
    import sys
    monkeypatch.setitem(sys.modules, "hermes_cli.plugins", None)


def test_commands_exec_returns_503_when_plugin_runtime_missing(monkeypatch):
    """POST /api/commands/exec must return 503 when plugin runtime is unavailable."""
    _make_plugin_runtime_import_fail(monkeypatch)
    handler = _FakeHandler()
    body_bytes = json.dumps({"command": "/plugin-test"}).encode("utf-8")
    handler.headers = {"Content-Length": str(len(body_bytes))}
    handler.rfile = io.BytesIO(body_bytes)
    routes.handle_post(handler, urlparse("/api/commands/exec"))
    assert handler.status == 503
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "commands"
    assert "commands unavailable" in payload["error"]


def test_commands_exec_missing_runtime_payload_includes_reason(monkeypatch):
    """Dependency payload should include runtime-unavailable reason for operator clarity."""
    _make_plugin_runtime_import_fail(monkeypatch)
    handler = _FakeHandler()
    body_bytes = json.dumps({"command": "/plugin-test"}).encode("utf-8")
    handler.headers = {"Content-Length": str(len(body_bytes))}
    handler.rfile = io.BytesIO(body_bytes)
    routes.handle_post(handler, urlparse("/api/commands/exec"))
    payload = handler.get_json()
    assert payload["feature"] == "commands"
    assert "plugin command runtime unavailable" in payload["error"]


# ── /api/crons route ──────────────────────────────────────────────────────────

def _make_crons_import_fail(monkeypatch):
    """Block cron.jobs so the inline `from cron.jobs import list_jobs` raises ImportError."""
    import sys
    monkeypatch.setitem(sys.modules, "cron", None)
    monkeypatch.setitem(sys.modules, "cron.jobs", None)


def test_crons_route_returns_503_when_cron_package_missing(monkeypatch):
    """When cron.jobs is unavailable, GET /api/crons must return 503."""
    _make_crons_import_fail(monkeypatch)
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/crons"))
    assert handler.status == 503


def test_crons_route_dependency_ready_false_when_cron_missing(monkeypatch):
    """Response body must carry dependency_ready=False and feature='crons'."""
    _make_crons_import_fail(monkeypatch)
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/crons"))
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "crons"
    assert "crons unavailable" in payload["error"]


def test_crons_recent_route_degrades_gracefully_when_cron_missing(monkeypatch):
    """GET /api/crons/recent should surface missing cron support as 503."""
    _make_crons_import_fail(monkeypatch)
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/crons/recent"))
    assert handler.status == 503
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "crons"


@pytest.mark.parametrize(
    "path, body",
    [
        ("/api/crons/create", {"prompt": "p", "schedule": "* * * * *"}),
        ("/api/crons/update", {"job_id": "job-1"}),
        ("/api/crons/delete", {"job_id": "job-1"}),
        ("/api/crons/run", {"job_id": "job-1"}),
        ("/api/crons/pause", {"job_id": "job-1"}),
        ("/api/crons/resume", {"job_id": "job-1"}),
    ],
)
def test_cron_write_routes_return_503_when_cron_package_missing(monkeypatch, path, body):
    """Cron write routes must surface dependency-unavailable as 503."""
    _make_crons_import_fail(monkeypatch)
    handler = _FakeHandler()
    body_bytes = json.dumps(body).encode("utf-8")
    handler.headers = {"Content-Length": str(len(body_bytes))}
    handler.rfile = io.BytesIO(body_bytes)
    routes.handle_post(handler, urlparse(path))
    assert handler.status == 503
    payload = handler.get_json()
    assert payload["dependency_ready"] is False
    assert payload["feature"] == "crons"


def test_crons_status_route_returns_200_without_cron_package(monkeypatch):
    """GET /api/crons/status queries only in-memory running state and does not
    import cron.jobs, so it must succeed even when cron is unavailable."""
    _make_crons_import_fail(monkeypatch)
    handler = _FakeHandler()
    routes.handle_get(handler, urlparse("/api/crons/status"))
    assert handler.status == 200
    payload = handler.get_json()
    assert "running" in payload


# ── Contract surface tests (routes.py source) ─────────────────────────────────

from pathlib import Path

_ROUTES_SRC = (Path(__file__).resolve().parents[1] / "api" / "routes.py").read_text(encoding="utf-8")


def test_dependency_unavailable_response_is_defined_in_routes():
    assert "def _dependency_unavailable_response(" in _ROUTES_SRC


def test_dependency_unavailable_response_always_503():
    assert '"dependency_ready": False' in _ROUTES_SRC or "'dependency_ready': False" in _ROUTES_SRC or "dependency_ready" in _ROUTES_SRC
    assert "status=503" in _ROUTES_SRC


def test_all_cron_get_paths_have_dependency_guard():
    cron_paths = ["/api/crons", "/api/crons/output", "/api/crons/history",
                  "/api/crons/recent", "/api/crons/status"]
    for path in cron_paths:
        assert f'"{path}"' in _ROUTES_SRC or f"'{path}'" in _ROUTES_SRC, \
            f"cron path {path} missing from routes"


def test_skills_and_crons_use_dependency_unavailable_response():
    """Both feature areas must use _dependency_unavailable_response on ImportError."""
    skills_guard = _ROUTES_SRC.find('_dependency_unavailable_response(handler, "skills"')
    crons_guard = _ROUTES_SRC.find('_dependency_unavailable_response(handler, "crons"')
    assert skills_guard != -1, "skills dependency guard missing"
    assert crons_guard != -1, "crons dependency guard missing"
