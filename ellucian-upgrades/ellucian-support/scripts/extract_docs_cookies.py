#!/usr/bin/env python3
"""Extract the cookies from the initial docs request."""

import json
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    # Entry 0 is the initial page load
    entry = entries[0]

    print(f"URL: {entry['request']['url']}\n")

    print("=== All cookies in request ===\n")
    for h in entry["request"]["headers"]:
        if h["name"].lower() == "cookie":
            cookies = h["value"].split("; ")
            for c in cookies:
                if "=" in c:
                    name, val = c.split("=", 1)
                    # Truncate long values
                    if len(val) > 60:
                        val = val[:60] + "..."
                    print(f"{name:30} = {val}")
                else:
                    print(f"{c}")

    print("\n=== Response Set-Cookie ===\n")
    for h in entry["response"]["headers"]:
        if h["name"].lower() == "set-cookie":
            print(h["value"][:100])


if __name__ == "__main__":
    main()
