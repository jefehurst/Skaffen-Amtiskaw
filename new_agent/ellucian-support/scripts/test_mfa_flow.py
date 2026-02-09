#!/usr/bin/env python3
"""Test MFA flow - pauses for code input."""

import base64
import codecs
import os
import re
import sys
import zlib
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


def extract_saml_response(html: str) -> tuple[str | None, str | None]:
    import html as html_module

    saml_match = re.search(r'name="SAMLResponse"[^>]*value="([^"]+)"', html)
    relay_match = re.search(r'name="RelayState"[^>]*value="([^"]+)"', html)

    saml = saml_match.group(1) if saml_match else None
    relay = relay_match.group(1) if relay_match else None

    # Decode HTML entities in RelayState (e.g., &#x3a; -> :)
    if relay:
        relay = html_module.unescape(relay)

    return saml, relay


def main():
    mfa_code = sys.argv[1] if len(sys.argv) > 1 else None

    username = os.environ.get("ELLUCIAN_SUPPORT_USER")
    password = os.environ.get("ELLUCIAN_SUPPORT_PW")

    if not mfa_code:
        print("Usage: python test_mfa_flow.py <MFA_CODE>")
        print("Run this with a fresh MFA code from Google Authenticator")
        sys.exit(1)

    print(f"Testing full auth flow for: {username}")
    print(f"MFA code: {mfa_code}")
    print()

    with httpx.Client(follow_redirects=False, timeout=30.0) as client:
        # Step 1: SSO initiate - start from customer_center like browser does
        # This sets RelayState to return to customer_center after auth
        print("[1/7] SSO initiate...")

        # First visit customer_center to establish the return URL context
        target_url = f"{SERVICENOW_BASE}/customer_center?id=customer_center_home"
        resp = client.get(target_url)
        print(f"  Initial page: {resp.status_code}")

        # Track JSESSIONID through the flow
        initial_jsessionid = None
        for c in client.cookies.jar:
            if c.name == "JSESSIONID" and "service-now.com" in c.domain:
                initial_jsessionid = c.value
                print(f"  Initial JSESSIONID: {initial_jsessionid[:20]}...")

        # Now initiate SSO with the target URL
        sso_url = f"{SERVICENOW_BASE}/login_with_sso.do?glide_sso_id={SSO_ID}&sysparm_url={target_url}"
        resp = client.get(sso_url)

        if resp.status_code == 302:
            redirect_url = resp.headers.get("location", "")
            if not redirect_url.startswith("http"):
                redirect_url = f"{SERVICENOW_BASE}{redirect_url}"
            resp = client.get(redirect_url)
        print("  OK")

        # Step 2: Get SAML URL and load Okta page
        saml_url = extract_saml_url(resp.text)
        if not saml_url:
            print("  ERROR: No SAML URL found")
            return False

        # Extract and decode SAMLRequest to get the request ID
        parsed = urlparse(saml_url)
        params = parse_qs(parsed.query)
        if "SAMLRequest" in params:
            try:
                saml_req = zlib.decompress(
                    base64.b64decode(params["SAMLRequest"][0]),  # noqa: F823
                    -15,
                ).decode("utf-8")
                req_id_match = re.search(r'ID="([^"]+)"', saml_req)  # noqa: F823
                if req_id_match:
                    print(f"  SAMLRequest ID: {req_id_match.group(1)}")
            except Exception as e:
                print(f"  Error decoding SAMLRequest: {e}")

        print("[2/7] Load Okta login page...")
        okta_resp = client.get(saml_url)
        state_token = extract_state_token(okta_resp.text)
        if not state_token:
            print("  ERROR: No stateToken")
            return False
        print(f"  OK (token length: {len(state_token)})")

        # Step 3: Introspect
        print("[3/7] Introspect...")
        introspect_resp = client.post(
            f"{OKTA_BASE}/idp/idx/introspect",
            json={"stateToken": state_token},
            headers=IDX_HEADERS,
        )
        if introspect_resp.status_code != 200:
            print(f"  ERROR: {introspect_resp.status_code}")
            print(f"  {introspect_resp.text[:200]}")
            return False
        state_handle = introspect_resp.json().get("stateHandle", "")
        print("  OK")

        # Step 4: Identify (submit credentials)
        print("[4/7] Submit credentials...")
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
            print(f"  {identify_resp.text[:200]}")
            return False
        identify_data = identify_resp.json()
        state_handle = identify_data.get("stateHandle", state_handle)
        print("  OK (MFA required)")

        # Step 5: Submit MFA code
        print(f"[5/7] Submit MFA code ({mfa_code})...")
        challenge_resp = client.post(
            f"{OKTA_BASE}/idp/idx/challenge/answer",
            json={
                "credentials": {"passcode": mfa_code},
                "stateHandle": state_handle,
            },
            headers=IDX_HEADERS,
        )
        if challenge_resp.status_code != 200:
            print(f"  ERROR: {challenge_resp.status_code}")
            error_text = challenge_resp.text[:500]
            print(f"  {error_text}")
            return False
        challenge_data = challenge_resp.json()
        print(f"  OK (response keys: {list(challenge_data.keys())[:8]})")

        # Get the success redirect URL - this contains the correct short stateToken
        success_info = challenge_data.get("success", {})
        if success_info:
            success_url = success_info.get("href", "")
            print(f"  Success URL: {success_url[:70]}...")
        else:
            print("  WARNING: No success object in response!")
            success_url = None

        # Step 6: Get SAML assertion via token redirect
        print("[6/7] Get SAML assertion...")
        if success_url:
            token_redirect = success_url
        else:
            # Fallback to constructing URL (this was the bug - using full stateHandle)
            state_handle = challenge_data.get("stateHandle", state_handle)
            token_redirect = f"{OKTA_BASE}/login/token/redirect?stateToken={state_handle}"

        print(f"  Fetching: {token_redirect[:70]}...")
        token_resp = client.get(token_redirect, follow_redirects=True)

        saml_response, relay_state = extract_saml_response(token_resp.text)
        if not saml_response:
            print("  ERROR: No SAML response in page")
            # Debug: save page
            Path("/tmp/token_redirect.html").write_text(token_resp.text)
            print("  Saved page to /tmp/token_redirect.html")
            return False
        print(f"  OK (SAML response length: {len(saml_response)})")
        print(f"  RelayState: {relay_state}")

        # Decode and inspect SAML response
        import base64

        try:
            saml_decoded = base64.b64decode(saml_response).decode("utf-8")
            import re

            dest = re.search(r'Destination="([^"]+)"', saml_decoded)
            inresp = re.search(r'InResponseTo="([^"]+)"', saml_decoded)
            nameid = re.search(r"<saml2:NameID[^>]*>([^<]+)</saml2:NameID>", saml_decoded)
            print(f"  SAML Destination: {dest.group(1) if dest else 'N/A'}")
            print(f"  SAML InResponseTo: {inresp.group(1) if inresp else 'N/A'}")
            print(f"  SAML NameID: {nameid.group(1) if nameid else 'N/A'}")
        except Exception as e:
            print(f"  Error decoding SAML: {e}")

        # Step 7: Submit SAML to ServiceNow
        print("[7/7] Complete SSO callback...")

        # Debug: show cookies we'll send and check JSESSIONID
        print("  Cookies being sent:")
        final_jsessionid = None
        for c in client.cookies.jar:
            if c.domain == "elluciansupport.service-now.com":
                print(f"    {c.name}: {c.value[:40]}...")
                if c.name == "JSESSIONID":
                    final_jsessionid = c.value

        if initial_jsessionid and final_jsessionid:
            if initial_jsessionid == final_jsessionid:
                print("  JSESSIONID: SAME (good)")
            else:
                print(f"  JSESSIONID: CHANGED! Initial={initial_jsessionid[:20]}... Final={final_jsessionid[:20]}...")

        callback_resp = client.post(
            f"{SERVICENOW_BASE}/nav_to.do",
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
        print(f"  POST nav_to.do: {callback_resp.status_code}")

        # Debug: Show cookies set by this response
        print("  Cookies set by nav_to.do POST:")
        for h_name, h_val in callback_resp.headers.multi_items():
            if h_name.lower() == "set-cookie":
                cookie_name = h_val.split("=")[0]
                print(f"    {cookie_name}")

        # Debug: Show redirect location
        if callback_resp.status_code == 302:
            print(f"  Location: {callback_resp.headers.get('location', 'N/A')}")

        # Follow redirects to establish session
        while callback_resp.status_code in (301, 302):
            location = callback_resp.headers.get("location", "")
            if not location.startswith("http"):
                location = f"{SERVICENOW_BASE}{location}"
            print(f"  Following redirect to: {location[:60]}...")
            callback_resp = client.get(location)
            print(f"  Status: {callback_resp.status_code}")

        # The glide_session_store is set when visiting customer_center
        # Make sure we hit that page
        if "customer_center" not in str(callback_resp.url):
            print("  Visiting customer_center to establish session...")
            customer_resp = client.get(f"{SERVICENOW_BASE}/customer_center?id=customer_center_home")
            print(f"  Status: {customer_resp.status_code}")

        # Check session
        glide_session = None
        for cookie in client.cookies.jar:
            if cookie.name == "glide_session_store":
                glide_session = cookie.value
                break

        if glide_session:
            print("  OK")
            print()
            print("=" * 50)
            print("SUCCESS! Authenticated session established.")
            print(f"glide_session_store: {glide_session[:40]}...")
            print()
            print("Cookies obtained:")
            for cookie in client.cookies.jar:
                if cookie.domain == "elluciansupport.service-now.com":
                    print(f"  {cookie.name}: {cookie.value[:30]}...")
            return True
        else:
            print("  WARNING: No glide_session_store cookie")
            print("  Cookies present:")
            for cookie in client.cookies.jar:
                print(f"    {cookie.name} ({cookie.domain})")
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
