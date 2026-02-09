#!/usr/bin/env python3
"""Find search-related API calls in the HAR file."""

import json
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== Search-Related API Calls ===\n")

    search_keywords = ["search", "coveo", "query", "find", "lookup", "article", "case", "kb"]

    for i, entry in enumerate(entries):
        req = entry["request"]
        url = req["url"].lower()
        method = req["method"]

        if any(kw in url for kw in search_keywords):
            print(f"{i:3}. [{method:4}] {req['url'][:100]}")

            # Show POST body if present
            if method == "POST" and "postData" in req:
                pd = req["postData"]
                if "text" in pd:
                    text = pd["text"]
                    if len(text) > 200:
                        text = text[:200] + "..."
                    print(f"     Body: {text}")
                elif "params" in pd:
                    params = {p["name"]: p.get("value", "")[:50] for p in pd["params"]}
                    print(f"     Params: {params}")

            # Show response status
            print(f"     Status: {entry['response']['status']}")
            print()


if __name__ == "__main__":
    main()
