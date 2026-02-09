"""Release fetching for Ellucian Support Center.

Fetches product releases with related defects and enhancements from
the ServiceNow-based Ellucian Customer Center.
"""

from dataclasses import dataclass, field
from typing import Any

import httpx

from .auth import AuthSession
from .search import SearchResponse, search

SERVICENOW_BASE = "https://elluciansupport.service-now.com"


class ReleaseError(Exception):
    """Release operation failed."""

    pass


@dataclass
class Defect:
    """A product defect."""

    sys_id: str
    number: str
    summary: str
    description: str = ""
    resolution: str = ""
    client_impact: str = ""
    object_process: str = ""
    patch_number: str = ""
    product_hierarchy: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Defect":
        """Create from ServiceNow Table API response."""
        return cls(
            sys_id=data.get("sys_id", ""),
            number=data.get("number", ""),
            summary=data.get("summary", data.get("short_description", "")),
            description=data.get("description", ""),
            resolution=data.get("resolution", ""),
            client_impact=data.get("client_impact", ""),
            object_process=data.get("object_process", ""),
            patch_number=data.get("patch_number", ""),
            product_hierarchy=data.get("ellucian_product_full_hierarchy", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sys_id": self.sys_id,
            "number": self.number,
            "summary": self.summary,
            "description": self.description,
            "resolution": self.resolution,
            "client_impact": self.client_impact,
            "object_process": self.object_process,
            "patch_number": self.patch_number,
            "product_hierarchy": self.product_hierarchy,
        }


@dataclass
class Enhancement:
    """A product enhancement."""

    sys_id: str
    number: str
    summary: str
    description: str = ""
    business_purpose: str = ""
    product_hierarchy: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Enhancement":
        """Create from ServiceNow Table API response."""
        return cls(
            sys_id=data.get("sys_id", ""),
            number=data.get("number", ""),
            summary=data.get("summary", data.get("short_description", "")),
            description=data.get("description", ""),
            business_purpose=data.get("business_purpose", ""),
            product_hierarchy=data.get("ellucian_product_full_hierarchy", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sys_id": self.sys_id,
            "number": self.number,
            "summary": self.summary,
            "description": self.description,
            "business_purpose": self.business_purpose,
            "product_hierarchy": self.product_hierarchy,
        }


@dataclass
class Release:
    """A product release with optional related defects/enhancements."""

    sys_id: str
    number: str
    short_description: str
    date_released: str = ""
    product_line: str = ""
    product_name: str = ""
    version: str = ""
    url: str = ""
    defects: list[Defect] = field(default_factory=list)
    enhancements: list[Enhancement] = field(default_factory=list)

    @classmethod
    def from_search_result(cls, raw: dict[str, Any]) -> "Release":
        """Create from Coveo search result raw data.

        Coveo results have ServiceNow fields prefixed with 'sn' inside the 'raw' object.
        """
        # The actual field data is in raw.raw for Coveo results
        inner = raw.get("raw", raw)

        return cls(
            sys_id=inner.get("snsysid", inner.get("permanentid", "")),
            number=inner.get("snnumber", ""),
            short_description=inner.get("snshortdescription", raw.get("title", "")),
            date_released=inner.get("sndatereleased", ""),
            product_line=inner.get("snellucianproductline", ""),
            product_name=inner.get("snellucianproductname", ""),
            version=inner.get("snellucianproductversionname", inner.get("snellucianproductversion", "")),
            url=inner.get("sndirectlink", raw.get("clickUri", "")),
        )

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Release":
        """Create from ServiceNow Table API response."""
        # Handle reference fields that come as {link, value} objects
        product_line = data.get("ellucian_product_line", "")
        if isinstance(product_line, dict):
            product_line = product_line.get("value", "")

        product_name = data.get("ellucian_product_name", "")
        if isinstance(product_name, dict):
            product_name = product_name.get("value", "")

        version = data.get("ellucian_product_version", "")
        if isinstance(version, dict):
            version = version.get("value", "")

        return cls(
            sys_id=data.get("sys_id", ""),
            number=data.get("number", ""),
            short_description=data.get("short_description", ""),
            date_released=data.get("date_released", ""),
            product_line=product_line,
            product_name=product_name,
            version=version,
            url=data.get("community_url", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "sys_id": self.sys_id,
            "number": self.number,
            "short_description": self.short_description,
            "date_released": self.date_released,
            "product_line": self.product_line,
            "product_name": self.product_name,
            "version": self.version,
            "url": self.url,
            "defects": [d.to_dict() for d in self.defects],
            "enhancements": [e.to_dict() for e in self.enhancements],
        }


def search_releases(
    session: AuthSession,
    query: str = "",
    num_results: int = 20,
) -> list[Release]:
    """Search for product releases.

    Args:
        session: Authenticated session with cookies.
        query: Search query (e.g., "Banner Financial Aid").
        num_results: Maximum results to return.

    Returns:
        List of Release objects (without defects/enhancements populated).

    Raises:
        ReleaseError: If search fails.
    """
    try:
        # Use "release" source filter to only get releases
        results = search(
            session,
            query if query else "*",
            num_results=num_results,
            source_filter="release",
        )
    except Exception as e:
        raise ReleaseError(f"Release search failed: {e}")

    releases = []
    for r in results.results:
        # The raw field contains Coveo metadata
        raw = r.raw.get("raw", r.raw)
        releases.append(Release.from_search_result(raw))

    return releases


def get_release(session: AuthSession, sys_id: str) -> Release:
    """Get release details by sys_id.

    Args:
        session: Authenticated session with cookies.
        sys_id: ServiceNow sys_id of the release.

    Returns:
        Release object (without defects/enhancements populated).

    Raises:
        ReleaseError: If fetch fails.
    """
    with httpx.Client(timeout=30.0) as client:
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_release/{sys_id}"
        resp = client.get(url, headers={"Accept": "application/json"})

        if resp.status_code != 200:
            raise ReleaseError(f"Failed to fetch release {sys_id}: HTTP {resp.status_code}")

        data = resp.json().get("result", {})
        return Release.from_api(data)


def _get_related_ids_from_page(client: httpx.Client, sys_id: str) -> tuple[list[str], list[str]]:
    """Extract related defect/enhancement IDs from SP page API.

    The ServiceNow Service Portal page contains widget data with related
    item IDs embedded in filter strings like "sys_idINabc,def,ghi".

    Returns:
        Tuple of (defect_ids, enhancement_ids).
    """
    sp_url = f"{SERVICENOW_BASE}/api/now/sp/page"
    params = {
        "id": "standard_ticket",
        "table": "ellucian_product_release",
        "sys_id": sys_id,
    }
    resp = client.get(sp_url, params=params, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        return [], []

    data = resp.json()
    defect_ids = []
    enhancement_ids = []

    # Navigate to Standard Ticket Tab widget
    containers = data.get("result", {}).get("containers", [])
    for container in containers:
        for row in container.get("rows", []):
            for col in row.get("columns", []):
                for widget in col.get("widgets", []):
                    w = widget.get("widget", {})
                    if w.get("name") == "Standard Ticket Tab":
                        tabs = w.get("data", {}).get("tabs", [])
                        for tab in tabs:
                            name = tab.get("name", "")
                            nested = tab.get("widget", {}).get("data", {}).get("widget", {})
                            options = nested.get("options", {})
                            filter_str = options.get("filter", "")

                            # Extract sys_ids from filter like "sys_idINabc,def,ghi"
                            if filter_str.startswith("sys_idIN"):
                                ids = filter_str[8:].split(",")
                                ids = [i.strip() for i in ids if i.strip()]
                                if "Defect" in name:
                                    defect_ids.extend(ids)
                                elif "Enhancement" in name:
                                    enhancement_ids.extend(ids)

    return defect_ids, enhancement_ids


def _fetch_defects(client: httpx.Client, sys_ids: list[str]) -> list[Defect]:
    """Fetch defect details by sys_ids (individually to avoid 403 on query)."""
    results = []
    for sys_id in sys_ids:
        url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_defect/{sys_id}"
        resp = client.get(url, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            results.append(Defect.from_api(data))
    return results


def _fetch_enhancements(client: httpx.Client, sys_ids: list[str]) -> list[Enhancement]:
    """Fetch enhancement details by sys_ids (individually to avoid 403 on query)."""
    results = []
    for sys_id in sys_ids:
        url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_enhancement/{sys_id}"
        resp = client.get(url, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            data = resp.json().get("result", {})
            results.append(Enhancement.from_api(data))
    return results


def enrich_release(session: AuthSession, release: Release) -> Release:
    """Fetch and attach defects/enhancements to a release.

    Modifies the release in place and returns it.

    Args:
        session: Authenticated session with cookies.
        release: Release object to enrich.

    Returns:
        The same Release object with defects/enhancements populated.

    Raises:
        ReleaseError: If enrichment fails.
    """
    with httpx.Client(timeout=30.0) as client:
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Get related item IDs from page
        defect_ids, enhancement_ids = _get_related_ids_from_page(client, release.sys_id)

        # Fetch details
        if defect_ids:
            release.defects = _fetch_defects(client, defect_ids)
        if enhancement_ids:
            release.enhancements = _fetch_enhancements(client, enhancement_ids)

    return release


def get_release_with_details(session: AuthSession, sys_id: str) -> Release:
    """Get release with all defects and enhancements populated.

    Convenience function that combines get_release and enrich_release.

    Args:
        session: Authenticated session with cookies.
        sys_id: ServiceNow sys_id of the release.

    Returns:
        Fully populated Release object.

    Raises:
        ReleaseError: If fetch fails.
    """
    release = get_release(session, sys_id)
    return enrich_release(session, release)
