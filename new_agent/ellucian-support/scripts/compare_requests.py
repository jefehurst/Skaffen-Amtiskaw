#!/usr/bin/env python3
"""Compare our introspect request vs what the browser sends."""

import json
from pathlib import Path

HAR_FILE = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"


def get_browser_introspect():
    """Extract the browser's introspect request from HAR."""
    with open(HAR_FILE) as f:
        har = json.load(f)

    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        if "introspect" in url:
            req = entry["request"]
            return {
                "url": url,
                "method": req["method"],
                "headers": {h["name"]: h["value"] for h in req.get("headers", [])},
                "cookies": {c["name"]: c["value"] for c in req.get("cookies", [])},
                "body": req.get("postData", {}).get("text", ""),
            }
    return None


def get_browser_okta_page():
    """Get the Okta SAML page load from HAR."""
    with open(HAR_FILE) as f:
        har = json.load(f)

    for entry in har["log"]["entries"]:
        url = entry["request"]["url"]
        if "sso.ellucian.com/app/" in url and "saml" in url.lower():
            resp = entry["response"]
            return {
                "url": url,
                "status": resp["status"],
                "content": resp.get("content", {}).get("text", ""),
                "cookies_set": [(c["name"], c["value"][:40]) for c in resp.get("cookies", [])],
            }
    return None


def main():
    browser = get_browser_introspect()
    if not browser:
        print("No introspect request found in HAR")
        return

    print("=== Browser Introspect Request ===\n")

    print("Headers (relevant):")
    relevant_headers = [
        "Accept",
        "Content-Type",
        "Origin",
        "Referer",
        "X-Okta-User-Agent-Extended",
        "User-Agent",
    ]
    for h in relevant_headers:
        val = browser["headers"].get(h, "(not set)")
        print(f"  {h}: {val}")

    print(f"\nCookies sent: {list(browser['cookies'].keys())}")
    for name, val in browser["cookies"].items():
        print(f"  {name}: {val[:50]}...")

    # Parse the body to see structure
    if browser["body"]:
        body = json.loads(browser["body"])
        print(f"\nBody keys: {list(body.keys())}")
        if "stateToken" in body:
            token = body["stateToken"]
            print(f"  stateToken length: {len(token)}")
            print(f"  stateToken prefix: {token[:80]}...")

    # Check what cookies were set by the Okta page
    okta_page = get_browser_okta_page()
    if okta_page:
        print("\n=== Okta SAML Page Response ===")
        print(f"Cookies set by page: {okta_page['cookies_set']}")

    print("\n" + "=" * 50)
    print("\nHeaders we should add to match browser:")
    print()

    # Generate the headers dict we need
    print("INTROSPECT_HEADERS = {")
    print(f'    "Accept": "{browser["headers"].get("Accept", "")}",')
    print(f'    "Content-Type": "{browser["headers"].get("Content-Type", "")}",')
    print(f'    "Origin": "{browser["headers"].get("Origin", "")}",')
    x_okta = browser["headers"].get("X-Okta-User-Agent-Extended", "")
    print(f'    "X-Okta-User-Agent-Extended": "{x_okta}",')
    print("}")


if __name__ == "__main__":
    main()
