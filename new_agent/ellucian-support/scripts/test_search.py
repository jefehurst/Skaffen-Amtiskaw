#!/usr/bin/env python3
"""Test the search functionality with our authenticated session."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

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

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ellucian_support.auth import AuthSession

SERVICENOW_BASE = "https://elluciansupport.service-now.com"
COVEO_BASE = "https://platform.cloud.coveo.com"


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "banner upgrade"

    print(f"=== Testing Search: '{query}' ===\n")

    # Load saved session
    session = AuthSession.load()
    if not session:
        print("No saved session. Run 'poetry run ellucian-support login' first.")
        sys.exit(1)

    print("Session loaded.")

    with httpx.Client(timeout=30.0) as client:
        # Set cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Step 1: Get search token from ServiceNow
        print("\n[1] Getting search token...")
        page_url = f"{SERVICENOW_BASE}/api/now/sp/page?id=csm_coveo_search"
        resp = client.get(page_url)

        if resp.status_code != 200:
            print(f"  Failed: {resp.status_code}")
            print(f"  x-is-logged-in: {resp.headers.get('x-is-logged-in', 'N/A')}")
            sys.exit(1)

        # Extract searchToken from response
        data = resp.json()
        search_token = None

        # Try to find searchToken in the data
        def find_token(obj, key="searchToken"):
            if isinstance(obj, dict):
                if key in obj:
                    return obj[key]
                for v in obj.values():
                    result = find_token(v, key)
                    if result:
                        return result
            elif isinstance(obj, list):
                for item in obj:
                    result = find_token(item, key)
                    if result:
                        return result
            return None

        search_token = find_token(data)

        if not search_token:
            print("  Could not find searchToken in response")
            print(f"  Response keys: {list(data.keys())}")
            # Save for debugging
            Path("/tmp/search_page_response.json").write_text(json.dumps(data, indent=2))
            print("  Saved response to /tmp/search_page_response.json")
            sys.exit(1)

        print(f"  Got token: {search_token[:50]}...")

        # Step 2: Search with Coveo
        print("\n[2] Searching Coveo...")

        search_params = {
            "q": query,
            "searchHub": "CustomerCenter_MainSearch",
            "locale": "en",
            "firstResult": 0,
            "numberOfResults": 10,
            "excerptLength": 200,
            "enableDidYouMean": "true",
            "sortCriteria": "relevancy",
        }

        search_resp = client.post(
            f"{COVEO_BASE}/rest/search/v2?organizationId=ellucian",
            data=urlencode(search_params),
            headers={
                "Authorization": f"Bearer {search_token}",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Accept": "*/*",
            },
        )

        if search_resp.status_code != 200:
            print(f"  Failed: {search_resp.status_code}")
            print(f"  Response: {search_resp.text[:500]}")
            sys.exit(1)

        results = search_resp.json()
        total = results.get("totalCount", 0)
        items = results.get("results", [])

        print(f"  Total results: {total}")
        print(f"  Returned: {len(items)}")

        print("\n=== Results ===\n")
        for i, item in enumerate(items[:5], 1):
            title = item.get("title", "No title")
            uri = item.get("clickUri", item.get("uri", ""))
            excerpt = item.get("excerpt", "")[:150]
            print(f"{i}. {title}")
            print(f"   {uri}")
            print(f"   {excerpt}...")
            print()


if __name__ == "__main__":
    main()
