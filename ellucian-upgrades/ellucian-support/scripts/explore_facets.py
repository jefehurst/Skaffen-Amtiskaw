#!/usr/bin/env python3
"""Explore Coveo search facets/filters."""

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

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ellucian_support.auth import AuthSession

SERVICENOW_BASE = "https://elluciansupport.service-now.com"
COVEO_BASE = "https://platform.cloud.coveo.com"


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


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "banner"

    session = AuthSession.load()
    if not session:
        print("No saved session. Run 'poetry run ellucian-support login' first.")
        sys.exit(1)

    with httpx.Client(timeout=30.0) as client:
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Get search token
        page_resp = client.get(f"{SERVICENOW_BASE}/api/now/sp/page?id=csm_coveo_search")
        token = find_token(page_resp.json())

        # Search with facet request
        search_params = {
            "q": query,
            "searchHub": "CustomerCenter_MainSearch",
            "locale": "en",
            "firstResult": 0,
            "numberOfResults": 5,
            "excerptLength": 200,
            "enableDidYouMean": "true",
            "sortCriteria": "relevancy",
            # Request facets
            "groupBy": json.dumps(
                [
                    {"field": "@source", "maximumNumberOfValues": 20},
                    {"field": "@filetype", "maximumNumberOfValues": 20},
                    {"field": "@ellucianproduct", "maximumNumberOfValues": 30},
                    {"field": "@elluciancontenttype", "maximumNumberOfValues": 20},
                    {"field": "@year", "maximumNumberOfValues": 10},
                ]
            ),
        }

        resp = client.post(
            f"{COVEO_BASE}/rest/search/v2?organizationId=ellucian",
            data=urlencode(search_params),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )

        data = resp.json()

        print(f"=== Facets for query: '{query}' ===\n")
        print(f"Total results: {data.get('totalCount', 0)}\n")

        group_by = data.get("groupByResults", [])
        for group in group_by:
            field = group.get("field", "unknown")
            values = group.get("values", [])
            print(f"\n{field}:")
            for v in values[:15]:
                name = v.get("value", v.get("lookupValue", "?"))
                count = v.get("numberOfResults", 0)
                print(f"  {name}: {count}")
            if len(values) > 15:
                print(f"  ... and {len(values) - 15} more")


if __name__ == "__main__":
    main()
