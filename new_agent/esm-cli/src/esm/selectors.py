"""Centralized CSS selectors and URL patterns for ESM page parsing.

Default selectors target ESM 24.x. Version-specific overrides are applied
based on the detected ESM version.
"""

# Default selectors (ESM 24.x)
SELECTORS = {
    # Tables
    "data_table": "table.simple-table",
    # Authentication
    "csrf_cookie": "XSRF-TOKEN",
    "csrf_header": "X-XSRF-TOKEN",
    "csrf_form_field": "_csrf",
    "login_form_action": "/login/authenticate",
    "login_success_indicator": "adminMain",
    "password_init_indicator": "initializeUserPrompt",
    # Navigation
    "main_content_header": ".main-content-header",
    "dialog_title": ".dialog-title",
    "nav_node": ".admin-main-nav-node",
    # Environment
    "env_nav_link": "[target-url*='adminEnv']",
    # Products
    "product_id_attr": "target-url",
    "product_id_pattern": r"productId=([^&]+)",
    # Upgrades
    "target_radio": "input[name='targetRadioSelection']",
    "property_checkbox": "input[name='adminEnvUpgradeSpecificSections']",
    "upgrade_props_btn": ".admin-env-upgrade-props-node",
    "save_props_btn": ".admin-env-save-upgrade-properties-btn",
    "install_releases_btn": ".admin-env-install-releases",
    "target_url_attr": "target-url",
    # Job Monitor
    "job_status_in_progress": ".icon-in-progress",
    "job_status_completed": ".icon-completed",
    "job_status_failed": ".icon-failed",
    "job_console": "#out",
    "job_refresh_btn": "#admin-main-job-monitor-refresh",
    "job_refresh_interval": "#jobMonitorRefreshIntervalFld",
    # Credentials
    "password_field": "input[type='password']",
    "text_field": "input[type='text']",
    # Documentation links
    "doc_link": ".doc-link",
    "doc_check_link": ".doc-check-link",
}

# URL patterns (relative to base /admin)
URL_PATTERNS = {
    "login_page": "/login/auth",
    "login_submit": "/login/authenticate",
    "logout": "/logout/index",
    "dashboard": "/adminMain/adminMain",
    "environments": "/adminMain/environments",
    "env_detail": "/adminEnv/adminEnv",
    "products": "/adminEnv/products",
    "machines": "/adminEnv/machines",
    "credentials": "/adminEnv/credentials",
    "available_releases": "/adminEnv/availableReleases",
    "upgrade_properties": "/adminEnv/upgradeSpecificProperties",
    "save_upgrade_properties": "/adminEnv/saveUpgradeSpecificProperties",
    "install_releases_prompt": "/adminEnv/installReleasesPrompt",
    "install_releases": "/adminEnv/installReleases",
    "upgrade_monitor": "/adminEnv/upgradeMonitor",
    "select_target": "/adminEnv/selectTarget",
}

# Version-specific overrides
VERSION_OVERRIDES: dict[str, dict[str, str]] = {
    # Placeholder for future ESM versions with different selectors
    # "23.": {
    #     "data_table": "table.data-grid",
    # },
}


def get_selectors(version: str | None = None) -> dict[str, str]:
    """Get selectors, optionally applying version-specific overrides.

    Args:
        version: ESM version string (e.g., "24.2.0"). If None, returns defaults.

    Returns:
        Dict of selector names to CSS selectors/patterns.
    """
    result = SELECTORS.copy()
    if version:
        for ver_prefix, overrides in VERSION_OVERRIDES.items():
            if version.startswith(ver_prefix):
                result.update(overrides)
                break
    return result


def get_url_patterns(version: str | None = None) -> dict[str, str]:
    """Get URL patterns, optionally applying version-specific overrides.

    Args:
        version: ESM version string. Currently unused but reserved for future.

    Returns:
        Dict of endpoint names to URL patterns.
    """
    # No version-specific URL overrides yet
    return URL_PATTERNS.copy()
