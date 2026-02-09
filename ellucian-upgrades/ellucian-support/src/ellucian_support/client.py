"""Ellucian support site client with MFA support.

The Ellucian Customer Center runs on ServiceNow with multi-SSO enabled.
Authentication flows through Okta with MFA (Google Authenticator TOTP).
"""

import os
from dataclasses import dataclass
from typing import Callable

import httpx

from .auth import AuthSession, OktaAuthenticator


@dataclass
class EllucianCredentials:
    """Credentials for Ellucian support site."""

    username: str
    password: str

    @classmethod
    def from_env(cls) -> "EllucianCredentials":
        """Load credentials from environment variables."""
        username = os.environ.get("ELLUCIAN_SUPPORT_USER")
        password = os.environ.get("ELLUCIAN_SUPPORT_PW")

        if not username or not password:
            raise ValueError("ELLUCIAN_SUPPORT_USER and ELLUCIAN_SUPPORT_PW must be set in environment")

        return cls(username=username, password=password)


class EllucianClient:
    """Client for Ellucian support site with MFA handling.

    The client attempts to reuse saved sessions to minimize MFA prompts.
    Only authenticates fresh when the saved session is invalid/expired.
    """

    BASE_URL = "https://elluciansupport.service-now.com"
    PORTAL_PATH = "/customer_center"

    def __init__(
        self,
        credentials: EllucianCredentials | None = None,
        mfa_callback: Callable[[], str] | None = None,
    ):
        """Initialize the client.

        Args:
            credentials: Login credentials. If None, loaded from environment.
            mfa_callback: Function to call when MFA code is needed.
                         Should return the MFA code as a string.
                         If None, uses interactive input().
        """
        self.credentials = credentials or EllucianCredentials.from_env()
        self.mfa_callback = mfa_callback or self._default_mfa_prompt
        self._session: AuthSession | None = None
        self._client: httpx.Client | None = None

    def _default_mfa_prompt(self) -> str:
        """Default MFA prompt using input()."""
        return input("Enter MFA code: ").strip()

    def _ensure_client(self) -> httpx.Client:
        """Get or create HTTP client with session cookies."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                follow_redirects=True,
                timeout=30.0,
            )
            # Apply session cookies if we have them
            if self._session:
                for name, value in self._session.cookies.items():
                    self._client.cookies.set(name, value, domain="elluciansupport.service-now.com")
        return self._client

    def authenticate(self, force: bool = False) -> bool:
        """Authenticate with the support site.

        Tries to reuse a saved session first. Only prompts for MFA
        if the saved session is invalid or force=True.

        Args:
            force: If True, ignore saved session and re-authenticate.

        Returns:
            True if authentication succeeded.

        Raises:
            AuthenticationError: If authentication fails.
        """
        # Try to load saved session
        if not force:
            saved = AuthSession.load()
            if saved and OktaAuthenticator.validate_session(saved):
                print("Using saved session (still valid)")
                self._session = saved
                return True
            elif saved:
                print("Saved session expired, re-authenticating...")

        # Need fresh authentication
        with OktaAuthenticator(
            username=self.credentials.username,
            password=self.credentials.password,
            mfa_callback=self.mfa_callback,
        ) as auth:
            self._session = auth.authenticate()

        # Reset client to pick up new cookies
        if self._client:
            self._client.close()
            self._client = None

        return True

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid session."""
        return self._session is not None and self._session.is_authenticated

    def get(self, path: str, **kwargs) -> httpx.Response:
        """Make authenticated GET request."""
        if not self.is_authenticated:
            self.authenticate()
        return self._ensure_client().get(path, **kwargs)

    def post(self, path: str, **kwargs) -> httpx.Response:
        """Make authenticated POST request."""
        if not self.is_authenticated:
            self.authenticate()
        return self._ensure_client().post(path, **kwargs)

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "EllucianClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
