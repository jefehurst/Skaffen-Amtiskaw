#!/usr/bin/env python3
"""Extract page content from HAR to understand the API response structure."""

import json
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== Page Content API Responses ===\n")

    for i, entry in enumerate(entries):
        url = entry["request"]["url"]
        if "/api/bundle/" not in url or "/page/" not in url:
            continue

        print(f"Entry {i}: {url}")

        # Get request headers
        print("\nRequest Headers:")
        for h in entry["request"]["headers"]:
            if h["name"].lower() in ["authorization", "cookie", "x-", "accept"]:
                val = h["value"][:80] + "..." if len(h["value"]) > 80 else h["value"]
                print(f"  {h['name']}: {val}")

        resp = entry["response"]
        if "content" in resp and "text" in resp["content"]:
            try:
                data = json.loads(resp["content"]["text"])
                print(f"\nResponse keys: {list(data.keys())}")

                # Show the structure
                for key, val in data.items():
                    if isinstance(val, str):
                        preview = val[:100] + "..." if len(val) > 100 else val
                        print(f"  {key}: {preview}")
                    elif isinstance(val, dict):
                        print(f"  {key}: {{...}} ({len(val)} keys: {list(val.keys())[:5]})")
                    elif isinstance(val, list):
                        print(f"  {key}: [...] ({len(val)} items)")
                    else:
                        print(f"  {key}: {val}")

                # If there's HTML content, show a snippet
                if "content" in data:
                    html = data["content"]
                    print(f"\n  Content preview ({len(html)} chars):")
                    # Strip tags for preview
                    import re

                    text = re.sub(r"<[^>]+>", " ", html)
                    text = re.sub(r"\s+", " ", text).strip()
                    print(f"    {text[:300]}...")

            except json.JSONDecodeError:
                print("  (Not valid JSON)")

        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
