#!/usr/bin/env python3
"""Check what auth is needed for the docs API."""

import json
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    # Find a page request
    for entry in entries:
        url = entry["request"]["url"]
        if "/api/bundle/" in url and "/page/" in url and entry["response"]["status"] == 200:
            print(f"URL: {url}\n")
            print("=== ALL Request Headers ===")
            for h in entry["request"]["headers"]:
                name = h["name"]
                val = h["value"]
                if len(val) > 100:
                    val = val[:100] + "..."
                print(f"  {name}: {val}")

            print("\n=== Cookies ===")
            for h in entry["request"]["headers"]:
                if h["name"].lower() == "cookie":
                    cookies = h["value"].split("; ")
                    for c in cookies:
                        name = c.split("=")[0]
                        val = c.split("=")[1] if "=" in c else ""
                        if len(val) > 50:
                            val = val[:50] + "..."
                        print(f"  {name}: {val}")
            break


if __name__ == "__main__":
    main()
