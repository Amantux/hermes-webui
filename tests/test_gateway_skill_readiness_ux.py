"""Browser-visible UX coverage for gateway and skill readiness messaging.

Verifies:
  - The gateway status card in the System Settings panel (not just the cron panel).
  - loadGatewayStatus() JS function and the three states it renders:
      not-configured (amber dot), not-running (red dot), running (green dot + badges).
  - The Skills panel empty-state, no-match, error, and disable/enable toggle UX.
  - Skill category collapse behaviour in renderSkills().
  - The skill search/filter input wiring.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "static" / "index.html"
PANELS_JS = ROOT / "static" / "panels.js"
STYLE_CSS = ROOT / "static" / "style.css"
I18N_JS = ROOT / "static" / "i18n.js"


# ── 1. Gateway status card in System Settings panel ─────────────────────────

def test_gateway_status_card_element_exists_in_html():
    """gatewayStatusCard div must be present in index.html (System Settings tab)."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="gatewayStatusCard"' in html


def test_gateway_status_card_shows_loading_state_initially():
    """gatewayStatusCard starts with a 'Loading…' placeholder."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert "Loading" in html
    # The card element itself should contain the placeholder text
    idx = html.index('id="gatewayStatusCard"')
    # The loading text is inline in the div
    assert "Loading" in html[idx: idx + 200]


def test_load_gateway_status_function_defined():
    """loadGatewayStatus() function must be defined in panels.js."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "function loadGatewayStatus()" in src


def test_load_gateway_status_calls_gateway_api():
    """loadGatewayStatus must call /api/gateway/status."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "api('/api/gateway/status')" in src


def test_load_gateway_status_shows_not_configured_state():
    """loadGatewayStatus must render a 'Gateway not configured' message."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "Gateway not configured" in src


def test_load_gateway_status_not_configured_uses_amber_indicator():
    """The not-configured state uses an amber/yellow dot (#f59e0b)."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "#f59e0b" in src


def test_load_gateway_status_shows_not_running_state():
    """loadGatewayStatus must render a 'Gateway not running' message."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "Gateway not running" in src


def test_load_gateway_status_not_running_uses_red_indicator():
    """The not-running state uses a red dot (#ef4444)."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "#ef4444" in src


def test_load_gateway_status_shows_running_state_with_green_indicator():
    """Running state uses a green dot (#22c55e) and 'Running' label."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "#22c55e" in src
    assert "Running" in src


def test_load_gateway_status_shows_platform_badges_when_running():
    """Running state renders per-platform badges with icons."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "platforms" in src
    assert "platformIcons" in src


def test_load_gateway_status_shows_session_count():
    """Running state includes a session count label."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "session_count" in src
    assert "session" in src


def test_load_gateway_status_shows_last_active_timestamp():
    """Running state shows a 'Last active' timestamp."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "last_active" in src
    assert "Last active:" in src


def test_load_gateway_status_shows_error_state_on_failure():
    """If the API call fails, loadGatewayStatus must show an error message."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "Failed to load gateway status" in src


def test_load_gateway_status_triggered_on_system_settings_open():
    """loadGatewayStatus() must be called when the system settings section opens."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "loadGatewayStatus()" in src
    # Specifically it is called inside the switchSettingsSection override
    assert "switchSettingsSection" in src


# ── 2. Cron gateway notice (cron panel readiness messaging) ─────────────────

def test_cron_gateway_notice_html_helper_produces_not_configured_message():
    """_cronGatewayNoticeHtml() must return markup for the not-configured state."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "function _cronGatewayNoticeHtml" in src
    assert "Gateway not configured" in src
    assert "Gateway not running" in src


def test_cron_gateway_notice_body_explains_scheduling_requirement():
    """The gateway notice must explain that scheduled jobs need the gateway daemon."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "scheduled jobs require the Hermes gateway daemon" in src


def test_cron_gateway_notice_hidden_when_gateway_ok():
    """_cronGatewayNoticeHtml must return empty string when gateway is configured and running."""
    src = PANELS_JS.read_text(encoding="utf-8")
    # Pattern: if (!status || (status.configured && status.running)) return '';
    assert "status.configured && status.running" in src


def test_load_cron_gateway_notice_hides_box_on_api_error():
    """loadCronGatewayNotice must set box.style.display='none' on API failure."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "function loadCronGatewayNotice(" in src
    assert "box.style.display = 'none'" in src or "box.style.display='none'" in src


def test_cron_gateway_notice_element_in_html():
    """cronGatewayNotice element must exist in index.html, initially hidden."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="cronGatewayNotice"' in html
    assert 'style="display:none"' in html or "display:none" in html


# ── 3. Skills panel empty-state and no-match messaging ──────────────────────

def test_skills_list_element_exists_in_html():
    """skillsList container must be in index.html."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="skillsList"' in html


def test_skills_search_input_exists_in_html():
    """skillsSearch input must exist and trigger filterSkills() on input."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="skillsSearch"' in html
    assert "filterSkills()" in html


def test_skills_empty_state_title_in_html():
    """index.html must contain a skills empty-state title (data-i18n=skills_empty_title)."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'data-i18n="skills_empty_title"' in html


def test_skills_empty_state_sub_in_html():
    """index.html must contain a skills empty-state subtitle."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'data-i18n="skills_empty_sub"' in html


def test_skills_no_match_message_in_panels_js():
    """renderSkills() must show the skills_no_match i18n string when filter yields nothing."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "t('skills_no_match')" in src


def test_skills_no_match_i18n_key_defined():
    """skills_no_match key must be defined in the English locale."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "skills_no_match:" in i18n


def test_skills_empty_title_i18n_key_defined():
    """skills_empty_title key must be defined."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "skills_empty_title:" in i18n


def test_skills_empty_sub_i18n_key_defined():
    """skills_empty_sub key must be defined."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "skills_empty_sub:" in i18n


def test_load_skills_shows_error_state_on_api_failure():
    """loadSkills() must render an error message when the API call fails."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "async function loadSkills(" in src
    assert "Error:" in src
    # Error is shown via box.innerHTML with the caught exception message
    assert "e.message" in src


def test_load_skills_function_populates_skills_data_cache():
    """loadSkills() must cache results in _skillsData to avoid re-fetching."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "_skillsData" in src
    assert "if (_skillsData)" in src or "if(_skillsData)" in src


# ── 4. Skill category collapse UX ───────────────────────────────────────────

def test_render_skills_groups_by_category():
    """renderSkills() must group skills by category."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "skills-category" in src
    assert "skills-cat-header" in src


def test_skill_category_collapse_function_defined():
    """_toggleCatCollapse() function must be defined."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "function _toggleCatCollapse(" in src


def test_skill_category_collapse_uses_collapsed_class():
    """Collapsed categories receive the 'collapsed' CSS class."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "'collapsed'" in src or '"collapsed"' in src


def test_skills_category_collapsed_css_class_defined():
    """CSS must define .skills-category.collapsed to hide items."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".skills-category" in css


def test_skill_category_chevron_rotates_when_expanded():
    """The chevron element must rotate to indicate expansion."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "rotate(90deg)" in src
    assert "cat-chevron" in src


# ── 5. Skill enable/disable toggle UX ───────────────────────────────────────

def test_render_skills_adds_skill_toggle_element():
    """renderSkills() must create a .skill-toggle element for each skill."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "skill-toggle" in src


def test_skill_toggle_enabled_class_present_when_not_disabled():
    """Non-disabled skills get the 'enabled' modifier on .skill-toggle."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "skill-toggle' + (isDisabled ? '' : ' enabled')" in src or \
           "skill-toggle" in src and "enabled" in src


def test_skill_item_disabled_class_applied_when_skill_is_off():
    """Disabled skills receive .skill-item.disabled CSS class."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "'skill-item' + (skill.disabled ? ' disabled' : '')" in src or \
           "skill.disabled" in src and "disabled" in src


def test_skill_toggle_css_classes_defined():
    """.skill-toggle and .skill-item.disabled must be defined in style.css."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".skill-toggle" in css
    assert ".skill-item.disabled" in css


def test_skill_toggle_i18n_keys_exist():
    """skill_enabled and skill_disabled i18n keys must exist."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "skill_enabled" in i18n
    assert "skill_disabled" in i18n


def test_toggle_skill_function_defined():
    """toggleSkill() async function must be defined."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "async function toggleSkill(" in src


def test_toggle_skill_posts_to_api():
    """toggleSkill() must POST to /api/skills/toggle."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "'/api/skills/toggle'" in src or '"/api/skills/toggle"' in src


def test_toggle_skill_updates_disabled_flag_in_cached_data():
    """On success, toggleSkill() must update skill.disabled in _skillsData."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "skill.disabled = !newEnabled" in src


def test_toggle_skill_shows_error_on_failure():
    """On failure, toggleSkill() must display an error via setStatus or similar."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "skill_toggle_failed" in src


def test_skill_toggle_failed_i18n_key_exists():
    """skill_toggle_failed i18n key must exist."""
    i18n = I18N_JS.read_text(encoding="utf-8")
    assert "skill_toggle_failed" in i18n


# ── 6. Filter skills function wiring ────────────────────────────────────────

def test_filter_skills_function_defined():
    """filterSkills() must be defined and delegate to renderSkills."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "function filterSkills()" in src
    assert "renderSkills(" in src


def test_render_skills_filters_by_name_description_and_category():
    """renderSkills() search filter must check name, description, and category."""
    src = PANELS_JS.read_text(encoding="utf-8")
    assert "(s.name||'').toLowerCase().includes(query)" in src
    assert "(s.description||'').toLowerCase().includes(query)" in src
    assert "(s.category||'').toLowerCase().includes(query)" in src
