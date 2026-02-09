#!/usr/bin/env python3
"""Analyze the Coveo search API call."""

import json
from pathlib import Path
from urllib.parse import parse_qs, unquote


def main():
    har_path = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== Coveo Search API Analysis ===\n")

    # Entry 260 is the main search POST
    entry = entries[260]
    req = entry["request"]
    resp = entry["response"]

    print(f"URL: {req['url']}")
    print(f"Method: {req['method']}")
    print(f"Status: {resp['status']}")
    print()

    # Parse headers
    print("Request Headers:")
    for h in req["headers"]:
        name = h["name"]
        if name.lower() in ["authorization", "content-type", "accept", "origin"]:
            print(f"  {name}: {h['value'][:80]}...")
    print()

    # Parse POST body
    if "postData" in req:
        pd = req["postData"]
        if "text" in pd:
            # URL-encoded body
            params = parse_qs(pd["text"])
            print("POST Parameters:")
            for key, values in params.items():
                val = values[0] if values else ""
                if key == "q":
                    print(f"  q (query): {unquote(val)}")
                elif key == "searchHub":
                    print(f"  searchHub: {val}")
                elif key == "tab":
                    print(f"  tab: {val}")
                elif key == "pipeline":
                    print(f"  pipeline: {val}")
                elif key == "firstResult":
                    print(f"  firstResult: {val}")
                elif key == "numberOfResults":
                    print(f"  numberOfResults: {val}")
                elif len(val) < 100:
                    print(f"  {key}: {val}")
                else:
                    print(f"  {key}: ({len(val)} chars)")
    print()

    # Check response
    if "content" in resp and "text" in resp["content"]:
        try:
            data = json.loads(resp["content"]["text"])
            print("Response Structure:")
            print(f"  totalCount: {data.get('totalCount', 'N/A')}")
            print(f"  duration: {data.get('duration', 'N/A')} ms")

            results = data.get("results", [])
            print(f"  results: {len(results)} items")

            if results:
                print("\n  First result:")
                first = results[0]
                print(f"    title: {first.get('title', 'N/A')[:60]}")
                print(f"    uri: {first.get('uri', 'N/A')[:60]}")
                print(f"    clickUri: {first.get('clickUri', 'N/A')[:60]}")

        except json.JSONDecodeError:
            print("  (Could not parse response as JSON)")


if __name__ == "__main__":
    main()
