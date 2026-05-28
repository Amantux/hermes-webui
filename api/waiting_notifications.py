from __future__ import annotations

import json
import logging
import os
import threading
from urllib import request

logger = logging.getLogger(__name__)


def _session_wait_notifications_enabled(session) -> bool:
    if bool(getattr(session, "notify_on_waiting_input", False)):
        return True
    title = str(getattr(session, "title", "") or "").lower()
    return "#notify" in title or "[notify]" in title


def _session_waiting_webhook_url(session) -> str | None:
    override = getattr(session, "waiting_input_webhook_url", None)
    if isinstance(override, str) and override.strip():
        return override.strip()
    env_default = os.environ.get("HERMES_WEBUI_WAITING_INPUT_WEBHOOK", "").strip()
    return env_default or None


def _post_json(url: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=5) as resp:
        resp.read(1)


def notify_waiting_input(session_id: str, kind: str, pending_payload: dict | None = None, pending_count: int = 1) -> None:
    try:
        from api.models import get_session
    except Exception:
        return
    try:
        session = get_session(str(session_id or ""), metadata_only=True)
    except Exception:
        return
    if not _session_wait_notifications_enabled(session):
        return
    webhook_url = _session_waiting_webhook_url(session)
    if not webhook_url:
        return
    safe_kind = str(kind or "input").strip() or "input"
    payload = {
        "event": "waiting_input",
        "kind": safe_kind,
        "session_id": str(getattr(session, "session_id", session_id) or ""),
        "session_title": str(getattr(session, "title", "") or ""),
        "pending_count": max(1, int(pending_count or 1)),
        "message": "Hermes WebUI is waiting for your input.",
        "question": str((pending_payload or {}).get("question") or ""),
        "description": str((pending_payload or {}).get("description") or ""),
        "tags": ["hermes", "waiting-input", safe_kind],
    }

    def _worker():
        try:
            _post_json(webhook_url, payload)
        except Exception as exc:
            logger.debug("waiting-input webhook dispatch failed for %s: %s", session_id, exc)

    threading.Thread(target=_worker, daemon=True).start()

