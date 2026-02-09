#!/usr/bin/env python3
"""Test the timing of the Okta auth flow."""

import os
import re
import time
from pathlib import Path

import httpx

# Load env
env_file = Path(__file__).parent.parent.parent / "local.env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)


SERVICENOW_BASE = "https://elluciansupport.service-now.com"
OKTA_BASE = "https://sso.ellucian.com"
SSO_ID = "7d6eb13447c309500cf60562846d430c"


def extract_saml_url(html: str) -> str | None:
    match = re.search(r"(https?://sso\.ellucian\.com/app/[^\"'<>\s;]+)", html)
    if match:
        return match.group(1).replace("&amp;", "&")
    return None


def extract_state_token(html: str) -> str | None:
    import codecs

    match = re.search(r'"stateToken"\s*:\s*"([^"]+)"', html)
    if match:
        # Decode unicode escapes (e.g., \x2D -> -)
        token = codecs.decode(match.group(1), "unicode_escape")
        return token
    return None


def test_flow():
    with httpx.Client(follow_redirects=False, timeout=30.0) as client:
        # Step 1: Get SSO redirect
        t0 = time.time()
        resp = client.get(f"{SERVICENOW_BASE}/login_with_sso.do?glide_sso_id={SSO_ID}")
        t1 = time.time()
        print(f"[{t1 - t0:.2f}s] SSO initiate: {resp.status_code}")

        if resp.status_code == 302:
            redirect_url = resp.headers.get("location", "")
            if not redirect_url.startswith("http"):
                redirect_url = f"{SERVICENOW_BASE}{redirect_url}"
            resp = client.get(redirect_url)
            t2 = time.time()
            print(f"[{t2 - t1:.2f}s] auth_redirect: {resp.status_code}")

        # Extract SAML URL
        saml_url = extract_saml_url(resp.text)
        if not saml_url:
            print("ERROR: No SAML URL found")
            return

        # Step 2: Load Okta page
        okta_resp = client.get(saml_url)
        t3 = time.time()
        print(f"[{t3 - t2:.2f}s] Okta page: {okta_resp.status_code}")

        # Check raw Set-Cookie headers
        print("  Raw Set-Cookie headers from Okta page:")
        for header_name, header_value in okta_resp.headers.multi_items():
            if header_name.lower() == "set-cookie":
                # Parse cookie name and value
                cookie_part = header_value.split(";")[0]
                print(f"    {cookie_part[:60]}...")

        print(f"  Cookie jar: {[(c.name, c.domain) for c in client.cookies.jar]}")

        # Extract stateToken
        state_token = extract_state_token(okta_resp.text)
        if not state_token:
            print("ERROR: No stateToken found")
            Path("/tmp/okta_page.html").write_text(okta_resp.text)
            print("  Saved page to /tmp/okta_page.html")
            return

        print(f"  stateToken: {state_token[:80]}...")
        print(f"  stateToken length: {len(state_token)}")

        # Check current cookies before introspect
        okta_cookies = {c.name: c.value for c in client.cookies.jar if c.domain == "sso.ellucian.com"}
        print(f"  JSESSIONID before introspect: {okta_cookies.get('JSESSIONID', 'none')[:40]}...")
        print(f"  DT before introspect: {okta_cookies.get('DT', 'none')[:40]}...")

        # Step 3: Call introspect with browser-matching headers
        t4 = time.time()

        # Build request manually to inspect what gets sent
        introspect_req = client.build_request(
            "POST",
            f"{OKTA_BASE}/idp/idx/introspect",
            json={"stateToken": state_token},
            headers={
                "Accept": "application/ion+json; okta-version=1.0.0",
                "Content-Type": "application/ion+json; okta-version=1.0.0",
                "Origin": "https://sso.ellucian.com",
                "Referer": saml_url,
                "X-Okta-User-Agent-Extended": "okta-auth-js/7.14.0 okta-signin-widget-7.37.1",
            },
        )
        print("\n  Introspect request headers:")
        for name, value in introspect_req.headers.items():
            if name.lower() == "cookie":
                print(f"    cookie: {value[:80]}...")
            elif name.lower() in ("accept", "content-type", "origin", "x-okta-user-agent-extended"):
                print(f"    {name}: {value}")

        introspect_resp = client.send(introspect_req)
        t5 = time.time()
        print(f"[{t5 - t4:.2f}s] Introspect: {introspect_resp.status_code}")

        if introspect_resp.status_code != 200:
            print(f"  Error: {introspect_resp.text[:200]}")
        else:
            data = introspect_resp.json()
            print(f"  stateHandle: {'yes' if 'stateHandle' in data else 'no'}")
            print(f"  expiresAt: {data.get('expiresAt', 'unknown')}")

        print(f"\nTotal time: {t5 - t0:.2f}s")


if __name__ == "__main__":
    test_flow()
