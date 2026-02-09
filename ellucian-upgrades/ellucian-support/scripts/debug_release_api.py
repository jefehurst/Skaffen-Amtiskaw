#!/usr/bin/env python3
"""Test fetching release details via ServiceNow Table API."""

import json
import os
from pathlib import Path

import httpx

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

SERVICENOW_BASE = "https://elluciansupport.service-now.com"


def main():
    session = AuthSession.load()
    if not session:
        print("No session - run 'ellucian-support login' first")
        return

    # Test sys_id from earlier search
    sys_id = "5beda846973ef15ca7bcfbc3f153afce"

    with httpx.Client(timeout=30.0) as client:
        # Set cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Try the Table API directly
        print(f"[1] Fetching release via Table API...")
        api_url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_release/{sys_id}"
        resp = client.get(api_url, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"    Keys: {list(data.keys())}")
            if "result" in data:
                result = data["result"]
                print(f"\n    Release fields ({len(result)} total):")
                for key in sorted(result.keys())[:30]:
                    val = str(result[key])[:60]
                    print(f"      {key}: {val}")

                # Save full response
                Path("/tmp/release_api.json").write_text(json.dumps(data, indent=2))
                print(f"\n    Full response saved to /tmp/release_api.json")
        else:
            print(f"    Error: {resp.text[:500]}")

        # Try to find related defects/enhancements
        print(f"\n[2] Looking for related defects...")

        # Try querying the defect table with release filter
        defect_url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_defect"
        params = {
            "sysparm_query": f"release={sys_id}",
            "sysparm_limit": "5",
            "sysparm_fields": "number,short_description,state"
        }
        resp = client.get(defect_url, params=params, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            results = data.get("result", [])
            print(f"    Found {len(results)} defects")
            for d in results[:5]:
                print(f"      - {d.get('number')}: {d.get('short_description', '')[:50]}")
        else:
            print(f"    Error: {resp.text[:300]}")

        # Try related list approach - look for release_defect or similar table
        print(f"\n[3] Trying customer portal API for release details...")
        portal_url = f"{SERVICENOW_BASE}/api/now/sp/widget/customer_center_product_release_detail"
        params = {"sys_id": sys_id}
        resp = client.get(portal_url, params=params, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            Path("/tmp/release_portal.json").write_text(json.dumps(data, indent=2))
            print(f"    Response saved to /tmp/release_portal.json")

            # Look for defects/enhancements in the response
            def find_lists(obj, path=""):
                """Recursively find lists that might be defects/enhancements."""
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        find_lists(v, f"{path}.{k}" if path else k)
                elif isinstance(obj, list) and len(obj) > 0:
                    if isinstance(obj[0], dict):
                        print(f"    Found list at {path}: {len(obj)} items")
                        if obj[0]:
                            print(f"      Keys: {list(obj[0].keys())[:8]}")

            find_lists(data)
        else:
            print(f"    Error: {resp.text[:300]}")


if __name__ == "__main__":
    main()
