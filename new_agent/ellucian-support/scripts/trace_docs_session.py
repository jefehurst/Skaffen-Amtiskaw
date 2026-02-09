#!/usr/bin/env python3
"""Trace how the docs session cookie gets established."""

import json
from pathlib import Path
from urllib.parse import urlparse


def main():
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== Tracing Session Establishment ===\n")

    # Look for Set-Cookie with _SESSION
    for i, entry in enumerate(entries):
        url = entry["request"]["url"]
        parsed = urlparse(url)

        # Check response headers for Set-Cookie
        for h in entry["response"]["headers"]:
            if h["name"].lower() == "set-cookie" and "_SESSION" in h["value"]:
                print(f"Entry {i}: Set-Cookie _SESSION")
                print(f"  URL: {url[:100]}")
                print(f"  Method: {entry['request']['method']}")
                print(f"  Status: {entry['response']['status']}")
                print(f"  Cookie: {h['value'][:100]}...")
                print()

    print("\n=== First few requests to resources domains ===\n")

    count = 0
    for i, entry in enumerate(entries):
        url = entry["request"]["url"]
        if "resources" in url and "elluciancloud.com" in url:
            parsed = urlparse(url)
            method = entry["request"]["method"]
            status = entry["response"]["status"]

            # Check if this request has _SESSION cookie
            has_session = False
            for h in entry["request"]["headers"]:
                if h["name"].lower() == "cookie" and "_SESSION" in h["value"]:
                    has_session = True
                    break

            session_marker = "✓" if has_session else "✗"
            print(f"{i:3}. [{method}] {status} {session_marker} {parsed.netloc}{parsed.path[:60]}")

            count += 1
            if count > 30:
                break


if __name__ == "__main__":
    main()
