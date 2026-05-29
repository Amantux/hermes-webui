from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlparse


def _json_payload(handler):
    body = handler.wfile.write.call_args[0][0]
    return json.loads(body.decode("utf-8"))


def _mk_handler():
    h = MagicMock()
    h.wfile = MagicMock()
    h.send_response = MagicMock()
    h.send_header = MagicMock()
    h.end_headers = MagicMock()
    return h


def test_mcp_effective_scope_prefers_project_over_global():
    from api import routes

    merged_cfg = {
        "mcp_servers": {
            "alpha": {"url": "https://global.example"},
            "gamma": {"url": "https://global-gamma.example"},
        }
    }
    project_cfg = {
        "mcp_servers": {
            "alpha": {"command": "project-alpha"},
            "beta": {"url": "https://project-beta.example"},
            "gamma": None,
        }
    }

    original = routes._load_project_config_for_workspace
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    try:
        effective, src = routes._effective_mcp_servers(merged_cfg, "/tmp/ws", "effective")
    finally:
        routes._load_project_config_for_workspace = original

    assert effective["alpha"]["command"] == "project-alpha"
    assert effective["beta"]["url"] == "https://project-beta.example"
    assert "gamma" not in effective
    assert src["alpha"] == "project"
    assert src["beta"] == "project"
    assert src["gamma"] == "project_disabled"


def test_skills_effective_scope_prefers_project_over_global():
    from api import routes

    skills = [
        {"name": "alpha", "disabled": True},
        {"name": "beta", "disabled": False},
        {"name": "gamma", "disabled": False},
    ]
    project_cfg = {"skills": {"enabled": ["alpha"], "disabled": ["beta"]}}

    original = routes._load_project_config_for_workspace
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    try:
        effective = routes._apply_skills_scope(skills, "effective", "/tmp/ws")
    finally:
        routes._load_project_config_for_workspace = original

    by_name = {s["name"]: s for s in effective}
    assert by_name["alpha"]["disabled"] is False  # project enabled overrides global disabled
    assert by_name["beta"]["disabled"] is True
    assert by_name["gamma"]["disabled"] is False


def test_memory_effective_scope_prefers_project_over_global(tmp_path):
    from api import routes

    global_payload = {"memory": "global-memory", "user": "global-user", "soul": "global-soul"}
    project_cfg = {"memory": {"mode": "override", "memory": "project-memory", "user": "project-user"}}

    original = routes._load_project_config_for_workspace
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    try:
        effective = routes._effective_memory_payload(global_payload, "effective", str(tmp_path))
    finally:
        routes._load_project_config_for_workspace = original

    assert effective["memory"] == "project-memory"
    assert effective["user"] == "project-user"
    assert effective["soul"] == "global-soul"
    assert effective["scope"] == "effective"


def test_wiki_path_resolution_prefers_project_then_global(tmp_path, monkeypatch):
    from api import routes

    project_wiki = tmp_path / "project-wiki"
    global_wiki = tmp_path / "global-wiki"
    monkeypatch.setenv("WIKI_PATH", str(global_wiki))

    project_cfg = {"wiki": {"path": str(project_wiki)}}
    original = routes._load_project_config_for_workspace
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    try:
        p_eff, source_eff, _ = routes._llm_wiki_resolve_path(workspace=str(tmp_path), scope="effective")
        p_glob, source_glob, _ = routes._llm_wiki_resolve_path(workspace=str(tmp_path), scope="global")
    finally:
        routes._load_project_config_for_workspace = original

    assert p_eff == project_wiki
    assert source_eff == "project.wiki.path"
    assert p_glob == global_wiki
    assert source_glob == "WIKI_PATH"


def test_wiki_graph_endpoint_uses_scope_workspace(tmp_path):
    from api import routes

    wiki = tmp_path / ".hermes" / "wiki" / "entities"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "alpha.md").write_text("# Alpha\n[[beta]]", encoding="utf-8")
    (wiki / "beta.md").write_text("# Beta", encoding="utf-8")

    project_cfg = {"wiki": {"path": str(tmp_path / ".hermes" / "wiki")}}
    original = routes._load_project_config_for_workspace
    original_ws = routes._workspace_from_request
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    routes._workspace_from_request = lambda parsed=None, body=None: str(tmp_path)
    try:
        handler = _mk_handler()
        parsed = urlparse(f"/api/wiki/graph?scope=project&workspace={tmp_path}")
        ok = routes._handle_llm_wiki_graph(handler, parsed)
        payload = _json_payload(handler)
    finally:
        routes._load_project_config_for_workspace = original
        routes._workspace_from_request = original_ws

    assert ok is True
    assert payload["scope"] == "project"
    assert len(payload["nodes"]) >= 1
    assert any(edge["target"].endswith("beta.md") for edge in payload["edges"])


def test_frontend_scope_wiring_present():
    repo = Path(__file__).resolve().parents[1]
    index_html = (repo / "static" / "index.html").read_text(encoding="utf-8")
    panels_js = (repo / "static" / "panels.js").read_text(encoding="utf-8")

    assert 'id="skillsScope"' in index_html
    assert 'id="memoryScope"' in index_html
    assert 'id="mcpScope"' in index_html
    assert 'id="wikiScope"' in index_html
    assert "/api/mcp/servers?" in panels_js
    assert "/api/mcp/tools?" in panels_js
    assert "/api/wiki/graph?" in panels_js
    assert "/api/wiki/pages?" in panels_js
    assert "function setWikiScope" in panels_js


def test_mcp_project_save_writes_only_project_config(tmp_path):
    from api import routes

    saved_project = {}
    global_save_called = {"value": False}
    original_load = routes._load_project_config_for_workspace
    original_save_project = routes._save_project_config_for_workspace
    original_save_global = routes._save_yaml_config_file
    original_workspace = routes._workspace_from_request
    routes._load_project_config_for_workspace = lambda _ws: {"mcp_servers": {}}
    routes._workspace_from_request = lambda parsed=None, body=None: str(tmp_path)

    def _save_project(_ws, cfg):
        saved_project.update(cfg)
        return Path(_ws) / ".hermes" / "webui.project.yaml"

    def _save_global(*_args, **_kwargs):
        global_save_called["value"] = True

    routes._save_project_config_for_workspace = _save_project
    routes._save_yaml_config_file = _save_global
    try:
        handler = _mk_handler()
        body = {
            "name": "alpha",
            "scope": "project",
            "workspace": str(tmp_path),
            "url": "https://example.test/mcp",
        }
        routes._handle_mcp_server_save(handler, body)
        payload = _json_payload(handler)
    finally:
        routes._load_project_config_for_workspace = original_load
        routes._save_project_config_for_workspace = original_save_project
        routes._save_yaml_config_file = original_save_global
        routes._workspace_from_request = original_workspace

    assert payload["ok"] is True
    assert payload["scope"] == "project"
    assert "alpha" in saved_project["mcp_servers"]
    assert global_save_called["value"] is False


def test_mcp_project_delete_tombstone_hides_global_in_effective(tmp_path):
    from api import routes

    project_cfg = {"mcp_servers": {}}
    original_load = routes._load_project_config_for_workspace
    original_save = routes._save_project_config_for_workspace
    original_workspace = routes._workspace_from_request
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    routes._workspace_from_request = lambda parsed=None, body=None: str(tmp_path)
    routes._save_project_config_for_workspace = lambda _ws, cfg: project_cfg.update(cfg) or (Path(_ws) / ".hermes" / "webui.project.yaml")
    try:
        handler = _mk_handler()
        routes._handle_mcp_server_delete_by_body(
            handler,
            {"name": "alpha", "scope": "project", "workspace": str(tmp_path)},
        )
        merged, src = routes._effective_mcp_servers(
            {"mcp_servers": {"alpha": {"url": "https://global.example"}}},
            str(tmp_path),
            "effective",
        )
    finally:
        routes._load_project_config_for_workspace = original_load
        routes._save_project_config_for_workspace = original_save
        routes._workspace_from_request = original_workspace

    assert "alpha" not in merged
    assert src["alpha"] == "project_disabled"


def test_skill_toggle_project_requires_workspace():
    from api import routes

    handler = _mk_handler()
    routes._handle_skill_toggle(handler, {"name": "alpha", "enabled": True, "scope": "project"})
    payload = _json_payload(handler)
    assert "workspace is required" in payload["error"]


def test_memory_effective_append_mode_merges_global_and_project(tmp_path):
    from api import routes

    global_payload = {"memory": "gmem", "user": "guser", "soul": "gsoul"}
    original = routes._load_project_config_for_workspace
    routes._load_project_config_for_workspace = lambda _ws: {
        "memory": {"mode": "append", "memory": "pmem", "user": "puser", "soul": "psoul"}
    }
    try:
        effective = routes._effective_memory_payload(global_payload, "effective", str(tmp_path))
    finally:
        routes._load_project_config_for_workspace = original
    assert "gmem" in effective["memory"] and "pmem" in effective["memory"]
    assert "guser" in effective["user"] and "puser" in effective["user"]
    assert "gsoul" in effective["soul"] and "psoul" in effective["soul"]
    assert effective["overlay_mode"] == "append"


def test_memory_write_project_scope_requires_workspace():
    from api import routes

    handler = _mk_handler()
    routes._handle_memory_write(handler, {"section": "memory", "content": "x", "scope": "project"})
    payload = _json_payload(handler)
    assert "workspace is required" in payload["error"]


def test_wiki_page_rejects_forbidden_root(monkeypatch):
    from api import routes

    original = routes._llm_wiki_resolve_path
    routes._llm_wiki_resolve_path = lambda workspace=None, scope="effective": (Path("/etc"), "forced", True)
    try:
        handler = _mk_handler()
        parsed = urlparse("/api/wiki/page?scope=global&path=hosts")
        routes._handle_llm_wiki_page(handler, parsed)
        payload = _json_payload(handler)
    finally:
        routes._llm_wiki_resolve_path = original
    assert "blocked" in payload["error"].lower()


def test_wiki_pages_and_graph_include_provenance(tmp_path):
    from api import routes

    wiki = tmp_path / ".hermes" / "wiki"
    entities = wiki / "entities"
    entities.mkdir(parents=True, exist_ok=True)
    (entities / "alpha.md").write_text("# Alpha\n[[beta]]", encoding="utf-8")
    (entities / "beta.md").write_text("# Beta", encoding="utf-8")

    project_cfg = {"wiki": {"path": str(wiki)}}
    original = routes._load_project_config_for_workspace
    original_ws = routes._workspace_from_request
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    routes._workspace_from_request = lambda parsed=None, body=None: str(tmp_path)
    try:
        pages_handler = _mk_handler()
        pages_parsed = urlparse(f"/api/wiki/pages?scope=project&workspace={tmp_path}")
        routes._handle_llm_wiki_pages(pages_handler, pages_parsed)
        pages_payload = _json_payload(pages_handler)

        graph_handler = _mk_handler()
        graph_parsed = urlparse(f"/api/wiki/graph?scope=project&workspace={tmp_path}")
        routes._handle_llm_wiki_graph(graph_handler, graph_parsed)
        graph_payload = _json_payload(graph_handler)
    finally:
        routes._load_project_config_for_workspace = original
        routes._workspace_from_request = original_ws

    assert pages_payload["provenance"]["path_source"] == "project.wiki.path"
    assert pages_payload["provenance"]["scope"] == "project"
    assert pages_payload["pages"][0]["provenance"]["type"] == "wiki_page"

    assert graph_payload["provenance"]["path_source"] == "project.wiki.path"
    assert graph_payload["provenance"]["scope"] == "project"
    assert graph_payload["nodes"][0]["provenance"]["type"] == "wiki_page"
    assert graph_payload["edges"][0]["provenance"]["type"] == "wikilink"


def test_wiki_page_rejects_non_markdown_file(tmp_path):
    from api import routes

    (tmp_path / "notes.txt").write_text("plain text", encoding="utf-8")
    original = routes._llm_wiki_resolve_path
    routes._llm_wiki_resolve_path = lambda workspace=None, scope="effective": (tmp_path, "forced", True)
    try:
        handler = _mk_handler()
        parsed = urlparse("/api/wiki/page?scope=effective&path=notes.txt")
        routes._handle_llm_wiki_page(handler, parsed)
        payload = _json_payload(handler)
    finally:
        routes._llm_wiki_resolve_path = original

    assert "markdown" in payload["error"].lower()


def test_wiki_page_rejects_oversized_markdown(tmp_path):
    from api import routes

    page = tmp_path / "large.md"
    page.write_text("x" * 64, encoding="utf-8")

    original_resolve = routes._llm_wiki_resolve_path
    original_max = routes._LLM_WIKI_MAX_PAGE_BYTES
    routes._llm_wiki_resolve_path = lambda workspace=None, scope="effective": (tmp_path, "forced", True)
    routes._LLM_WIKI_MAX_PAGE_BYTES = 16
    try:
        handler = _mk_handler()
        parsed = urlparse("/api/wiki/page?scope=effective&path=large.md")
        routes._handle_llm_wiki_page(handler, parsed)
        payload = _json_payload(handler)
    finally:
        routes._llm_wiki_resolve_path = original_resolve
        routes._LLM_WIKI_MAX_PAGE_BYTES = original_max

    assert payload["error"] == "page exceeds max allowed size"


def test_wiki_pages_contract_includes_scope_workspace_and_total(tmp_path):
    from api import routes

    wiki = tmp_path / ".hermes" / "wiki" / "entities"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "alpha.md").write_text("# Alpha", encoding="utf-8")
    (wiki / "beta.md").write_text("# Beta", encoding="utf-8")

    project_cfg = {"wiki": {"path": str(tmp_path / ".hermes" / "wiki")}}
    original_load = routes._load_project_config_for_workspace
    original_ws = routes._workspace_from_request
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    routes._workspace_from_request = lambda parsed=None, body=None: str(tmp_path)
    try:
        handler = _mk_handler()
        parsed = urlparse(f"/api/wiki/pages?scope=project&workspace={tmp_path}")
        ok = routes._handle_llm_wiki_pages(handler, parsed)
        payload = _json_payload(handler)
    finally:
        routes._load_project_config_for_workspace = original_load
        routes._workspace_from_request = original_ws

    assert ok is True
    assert payload["scope"] == "project"
    assert payload["workspace"] == str(tmp_path)
    assert payload["wiki_path"] == str(tmp_path / ".hermes" / "wiki")
    assert payload["total"] == 2
    assert sorted(page["path"] for page in payload["pages"]) == ["entities/alpha.md", "entities/beta.md"]


def test_wiki_search_contract_includes_query_and_scope(tmp_path):
    from api import routes

    wiki = tmp_path / ".hermes" / "wiki" / "entities"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "alpha.md").write_text("# Alpha\nContains token-needle.", encoding="utf-8")

    project_cfg = {"wiki": {"path": str(tmp_path / ".hermes" / "wiki")}}
    original_load = routes._load_project_config_for_workspace
    original_ws = routes._workspace_from_request
    routes._load_project_config_for_workspace = lambda _ws: project_cfg
    routes._workspace_from_request = lambda parsed=None, body=None: str(tmp_path)
    try:
        handler = _mk_handler()
        parsed = urlparse(f"/api/wiki/search?scope=project&workspace={tmp_path}&q=needle")
        ok = routes._handle_llm_wiki_search(handler, parsed)
        payload = _json_payload(handler)
    finally:
        routes._load_project_config_for_workspace = original_load
        routes._workspace_from_request = original_ws

    assert ok is True
    assert payload["query"] == "needle"
    assert payload["scope"] == "project"
    assert payload["workspace"] == str(tmp_path)
    assert payload["wiki_path"] == str(tmp_path / ".hermes" / "wiki")
    assert len(payload["results"]) == 1
    assert payload["results"][0]["path"] == "entities/alpha.md"
    assert "needle" in payload["results"][0]["snippet"].lower()


def test_mcp_global_scope_uses_global_source_map_only():
    from api import routes

    merged_cfg = {"mcp_servers": {"alpha": {"url": "https://global.example"}}}
    servers, source = routes._effective_mcp_servers(merged_cfg, workspace=None, scope="global")

    assert servers == merged_cfg["mcp_servers"]
    assert source == {"alpha": "global"}


def test_wiki_path_resolution_falls_back_to_default_when_unconfigured(monkeypatch):
    from api import routes

    monkeypatch.delenv("WIKI_PATH", raising=False)
    original_env_file = routes._llm_wiki_env_file_path
    original_cfg_path = routes._llm_wiki_config_path
    routes._llm_wiki_env_file_path = lambda _home: None
    routes._llm_wiki_config_path = lambda: None
    try:
        path, source, configured = routes._llm_wiki_resolve_path(workspace=None, scope="global")
    finally:
        routes._llm_wiki_env_file_path = original_env_file
        routes._llm_wiki_config_path = original_cfg_path

    assert path == Path("~/wiki").expanduser()
    assert source == "default"
    assert configured is False
