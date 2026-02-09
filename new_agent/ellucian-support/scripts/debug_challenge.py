#!/usr/bin/env python3
"""Debug the challenge step to see exact error."""

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
    mfa_code = sys.argv[1] if len(sys.argv) > 1 else None
    if not mfa_code:
        print("Usage: python debug_challenge.py <MFA_CODE>")
        sys.exit(1)

    username = os.environ.get("ELLUCIAN_SUPPORT_USER")
    password = os.environ.get("ELLUCIAN_SUPPORT_PW")

    print(f"Testing challenge flow for: {username}")
    print(f"MFA code: {mfa_code}")
    print()

    with httpx.Client(follow_redirects=False, timeout=30.0) as client:
        # Steps 1-4: Get to identify
        print("[1-3] SSO + Okta + Introspect...")
        target_url = f"{SERVICENOW_BASE}/customer_center?id=customer_center_home"
        client.get(target_url)
        sso_url = f"{SERVICENOW_BASE}/login_with_sso.do?glide_sso_id={SSO_ID}"
        resp = client.get(sso_url)
        if resp.status_code == 302:
            redirect_url = resp.headers.get("location", "")
            if not redirect_url.startswith("http"):
                redirect_url = f"{SERVICENOW_BASE}{redirect_url}"
            resp = client.get(redirect_url)

        saml_url = extract_saml_url(resp.text)
        okta_resp = client.get(saml_url)
        state_token = extract_state_token(okta_resp.text)

        introspect_resp = client.post(
            f"{OKTA_BASE}/idp/idx/introspect",
            json={"stateToken": state_token},
            headers=IDX_HEADERS,
        )
        state_handle = introspect_resp.json().get("stateHandle", "")
        print("  OK")

        # Step 4: Identify
        print("[4] Identify...")
        identify_resp = client.post(
            f"{OKTA_BASE}/idp/idx/identify",
            json={
                "identifier": username,
                "credentials": {"passcode": password},
                "stateHandle": state_handle,
            },
            headers=IDX_HEADERS,
        )
        identify_data = identify_resp.json()
        state_handle = identify_data.get("stateHandle", state_handle)
        print("  OK")

        # Extract authenticator ID for Okta Verify
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

        print(f"  Okta Verify ID: {authenticator_id}")

        # Step 5a: Call challenge to select authenticator
        print("[5a] Challenge (select authenticator)...")
        challenge_payload = {
            "authenticator": {
                "id": authenticator_id,
                "methodType": "totp"
            },
            "stateHandle": state_handle,
        }
        print(f"  Payload: {json.dumps(challenge_payload, indent=2)}")

        challenge_select_resp = client.post(
            f"{OKTA_BASE}/idp/idx/challenge",
            json=challenge_payload,
            headers=IDX_HEADERS,
        )
        print(f"  Status: {challenge_select_resp.status_code}")

        if challenge_select_resp.status_code != 200:
            print(f"  ERROR Response:")
            try:
                err_json = challenge_select_resp.json()
                print(json.dumps(err_json, indent=2)[:1000])
            except:
                print(challenge_select_resp.text[:1000])
            return

        challenge_select_data = challenge_select_resp.json()
        state_handle = challenge_select_data.get("stateHandle", state_handle)
        print("  OK - Authenticator selected")

        # Save challenge response for inspection
        Path("/tmp/challenge_response.json").write_text(json.dumps(challenge_select_data, indent=2))
        print("  Response saved to /tmp/challenge_response.json")

        # Step 5b: Submit MFA code
        print(f"[5b] Challenge/answer (submit code {mfa_code})...")
        answer_resp = client.post(
            f"{OKTA_BASE}/idp/idx/challenge/answer",
            json={
                "credentials": {"totp": mfa_code},
                "stateHandle": state_handle,
            },
            headers=IDX_HEADERS,
        )
        print(f"  Status: {answer_resp.status_code}")

        if answer_resp.status_code != 200:
            print(f"  ERROR Response:")
            try:
                err_json = answer_resp.json()
                print(json.dumps(err_json, indent=2)[:1000])
            except:
                print(answer_resp.text[:1000])
            return

        answer_data = answer_resp.json()
        print("  OK - MFA accepted!")

        # Check for success URL
        success_info = answer_data.get("success", {})
        if success_info:
            print(f"  Success URL: {success_info.get('href', 'N/A')[:60]}...")
        else:
            print("  WARNING: No success URL in response")
            print(f"  Response keys: {list(answer_data.keys())}")


if __name__ == "__main__":
    main()
