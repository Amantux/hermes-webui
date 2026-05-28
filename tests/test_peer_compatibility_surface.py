from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTES_PY = (REPO_ROOT / "api" / "routes.py").read_text(encoding="utf-8")
README_MD = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
TESTING_MD = (REPO_ROOT / "TESTING.md").read_text(encoding="utf-8")


def _routes():
    return set(re.findall(r'parsed\.path == "([^"]+)"', ROUTES_PY))


def test_core_peer_compatibility_endpoints_exist():
    routes = _routes()
    required = {
        "/health",
        "/api/session",
        "/api/sessions",
        "/api/chat",
        "/api/chat/stream",
        "/api/chat/cancel",
        "/api/upload",
        "/api/upload/extract",
        "/api/workspaces",
        "/api/file",
        "/api/settings",
        "/api/profiles",
        "/api/providers",
        "/api/onboarding/status",
        "/api/memory",
        "/api/skills",
        "/api/crons",
        "/api/approval/pending",
        "/api/mcp/servers",
    }
    missing = sorted(required - routes)
    assert not missing, f"Missing peer-compatibility routes: {missing}"


def test_route_surface_is_not_prototype_scale():
    routes = _routes()
    assert len(routes) >= 180, (
        "Route surface unexpectedly small; parity runtime should expose a large API "
        f"surface. Found {len(routes)} routes."
    )


def test_peer_compatibility_frontend_modules_exist():
    required_files = [
        "static/index.html",
        "static/boot.js",
        "static/messages.js",
        "static/sessions.js",
        "static/workspace.js",
        "static/panels.js",
        "static/ui.js",
        "static/commands.js",
        "static/i18n.js",
    ]
    missing = [p for p in required_files if not (REPO_ROOT / p).exists()]
    assert not missing, f"Missing frontend parity modules: {missing}"


def test_readme_documents_pytest_workflow():
    assert "pytest tests/ -v --timeout=60" in README_MD
    assert "pytest tests/ --collect-only -q" in TESTING_MD
