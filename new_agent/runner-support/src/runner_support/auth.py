"""Runner Technologies support site authentication."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

# Default cookie storage location
DEFAULT_COOKIE_FILE = Path.home() / ".config" / "stibbons" / "runner_cookies.json"

# Base URL for Runner support
BASE_URL = "https://support.runnertech.com"

# Browser-like headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "TE": "trailers",
}


@dataclass
class AuthSession:
    """Authenticated session with cookies and tokens."""

    cookies: dict[str, str] = field(default_factory=dict)
    csrf_token: str = ""
    user_email: str = ""

    @property
    def is_authenticated(self) -> bool:
        """Check if session appears to be authenticated."""
        return "user_credentials" in self.cookies

    def save(self, path: Path = DEFAULT_COOKIE_FILE) -> None:
        """Save session cookies to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "cookies": self.cookies,
            "csrf_token": self.csrf_token,
            "user_email": self.user_email,
        }
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = DEFAULT_COOKIE_FILE) -> "AuthSession | None":
        """Load session from file if exists and valid."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return cls(
                cookies=data.get("cookies", {}),
                csrf_token=data.get("csrf_token", ""),
                user_email=data.get("user_email", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    @staticmethod
    def clear(path: Path = DEFAULT_COOKIE_FILE) -> None:
        """Delete saved session."""
        if path.exists():
            path.unlink()


class AuthenticationError(Exception):
    """Authentication failed."""

    pass


def authenticate(username: str, password: str) -> AuthSession:
    """Authenticate with Runner Technologies Support.

    Args:
        username: Email address
        password: Password

    Returns:
        AuthSession with cookies for authenticated requests

    Raises:
        AuthenticationError: If login fails
    """
    with httpx.Client(
        timeout=30.0,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    ) as client:
        # Step 1: GET login page to get session cookie and CSRF token
        login_url = f"{BASE_URL}/support/login"
        resp = client.get(login_url)

        if resp.status_code != 200:
            raise AuthenticationError(f"Failed to load login page: {resp.status_code}")

        # Extract authenticity_token from form
        token_match = re.search(r'name="authenticity_token"[^>]*value="([^"]+)"', resp.text)
        if not token_match:
            raise AuthenticationError("Could not find authenticity_token in login page")
        authenticity_token = token_match.group(1)

        # Extract csrf-token meta tag (used for AJAX requests after login)
        csrf_match = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', resp.text)
        csrf_token = csrf_match.group(1) if csrf_match else ""

        # Step 2: POST login with credentials
        form_data = {
            "utf8": "✓",
            "authenticity_token": authenticity_token,
            "user_session[email]": username,
            "user_session[password]": password,
            "user_session[remember_me]": "1",
            "meta[enterprise_enabled]": "false",
        }

        post_headers = {
            **DEFAULT_HEADERS,
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_URL,
            "Referer": login_url,
            "Sec-Fetch-Site": "same-origin",
        }

        resp = client.post(login_url, data=form_data, headers=post_headers)

        # After redirects, we should be at /support/home if successful
        if resp.status_code != 200:
            raise AuthenticationError(f"Login failed with status: {resp.status_code}")

        # Check for user_credentials cookie
        # Filter to only support.runnertech.com cookies (avoid conflicts from other domains)
        cookies = {}
        for cookie in client.cookies.jar:
            if "runnertech.com" in cookie.domain and cookie.domain.startswith(
                ("support", ".support")
            ):
                cookies[cookie.name] = cookie.value
        if "user_credentials" not in cookies:
            raise AuthenticationError("Login failed: no user_credentials cookie set")

        # Extract updated CSRF token from home page
        csrf_match = re.search(r'<meta[^>]*name="csrf-token"[^>]*content="([^"]+)"', resp.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)

        return AuthSession(
            cookies=cookies,
            csrf_token=csrf_token,
            user_email=username,
        )
