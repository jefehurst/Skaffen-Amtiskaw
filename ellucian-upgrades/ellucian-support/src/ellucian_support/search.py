"""Search functionality for Ellucian Support Center.

Uses the Coveo search API that powers the ServiceNow portal's search.

Source filters (use with source_filter parameter):
- "docs"      -> Zoomin - Ellucian Resources (official documentation)
- "kb"        -> ServiceNow - Knowledge - Support (knowledge base articles)
- "defect"    -> ServiceNow - Defect - Support (bug reports)
- "release"   -> ServiceNow - Releases - Support (release notes)
- "idea"      -> ServiceNow - Ideas - Support (feature requests)
- "community" -> ServiceNow - Community - Content - Support (forum posts)

File type filters (use with filetype_filter parameter):
- "html"      -> HTML pages (docs)
- "pdf"       -> PDF attachments
- "kb"        -> Knowledge base articles (kb_knowledge)
"""

from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlencode

import httpx

from .auth import AuthSession

SERVICENOW_BASE = "https://elluciansupport.service-now.com"
COVEO_BASE = "https://platform.cloud.coveo.com"

# Map friendly names to Coveo @source values
SOURCE_MAP = {
    "docs": "Zoomin - Ellucian Resources",
    "kb": "ServiceNow - Knowledge - Support",
    "defect": "ServiceNow - Defect - Support",
    "release": "ServiceNow - Releases - Support",
    "idea": "ServiceNow - Ideas - Support",
    "community": "ServiceNow - Community - Content - Support",
    "enhancement": "ServiceNow - Enhancements - Support",
}

# Map friendly names to Coveo @filetype values
FILETYPE_MAP = {
    "html": "html",
    "pdf": "pdf",
    "kb": "kb_knowledge",
    "defect": "ellucian_product_defect",
    "release": "ellucian_product_release",
}

SourceFilter = Literal["docs", "kb", "defect", "release", "idea", "community", "enhancement"]
FiletypeFilter = Literal["html", "pdf", "kb", "defect", "release"]


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    excerpt: str
    source: str
    raw: dict[str, Any]

    @classmethod
    def from_coveo(cls, item: dict[str, Any]) -> "SearchResult":
        """Create from Coveo API response item."""
        # Determine source from URL pattern
        url = item.get("clickUri", item.get("uri", ""))
        if "resources.elluciancloud.com" in url:
            source = "docs"
        elif "kb_knowledge" in url:
            source = "kb"
        elif "ellucian_product_release" in url:
            source = "release"
        else:
            source = "other"

        return cls(
            title=item.get("title", "No title"),
            url=url,
            excerpt=item.get("excerpt", ""),
            source=source,
            raw=item,
        )


@dataclass
class SearchResponse:
    """Search results from Coveo."""

    total_count: int
    results: list[SearchResult]
    duration_ms: int
    query: str

    @classmethod
    def from_coveo(cls, data: dict[str, Any], query: str) -> "SearchResponse":
        """Create from Coveo API response."""
        return cls(
            total_count=data.get("totalCount", 0),
            results=[SearchResult.from_coveo(item) for item in data.get("results", [])],
            duration_ms=data.get("duration", 0),
            query=query,
        )


class SearchError(Exception):
    """Search operation failed."""

    pass


def _find_token(obj: Any, key: str = "searchToken") -> str | None:
    """Recursively search for a key in nested dict/list structure."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            result = _find_token(v, key)
            if result:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_token(item, key)
            if result:
                return result
    return None


def get_search_token(session: AuthSession, client: httpx.Client) -> str:
    """Get Coveo search token from ServiceNow.

    The token is obtained by requesting the search page data from
    ServiceNow's Service Portal API.

    Args:
        session: Authenticated session with cookies.
        client: HTTP client to use.

    Returns:
        Coveo search token (JWT).

    Raises:
        SearchError: If token cannot be obtained.
    """
    # Set cookies from session
    for name, value in session.cookies.items():
        client.cookies.set(name, value, domain="elluciansupport.service-now.com")

    # Request the search page data
    resp = client.get(f"{SERVICENOW_BASE}/api/now/sp/page?id=csm_coveo_search")

    if resp.status_code != 200:
        logged_in = resp.headers.get("x-is-logged-in", "unknown")
        raise SearchError(f"Failed to get search page (status {resp.status_code}, logged_in={logged_in})")

    data = resp.json()
    token = _find_token(data)

    if not token:
        raise SearchError("searchToken not found in ServiceNow response")

    return token


def _build_filter_query(
    source_filter: SourceFilter | list[SourceFilter] | None = None,
    filetype_filter: FiletypeFilter | list[FiletypeFilter] | None = None,
) -> str | None:
    """Build Coveo advanced query (aq) filter string.

    Args:
        source_filter: Filter by source type(s).
        filetype_filter: Filter by file type(s).

    Returns:
        Coveo aq filter string, or None if no filters.
    """
    clauses = []

    # Handle source filter
    if source_filter:
        sources = [source_filter] if isinstance(source_filter, str) else source_filter
        source_values = [SOURCE_MAP[s] for s in sources if s in SOURCE_MAP]
        if source_values:
            if len(source_values) == 1:
                clauses.append(f'@source=="{source_values[0]}"')
            else:
                quoted = ", ".join(f'"{v}"' for v in source_values)
                clauses.append(f"@source==({quoted})")

    # Handle filetype filter
    if filetype_filter:
        types = [filetype_filter] if isinstance(filetype_filter, str) else filetype_filter
        type_values = [FILETYPE_MAP[t] for t in types if t in FILETYPE_MAP]
        if type_values:
            if len(type_values) == 1:
                clauses.append(f'@filetype=="{type_values[0]}"')
            else:
                quoted = ", ".join(f'"{v}"' for v in type_values)
                clauses.append(f"@filetype==({quoted})")

    if not clauses:
        return None

    return " AND ".join(clauses)


def search(
    session: AuthSession,
    query: str,
    num_results: int = 10,
    first_result: int = 0,
    source_filter: SourceFilter | list[SourceFilter] | None = None,
    filetype_filter: FiletypeFilter | list[FiletypeFilter] | None = None,
) -> SearchResponse:
    """Search the Ellucian Support Center.

    Args:
        session: Authenticated session with cookies.
        query: Search query string.
        num_results: Number of results to return (max 50).
        first_result: Offset for pagination.
        source_filter: Filter by source - "docs", "kb", "defect", "release",
                      "idea", "community", "enhancement". Can be single value
                      or list for OR.
        filetype_filter: Filter by type - "html", "pdf", "kb", "defect",
                        "release". Can be single value or list for OR.

    Returns:
        SearchResponse with results.

    Raises:
        SearchError: If search fails.

    Examples:
        # Search only official documentation
        search(session, "banner upgrade", source_filter="docs")

        # Search knowledge base articles and defects
        search(session, "error", source_filter=["kb", "defect"])

        # Search only PDFs
        search(session, "installation guide", filetype_filter="pdf")
    """
    with httpx.Client(timeout=30.0) as client:
        # Get search token
        token = get_search_token(session, client)

        # Build search request
        search_params = {
            "q": query,
            "searchHub": "CustomerCenter_MainSearch",
            "locale": "en",
            "firstResult": first_result,
            "numberOfResults": min(num_results, 50),
            "excerptLength": 200,
            "enableDidYouMean": "true",
            "sortCriteria": "relevancy",
        }

        # Add filters if specified
        aq = _build_filter_query(source_filter, filetype_filter)
        if aq:
            search_params["aq"] = aq

        # Execute search against Coveo
        resp = client.post(
            f"{COVEO_BASE}/rest/search/v2?organizationId=ellucian",
            data=urlencode(search_params),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Accept": "*/*",
            },
        )

        if resp.status_code != 200:
            raise SearchError(f"Coveo search failed (status {resp.status_code}): {resp.text[:200]}")

        return SearchResponse.from_coveo(resp.json(), query)
