#!/usr/bin/env python3
"""See what fields are available in release search results."""

import json
import os
from pathlib import Path

# Load env
env_file = Path(__file__).parent.parent.parent / "local.env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)

from ellucian_support.auth import AuthSession
from ellucian_support.search import search

def main():
    session = AuthSession.load()
    if not session:
        print("No session - run 'ellucian-support login' first")
        return

    # Search for a specific release
    results = search(session, "Banner General 9.19", source_filter="release", num_results=1)

    if not results.results:
        print("No results found")
        return

    result = results.results[0]
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print()
    print("=" * 60)
    print("RAW FIELDS FROM COVEO:")
    print("=" * 60)

    # Show all fields, sorted
    for key in sorted(result.raw.keys()):
        value = result.raw[key]
        # Truncate long values
        str_val = str(value)
        if len(str_val) > 100:
            str_val = str_val[:100] + "..."
        print(f"  {key}: {str_val}")

    # Save full raw to file for inspection
    output_file = Path("/tmp/release_raw.json")
    output_file.write_text(json.dumps(result.raw, indent=2, default=str))
    print()
    print(f"Full raw data saved to: {output_file}")


if __name__ == "__main__":
    main()
