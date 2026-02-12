"""Confluence page rendering and API client for upgrade documentation.

Generates Confluence storage format XML matching the existing baseline
page structure, and provides create/update via the REST API v2.
"""

from html import escape
from typing import Any

import httpx

from .release import Defect, Enhancement, Release
from .upgrade import UpgradeModule, UpgradeRound, parse_module_name

SERVICENOW_BASE = "https://elluciansupport.service-now.com"


class ConfluenceError(Exception):
    """Confluence API operation failed."""

    pass


# ---------------------------------------------------------------------------
# Storage format rendering
# ---------------------------------------------------------------------------


_BOILERPLATE_PHRASES = [
    "This release includes changes to improve product quality",
]


def _is_boilerplate(text: str) -> bool:
    """Check if text is generic boilerplate that adds no value."""
    return any(phrase in text for phrase in _BOILERPLATE_PHRASES)


def _release_type_label(release: Release) -> str:
    """Determine the Defect/Enhancement/Regulatory label for a release."""
    parts = []
    if release.defects:
        parts.append("Defect")
    if release.enhancements:
        parts.append("Enhancement")
    if release.release_purpose and "regulatory" in release.release_purpose.lower():
        parts.append("Regulatory")
    return "/".join(parts)


def _version_from_short_desc(short_description: str) -> str:
    """Extract version from short_description (the part after module name)."""
    module = parse_module_name(short_description)
    version = short_description[len(module):].strip()
    return version or short_description


def _format_date(date_str: str) -> str:
    """Format a date string for the Details table (MM-DD)."""
    if not date_str:
        return ""
    # Input: "2026-03-19" or "2026-03-19 00:00:00" → "03-19"
    parts = date_str.strip().split(" ")[0].split("-")
    if len(parts) >= 3:
        return f"{parts[1]}-{parts[2]}"
    return date_str


def _dependencies_html(prerequisites: list[str]) -> str:
    """Render prerequisite list as <p> elements."""
    if not prerequisites:
        return "<p />"
    return "".join(f"<p>{escape(p)}</p>" for p in prerequisites)


def _version_cell(version: str, link_url: str = "") -> str:
    """Render a version cell, optionally as a link."""
    v = escape(version)
    if link_url:
        return f'<p><a href="{escape(link_url)}">{v}</a></p>'
    return f"<p>{v}</p>"


def render_root_page(round_: UpgradeRound, detail_links: dict[str, str] = None) -> str:
    """Generate storage format XML for the baseline root page.

    Args:
        round_: The upgrade round data.
        detail_links: Optional map of module name -> Confluence page URL (tinyui).

    Returns:
        Confluence storage format XML string.
    """
    if detail_links is None:
        detail_links = {}

    # Build Details table rows
    detail_rows = []
    for module in round_.modules:
        for i, release in enumerate(module.releases):
            version = _version_from_short_desc(release.short_description)
            date_str = _format_date(release.target_ga_date or release.date_released)
            type_label = _release_type_label(release)
            deps_html = _dependencies_html(release.prerequisites)
            link = detail_links.get(module.name, "")
            ver_html = _version_cell(version, link)

            # Module name only on first row of group
            module_cell = f"<p>{escape(module.name)}</p>" if i == 0 else "<p />"

            detail_rows.append(
                f"<tr>"
                f"<td>{module_cell}</td>"
                f"<td>{ver_html}</td>"
                f"<td><p>{escape(date_str)}</p></td>"
                f"<td><p>{escape(type_label)}</p></td>"
                f"<td>{deps_html}</td>"
                f"</tr>"
            )

    details_html = "".join(detail_rows)

    # Module list for synopsis placeholder
    module_names = ", ".join(m.name for m in round_.modules)

    return (
        '<ac:layout>'
        # Two-column header
        '<ac:layout-section ac:type="two_right_sidebar" ac:breakout-mode="wide" ac:breakout-width="1388">'
        '<ac:layout-cell>'
        '<p><strong>Synopsis</strong></p>'
        f'<p>Baseline upgrade documentation for {escape(round_.title)}. '
        f'Cutoff date: {escape(round_.cutoff_date)}.</p>'
        f'<p>Modules included: {escape(module_names)}</p>'
        '</ac:layout-cell>'
        '<ac:layout-cell>'
        '<p><strong>Campus Details</strong></p>'
        '<p />'
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        '<ac:rich-text-body>'
        '<p><strong>Special Upgrade Instructions</strong></p>'
        '<p />'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
        '<p />'
        '</ac:layout-cell>'
        '</ac:layout-section>'
        # Full-width body
        '<ac:layout-section ac:type="fixed-width" ac:breakout-mode="default">'
        '<ac:layout-cell>'
        '<h3>Local Objects Requiring Testing</h3>'
        '<p />'
        '<h3>Timeline</h3>'
        '<table data-table-width="760" data-layout="default">'
        '<colgroup>'
        '<col style="width: 152.0px;" />'
        '<col style="width: 152.0px;" />'
        '<col style="width: 192.0px;" />'
        '<col style="width: 138.0px;" />'
        '<col style="width: 124.0px;" />'
        '</colgroup>'
        '<tbody>'
        '<tr>'
        '<th><p><strong>Environment</strong></p></th>'
        '<th><p><strong>Release Date</strong></p></th>'
        '<th><p><strong>Proposed Dates</strong></p></th>'
        '<th><p /></th>'
        '<th><p /></th>'
        '</tr>'
        '<tr><td><p>UPGR</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '<tr><td><p>TEST</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '<tr><td><p>PROD</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '<tr><td><p>DEVL</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '</tbody>'
        '</table>'
        '<h3>Details</h3>'
        '<table data-table-width="1032" data-layout="center">'
        '<colgroup>'
        '<col style="width: 221.0px;" />'
        '<col style="width: 143.0px;" />'
        '<col style="width: 137.0px;" />'
        '<col style="width: 217.0px;" />'
        '<col style="width: 314.0px;" />'
        '</colgroup>'
        '<tbody>'
        '<tr>'
        '<th><p><strong>Module</strong></p></th>'
        '<th><p><strong>Latest Version</strong></p></th>'
        '<th><p><strong>Release Date</strong></p></th>'
        '<th><p><strong>Defect/Enhancement/Regulatory</strong></p></th>'
        '<th><p><strong>Dependencies</strong></p></th>'
        '</tr>'
        f'{details_html}'
        '</tbody>'
        '</table>'
        '<p />'
        '</ac:layout-cell>'
        '</ac:layout-section>'
        '</ac:layout>'
    )


def render_client_page(
    round_: UpgradeRound,
    installed_versions: dict[str, str],
    detail_links: dict[str, str] = None,
    client_name: str = "",
) -> str:
    """Generate storage format XML for a client-specific upgrade page.

    Produces a flat page (no child pages) with 6 columns:
    Module | Current Version | Latest Version | Release Date |
    Defect/Enhancement/Regulatory | Dependencies

    Only includes modules present in installed_versions.
    Latest Version links point to baseline detail pages (cross-space).

    Args:
        round_: The upgrade round data.
        installed_versions: Module name -> currently installed version.
        detail_links: Optional map of module name -> baseline detail page URL.
        client_name: Client name for synopsis (e.g. "FHDA").

    Returns:
        Confluence storage format XML string.
    """
    if detail_links is None:
        detail_links = {}

    # Filter to only installed modules
    installed_modules = [m for m in round_.modules if m.name in installed_versions]

    # Build Details table rows
    detail_rows = []
    for module in installed_modules:
        current_ver = installed_versions.get(module.name, "")
        for i, release in enumerate(module.releases):
            version = _version_from_short_desc(release.short_description)
            date_str = _format_date(release.target_ga_date or release.date_released)
            type_label = _release_type_label(release)
            deps_html = _dependencies_html(release.prerequisites)
            link = detail_links.get(module.name, "")
            ver_html = _version_cell(version, link)

            # Module name and current version only on first row of group
            module_cell = f"<p>{escape(module.name)}</p>" if i == 0 else "<p />"
            current_cell = f"<p>{escape(current_ver)}</p>" if i == 0 else "<p />"

            detail_rows.append(
                f"<tr>"
                f"<td>{module_cell}</td>"
                f"<td>{current_cell}</td>"
                f"<td>{ver_html}</td>"
                f"<td><p>{escape(date_str)}</p></td>"
                f"<td><p>{escape(type_label)}</p></td>"
                f"<td>{deps_html}</td>"
                f"</tr>"
            )

    details_html = "".join(detail_rows)

    # Module list for synopsis
    module_names = ", ".join(m.name for m in installed_modules)
    client_label = f"{client_name} " if client_name else ""

    return (
        '<ac:layout>'
        # Two-column header
        '<ac:layout-section ac:type="two_right_sidebar" ac:breakout-mode="wide" ac:breakout-width="1388">'
        '<ac:layout-cell>'
        '<p><strong>Synopsis</strong></p>'
        f'<p>{escape(client_label)}upgrade documentation for {escape(round_.title)}. '
        f'Cutoff date: {escape(round_.cutoff_date)}.</p>'
        f'<p>Modules included: {escape(module_names)}</p>'
        '</ac:layout-cell>'
        '<ac:layout-cell>'
        '<p><strong>Campus Details</strong></p>'
        '<p />'
        '<ac:structured-macro ac:name="note" ac:schema-version="1">'
        '<ac:rich-text-body>'
        '<p><strong>Special Upgrade Instructions</strong></p>'
        '<p />'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
        '<p />'
        '</ac:layout-cell>'
        '</ac:layout-section>'
        # Full-width body
        '<ac:layout-section ac:type="fixed-width" ac:breakout-mode="default">'
        '<ac:layout-cell>'
        '<h3>Local Objects Requiring Testing</h3>'
        '<p />'
        '<h3>Timeline</h3>'
        '<table data-table-width="760" data-layout="default">'
        '<colgroup>'
        '<col style="width: 152.0px;" />'
        '<col style="width: 152.0px;" />'
        '<col style="width: 192.0px;" />'
        '<col style="width: 138.0px;" />'
        '<col style="width: 124.0px;" />'
        '</colgroup>'
        '<tbody>'
        '<tr>'
        '<th><p><strong>Environment</strong></p></th>'
        '<th><p><strong>Release Date</strong></p></th>'
        '<th><p><strong>Proposed Dates</strong></p></th>'
        '<th><p /></th>'
        '<th><p /></th>'
        '</tr>'
        '<tr><td><p>UPGR</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '<tr><td><p>TEST</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '<tr><td><p>PROD</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '<tr><td><p>DEVL</p></td><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>'
        '</tbody>'
        '</table>'
        '<h3>Details</h3>'
        '<table data-table-width="1200" data-layout="center">'
        '<colgroup>'
        '<col style="width: 180.0px;" />'
        '<col style="width: 130.0px;" />'
        '<col style="width: 130.0px;" />'
        '<col style="width: 110.0px;" />'
        '<col style="width: 220.0px;" />'
        '<col style="width: 230.0px;" />'
        '</colgroup>'
        '<tbody>'
        '<tr>'
        '<th><p><strong>Module</strong></p></th>'
        '<th><p><strong>Current Version</strong></p></th>'
        '<th><p><strong>Latest Version</strong></p></th>'
        '<th><p><strong>Release Date</strong></p></th>'
        '<th><p><strong>Defect/Enhancement/Regulatory</strong></p></th>'
        '<th><p><strong>Dependencies</strong></p></th>'
        '</tr>'
        f'{details_html}'
        '</tbody>'
        '</table>'
        '<p />'
        '</ac:layout-cell>'
        '</ac:layout-section>'
        '</ac:layout>'
    )


# ---------------------------------------------------------------------------
# Status page — cross-client upgrade posture dashboard
# ---------------------------------------------------------------------------

# Thresholds for weighted score → color
_GREEN_MAX = 5
_YELLOW_MAX = 12


def _release_weight(release: Release) -> int:
    """Determine the urgency weight for a release.

    Returns:
        3 for regulatory releases,
        2 for security/CVE patches,
        1 for normal maintenance.
    """
    if release.release_purpose and "regulatory" in release.release_purpose.lower():
        return 3
    # Check defect summaries for CVE patterns
    for defect in release.defects:
        if "CVE-" in defect.summary.upper():
            return 2
    return 1


def compute_client_status(
    round_: UpgradeRound,
    installed_versions: dict[str, str],
    detail_links: dict[str, str],
    client_page_url: str = "",
    client_name: str = "",
) -> dict[str, Any]:
    """Compute upgrade status for a single client.

    Compares installed versions against the latest releases in the round
    to determine which modules are behind and compute a weighted score.

    Args:
        round_: The upgrade round data.
        installed_versions: Module name -> installed version string.
        detail_links: Module name -> baseline detail page URL.
        client_page_url: URL to the client's upgrade page.
        client_name: Display name for the client.

    Returns:
        Dict with color, score, behind_count, modules_behind details.
    """
    installed_modules = [m for m in round_.modules if m.name in installed_versions]
    modules_behind = []
    weighted_score = 0

    for module in installed_modules:
        if not module.releases:
            continue
        # The last release is the latest (sorted by date in gather)
        latest_release = module.releases[-1]
        latest_version = _version_from_short_desc(latest_release.short_description)
        current_version = installed_versions.get(module.name, "")

        # Simple string comparison — if installed matches latest, they're current.
        # Otherwise they're behind. We compare against ALL releases, not just latest,
        # because the client may be on an intermediate version.
        is_behind = current_version != latest_version

        if is_behind:
            # Use the highest weight across all releases for this module
            weight = max(_release_weight(r) for r in module.releases)
            type_label = _release_type_label(latest_release)
            modules_behind.append({
                "name": module.name,
                "installed": current_version,
                "latest": latest_version,
                "type_label": type_label,
                "weight": weight,
                "detail_link": detail_links.get(module.name, ""),
            })
            weighted_score += weight

    if weighted_score <= _GREEN_MAX:
        color = "green"
    elif weighted_score <= _YELLOW_MAX:
        color = "yellow"
    else:
        color = "red"

    return {
        "client_name": client_name,
        "client_page_url": client_page_url,
        "total_modules": len(installed_modules),
        "behind_count": len(modules_behind),
        "weighted_score": weighted_score,
        "color": color,
        "modules_behind": modules_behind,
    }


def render_status_page(
    client_statuses: list[dict[str, Any]],
    round_title: str,
) -> str:
    """Generate Confluence storage format for the cross-client status dashboard.

    Args:
        client_statuses: List of dicts from compute_client_status().
        round_title: e.g. "Spring 2026".

    Returns:
        Confluence storage format XML string.
    """
    color_map = {"green": "Green", "yellow": "Yellow", "red": "Red"}
    label_map = {"green": "Current", "yellow": "Behind", "red": "At Risk"}

    rows = []
    for cs in client_statuses:
        conf_color = color_map.get(cs["color"], "Grey")
        conf_label = label_map.get(cs["color"], "Unknown")

        # Client name as link to their upgrade page
        name = escape(cs["client_name"])
        if cs.get("client_page_url"):
            name_cell = f'<a href="{escape(cs["client_page_url"])}">{name}</a>'
        else:
            name_cell = name

        # Status lozenge using Confluence status macro
        status_macro = (
            f'<ac:structured-macro ac:name="status" ac:schema-version="1">'
            f'<ac:parameter ac:name="colour">{conf_color}</ac:parameter>'
            f'<ac:parameter ac:name="title">{conf_label}</ac:parameter>'
            f'</ac:structured-macro>'
        )

        # Progress: up-to-date / total
        up_to_date = cs["total_modules"] - cs["behind_count"]

        # Expand macro with module-level detail
        if cs["modules_behind"]:
            detail_rows = []
            for mb in cs["modules_behind"]:
                w_label = ""
                if mb["weight"] == 3:
                    w_label = " (regulatory)"
                elif mb["weight"] == 2:
                    w_label = " (security)"
                mod_name = escape(mb["name"])
                if mb.get("detail_link"):
                    mod_name = f'<a href="{escape(mb["detail_link"])}">{mod_name}</a>'
                detail_rows.append(
                    f'<tr>'
                    f'<td><p>{mod_name}</p></td>'
                    f'<td><p>{escape(mb["installed"])}</p></td>'
                    f'<td><p>{escape(mb["latest"])}</p></td>'
                    f'<td><p>{escape(mb["type_label"])}{escape(w_label)}</p></td>'
                    f'</tr>'
                )
            detail_table = (
                '<table data-table-width="760" data-layout="default">'
                '<colgroup>'
                '<col style="width: 200.0px;" />'
                '<col style="width: 140.0px;" />'
                '<col style="width: 140.0px;" />'
                '<col style="width: 280.0px;" />'
                '</colgroup>'
                '<tbody>'
                '<tr>'
                '<th><p><strong>Module</strong></p></th>'
                '<th><p><strong>Installed</strong></p></th>'
                '<th><p><strong>Latest</strong></p></th>'
                '<th><p><strong>Type</strong></p></th>'
                '</tr>'
                + "".join(detail_rows) +
                '</tbody>'
                '</table>'
            )
            expand_html = (
                f'<ac:structured-macro ac:name="expand" ac:schema-version="1">'
                f'<ac:parameter ac:name="title">{cs["behind_count"]} modules behind</ac:parameter>'
                f'<ac:rich-text-body>'
                f'{detail_table}'
                f'</ac:rich-text-body>'
                f'</ac:structured-macro>'
            )
        else:
            expand_html = '<p />'

        rows.append(
            f'<tr>'
            f'<td><p>{name_cell}</p></td>'
            f'<td><p>{status_macro}</p></td>'
            f'<td><p>{cs["total_modules"]}</p></td>'
            f'<td><p>{cs["behind_count"]}</p></td>'
            f'<td><p>{up_to_date}</p></td>'
            f'<td><p>{cs["weighted_score"]}</p></td>'
            f'<td>{expand_html}</td>'
            f'</tr>'
        )

    rows_html = "".join(rows)

    return (
        f'<h2>Upgrade Status — {escape(round_title)}</h2>'
        '<p>Weighted scoring: regulatory releases count 3x, '
        'security/CVE patches count 2x, maintenance releases count 1x. '
        'Green ≤ 5, Yellow 6-12, Red 13+.</p>'
        '<table data-table-width="1200" data-layout="center">'
        '<colgroup>'
        '<col style="width: 160.0px;" />'
        '<col style="width: 120.0px;" />'
        '<col style="width: 90.0px;" />'
        '<col style="width: 90.0px;" />'
        '<col style="width: 110.0px;" />'
        '<col style="width: 90.0px;" />'
        '<col style="width: 340.0px;" />'
        '</colgroup>'
        '<tbody>'
        '<tr>'
        '<th><p><strong>Client</strong></p></th>'
        '<th><p><strong>Status</strong></p></th>'
        '<th><p><strong>Modules</strong></p></th>'
        '<th><p><strong>Behind</strong></p></th>'
        '<th><p><strong>Up to Date</strong></p></th>'
        '<th><p><strong>Score</strong></p></th>'
        '<th><p><strong>Details</strong></p></th>'
        '</tr>'
        f'{rows_html}'
        '</tbody>'
        '</table>'
    )


def _defect_link(defect: Defect) -> str:
    """Build a link to the defect in Ellucian Support."""
    url = (
        f"{SERVICENOW_BASE}/customer_center"
        f"?id=standard_ticket&table=ellucian_product_defect"
        f"&sys_id={defect.sys_id}"
    )
    return f'<a href="{escape(url)}">{escape(defect.number)}</a>'


def _enhancement_link(enh: Enhancement) -> str:
    """Build a link to the enhancement in Ellucian Support."""
    url = (
        f"{SERVICENOW_BASE}/customer_center"
        f"?id=standard_ticket&table=ellucian_product_enhancement"
        f"&sys_id={enh.sys_id}"
    )
    return f'<a href="{escape(url)}">{escape(enh.number)}</a>'


def render_detail_page(module: UpgradeModule) -> str:
    """Generate storage format XML for a module detail page.

    Args:
        module: The UpgradeModule with releases containing defects/enhancements.

    Returns:
        Confluence storage format XML string.
    """
    # Collect all enhancements and defects across releases
    enhancement_rows = []
    defect_rows = []

    for release in module.releases:
        version = _version_from_short_desc(release.short_description)

        for enh in release.enhancements:
            enhancement_rows.append(
                f"<tr>"
                f"<td><p>{escape(version)}</p></td>"
                f"<td><p>{_enhancement_link(enh)}</p></td>"
                f"<td><p>{escape(enh.summary)}</p></td>"
                f"<td><p /></td>"
                f"</tr>"
            )

        for defect in release.defects:
            defect_rows.append(
                f"<tr>"
                f"<td><p>{escape(version)}</p></td>"
                f"<td><p>{_defect_link(defect)}</p></td>"
                f"<td><p>{escape(defect.summary)}</p></td>"
                f"<td><p /></td>"
                f"</tr>"
            )

    # If no rows, add an empty placeholder row
    if not enhancement_rows:
        enhancement_rows.append(
            "<tr><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>"
        )
    if not defect_rows:
        defect_rows.append(
            "<tr><td><p /></td><td><p /></td><td><p /></td><td><p /></td></tr>"
        )

    enhancements_html = "".join(enhancement_rows)
    defects_html = "".join(defect_rows)

    # Build synopsis from release descriptions
    synopsis_parts = []
    for release in module.releases:
        version = _version_from_short_desc(release.short_description)
        desc = release.summary or release.description or ""
        if desc and not _is_boilerplate(desc):
            synopsis_parts.append(f"<li><p>{escape(version)}: {escape(desc)}</p></li>")

    if synopsis_parts:
        synopsis_html = f'<ul>{"".join(synopsis_parts)}</ul>'
    else:
        synopsis_html = "<p />"

    return (
        '<ac:layout>'
        # Two-column header
        '<ac:layout-section ac:type="two_right_sidebar" ac:breakout-mode="wide" ac:breakout-width="1800">'
        '<ac:layout-cell>'
        '<h3><strong>Synopsis</strong></h3>'
        f'{synopsis_html}'
        '</ac:layout-cell>'
        '<ac:layout-cell>'
        '<ac:structured-macro ac:name="panel" ac:schema-version="1">'
        '<ac:parameter ac:name="panelIcon">:note:</ac:parameter>'
        '<ac:parameter ac:name="panelIconId">atlassian-note</ac:parameter>'
        '<ac:parameter ac:name="bgColor">#F4F5F7</ac:parameter>'
        '<ac:rich-text-body>'
        '<p><strong>Upgrade Notes</strong></p>'
        '</ac:rich-text-body>'
        '</ac:structured-macro>'
        '</ac:layout-cell>'
        '</ac:layout-section>'
        # Full-width body
        '<ac:layout-section ac:type="fixed-width" ac:breakout-mode="default">'
        '<ac:layout-cell>'
        '<p />'
        '<h3>Enhancements</h3>'
        '<table data-table-width="1136" data-layout="center">'
        '<colgroup>'
        '<col style="width: 227.0px;" />'
        '<col style="width: 263.0px;" />'
        '<col style="width: 374.0px;" />'
        '<col style="width: 272.0px;" />'
        '</colgroup>'
        '<tbody>'
        '<tr>'
        '<th><p><strong>Module/Version</strong></p></th>'
        '<th><p><strong>Change Request</strong></p></th>'
        '<th><p><strong>Details</strong></p></th>'
        '<th><p><strong>Testing Notes</strong></p></th>'
        '</tr>'
        f'{enhancements_html}'
        '</tbody>'
        '</table>'
        '<h3>Defects</h3>'
        '<table data-table-width="1106" data-layout="center">'
        '<colgroup>'
        '<col style="width: 220.0px;" />'
        '<col style="width: 259.0px;" />'
        '<col style="width: 365.0px;" />'
        '<col style="width: 262.0px;" />'
        '</colgroup>'
        '<tbody>'
        '<tr>'
        '<th><p><strong>Module/Version</strong></p></th>'
        '<th><p><strong>Change Request</strong></p></th>'
        '<th><p><strong>Details</strong></p></th>'
        '<th><p><strong>Testing Notes</strong></p></th>'
        '</tr>'
        f'{defects_html}'
        '</tbody>'
        '</table>'
        '</ac:layout-cell>'
        '</ac:layout-section>'
        '</ac:layout>'
    )


def _detail_page_title(module: UpgradeModule) -> str:
    """Generate a detail page title from module data.

    Combines module name with version(s), e.g. "BA FIN AID 8.56/9.3.57".
    """
    versions = []
    for r in module.releases:
        v = _version_from_short_desc(r.short_description)
        if v and v not in versions:
            versions.append(v)
    if versions:
        return f"{module.name} {'/'.join(versions)}"
    return module.name


# ---------------------------------------------------------------------------
# Confluence REST API v2
# ---------------------------------------------------------------------------


def _confluence_headers(user: str, token: str) -> dict[str, str]:
    """Build auth headers for Confluence API."""
    import base64

    credentials = base64.b64encode(f"{user}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_page(
    title: str,
    space_id: str,
    parent_id: str,
    body: str,
    user: str,
    token: str,
    site: str,
) -> dict[str, Any]:
    """Create a Confluence page via REST API v2.

    Args:
        title: Page title.
        space_id: Confluence space ID.
        parent_id: Parent page or folder ID.
        body: Storage format XML body.
        user: Atlassian user email.
        token: Atlassian API token.
        site: Atlassian site (e.g. "apogeetelecom.atlassian.net").

    Returns:
        Page metadata dict including id, _links.tinyui.

    Raises:
        ConfluenceError: If creation fails.
    """
    url = f"https://{site}/wiki/api/v2/pages"
    headers = _confluence_headers(user, token)

    payload = {
        "spaceId": space_id,
        "status": "current",
        "title": title,
        "parentId": parent_id,
        "body": {
            "representation": "storage",
            "value": body,
        },
    }

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=headers, json=payload)

    if resp.status_code not in (200, 201):
        raise ConfluenceError(
            f"Failed to create page '{title}': HTTP {resp.status_code} — {resp.text[:500]}"
        )

    return resp.json()


def update_page(
    page_id: str,
    title: str,
    body: str,
    version: int,
    user: str,
    token: str,
    site: str,
) -> dict[str, Any]:
    """Update an existing Confluence page via REST API v2.

    Args:
        page_id: Confluence page ID.
        title: Page title.
        body: New storage format XML body.
        version: New version number (current + 1).
        user: Atlassian user email.
        token: Atlassian API token.
        site: Atlassian site.

    Returns:
        Updated page metadata.

    Raises:
        ConfluenceError: If update fails.
    """
    url = f"https://{site}/wiki/api/v2/pages/{page_id}"
    headers = _confluence_headers(user, token)

    payload = {
        "id": page_id,
        "status": "current",
        "title": title,
        "version": {"number": version},
        "body": {
            "representation": "storage",
            "value": body,
        },
    }

    with httpx.Client(timeout=60.0) as client:
        resp = client.put(url, headers=headers, json=payload)

    if resp.status_code != 200:
        raise ConfluenceError(
            f"Failed to update page {page_id}: HTTP {resp.status_code} — {resp.text[:500]}"
        )

    return resp.json()


def publish_upgrade_round(
    round_: UpgradeRound,
    space_id: str,
    parent_id: str,
    user: str,
    token: str,
    site: str,
    dry_run: bool = False,
    progress_callback=None,
) -> dict[str, Any]:
    """Publish a complete upgrade round to Confluence.

    Creates detail pages first (to get tinyui links), then creates the
    root page with links to details.

    Args:
        round_: The upgrade round data.
        space_id: Confluence space ID.
        parent_id: Parent folder/page ID.
        user: Atlassian user email.
        token: Atlassian API token.
        site: Atlassian site.
        dry_run: If True, generate HTML but don't create pages.
        progress_callback: Optional callable(message: str).

    Returns:
        Dict with root_page info and detail_pages list.
    """

    def _log(msg: str):
        if progress_callback:
            progress_callback(msg)

    result = {"root_page": None, "detail_pages": []}

    if dry_run:
        _log("DRY RUN — generating HTML without creating pages")
        root_html = render_root_page(round_)
        result["root_page"] = {"title": round_.title, "html": root_html}
        for module in round_.modules:
            title = _detail_page_title(module)
            html = render_detail_page(module)
            result["detail_pages"].append({"title": title, "html": html})
        _log(f"Would create 1 root + {len(round_.modules)} detail pages")
        return result

    # Step 1: Create root page first (needed as parent for detail pages)
    _log(f"Creating root page: {round_.title}")
    root_body = render_root_page(round_)  # Initial version without detail links
    root_page = create_page(round_.title, space_id, parent_id, root_body, user, token, site)
    root_page_id = root_page["id"]
    _log(f"  Root page created: id={root_page_id}")

    # Step 2: Create detail pages as children of root
    detail_links = {}
    for i, module in enumerate(round_.modules, 1):
        title = _detail_page_title(module)
        _log(f"  Creating detail page ({i}/{len(round_.modules)}): {title}")
        body = render_detail_page(module)
        detail_page = create_page(title, space_id, root_page_id, body, user, token, site)
        tinyui = detail_page.get("_links", {}).get("tinyui", "")
        if tinyui and not tinyui.startswith("http"):
            tinyui = f"https://{site}/wiki{tinyui}"
        detail_links[module.name] = tinyui
        result["detail_pages"].append({
            "title": title,
            "id": detail_page["id"],
            "url": tinyui,
        })

    # Step 3: Update root page with detail links
    _log("Updating root page with detail links...")
    root_body_with_links = render_root_page(round_, detail_links)
    updated_root = update_page(
        root_page_id, round_.title, root_body_with_links,
        version=2, user=user, token=token, site=site,
    )
    root_tinyui = updated_root.get("_links", {}).get("tinyui", "")
    if root_tinyui and not root_tinyui.startswith("http"):
        root_tinyui = f"https://{site}/wiki{root_tinyui}"
    result["root_page"] = {
        "title": round_.title,
        "id": root_page_id,
        "url": root_tinyui,
    }

    _log(f"Published {round_.title}: 1 root + {len(round_.modules)} detail pages")
    return result
