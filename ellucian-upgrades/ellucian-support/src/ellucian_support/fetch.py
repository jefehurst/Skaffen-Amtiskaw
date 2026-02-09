"""Fetch full content from Ellucian Support Center.

Retrieves articles and other content using the ServiceNow REST API.
"""

import html
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from .auth import AuthSession

SERVICENOW_BASE = "https://elluciansupport.service-now.com"


class FetchError(Exception):
    """Content fetch failed."""

    pass


@dataclass
class KBArticle:
    """Knowledge Base article content."""

    sys_id: str
    number: str
    title: str
    text: str
    text_html: str
    published: str
    category: str
    raw: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any], table: str = "kb_knowledge") -> "KBArticle":
        """Create from ServiceNow API response.

        Handles different table schemas:
        - kb_knowledge: uses 'text' field for content
        - ellucian_product_release: uses 'description' and 'summary' fields
        - ellucian_product_defect: uses 'description', 'summary', 'resolution' fields
        """
        # Get content based on table type
        if table == "ellucian_product_release":
            # Release notes use description/summary instead of text
            description = data.get("description", "")
            summary = data.get("summary", "")
            text_html = description or summary
            published = data.get("date_released", "")
            category = data.get("release_purpose", "")
        elif table == "ellucian_product_defect":
            # Defects use summary, description, and resolution
            summary = data.get("summary", "")
            description = data.get("description", "")
            resolution = data.get("resolution", "")
            comments = data.get("comments", "")

            # Build combined content
            parts = []
            if summary:
                parts.append(f"<h2>Summary</h2><p>{summary}</p>")
            if description:
                parts.append(f"<h2>Description</h2><p>{description}</p>")
            if resolution:
                parts.append(f"<h2>Resolution</h2><p>{resolution}</p>")
            if comments:
                parts.append(f"<h2>Comments</h2><p>{comments}</p>")

            text_html = "\n".join(parts)
            published = data.get("sys_created_on", "")
            category = data.get("ellucian_product_full_hierarchy", "")
        else:
            # Knowledge base articles use text field
            text_html = data.get("text", "")
            published = data.get("published", "")
            category = data.get("kb_category", "")

        # Strip HTML tags for plain text version
        text = re.sub(r"<[^>]+>", " ", text_html)
        text = re.sub(r"\s+", " ", text).strip()
        # Decode HTML entities (&#39; -> ', &#34; -> ", etc.)
        text = html.unescape(text)

        # Title: defects use 'summary', others use 'short_description'
        title = data.get("short_description", "") or data.get("summary", "")

        return cls(
            sys_id=data.get("sys_id", ""),
            number=data.get("number", ""),
            title=title,
            text=text,
            text_html=text_html,
            published=published,
            category=category,
            raw=data,
        )


def extract_sys_id(url_or_id: str) -> tuple[str, str]:
    """Extract sys_id and table type from URL or raw ID.

    Args:
        url_or_id: Either a ServiceNow URL or a raw sys_id.

    Returns:
        Tuple of (sys_id, table_name).
    """
    # If it looks like a UUID, assume kb_knowledge
    if re.match(r"^[a-f0-9]{32}$", url_or_id):
        return url_or_id, "kb_knowledge"

    # Parse URL
    parsed = urlparse(url_or_id)
    uri = parse_qs(parsed.query).get("uri", [""])[0]

    if not uri:
        raise FetchError(f"Could not extract uri from URL: {url_or_id}")

    # Parse the uri parameter (e.g., "kb_knowledge.do?sys_id=xxx")
    if "sys_id=" in uri:
        # Extract table name from uri
        table_match = re.match(r"([a-z_]+)\.do", uri)
        table = table_match.group(1) if table_match else "kb_knowledge"

        # Extract sys_id
        id_match = re.search(r"sys_id=([a-f0-9]{32})", uri)
        if id_match:
            return id_match.group(1), table

    raise FetchError(f"Could not extract sys_id from: {url_or_id}")


def fetch_kb_article(session: AuthSession, url_or_id: str) -> KBArticle:
    """Fetch an article by URL or sys_id.

    Args:
        session: Authenticated session.
        url_or_id: ServiceNow article URL or raw sys_id.

    Returns:
        KBArticle with full content.

    Raises:
        FetchError: If article cannot be fetched.
    """
    sys_id, table = extract_sys_id(url_or_id)

    with httpx.Client(timeout=30.0) as client:
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        api_url = f"{SERVICENOW_BASE}/api/now/table/{table}/{sys_id}"
        resp = client.get(api_url, headers={"Accept": "application/json"})

        if resp.status_code == 404:
            raise FetchError(f"Article not found: {sys_id}")
        if resp.status_code != 200:
            raise FetchError(f"Failed to fetch article (status {resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        result = data.get("result")
        if not result:
            raise FetchError(f"Empty result for article: {sys_id}")

        return KBArticle.from_api(result, table=table)


def fetch_attachments(session: AuthSession, sys_id: str) -> list[dict[str, Any]]:
    """List attachments for a record.

    Args:
        session: Authenticated session.
        sys_id: Record sys_id.

    Returns:
        List of attachment metadata dicts.
    """
    with httpx.Client(timeout=30.0) as client:
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        api_url = f"{SERVICENOW_BASE}/api/now/attachment"
        resp = client.get(
            api_url,
            params={"sysparm_query": f"table_sys_id={sys_id}"},
            headers={"Accept": "application/json"},
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        return data.get("result", [])
