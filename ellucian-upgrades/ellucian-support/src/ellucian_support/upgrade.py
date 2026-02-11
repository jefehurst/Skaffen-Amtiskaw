"""Upgrade round data gathering and grouping.

Orchestrates gathering all release data for a quarterly upgrade round,
grouping by module and filtering out irrelevant releases.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .auth import AuthSession
from .release import (
    BANNER_PRODUCT_LINE_ID,
    Release,
    enrich_release,
    query_releases,
)

# ESM product name → ServiceNow module name
# Seeded from ESM PROD product list + Winter 2025 FHDA page
ESM_TO_MODULE = {
    "General DB": "BA GENERAL CMN DB",
    "Accounts Receivable": "Banner Accounts Receivable",
    "Application Navigator": "BA GEN AppNav",
    "Financial Aid": "BA FIN AID",
    "CAL-B Student": "BA CALBSTU",
    "General": "BA GENERAL",
    "General Self Service": "BA GENERAL SELF-SERVICE",
    "Finance": "BA FINANCE",
    "Finance Self Service": "BA WWW-FIN",
    "Employee Self Service": "BA WWW-EMP",
    "Registration Self Service": "Banner Student Registration Self-Service",
    "Student": "Banner Student",
    "Student Self Service": "Banner Student Self-Service",
    "Event Publisher": "Banner Event Publisher",
    "Business Process API": "BA GEN BUS PROC API",
    "Student API": "Banner Student API",
    "HR": "BA HR",
    "Position Control": "BA POS CONT",
    "CAL-B Financial Aid": "BA CALBHR",
    "Document Management API": "Banner Document Management API",
    "Event Publisher DB": "Banner Event Publisher DB",
}

# Reverse mapping: ServiceNow module name → ESM product name
MODULE_TO_ESM = {v: k for k, v in ESM_TO_MODULE.items()}


def match_installed_versions(
    esm_versions: dict[str, str],
    round_: "UpgradeRound",
) -> dict[str, str]:
    """Match ESM installed versions to modules in an upgrade round.

    Args:
        esm_versions: ESM product name → installed version string.
        round_: The upgrade round to match against.

    Returns:
        Dict of module_name → installed_version for modules present
        in both ESM and the upgrade round.
    """
    round_module_names = {m.name for m in round_.modules}
    result = {}
    for esm_name, version in esm_versions.items():
        module_name = ESM_TO_MODULE.get(esm_name)
        if module_name and module_name in round_module_names:
            result[module_name] = version
    return result


EXCLUDE_PATTERNS = [
    "SaaS", "Europe", "Australia", "Texas", "UK",
    "TCC", "NPYRE", "Structured Progression", "BDR", "TRIC",
    "Canada", "Canadian", "Banner in Experience", "PRINT APP",
]


def parse_module_name(short_description: str) -> str:
    """Extract module name from short_description by removing version suffix.

    Examples:
        "BA FIN AID 9.3.57" → "BA FIN AID"
        "BA GENERAL CMN DB 9.41" → "BA GENERAL CMN DB"
        "Banner Event Publisher 9.21" → "Banner Event Publisher"
        "BA Student TCC 9.3.41.1" → "BA Student TCC"
        "BA HR Tax Update #346" → "BA HR Tax Update"
    """
    desc = short_description.strip()
    # Special case: "BA HR Tax Update #NNN" → "BA HR Tax Update"
    m = re.match(r"^(BA HR Tax Update)\s+#\d+", desc)
    if m:
        return m.group(1)
    # Strip trailing annotations like "- REPOST" before version parsing
    desc = re.sub(r"\s+-\s+REPOST$", "", desc)
    # Strip the version suffix: last token(s) that start with a digit
    # Walk backwards through space-separated tokens, dropping version parts
    parts = desc.split()
    while parts and re.match(r"^\d", parts[-1]):
        parts.pop()
    return " ".join(parts) if parts else short_description


def should_exclude(short_description: str) -> bool:
    """Check if a release should be excluded based on name patterns."""
    desc_lower = short_description.lower()
    return any(pat.lower() in desc_lower for pat in EXCLUDE_PATTERNS)


@dataclass
class UpgradeModule:
    """A module (e.g. 'BA FIN AID') with its releases for this upgrade round."""

    name: str
    releases: list[Release] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "releases": [r.to_dict() for r in self.releases],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpgradeModule":
        return cls(
            name=data["name"],
            releases=[Release.from_dict(r) for r in data.get("releases", [])],
        )


@dataclass
class UpgradeRound:
    """Complete data for one upgrade round."""

    title: str
    cutoff_date: str
    since_date: str = ""
    modules: list[UpgradeModule] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "cutoff_date": self.cutoff_date,
            "since_date": self.since_date,
            "modules": [m.to_dict() for m in self.modules],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpgradeRound":
        return cls(
            title=data["title"],
            cutoff_date=data["cutoff_date"],
            since_date=data.get("since_date", ""),
            modules=[UpgradeModule.from_dict(m) for m in data.get("modules", [])],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "UpgradeRound":
        return cls.from_dict(json.loads(json_str))


def _group_releases(releases: list[Release]) -> list[UpgradeModule]:
    """Group releases by module name, preserving encounter order."""
    modules: dict[str, UpgradeModule] = {}
    order: list[str] = []

    for release in releases:
        name = parse_module_name(release.short_description)
        if name not in modules:
            modules[name] = UpgradeModule(name=name)
            order.append(name)
        modules[name].releases.append(release)

    # Sort releases within each module by date (target_ga_date or date_released)
    for mod in modules.values():
        mod.releases.sort(key=lambda r: r.target_ga_date or r.date_released or "")

    # Special sort for tax updates: sort by update number
    for mod in modules.values():
        if mod.name == "BA HR Tax Update":
            mod.releases.sort(
                key=lambda r: int(m.group(1)) if (m := re.search(r"#(\d+)", r.short_description)) else 0
            )

    return [modules[name] for name in order]


def gather_upgrade_round(
    session: AuthSession,
    title: str,
    cutoff_date: str,
    since_date: str = "",
    enrich: bool = True,
    product_line_id: str = BANNER_PRODUCT_LINE_ID,
    progress_callback=None,
) -> UpgradeRound:
    """Gather all release data for an upgrade round.

    1. Query upcoming releases (target_ga_date <= cutoff_date, not cancelled/released)
    2. Query recent releases (date_released since since_date through cutoff_date)
    3. Deduplicate by sys_id
    4. Filter out excluded patterns
    5. Group by module name (parsed from short_description)
    6. Optionally enrich each release with defects/enhancements/prerequisites

    Args:
        session: Authenticated session.
        title: Round title (e.g. "Spring 2026").
        cutoff_date: Latest release date to include (e.g. "2026-03-19").
        since_date: Earliest released date for already-shipped releases.
        enrich: Whether to fetch defects/enhancements/prerequisites.
        product_line_id: ServiceNow product line sys_id.
        progress_callback: Optional callable(message: str) for progress updates.

    Returns:
        UpgradeRound with grouped, filtered modules.
    """

    def _log(msg: str):
        if progress_callback:
            progress_callback(msg)

    # Query 1: Upcoming releases (not yet released)
    upcoming_query = (
        f"target_ga_date>=javascript:gs.beginningOfToday()"
        f"^target_ga_date<={cutoff_date}"
        f"^stateNOT IN3,7"
        f"^ellucian_product_line={product_line_id}"
    )
    _log("Querying upcoming releases...")
    upcoming = query_releases(session, upcoming_query)
    _log(f"  Found {len(upcoming)} upcoming releases")

    # Query 2: Recently released (already shipped)
    all_releases = {r.sys_id: r for r in upcoming}

    if since_date:
        recent_query = (
            f"date_released>={since_date}"
            f"^date_released<={cutoff_date}"
            f"^ellucian_product_line={product_line_id}"
        )
        _log("Querying recent releases...")
        recent = query_releases(session, recent_query)
        _log(f"  Found {len(recent)} recent releases")

        # Merge, dedup by sys_id
        for r in recent:
            if r.sys_id not in all_releases:
                all_releases[r.sys_id] = r

    # Filter excluded patterns
    filtered = [
        r for r in all_releases.values() if not should_exclude(r.short_description)
    ]
    excluded_count = len(all_releases) - len(filtered)
    if excluded_count:
        _log(f"  Excluded {excluded_count} releases (SaaS/Europe/Australia/Texas/UK)")

    # Enrich with defects/enhancements/prerequisites
    if enrich:
        total = len(filtered)
        for i, release in enumerate(filtered, 1):
            _log(f"  Enriching ({i}/{total}) {release.short_description}...")
            enrich_release(session, release)

    # Group by module
    modules = _group_releases(filtered)
    _log(f"Grouped into {len(modules)} modules")

    return UpgradeRound(
        title=title,
        cutoff_date=cutoff_date,
        since_date=since_date,
        modules=modules,
    )
