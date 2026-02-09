#!/usr/bin/env python3
"""Test the docs API with Zoomin cookies from HAR."""

import json
from pathlib import Path

import httpx

DOCS_API = "https://resources-admin.elluciancloud.com"


def main():
    # Load cookies from HAR
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entry = har["log"]["entries"][0]

    cookies = {}
    for h in entry["request"]["headers"]:
        if h["name"].lower() == "cookie":
            for c in h["value"].split("; "):
                if "=" in c:
                    name, val = c.split("=", 1)
                    cookies[name] = val

    print("=== Cookies extracted ===")
    for name, val in cookies.items():
        print(f"  {name}: {val[:40]}...")

    print("\n=== Test with Zoomin cookies ===\n")

    with httpx.Client(timeout=30.0) as client:
        # Set the cookies
        for name, val in cookies.items():
            # Set for both domains
            client.cookies.set(name, val, domain="resources.elluciancloud.com")
            client.cookies.set(name, val, domain="resources-admin.elluciancloud.com")

        # Also try with the _SESSION cookie from a later request if available
        # Look for _SESSION in entry 17
        entry17 = har["log"]["entries"][17]
        for h in entry17["request"]["headers"]:
            if h["name"].lower() == "cookie" and "_SESSION" in h["value"]:
                for c in h["value"].split("; "):
                    if c.startswith("_SESSION="):
                        session_val = c.split("=", 1)[1]
                        client.cookies.set("_SESSION", session_val, domain="resources-admin.elluciancloud.com")
                        print(f"  Added _SESSION: {session_val[:40]}...")

        # Test page fetch
        resp = client.get(
            f"{DOCS_API}/api/bundle/ellucian_forms/page/c_forms_overview.html",
            headers={
                "Accept": "application/json",
                "Origin": "https://resources.elluciancloud.com",
                "Referer": "https://resources.elluciancloud.com/",
            },
        )
        print(f"\nPage fetch status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"Title: {data.get('title', 'N/A')}")
            html = data.get("topic_html", "")
            print(f"Content length: {len(html)} chars")

            # Strip HTML and show preview
            import re

            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            print(f"Preview: {text[:300]}...")
        else:
            print(f"Error: {resp.text[:300]}")

        # Check what cookies we have now
        print("\n=== Cookies after request ===")
        for cookie in client.cookies.jar:
            print(f"  {cookie.name} @ {cookie.domain}")


if __name__ == "__main__":
    main()
