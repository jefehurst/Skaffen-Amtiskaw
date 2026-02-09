#!/usr/bin/env python3
"""Find where the Coveo Bearer token comes from."""

import json
import re
from pathlib import Path


def main():
    har_path = Path(__file__).parent.parent / "tmp" / "ellucian_support_login_and_search.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== Finding Coveo Token Source ===\n")

    # First, get the token from the search request
    search_entry = entries[260]
    token = None
    for h in search_entry["request"]["headers"]:
        if h["name"].lower() == "authorization":
            token = h["value"].replace("Bearer ", "")
            print(f"Token from search request: {token[:50]}...")
            break

    if not token:
        print("No token found in search request")
        return

    # Look for this token in earlier responses
    print("\nSearching for token in earlier responses...\n")

    for i, entry in enumerate(entries[:260]):
        resp = entry["response"]
        if "content" in resp and "text" in resp["content"]:
            text = resp["content"]["text"]
            if token[:30] in text:
                print(f"Found in entry {i}: {entry['request']['url'][:80]}")

                # Try to find context around the token
                idx = text.find(token[:30])
                context_start = max(0, idx - 50)
                context_end = min(len(text), idx + 100)
                print(f"  Context: ...{text[context_start:context_end]}...")
                print()

    # Also check for "searchToken" or "apiKey" patterns
    print("\nSearching for token-related patterns in responses...\n")

    patterns = [
        r'"searchToken"\s*:\s*"([^"]+)"',
        r'"apiKey"\s*:\s*"([^"]+)"',
        r'"accessToken"\s*:\s*"([^"]+)"',
        r'"token"\s*:\s*"(eyJ[^"]+)"',  # JWT pattern
    ]

    for i, entry in enumerate(entries[:260]):
        resp = entry["response"]
        if "content" in resp and "text" in resp["content"]:
            text = resp["content"]["text"]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    found_token = match.group(1)
                    print(f"Entry {i}: {entry['request']['url'][:60]}...")
                    print(f"  Pattern: {pattern[:30]}...")
                    print(f"  Token: {found_token[:50]}...")
                    print()


if __name__ == "__main__":
    main()
