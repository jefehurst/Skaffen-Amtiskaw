#!/usr/bin/env python3
"""Analyze the login HAR file to understand the auth flow."""

import json
from pathlib import Path

HAR_FILE = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"


def load_har():
    with open(HAR_FILE) as f:
        return json.load(f)


def analyze_introspect():
    """Analyze the introspect request."""
    har = load_har()

    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        if "introspect" in url:
            req = entry["request"]
            resp = entry["response"]

            print("=== INTROSPECT REQUEST ===")
            print(f"URL: {url}")
            print(f"Method: {req['method']}")

            print("\nCookies:")
            for c in req.get("cookies", []):
                print(f"  {c['name']}: {c['value'][:40]}...")

            print("\nAll headers:")
            for h in req.get("headers", []):
                name = h["name"]
                value = h["value"]
                # Truncate long values
                if len(value) > 80:
                    value = value[:80] + "..."
                print(f"  {name}: {value}")

            body = req.get("postData", {}).get("text", "")
            if body:
                print(f"\nRequest body (truncated): {body[:100]}...")

            print(f"\nResponse status: {resp['status']}")
            resp_content = resp.get("content", {}).get("text", "")
            if resp_content:
                data = json.loads(resp_content)
                print(f"Response keys: {list(data.keys())}")

            return


def analyze_saml_request():
    """Find where the stateToken comes from."""
    har = load_har()

    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        if "sso.ellucian.com/app/" in url and "saml" in url.lower():
            resp = entry["response"]
            content = resp.get("content", {}).get("text", "")

            print("=== SAML ENTRY POINT ===")
            print(f"URL: {url[:100]}...")
            print(f"Status: {resp['status']}")

            # Look for stateToken in response
            if "stateToken" in content:
                import re

                match = re.search(r'"stateToken"\s*:\s*"([^"]+)"', content)
                if match:
                    print(f"\nstateToken found: {match.group(1)[:50]}...")

            # Check for OktaSignIn config
            if "OktaSignIn" in content:
                print("\nOktaSignIn widget detected")
                # Extract config
                match = re.search(r"OktaSignIn\(\s*(\{[^}]+)", content)
                if match:
                    print(f"Config snippet: {match.group(1)[:200]}...")

            return


def analyze_identify():
    """Analyze the identify (credential submission) request."""
    har = load_har()

    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        if "idx/identify" in url:
            req = entry["request"]
            resp = entry["response"]

            print("=== IDENTIFY REQUEST ===")
            print(f"URL: {url}")

            body = req.get("postData", {}).get("text", "")
            if body:
                data = json.loads(body)
                print(f"Request keys: {list(data.keys())}")
                print(f"stateHandle present: {'stateHandle' in data}")

            print(f"\nResponse status: {resp['status']}")
            resp_content = resp.get("content", {}).get("text", "")
            if resp_content:
                data = json.loads(resp_content)
                print(f"Response keys: {list(data.keys())[:10]}")
                if "currentAuthenticator" in data:
                    print("MFA required (currentAuthenticator present)")

            return


def analyze_challenge():
    """Analyze the MFA challenge request."""
    har = load_har()

    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        if "challenge/answer" in url:
            req = entry["request"]
            resp = entry["response"]

            print("=== CHALLENGE/ANSWER REQUEST ===")
            print(f"URL: {url}")

            body = req.get("postData", {}).get("text", "")
            if body:
                data = json.loads(body)
                print(f"Request keys: {list(data.keys())}")

            print(f"\nResponse status: {resp['status']}")
            resp_content = resp.get("content", {}).get("text", "")
            if resp_content:
                data = json.loads(resp_content)
                print(f"Response keys: {list(data.keys())[:10]}")

            return


def analyze_token_redirect():
    """Analyze the token redirect that gets the SAML response."""
    har = load_har()

    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        if "login/token/redirect" in url:
            resp = entry["response"]

            print("=== TOKEN REDIRECT ===")
            print(f"URL: {url[:100]}...")
            print(f"Status: {resp['status']}")

            content = resp.get("content", {}).get("text", "")
            if "SAMLResponse" in content:
                print("SAMLResponse found in page")

            return


if __name__ == "__main__":
    print("\n" + "=" * 60)
    analyze_saml_request()
    print("\n" + "=" * 60)
    analyze_introspect()
    print("\n" + "=" * 60)
    analyze_identify()
    print("\n" + "=" * 60)
    analyze_challenge()
    print("\n" + "=" * 60)
    analyze_token_redirect()
