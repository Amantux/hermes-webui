"""Browser-visible UX coverage for waiting-input notifications and session toggle.

Verifies:
  - The session action-menu toggle button for per-session waiting-input notifications.
  - Label text, active-state CSS class, and toast messages shown when toggling.
  - The approval-card and clarify-card DOM structure used to present waiting-input
    prompts to the user (the browser-visible "waiting for input" UX).
  - CSS rules that animate / reveal those cards.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "static" / "index.html"
SESSIONS_JS = ROOT / "static" / "sessions.js"
MESSAGES_JS = ROOT / "static" / "messages.js"
STYLE_CSS = ROOT / "static" / "style.css"
I18N_JS = ROOT / "static" / "i18n.js"


# ── 1. Session action-menu: waiting-input notify toggle ─────────────────────

def test_session_action_menu_has_waiting_notify_toggle():
    """sessions.js builds a menu item that reads notify_on_waiting_input."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "notify_on_waiting_input" in src, (
        "Expected notify_on_waiting_input field to be referenced in sessions.js"
    )
    assert "waitingNotifyEnabled" in src, (
        "Expected a waitingNotifyEnabled local variable derived from session state"
    )


def test_session_notify_toggle_label_when_disabled():
    """When notify is off the menu shows 'Notify me when waiting for input'."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "Notify me when waiting for input" in src


def test_session_notify_toggle_label_when_enabled():
    """When notify is on the menu shows 'Disable waiting-input notify'."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "Disable waiting-input notify" in src


def test_session_notify_toggle_uses_is_active_class_when_enabled():
    """The menu item receives the is-active CSS class when notify is enabled."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    # The pattern: waitingNotifyEnabled?'is-active':'' passed to _buildSessionAction
    assert "waitingNotifyEnabled?'is-active':''" in src or \
           "waitingNotifyEnabled ? 'is-active' : ''" in src


def test_session_notify_toggle_posts_to_session_update_endpoint():
    """The toggle handler POSTs to /api/session/update with notify_on_waiting_input."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "/api/session/update" in src
    assert "notify_on_waiting_input:nextEnabled" in src or \
           "notify_on_waiting_input: nextEnabled" in src


def test_session_notify_toggle_updates_session_state_in_memory():
    """After the API call, session.notify_on_waiting_input is updated in memory."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "session.notify_on_waiting_input = !!updated.notify_on_waiting_input" in src


def test_session_notify_toggle_syncs_active_session_state():
    """If toggled session is the active session, S.session.notify_on_waiting_input is synced."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "S.session.notify_on_waiting_input = session.notify_on_waiting_input" in src


def test_session_notify_toggle_shows_enable_toast():
    """Enabling notifications shows a confirmation toast."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "Waiting-input notifications enabled for this conversation." in src


def test_session_notify_toggle_shows_disable_toast():
    """Disabling notifications shows a confirmation toast."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "Waiting-input notifications disabled for this conversation." in src


def test_session_notify_toggle_shows_error_toast_on_failure():
    """On API error, a toast is shown with the error message."""
    src = SESSIONS_JS.read_text(encoding="utf-8")
    assert "Failed to update waiting-input notifications:" in src


# ── 2. CSS: is-active rule is visible in the action-menu ────────────────────

def test_session_action_opt_is_active_css_rule_exists():
    """CSS rule for .session-action-opt.is-active must exist so the active state
    is visually distinct when waiting-input notify is enabled."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".session-action-opt.is-active" in css


# ── 3. Approval card — waiting-input "approval required" UX ─────────────────

def test_approval_card_element_exists_in_html():
    """approvalCard div must be present in index.html."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="approvalCard"' in html


def test_approval_card_has_alertdialog_role():
    """Approval card must carry role=alertdialog for accessibility."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'role="alertdialog"' in html


def test_approval_card_has_allow_once_button():
    """'Allow once' button must exist (respondApproval('once'))."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "respondApproval('once')" in html
    assert 'id="approvalBtnOnce"' in html


def test_approval_card_has_deny_button():
    """'Deny' button must exist (respondApproval('deny'))."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "respondApproval('deny')" in html
    assert 'id="approvalBtnDeny"' in html


def test_approval_card_has_allow_session_button():
    """'Allow session' button must exist."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "respondApproval('session')" in html
    assert 'id="approvalBtnSession"' in html


def test_approval_card_has_always_allow_button():
    """'Always allow' button must exist."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "respondApproval('always')" in html
    assert 'id="approvalBtnAlways"' in html


def test_approval_card_has_skip_all_yolo_button():
    """'Skip all' (YOLO) button must be present in the approval card."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="approvalSkipAll"' in html
    assert "toggleYoloFromApproval()" in html


def test_approval_card_pending_counter_element_exists():
    """'1 of N' pending counter element must be present."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="approvalCounter"' in html


def test_approval_card_i18n_heading_key_exists():
    """approval_heading i18n key must exist in i18n.js."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "approval_heading:" in i18n


def test_approval_card_i18n_button_keys_exist():
    """All four approval button i18n keys must be defined."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    for key in ("approval_btn_once", "approval_btn_session", "approval_btn_always", "approval_btn_deny"):
        assert f"{key}:" in i18n, f"Missing i18n key: {key}"


def test_approval_card_css_visible_class_exists():
    """CSS must define .approval-card.visible to show the card."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".approval-card.visible" in css


def test_approval_card_css_slide_animation_exists():
    """Approval card must have a slide transition so the card animates into view."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".approval-card" in css
    # The inner div transforms for the slide-up animation
    assert ".approval-inner" in css


def test_show_approval_card_function_defined():
    """showApprovalCard() function must exist in messages.js."""
    src = MESSAGES_JS.read_text(encoding="utf-8")
    assert "function showApprovalCard(" in src


def test_approval_card_pending_count_shows_counter():
    """showApprovalCard must render '1 of N pending' when pendingCount > 1."""
    src = MESSAGES_JS.read_text(encoding="utf-8")
    assert "1 of " in src
    assert "pending" in src


# ── 4. Clarify card — waiting-input "clarification needed" UX ───────────────

def test_clarify_card_element_exists_in_html():
    """clarifyCard div must be present in index.html."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="clarifyCard"' in html


def test_clarify_card_has_dialog_role():
    """Clarify card must carry role=dialog for accessibility."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    # clarifyCard has role="dialog"
    assert 'id="clarifyCard" role="dialog"' in html or \
           'id="clarifyCard"\n' in html and 'role="dialog"' in html


def test_clarify_card_has_input_and_send_button():
    """Clarify card must contain a text input and a Send button."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="clarifyInput"' in html
    assert 'id="clarifySubmit"' in html


def test_clarify_card_has_collapse_button():
    """Clarify card must have a collapse button so the user can dismiss it visually."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="clarifyCollapse"' in html
    assert "toggleClarifyCardCollapsed()" in html


def test_clarify_card_has_countdown_element():
    """Clarify card must show a countdown element."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="clarifyCountdown"' in html


def test_clarify_card_i18n_heading_key_exists():
    """clarify_heading i18n key must exist."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "clarify_heading:" in i18n


def test_clarify_card_i18n_hint_key_exists():
    """clarify_hint i18n key must exist."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "clarify_hint:" in i18n


def test_clarify_card_css_visible_class_exists():
    """CSS must define .clarify-card.visible to show the card."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".clarify-card.visible" in css


def test_clarify_card_collapsed_css_class_exists():
    """CSS must define .clarify-card.collapsed so the card can be minimised."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".clarify-card.collapsed" in css


def test_show_clarify_card_function_defined():
    """showClarifyCard() function must exist in messages.js."""
    src = MESSAGES_JS.read_text(encoding="utf-8")
    assert "function showClarifyCard(" in src


def test_clarify_card_renders_choices_as_buttons():
    """showClarifyCard must create choice buttons from the choices array."""
    src = MESSAGES_JS.read_text(encoding="utf-8")
    assert "clarify-choice" in src
    assert "clarify-choice-badge" in src


def test_clarify_choices_el_hidden_when_no_choices():
    """Clarify choices container must be hidden when choices array is empty."""
    src = MESSAGES_JS.read_text(encoding="utf-8")
    assert "choicesEl.style.display = choices.length ? '' : 'none'" in src or \
           "choices.length ?" in src
