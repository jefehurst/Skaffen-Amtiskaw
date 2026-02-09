"""Ellucian support site authentication via Okta SAML."""

import codecs
import html as html_module
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx

# Default cookie storage location
DEFAULT_COOKIE_FILE = Path.home() / ".config" / "stibbons" / "ellucian_cookies.json"


@dataclass
class AuthSession:
    """Authenticated session with cookies and tokens."""

    cookies: dict[str, str] = field(default_factory=dict)
    user_email: str = ""
    user_id: str = ""
    glide_session_store: str = ""

    @property
    def is_authenticated(self) -> bool:
        return bool(self.glide_session_store)

    def save(self, path: Path = DEFAULT_COOKIE_FILE) -> None:
        """Save session cookies to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "cookies": self.cookies,
            "user_email": self.user_email,
            "user_id": self.user_id,
            "glide_session_store": self.glide_session_store,
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
                user_email=data.get("user_email", ""),
                user_id=data.get("user_id", ""),
                glide_session_store=data.get("glide_session_store", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    @staticmethod
    def clear(path: Path = DEFAULT_COOKIE_FILE) -> None:
        """Delete saved session."""
        if path.exists():
            path.unlink()


class OktaAuthenticator:
    """Handle Okta SAML authentication with MFA."""

    SERVICENOW_BASE = "https://elluciansupport.service-now.com"
    OKTA_BASE = "https://sso.ellucian.com"
    SSO_ID = "7d6eb13447c309500cf60562846d430c"

    # Headers for Okta IDX API requests
    IDX_HEADERS = {
        "Accept": "application/ion+json; okta-version=1.0.0",
        "Content-Type": "application/ion+json; okta-version=1.0.0",
        "Origin": "https://sso.ellucian.com",
        "X-Okta-User-Agent-Extended": "okta-auth-js/7.14.0 okta-signin-widget-7.37.1",
    }

    def __init__(
        self,
        username: str,
        password: str,
        mfa_callback: Callable[[], str],
    ):
        """Initialize authenticator.

        Args:
            username: Ellucian support username
            password: Ellucian support password
            mfa_callback: Function that returns MFA code when called
        """
        self.username = username
        self.password = password
        self.mfa_callback = mfa_callback
        self._client = httpx.Client(
            follow_redirects=False,
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/145.0",
            },
        )

    def authenticate(self) -> AuthSession:
        """Perform full authentication flow.

        Returns:
            AuthSession with cookies for authenticated requests.

        Raises:
            AuthenticationError: If authentication fails.
        """
        # Step 1: Visit target page first to establish session context
        # ServiceNow uses the Referer header to construct RelayState
        print("Initiating SSO...")
        target_url = f"{self.SERVICENOW_BASE}/customer_center?id=customer_center_home"
        self._client.get(target_url)

        # Track JSESSIONID through the flow - SAML is tied to this session
        initial_jsessionid = None
        for c in self._client.cookies.jar:
            if c.name == "JSESSIONID" and "service-now.com" in c.domain:
                initial_jsessionid = c.value
                print(f"  Initial JSESSIONID: {initial_jsessionid[:30]}...")

        # Initiate SSO - Referer header tells ServiceNow where to return after auth
        # (Browser HAR shows this is how RelayState gets set correctly)
        sso_url = f"{self.SERVICENOW_BASE}/login_with_sso.do?glide_sso_id={self.SSO_ID}"
        resp = self._client.get(
            sso_url,
            headers={"Referer": target_url},
        )

        # Check if JSESSIONID changed
        for c in self._client.cookies.jar:
            if c.name == "JSESSIONID" and "service-now.com" in c.domain:
                if initial_jsessionid and c.value != initial_jsessionid:
                    print("  WARNING: JSESSIONID changed after login_with_sso.do!")
                    print(f"  New JSESSIONID: {c.value[:30]}...")

        # Follow redirect to auth_redirect.do
        if resp.status_code == 302:
            redirect_url = resp.headers.get("location", "")
            if not redirect_url.startswith("http"):
                redirect_url = f"{self.SERVICENOW_BASE}{redirect_url}"
            resp = self._client.get(redirect_url)

            # Check again after auth_redirect
            for c in self._client.cookies.jar:
                if c.name == "JSESSIONID" and "service-now.com" in c.domain:
                    if initial_jsessionid and c.value != initial_jsessionid:
                        print("  WARNING: JSESSIONID changed after auth_redirect.do!")
                        print(f"  New JSESSIONID: {c.value[:30]}...")

        # Extract the Okta SAML URL from the page
        saml_url = self._extract_saml_redirect(resp.text)
        if not saml_url:
            raise AuthenticationError("Could not find SAML redirect URL")

        # Step 2: Follow to Okta login page
        print("Loading Okta login...")
        okta_resp = self._client.get(saml_url)

        # Step 3: Introspect to get stateToken
        state_token = self._extract_state_token(okta_resp.text)
        if not state_token:
            raise AuthenticationError("Could not extract Okta state token")

        # Call introspect endpoint
        introspect_resp = self._client.post(
            f"{self.OKTA_BASE}/idp/idx/introspect",
            json={"stateToken": state_token},
            headers=self.IDX_HEADERS,
        )

        if introspect_resp.status_code != 200:
            raise AuthenticationError(
                f"Introspect failed: {introspect_resp.status_code} - {introspect_resp.text[:200]}"
            )

        introspect_data = introspect_resp.json()

        # Extract stateHandle for subsequent requests
        state_handle = introspect_data.get("stateHandle", "")
        if not state_handle:
            raise AuthenticationError("Could not get stateHandle from introspect")

        # Step 4: Submit credentials
        print("Submitting credentials...")
        identify_resp = self._client.post(
            f"{self.OKTA_BASE}/idp/idx/identify",
            json={
                "identifier": self.username,
                "credentials": {"passcode": self.password},
                "stateHandle": state_handle,
            },
            headers=self.IDX_HEADERS,
        )

        if identify_resp.status_code != 200:
            raise AuthenticationError(f"Login failed: {identify_resp.status_code}")

        identify_data = identify_resp.json()
        state_handle = identify_data.get("stateHandle", state_handle)

        # Variable to hold success URL from MFA or identify response
        success_url = None

        # Check if MFA is required
        if "remediation" in identify_data:
            print("MFA required.")

            # Step 5a: Select Okta Verify with TOTP method
            # Find the Okta Verify authenticator ID from the remediation options
            authenticator_id = None
            remediation_value = identify_data.get("remediation", {}).get("value", [])
            for rem in remediation_value:
                if rem.get("name") == "select-authenticator-authenticate":
                    auth_options = rem.get("value", [])
                    for val in auth_options:
                        if val.get("name") == "authenticator":
                            options = val.get("options", [])
                            for opt in options:
                                if opt.get("label") == "Okta Verify":
                                    form_values = opt.get("value", {}).get("form", {}).get("value", [])
                                    for fv in form_values:
                                        if fv.get("name") == "id":
                                            authenticator_id = fv.get("value")
                                            break
                                    break

            if not authenticator_id:
                # Fallback: try authenticators array
                authenticators = identify_data.get("authenticators", {}).get("value", [])
                for auth in authenticators:
                    if auth.get("key") == "okta_verify":
                        authenticator_id = auth.get("id")
                        break

            # Call /challenge to select Okta Verify with TOTP method
            if authenticator_id:
                print(f"  Selecting Okta Verify TOTP: {authenticator_id}")
                select_resp = self._client.post(
                    f"{self.OKTA_BASE}/idp/idx/challenge",
                    json={
                        "authenticator": {
                            "id": authenticator_id,
                            "methodType": "totp"
                        },
                        "stateHandle": state_handle,
                    },
                    headers=self.IDX_HEADERS,
                )
                if select_resp.status_code == 200:
                    select_data = select_resp.json()
                    state_handle = select_data.get("stateHandle", state_handle)
                    print("  Authenticator selected successfully")
                else:
                    print(f"  Warning: challenge select returned {select_resp.status_code}")
                    print(f"  Response: {select_resp.text[:200]}")

            # Step 5b: Submit MFA code
            mfa_code = self.mfa_callback()

            challenge_resp = self._client.post(
                f"{self.OKTA_BASE}/idp/idx/challenge/answer",
                json={
                    "credentials": {"totp": mfa_code},
                    "stateHandle": state_handle,
                },
                headers=self.IDX_HEADERS,
            )

            if challenge_resp.status_code != 200:
                raise AuthenticationError(f"MFA failed: {challenge_resp.status_code}")

            challenge_data = challenge_resp.json()

            # CRITICAL: Use success.href URL, NOT stateHandle
            # The success URL contains a short stateToken that produces valid SAML
            success_info = challenge_data.get("success", {})
            success_url = success_info.get("href")
        else:
            # No MFA - check for success in identify response
            success_info = identify_data.get("success", {})
            success_url = success_info.get("href")

        # Step 6: Get the redirect with SAML response
        print("Getting SAML assertion...")
        if success_url:
            token_redirect = success_url
        else:
            # Fallback (shouldn't happen if flow completed successfully)
            raise AuthenticationError("No success URL in authentication response")

        token_resp = self._client.get(token_redirect, follow_redirects=True)

        # Extract SAML response from the page (it's in a form that auto-submits)
        saml_response, relay_state = self._extract_saml_response(token_resp.text)
        if not saml_response:
            raise AuthenticationError("Could not extract SAML response")

        # Debug: Show RelayState we're sending
        print(f"  RelayState: {relay_state}")

        # Check JSESSIONID before SAML POST
        pre_saml_jsessionid = None
        for c in self._client.cookies.jar:
            if c.name == "JSESSIONID" and "service-now.com" in c.domain:
                pre_saml_jsessionid = c.value
                print(f"  JSESSIONID before SAML POST: {pre_saml_jsessionid[:30]}...")

        # Step 7: Submit SAML response to ServiceNow
        # Must include all browser headers - ServiceNow checks these
        print("Completing SSO callback...")
        callback_resp = self._client.post(
            f"{self.SERVICENOW_BASE}/nav_to.do",
            data={
                "SAMLResponse": saml_response,
                "RelayState": relay_state,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://sso.ellucian.com",
                "Referer": "https://sso.ellucian.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
            },
        )

        print(f"  nav_to.do response: {callback_resp.status_code}")

        # Debug: Show what cookies were set (including if cleared)
        for name, value in callback_resp.headers.multi_items():
            if name.lower() == "set-cookie":
                cookie_part = value.split(";")[0]  # Get name=value part
                cookie_name = cookie_part.split("=")[0]
                cookie_val = cookie_part.split("=", 1)[1] if "=" in cookie_part else ""
                if "Max-Age=0" in value or "Expires=Thu, 01-Jan-1970" in value:
                    print(f"  Set-Cookie: {cookie_name} (CLEARED)")
                elif len(cookie_val) > 20:
                    print(f"  Set-Cookie: {cookie_name}={cookie_val[:20]}...")
                else:
                    print(f"  Set-Cookie: {cookie_name}={cookie_val}")

        # Follow redirects to establish session
        while callback_resp.status_code in (301, 302):
            location = callback_resp.headers.get("location", "")
            print(f"  Location header: {location}")
            if not location.startswith("http"):
                location = f"{self.SERVICENOW_BASE}{location}"
            print(f"  Following redirect to: {location}")
            callback_resp = self._client.get(location)
            print(f"  Response: {callback_resp.status_code}")

            # Check x-is-logged-in header
            logged_in = callback_resp.headers.get("x-is-logged-in", "not-set")
            print(f"  x-is-logged-in: {logged_in}")

        # Ensure we hit customer_center to get glide_session_store cookie
        if "customer_center" not in str(callback_resp.url):
            print("  Visiting customer_center to establish session...")
            callback_resp = self._client.get(target_url)
            logged_in = callback_resp.headers.get("x-is-logged-in", "not-set")
            print(f"  x-is-logged-in: {logged_in}")

        # Build session from cookies
        session = AuthSession()
        for cookie in self._client.cookies.jar:
            session.cookies[cookie.name] = cookie.value
            if cookie.name == "glide_session_store":
                session.glide_session_store = cookie.value

        if session.is_authenticated:
            print("Authentication successful!")
            session.save()
            print(f"Session saved to {DEFAULT_COOKIE_FILE}")
        else:
            # Debug: Show all cookies we have
            print("  Cookies present:")
            for cookie in self._client.cookies.jar:
                print(f"    {cookie.name} ({cookie.domain})")
            raise AuthenticationError("Authentication completed but no session cookie")

        return session

    @classmethod
    def validate_session(cls, session: AuthSession) -> bool:
        """Check if a saved session is still valid.

        Args:
            session: Previously saved session to validate.

        Returns:
            True if session is still valid, False if re-auth needed.
        """
        if not session.is_authenticated:
            return False

        # Make a test request to see if we're still logged in
        with httpx.Client(timeout=30.0) as client:
            # Set cookies from session
            for name, value in session.cookies.items():
                client.cookies.set(name, value, domain="elluciansupport.service-now.com")

            resp = client.get(
                f"{cls.SERVICENOW_BASE}/customer_center?id=customer_center_home",
                follow_redirects=False,
            )

            # Check the x-is-logged-in header
            logged_in = resp.headers.get("x-is-logged-in", "false")
            return logged_in == "true"

    def _extract_saml_redirect(self, html: str) -> str | None:
        """Extract SAML redirect URL from ServiceNow page."""
        # Look for full SSO URL in the page content
        # The URL appears as: sso.ellucian.com/app/...
        match = re.search(
            r"(https?://sso\.ellucian\.com/app/[^\"'<>\s;]+)",
            html,
        )
        if match:
            url = match.group(1).replace("&amp;", "&")
            return url

        # Try window.location assignment
        match = re.search(r"window\.location\s*=\s*['\"]([^'\"]+)['\"]", html)
        if match:
            url = match.group(1)
            if url.startswith("http"):
                return url

        # Try looking for the URL-encoded version and decode it
        match = re.search(r"sso\.ellucian\.com[^\"'<>\s;]+", html)
        if match:
            from urllib.parse import unquote

            url = "https://" + unquote(match.group(0))
            return url

        return None

    def _extract_state_token(self, html: str) -> str | None:
        """Extract Okta stateToken from login page.

        The stateToken in the HTML is escaped with unicode escapes like \\x2D for dashes.
        We need to decode these escapes to get the actual token value.
        """

        match = re.search(r'"stateToken"\s*:\s*"([^"]+)"', html)
        if match:
            # Decode unicode escapes (e.g., \x2D -> -)
            token = codecs.decode(match.group(1), "unicode_escape")
            return token

        # Try alternate format (stateToken=... in URL)
        match = re.search(r"stateToken=([^&\"']+)", html)
        if match:
            token = codecs.decode(match.group(1), "unicode_escape")
            return token

        return None

    def _extract_saml_response(self, html: str) -> tuple[str | None, str | None]:
        """Extract SAMLResponse and RelayState from auto-submit form.

        IMPORTANT: Both values are HTML-encoded in the form and must be decoded.
        The SAMLResponse contains HTML entities like &#x2B; for + which break
        base64 decoding if not unescaped.
        """
        saml_match = re.search(
            r'name="SAMLResponse"[^>]*value="([^"]+)"',
            html,
        )
        relay_match = re.search(
            r'name="RelayState"[^>]*value="([^"]+)"',
            html,
        )

        saml = saml_match.group(1) if saml_match else None
        relay = relay_match.group(1) if relay_match else None

        # CRITICAL: Decode HTML entities in BOTH values
        # SAMLResponse contains &#x2B; for + and other HTML-encoded chars
        # RelayState contains &#x3a; for : etc.
        if saml:
            saml = html_module.unescape(saml)
        if relay:
            relay = html_module.unescape(relay)

        return saml, relay

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AuthenticationError(Exception):
    """Authentication failed."""

    pass
