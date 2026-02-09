#!/usr/bin/env python3
"""Scrape release detail page for defects/enhancements - standard_ticket format."""

import json
import os
import re
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

    # User-provided sys_id
    sys_id = "483bb9bbc3139a9088a01d63e4013138"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Set cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Try the SP page API with standard_ticket
        print(f"[1] Trying SP page API with standard_ticket...")
        sp_url = f"{SERVICENOW_BASE}/api/now/sp/page"
        params = {
            "id": "standard_ticket",
            "table": "ellucian_product_release",
            "sys_id": sys_id
        }
        resp = client.get(sp_url, params=params, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            Path("/tmp/release_standard_ticket.json").write_text(json.dumps(data, indent=2))
            print(f"    Saved to /tmp/release_standard_ticket.json")

            # Look for defects/enhancements in the data
            def find_by_key(obj, target_keys, path="", results=None):
                if results is None:
                    results = []
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if any(t in k.lower() for t in target_keys):
                            results.append((f"{path}.{k}" if path else k, v))
                        find_by_key(v, target_keys, f"{path}.{k}" if path else k, results)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj[:3]):  # Check first 3 items
                        find_by_key(item, target_keys, f"{path}[{i}]", results)
                return results

            print(f"\n    Looking for defect/enhancement data...")
            results = find_by_key(data, ['defect', 'enhancement', 'issue', 'fix', 'related_list', 'items'])
            for path, val in results[:20]:
                if isinstance(val, list):
                    print(f"      {path}: list[{len(val)}]")
                    if val and isinstance(val[0], dict):
                        print(f"        First item keys: {list(val[0].keys())[:8]}")
                elif isinstance(val, dict):
                    print(f"      {path}: dict with {len(val)} keys")
                else:
                    print(f"      {path}: {str(val)[:80]}")
        else:
            print(f"    Error: {resp.text[:500]}")

        # Also fetch the Table API for this release to get basic info
        print(f"\n[2] Fetching release info via Table API...")
        api_url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_release/{sys_id}"
        resp = client.get(api_url, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            result = data.get("result", {})
            print(f"    Release: {result.get('short_description', 'N/A')}")
            print(f"    Number: {result.get('number', 'N/A')}")
            print(f"    Date: {result.get('date_released', 'N/A')}")


if __name__ == "__main__":
    main()
