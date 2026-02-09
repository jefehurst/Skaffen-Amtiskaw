#!/usr/bin/env python3
"""Test through the identify (credential submission) step."""

import codecs
import os
import re
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
    match = re.search(r'"stateToken"\s*:\s*"([^"]+)"', html)
    if match:
        return codecs.decode(match.group(1), "unicode_escape")
    return None


def main():
    username = os.environ.get("ELLUCIAN_SUPPORT_USER")
    password = os.environ.get("ELLUCIAN_SUPPORT_PW")

    print(f"Testing auth for: {username}")

    with httpx.Client(follow_redirects=False, timeout=30.0) as client:
        # Step 1: SSO initiate
        print("\n[1] SSO initiate...")
        resp = client.get(f"{SERVICENOW_BASE}/login_with_sso.do?glide_sso_id={SSO_ID}")
        if resp.status_code == 302:
            redirect_url = resp.headers.get("location", "")
            if not redirect_url.startswith("http"):
                redirect_url = f"{SERVICENOW_BASE}{redirect_url}"
            resp = client.get(redirect_url)

        saml_url = extract_saml_url(resp.text)
        if not saml_url:
            print("ERROR: No SAML URL found")
            return
        print(f"  SAML URL: {saml_url[:80]}...")

        # Step 2: Load Okta page
        print("\n[2] Load Okta login page...")
        okta_resp = client.get(saml_url)
        print(f"  Status: {okta_resp.status_code}")

        state_token = extract_state_token(okta_resp.text)
        if not state_token:
            print("ERROR: No stateToken")
            return
        print(f"  stateToken: {state_token[:60]}...")

        # Step 3: Introspect
        print("\n[3] Introspect...")
        introspect_resp = client.post(
            f"{OKTA_BASE}/idp/idx/introspect",
            json={"stateToken": state_token},
            headers={
                "Accept": "application/ion+json; okta-version=1.0.0",
                "Content-Type": "application/ion+json; okta-version=1.0.0",
                "Origin": "https://sso.ellucian.com",
                "X-Okta-User-Agent-Extended": "okta-auth-js/7.14.0 okta-signin-widget-7.37.1",
            },
        )
        print(f"  Status: {introspect_resp.status_code}")

        if introspect_resp.status_code != 200:
            print(f"  Error: {introspect_resp.text[:200]}")
            return

        introspect_data = introspect_resp.json()
        state_handle = introspect_data.get("stateHandle", "")
        print(f"  stateHandle: {state_handle[:60]}..." if state_handle else "  No stateHandle!")

        # Step 4: Identify (submit credentials)
        print("\n[4] Identify (submit credentials)...")
        identify_resp = client.post(
            f"{OKTA_BASE}/idp/idx/identify",
            json={
                "identifier": username,
                "credentials": {"passcode": password},
                "stateHandle": state_handle,
            },
            headers={
                "Accept": "application/ion+json; okta-version=1.0.0",
                "Content-Type": "application/ion+json; okta-version=1.0.0",
                "Origin": "https://sso.ellucian.com",
                "X-Okta-User-Agent-Extended": "okta-auth-js/7.14.0 okta-signin-widget-7.37.1",
            },
        )
        print(f"  Status: {identify_resp.status_code}")

        if identify_resp.status_code != 200:
            print(f"  Error: {identify_resp.text[:500]}")
            return

        identify_data = identify_resp.json()
        print(f"  Response keys: {list(identify_data.keys())[:10]}")

        # Check for MFA requirement
        if "currentAuthenticator" in identify_data:
            auth_info = identify_data.get("currentAuthenticator", {}).get("value", {})
            print(f"  MFA required! Authenticator type: {auth_info.get('type', 'unknown')}")
            new_state_handle = identify_data.get("stateHandle", "")
            print(f"  New stateHandle for MFA: {new_state_handle[:60]}...")
        elif "authenticators" in identify_data:
            print("  MFA authenticator selection needed")
            for auth in identify_data.get("authenticators", {}).get("value", []):
                print(f"    - {auth.get('type', 'unknown')}: {auth.get('displayName', 'N/A')}")
        else:
            print("  No MFA required (unexpected)")

        print("\n=== READY FOR MFA CODE ===")


if __name__ == "__main__":
    main()
