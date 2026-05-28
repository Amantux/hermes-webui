"""Tests for api.waiting_notifications: notify_waiting_input() dispatch behavior.

Covers:
- Skip when session has notifications disabled and no env var webhook
- Post when session has notify_on_waiting_input=True with explicit webhook URL
- Skip when webhook URL is absent even if title contains #notify
- Title-based opt-in via #notify and [notify] flags
- Env-var webhook fallback (HERMES_WEBUI_WAITING_INPUT_WEBHOOK)
- Graceful skip when get_session() raises (session not found)
- Full payload structure: event, kind, session_id, session_title, pending_count,
  message, question, description, tags
- webhook dispatch failure is suppressed (no exception raised to caller)
"""

import types

import api.clarify as clarify
import api.routes as routes
from api import waiting_notifications as wn


class _ImmediateThread:
    """Runs the target callable inline so tests stay synchronous."""
    def __init__(self, target=None, daemon=None):
        self._target = target

    def start(self):
        if self._target:
            self._target()


def _make_session(
    *,
    session_id="s0",
    title="Test",
    notify_on_waiting_input=False,
    waiting_input_webhook_url=None,
):
    return types.SimpleNamespace(
        session_id=session_id,
        title=title,
        notify_on_waiting_input=notify_on_waiting_input,
        waiting_input_webhook_url=waiting_input_webhook_url,
    )


# ── Existing tests (preserved) ─────────────────────────────────────────────

def test_notify_waiting_input_skips_when_disabled(monkeypatch):
    session = _make_session(
        session_id="s1",
        title="Test",
        notify_on_waiting_input=False,
        waiting_input_webhook_url=None,
    )
    monkeypatch.setenv("HERMES_WEBUI_WAITING_INPUT_WEBHOOK", "")
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    called = {"n": 0}
    monkeypatch.setattr(wn, "_post_json", lambda *_a, **_k: called.__setitem__("n", called["n"] + 1))
    wn.notify_waiting_input("s1", "clarify", {"question": "q?"}, 1)
    assert called["n"] == 0


def test_notify_waiting_input_posts_when_enabled(monkeypatch):
    session = _make_session(
        session_id="s2",
        title="Test #notify",
        notify_on_waiting_input=True,
        waiting_input_webhook_url="https://example.com/hook",
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    seen = {}
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda url, payload: seen.update({"url": url, "payload": payload}))
    wn.notify_waiting_input("s2", "approval", {"description": "Need approval"}, 2)
    assert seen["url"] == "https://example.com/hook"
    assert seen["payload"]["event"] == "waiting_input"
    assert seen["payload"]["kind"] == "approval"
    assert seen["payload"]["pending_count"] == 2


# ── Title-based opt-in ─────────────────────────────────────────────────────

def test_notify_triggers_on_hash_notify_in_title(monkeypatch):
    """A session title containing '#notify' must be treated as opted-in."""
    session = _make_session(
        session_id="s3",
        title="My daily summary #notify",
        notify_on_waiting_input=False,
        waiting_input_webhook_url="https://hooks.example.com/daily",
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    seen = {}
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda url, payload: seen.update({"url": url, "payload": payload}))
    wn.notify_waiting_input("s3", "clarify", {"question": "What date?"}, 1)
    assert "url" in seen, "Expected webhook call due to #notify in title"
    assert seen["payload"]["session_title"] == "My daily summary #notify"


def test_notify_triggers_on_bracket_notify_in_title(monkeypatch):
    """A session title containing '[notify]' must also opt in to notifications."""
    session = _make_session(
        session_id="s4",
        title="[notify] Weekly report",
        notify_on_waiting_input=False,
        waiting_input_webhook_url="https://hooks.example.com/weekly",
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    seen = {}
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda url, payload: seen.update({"url": url, "payload": payload}))
    wn.notify_waiting_input("s4", "approval", {}, 1)
    assert "url" in seen, "Expected webhook call due to [notify] in title"


# ── Env-var webhook fallback ───────────────────────────────────────────────

def test_env_var_webhook_used_when_session_has_no_explicit_url(monkeypatch):
    """HERMES_WEBUI_WAITING_INPUT_WEBHOOK must be used when the session provides no URL."""
    session = _make_session(
        session_id="s5",
        title="Task #notify",
        notify_on_waiting_input=True,
        waiting_input_webhook_url=None,
    )
    env_url = "https://env-hook.example.com/default"
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    monkeypatch.setenv("HERMES_WEBUI_WAITING_INPUT_WEBHOOK", env_url)
    seen = {}
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda url, payload: seen.update({"url": url, "payload": payload}))
    wn.notify_waiting_input("s5", "clarify", {"question": "Confirm?"}, 1)
    assert seen.get("url") == env_url


def test_env_var_webhook_not_used_when_disabled_and_plain_title(monkeypatch):
    """Env-var webhook alone does not trigger when session is not opted in."""
    session = _make_session(
        session_id="s6",
        title="Plain session",
        notify_on_waiting_input=False,
        waiting_input_webhook_url=None,
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    monkeypatch.setenv("HERMES_WEBUI_WAITING_INPUT_WEBHOOK", "https://env-hook.example.com/default")
    called = {"n": 0}
    monkeypatch.setattr(wn, "_post_json", lambda *_a, **_k: called.__setitem__("n", called["n"] + 1))
    wn.notify_waiting_input("s6", "clarify", {}, 1)
    assert called["n"] == 0, "Must not post when session is not opted in even if env var is set"


# ── Graceful failure paths ─────────────────────────────────────────────────

def test_notify_skips_gracefully_when_get_session_raises(monkeypatch):
    """If get_session() raises an exception, notify_waiting_input() must not propagate it."""
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("db locked")))
    called = {"n": 0}
    monkeypatch.setattr(wn, "_post_json", lambda *_a, **_k: called.__setitem__("n", called["n"] + 1))
    # Must not raise
    wn.notify_waiting_input("missing-session", "clarify", {}, 1)
    assert called["n"] == 0


def test_notify_suppresses_post_json_exception(monkeypatch):
    """If _post_json() raises (e.g., network error), the caller must not see an exception."""
    session = _make_session(
        session_id="s7",
        title="Error session #notify",
        notify_on_waiting_input=True,
        waiting_input_webhook_url="https://dead.example.com/hook",
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda *_a, **_k: (_ for _ in ()).throw(OSError("connection refused")))
    # Must not raise despite _post_json failing
    wn.notify_waiting_input("s7", "clarify", {}, 1)


# ── Full payload structure validation ─────────────────────────────────────

def test_notify_payload_contains_all_required_fields(monkeypatch):
    """The webhook POST body must carry the full documented payload schema."""
    session = _make_session(
        session_id="session-abc",
        title="Full payload test #notify",
        notify_on_waiting_input=True,
        waiting_input_webhook_url="https://example.com/full",
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    seen = {}
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda url, payload: seen.update({"url": url, "payload": payload}))
    wn.notify_waiting_input("session-abc", "clarify", {"question": "What's next?", "description": "Step desc"}, 3)

    payload = seen["payload"]
    assert payload["event"] == "waiting_input"
    assert payload["kind"] == "clarify"
    assert payload["session_id"] == "session-abc"
    assert payload["session_title"] == "Full payload test #notify"
    assert payload["pending_count"] == 3
    assert payload["question"] == "What's next?"
    assert payload["description"] == "Step desc"
    assert isinstance(payload["tags"], list)
    assert "hermes" in payload["tags"]
    assert "waiting-input" in payload["tags"]
    assert "clarify" in payload["tags"]
    assert "message" in payload


def test_notify_payload_pending_count_minimum_is_one(monkeypatch):
    """pending_count must always be at least 1 even if caller passes 0 or None."""
    session = _make_session(
        session_id="s8",
        title="Count test #notify",
        notify_on_waiting_input=True,
        waiting_input_webhook_url="https://example.com/count",
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    seen = {}
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda url, payload: seen.update({"payload": payload}))
    wn.notify_waiting_input("s8", "approval", {}, 0)
    assert seen["payload"]["pending_count"] >= 1


def test_notify_kind_defaults_to_input_when_empty(monkeypatch):
    """An empty/None kind must fall back to 'input' in the payload."""
    session = _make_session(
        session_id="s9",
        title="Kind fallback #notify",
        notify_on_waiting_input=True,
        waiting_input_webhook_url="https://example.com/kind",
    )
    monkeypatch.setattr("api.models.get_session", lambda *_a, **_k: session)
    seen = {}
    monkeypatch.setattr("threading.Thread", _ImmediateThread)
    monkeypatch.setattr(wn, "_post_json", lambda url, payload: seen.update({"payload": payload}))
    wn.notify_waiting_input("s9", "", {}, 1)
    assert seen["payload"]["kind"] == "input"


# ── Helper unit tests ──────────────────────────────────────────────────────

def test_session_wait_notifications_enabled_by_flag():
    session = _make_session(notify_on_waiting_input=True, title="plain")
    assert wn._session_wait_notifications_enabled(session) is True


def test_session_wait_notifications_enabled_by_hash_notify():
    session = _make_session(notify_on_waiting_input=False, title="Report #notify run")
    assert wn._session_wait_notifications_enabled(session) is True


def test_session_wait_notifications_enabled_by_bracket_notify():
    session = _make_session(notify_on_waiting_input=False, title="[notify] Weekly")
    assert wn._session_wait_notifications_enabled(session) is True


def test_session_wait_notifications_disabled_by_default():
    session = _make_session(notify_on_waiting_input=False, title="Just a session")
    assert wn._session_wait_notifications_enabled(session) is False


def test_session_waiting_webhook_url_prefers_session_override(monkeypatch):
    session = _make_session(waiting_input_webhook_url="https://session.url/hook")
    monkeypatch.setenv("HERMES_WEBUI_WAITING_INPUT_WEBHOOK", "https://env.url/hook")
    assert wn._session_waiting_webhook_url(session) == "https://session.url/hook"


def test_session_waiting_webhook_url_falls_back_to_env(monkeypatch):
    session = _make_session(waiting_input_webhook_url=None)
    monkeypatch.setenv("HERMES_WEBUI_WAITING_INPUT_WEBHOOK", "https://env.url/hook")
    assert wn._session_waiting_webhook_url(session) == "https://env.url/hook"


def test_session_waiting_webhook_url_returns_none_when_no_source(monkeypatch):
    session = _make_session(waiting_input_webhook_url=None)
    monkeypatch.setenv("HERMES_WEBUI_WAITING_INPUT_WEBHOOK", "")
    assert wn._session_waiting_webhook_url(session) is None


def test_clarify_submit_pending_triggers_waiting_input_notifier(monkeypatch):
    seen = {}
    monkeypatch.setattr(wn, "notify_waiting_input", lambda *a, **k: seen.update({"args": a, "kwargs": k}))
    entry = clarify.submit_pending("session-clarify", {"question": "Need clarification?", "choices_offered": ["yes"]})
    assert entry.data["question"] == "Need clarification?"
    assert seen["args"][0] == "session-clarify"
    assert seen["args"][1] == "clarify"
    clarify.clear_pending("session-clarify")


def test_approval_submit_pending_triggers_waiting_input_notifier(monkeypatch):
    seen = {}
    monkeypatch.setattr(wn, "notify_waiting_input", lambda *a, **k: seen.update({"args": a, "kwargs": k}))
    routes.submit_pending("session-approval", {"description": "Approve command?"})
    assert seen["args"][0] == "session-approval"
    assert seen["args"][1] == "approval"
    routes._pending.pop("session-approval", None)
