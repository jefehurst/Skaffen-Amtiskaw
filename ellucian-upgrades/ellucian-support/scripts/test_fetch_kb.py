#!/usr/bin/env python3
"""Test fetching article content with authenticated session."""

import os
import re
import sys
from pathlib import Path

import httpx

# Load environment
env_file = Path(__file__).parent.parent.parent / "local.env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ellucian_support.auth import AuthSession


def main():
    # Article sys_id from URL
    sys_id = sys.argv[1] if len(sys.argv) > 1 else "2701d6478757c1102f5a0dc4dabb35fb"

    session = AuthSession.load()
    if not session:
        print("No saved session. Run 'poetry run ellucian-support login' first.")
        sys.exit(1)

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Try the REST API for articles
        api_url = f"https://elluciansupport.service-now.com/api/now/table/kb_knowledge/{sys_id}"
        print(f"Fetching: {api_url}")

        resp = client.get(
            api_url,
            headers={
                "Accept": "application/json",
            },
        )

        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result", {})

            print(f"\n=== {result.get('short_description', 'No title')} ===\n")
            print(f"Number: {result.get('number', 'N/A')}")
            print(f"Category: {result.get('kb_category', 'N/A')}")
            print(f"Published: {result.get('published', 'N/A')}")
            print()

            # Text field contains the article body (may be HTML)
            text = result.get("text", "")
            if text:
                # Strip HTML tags for readability
                clean = re.sub(r"<[^>]+>", " ", text)
                clean = re.sub(r"\s+", " ", clean).strip()
                print("Content:")
                print(clean[:2000])
                if len(clean) > 2000:
                    print(f"\n... ({len(clean)} chars total)")
            else:
                print("No text content found.")
                print(f"Available fields: {list(result.keys())}")
        else:
            print(f"Error: {resp.text[:500]}")


if __name__ == "__main__":
    main()
