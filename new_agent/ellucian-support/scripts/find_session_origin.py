#!/usr/bin/env python3
"""Find where the _SESSION cookie originates."""

import json
from pathlib import Path
from urllib.parse import urlparse


def main():
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== All requests in order with session status ===\n")

    for i, entry in enumerate(entries[:80]):
        url = entry["request"]["url"]
        parsed = urlparse(url)
        method = entry["request"]["method"]
        status = entry["response"]["status"]

        # Skip non-ellucian domains
        if "ellucian" not in url:
            continue

        # Check if request has _SESSION cookie
        has_session_req = False
        for h in entry["request"]["headers"]:
            if h["name"].lower() == "cookie" and "_SESSION" in h["value"]:
                has_session_req = True
                break

        # Check if response sets _SESSION cookie
        sets_session = False
        for h in entry["response"]["headers"]:
            if h["name"].lower() == "set-cookie" and "_SESSION" in h["value"]:
                sets_session = True
                break

        req_marker = "✓" if has_session_req else " "
        resp_marker = "SET" if sets_session else "   "

        host = parsed.netloc[:30]
        path = parsed.path[:50]
        print(f"{i:3}. [{method:4}] {status} req:{req_marker} resp:{resp_marker} {host:30} {path}")

    # Now look for what happens BEFORE entry 17
    print("\n\n=== Detailed look at entries 0-20 ===\n")

    for i, entry in enumerate(entries[:20]):
        url = entry["request"]["url"]
        if "ellucian" not in url:
            continue

        print(f"\n=== Entry {i} ===")
        print(f"URL: {url[:100]}")
        print(f"Method: {entry['request']['method']}")
        print(f"Status: {entry['response']['status']}")

        # Request cookies
        print("Request cookies:")
        for h in entry["request"]["headers"]:
            if h["name"].lower() == "cookie":
                cookies = h["value"].split("; ")
                for c in cookies[:5]:
                    print(f"  {c[:60]}")
                if len(cookies) > 5:
                    print(f"  ... and {len(cookies) - 5} more")

        # Response Set-Cookie
        print("Response Set-Cookie:")
        for h in entry["response"]["headers"]:
            if h["name"].lower() == "set-cookie":
                print(f"  {h['value'][:80]}...")


if __name__ == "__main__":
    main()
