"""Runner Technologies Support API client."""

import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .auth import (
    DEFAULT_HEADERS,
    BASE_URL,
    AuthSession,
    AuthenticationError,
    authenticate,
)


@dataclass
class RunnerCredentials:
    """Credentials for Runner support authentication."""

    username: str
    password: str

    @classmethod
    def from_env(cls) -> "RunnerCredentials":
        """Load credentials from environment variables."""
        username = os.environ.get("RUNNER_SUPPORT_USER", "")
        password = os.environ.get("RUNNER_SUPPORT_PW", "")
        return cls(username=username, password=password)


class RunnerSupportClient:
    """Client for Runner Technologies Support site."""

    def __init__(self, session: AuthSession | None = None):
        """Initialize client with optional existing session."""
        self._session = session
        self._client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
        )

    def _ensure_authenticated(self) -> AuthSession:
        """Ensure we have a valid session, authenticating if needed."""
        # Try to load saved session
        if self._session is None:
            self._session = AuthSession.load()

        # Check if session is valid
        if self._session is not None and self._session.is_authenticated:
            # Set cookies on client
            for name, value in self._session.cookies.items():
                self._client.cookies.set(name, value)
            return self._session

        # Need to authenticate
        creds = RunnerCredentials.from_env()
        if not creds.username or not creds.password:
            raise AuthenticationError(
                "No valid session and credentials not set. "
                "Set RUNNER_SUPPORT_USER and RUNNER_SUPPORT_PW environment variables."
            )

        self._session = authenticate(creds.username, creds.password)
        self._session.save()

        # Set cookies on client
        for name, value in self._session.cookies.items():
            self._client.cookies.set(name, value)

        return self._session

    def _ajax_headers(self) -> dict[str, str]:
        """Get headers for AJAX requests."""
        session = self._ensure_authenticated()
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-CSRF-Token": session.csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}/support/home",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def search(self, term: str, max_matches: int = 10) -> list[dict[str, Any]]:
        """Search support articles.

        Args:
            term: Search term
            max_matches: Maximum number of results

        Returns:
            List of search results
        """
        self._ensure_authenticated()

        resp = self._client.get(
            f"{BASE_URL}/support/search",
            params={"term": term, "max_matches": max_matches},
            headers=self._ajax_headers(),
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Search failed: {resp.status_code}")

        return resp.json()

    def get_article(self, article_id: str) -> dict[str, Any]:
        """Get a support article by ID.

        Args:
            article_id: Article ID or slug

        Returns:
            Article content
        """
        self._ensure_authenticated()

        resp = self._client.get(
            f"{BASE_URL}/support/solutions/articles/{article_id}",
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Failed to get article: {resp.status_code}")

        # Parse article content from HTML
        title_match = re.search(r"<h1[^>]*>([^<]+)</h1>", resp.text)
        title = title_match.group(1) if title_match else ""

        # Get article body - find start and end markers
        body = ""
        body_start = resp.text.find('id="article-body"')
        if body_start > 0:
            # Find the opening > after id="article-body"
            content_start = resp.text.find(">", body_start) + 1
            # Find end markers - article-vote, </section>, or sidebar
            end_markers = []
            for marker in ["article-vote", "</section>", "fc-related-articles"]:
                pos = resp.text.find(marker, content_start)
                if pos > 0:
                    end_markers.append(pos)
            if end_markers:
                content_end = min(end_markers)
                body = resp.text[content_start:content_end]
                # Strip trailing </div> and whitespace
                body = re.sub(r"(\s*</div>)+\s*$", "", body)

        return {
            "id": article_id,
            "title": title,
            "body": body,
            "url": f"{BASE_URL}/support/solutions/articles/{article_id}",
        }

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "RunnerSupportClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
