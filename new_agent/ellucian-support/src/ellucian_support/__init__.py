"""Ellucian Support Center client.

Provides authentication and API access to Ellucian's support portal
(ServiceNow-based). Handles Okta SSO with MFA, with session persistence
to minimize re-authentication.
"""

from .auth import AuthenticationError, AuthSession
from .client import EllucianClient, EllucianCredentials
from .fetch import FetchError, KBArticle, fetch_attachments, fetch_kb_article
from .search import SearchError, SearchResponse, SearchResult, search

__all__ = [
    "EllucianClient",
    "EllucianCredentials",
    "AuthSession",
    "AuthenticationError",
    "SearchError",
    "SearchResponse",
    "SearchResult",
    "search",
    "FetchError",
    "KBArticle",
    "fetch_kb_article",
    "fetch_attachments",
]
