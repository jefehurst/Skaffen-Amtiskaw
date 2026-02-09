#!/usr/bin/env python3
"""Test if we can bootstrap a docs session with just Zoomin cookies."""

import json
from pathlib import Path

import httpx

DOCS_API = "https://resources-admin.elluciancloud.com"


def main():
    # Load only the Zoomin cookies (not _SESSION)
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entry = har["log"]["entries"][0]

    zoomin_cookies = {}
    for h in entry["request"]["headers"]:
        if h["name"].lower() == "cookie":
            for c in h["value"].split("; "):
                if "=" in c:
                    name, val = c.split("=", 1)
                    # Only keep Zoomin auth cookies
                    if name in ("ZD__userAuthenticated", "zdgtm_session"):
                        zoomin_cookies[name] = val

    print("=== Zoomin cookies only ===")
    for name, val in zoomin_cookies.items():
        print(f"  {name}: {val[:50]}...")

    print("\n=== Test 1: Direct page fetch (expect 401) ===\n")

    with httpx.Client(timeout=30.0) as client:
        for name, val in zoomin_cookies.items():
            client.cookies.set(name, val, domain="resources-admin.elluciancloud.com")

        resp = client.get(
            f"{DOCS_API}/api/bundle/ellucian_forms/page/c_forms_overview.html",
            headers={
                "Accept": "application/json",
                "Origin": "https://resources.elluciancloud.com",
            },
        )
        print(f"Status: {resp.status_code}")

        # Check if we got a _SESSION cookie back
        for cookie in client.cookies.jar:
            if cookie.name == "_SESSION":
                print(f"Got _SESSION cookie: {cookie.value[:40]}...")

    print("\n=== Test 2: Hit user endpoint first to get session ===\n")

    with httpx.Client(timeout=30.0) as client:
        for name, val in zoomin_cookies.items():
            client.cookies.set(name, val, domain="resources-admin.elluciancloud.com")

        # First hit /api/user to establish session
        resp1 = client.get(
            f"{DOCS_API}/api/user",
            headers={
                "Accept": "application/json",
                "Origin": "https://resources.elluciancloud.com",
            },
        )
        print(f"/api/user status: {resp1.status_code}")

        # Check for _SESSION
        session_cookie = None
        for cookie in client.cookies.jar:
            if cookie.name == "_SESSION":
                session_cookie = cookie.value
                print(f"Got _SESSION: {session_cookie[:40]}...")

        if resp1.status_code == 200:
            user = resp1.json()
            print(f"User: {user.get('email', 'N/A')}")

        # Now try page fetch
        resp2 = client.get(
            f"{DOCS_API}/api/bundle/ellucian_forms/page/c_forms_overview.html",
            headers={
                "Accept": "application/json",
                "Origin": "https://resources.elluciancloud.com",
            },
        )
        print(f"\nPage fetch status: {resp2.status_code}")
        if resp2.status_code == 200:
            data = resp2.json()
            print(f"Title: {data.get('title', 'N/A')}")
            print("SUCCESS!")
        else:
            print(f"Error: {resp2.text[:200]}")


if __name__ == "__main__":
    main()
