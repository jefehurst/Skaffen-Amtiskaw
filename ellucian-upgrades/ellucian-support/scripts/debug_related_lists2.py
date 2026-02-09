#!/usr/bin/env python3
"""Find related defects/enhancements for a release that has them."""

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

    # Release with related defects/enhancements
    sys_id = "45cce3d283b20298c2649550ceaad3d8"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Set cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Get release info first
        print(f"[1] Fetching release info...")
        api_url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_release/{sys_id}"
        resp = client.get(api_url, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            result = resp.json().get("result", {})
            print(f"    Release: {result.get('short_description', 'N/A')}")
            print(f"    Number: {result.get('number', 'N/A')}")

        # Try SP page API
        print(f"\n[2] Trying SP page API...")
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
            Path("/tmp/release_with_related.json").write_text(json.dumps(data, indent=2))
            print(f"    Saved to /tmp/release_with_related.json")

            # Deep search for related lists and defect/enhancement data
            def find_data(obj, path="", depth=0):
                if depth > 15:
                    return
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        new_path = f"{path}.{k}" if path else k
                        # Look for related list data
                        if 'related' in k.lower() or 'defect' in k.lower() or 'enhancement' in k.lower():
                            if isinstance(v, list) and len(v) > 0:
                                print(f"    FOUND: {new_path} = list[{len(v)}]")
                                if isinstance(v[0], dict):
                                    print(f"           Keys: {list(v[0].keys())[:10]}")
                                    # Print first item
                                    for ik, iv in list(v[0].items())[:5]:
                                        print(f"           {ik}: {str(iv)[:60]}")
                            elif isinstance(v, dict) and v:
                                print(f"    FOUND: {new_path} = dict keys: {list(v.keys())[:8]}")
                            elif v:
                                print(f"    FOUND: {new_path} = {str(v)[:80]}")
                        find_data(v, new_path, depth + 1)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj[:3]):
                        find_data(item, f"{path}[{i}]", depth + 1)

            print(f"\n    Searching for related data...")
            find_data(data)

        # Also try the SP widget API directly for related lists
        print(f"\n[3] Trying SP related list widget API...")
        widget_url = f"{SERVICENOW_BASE}/api/now/sp/widget/widget-related-list"
        params = {
            "table": "ellucian_product_release",
            "sys_id": sys_id,
        }
        resp = client.get(widget_url, params=params, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            Path("/tmp/related_widget.json").write_text(json.dumps(data, indent=2))
            print(f"    Saved to /tmp/related_widget.json")

        # Try the record watcher/activity stream endpoint
        print(f"\n[4] Trying record detail endpoint...")
        detail_url = f"{SERVICENOW_BASE}/api/now/sp/record/ellucian_product_release/{sys_id}"
        resp = client.get(detail_url, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            Path("/tmp/release_record.json").write_text(json.dumps(data, indent=2))
            print(f"    Saved to /tmp/release_record.json")


if __name__ == "__main__":
    main()
