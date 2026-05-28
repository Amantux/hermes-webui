from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SESSIONS_JS = (ROOT / "static" / "sessions.js").read_text(encoding="utf-8")
MESSAGES_JS = (ROOT / "static" / "messages.js").read_text(encoding="utf-8")
PANELS_JS = (ROOT / "static" / "panels.js").read_text(encoding="utf-8")


def test_session_menu_exposes_waiting_input_notification_toggle():
    assert "Notify me when waiting for input" in SESSIONS_JS
    assert "notify_on_waiting_input:nextEnabled" in SESSIONS_JS
    assert "Waiting-input notifications enabled for this conversation." in SESSIONS_JS
    assert "Waiting-input notifications disabled for this conversation." in SESSIONS_JS


def test_browser_notifications_fire_for_waiting_input_events():
    assert "sendBrowserNotification('Approval required'" in MESSAGES_JS
    assert "sendBrowserNotification('Clarification needed'" in MESSAGES_JS
    assert "playNotificationSound();" in MESSAGES_JS


def test_gateway_readiness_notice_surfaces_in_tasks_panel():
    assert "_cronGatewayNoticeHtml" in PANELS_JS
    assert "Gateway not configured" in PANELS_JS
    assert "Gateway not running" in PANELS_JS
    assert "loadCronGatewayNotice" in PANELS_JS
    assert "/api/gateway/status" in PANELS_JS

