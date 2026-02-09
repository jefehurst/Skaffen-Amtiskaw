#!/usr/bin/env python3
"""Debug script to see the identify response structure."""

import codecs
import json
import os
import re
import sys
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

IDX_HEADERS = {
    "Accept": "application/ion+json; okta-version=1.0.0",
    "Content-Type": "application/ion+json; okta-version=1.0.0",
    "Origin": "https://sso.ellucian.com",
    "X-Okta-User-Agent-Extended": "okta-auth-js/7.14.0 okta-signin-widget-7.37.1",
}


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

    print(f"Debugging auth flow for: {username}")
    print()

    with httpx.Client(follow_redirects=False, timeout=30.0) as client:
        # Step 1: SSO initiate
        print("[1] SSO initiate...")
        target_url = f"{SERVICENOW_BASE}/customer_center?id=customer_center_home"
        client.get(target_url)
        sso_url = f"{SERVICENOW_BASE}/login_with_sso.do?glide_sso_id={SSO_ID}"
        resp = client.get(sso_url)
        if resp.status_code == 302:
            redirect_url = resp.headers.get("location", "")
            if not redirect_url.startswith("http"):
                redirect_url = f"{SERVICENOW_BASE}{redirect_url}"
            resp = client.get(redirect_url)
        print("  OK")

        # Step 2: Get Okta page
        saml_url = extract_saml_url(resp.text)
        if not saml_url:
            print("  ERROR: No SAML URL")
            return

        print("[2] Load Okta page...")
        okta_resp = client.get(saml_url)
        state_token = extract_state_token(okta_resp.text)
        if not state_token:
            print("  ERROR: No stateToken")
            return
        print("  OK")

        # Step 3: Introspect
        print("[3] Introspect...")
        introspect_resp = client.post(
            f"{OKTA_BASE}/idp/idx/introspect",
            json={"stateToken": state_token},
            headers=IDX_HEADERS,
        )
        if introspect_resp.status_code != 200:
            print(f"  ERROR: {introspect_resp.status_code}")
            return
        state_handle = introspect_resp.json().get("stateHandle", "")
        print("  OK")

        # Step 4: Identify
        print("[4] Identify (submit credentials)...")
        identify_resp = client.post(
            f"{OKTA_BASE}/idp/idx/identify",
            json={
                "identifier": username,
                "credentials": {"passcode": password},
                "stateHandle": state_handle,
            },
            headers=IDX_HEADERS,
        )
        if identify_resp.status_code != 200:
            print(f"  ERROR: {identify_resp.status_code}")
            print(identify_resp.text[:500])
            return

        identify_data = identify_resp.json()
        print("  OK")
        print()
        print("=" * 60)
        print("IDENTIFY RESPONSE (formatted):")
        print("=" * 60)
        print(json.dumps(identify_data, indent=2))
        print()

        # Save to file for easier reading
        output_file = Path("/tmp/identify_response.json")
        output_file.write_text(json.dumps(identify_data, indent=2))
        print(f"Full response saved to: {output_file}")


if __name__ == "__main__":
    main()
