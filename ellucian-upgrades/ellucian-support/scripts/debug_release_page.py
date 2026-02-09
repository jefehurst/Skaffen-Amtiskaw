#!/usr/bin/env python3
"""Scrape release detail page for defects/enhancements."""

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

    # Test sys_id from earlier search
    sys_id = "5beda846973ef15ca7bcfbc3f153afce"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Set cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Fetch the customer portal release page
        print(f"[1] Fetching release detail page...")
        page_url = f"{SERVICENOW_BASE}/customer_center?id=product_release_customer_center&sys_id={sys_id}"
        resp = client.get(page_url)
        print(f"    Status: {resp.status_code}")
        print(f"    URL: {resp.url}")

        # Save page for inspection
        Path("/tmp/release_page.html").write_text(resp.text)
        print(f"    Saved to /tmp/release_page.html ({len(resp.text)} bytes)")

        # Look for defect/enhancement data in the page
        # ServiceNow Service Portal often embeds data in window.NOW or ng-init attributes

        # Look for embedded JSON data
        print(f"\n[2] Looking for embedded data...")

        # Pattern 1: window.NOW
        now_match = re.search(r'window\.NOW\s*=\s*(\{.*?\});', resp.text, re.DOTALL)
        if now_match:
            print("    Found window.NOW data")

        # Pattern 2: data attributes with JSON
        data_matches = re.findall(r'data-[a-z-]+="(\{[^"]+\})"', resp.text)
        print(f"    Found {len(data_matches)} data attributes with JSON")

        # Pattern 3: Look for defect/enhancement related text
        defect_mentions = len(re.findall(r'defect', resp.text, re.I))
        enhancement_mentions = len(re.findall(r'enhancement', resp.text, re.I))
        print(f"    'defect' mentions: {defect_mentions}")
        print(f"    'enhancement' mentions: {enhancement_mentions}")

        # Pattern 4: Look for related list tables
        related_lists = re.findall(r'Related\s+(?:Defects?|Enhancements?|List)', resp.text, re.I)
        print(f"    Related list headers: {related_lists[:5]}")

        # Pattern 5: Look for API calls in embedded scripts
        api_calls = re.findall(r'/api/now/[^\s"\']+', resp.text)
        unique_apis = set(api_calls)
        print(f"\n    API endpoints referenced:")
        for api in sorted(unique_apis)[:10]:
            print(f"      {api}")

        # Try the Service Portal page API to get the page data
        print(f"\n[3] Trying SP page API...")
        sp_url = f"{SERVICENOW_BASE}/api/now/sp/page"
        params = {
            "id": "product_release_customer_center",
            "sys_id": sys_id
        }
        resp = client.get(sp_url, params=params, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            Path("/tmp/release_sp_page.json").write_text(json.dumps(data, indent=2))
            print(f"    Saved to /tmp/release_sp_page.json")

            # Recursively find arrays that might be defects/enhancements
            def find_interesting_data(obj, path="", depth=0):
                if depth > 10:
                    return
                if isinstance(obj, dict):
                    # Look for keys that suggest defects/enhancements
                    for k in obj.keys():
                        if any(x in k.lower() for x in ['defect', 'enhancement', 'issue', 'fix', 'related']):
                            val = obj[k]
                            if isinstance(val, list):
                                print(f"    {path}.{k}: list with {len(val)} items")
                            elif isinstance(val, dict):
                                print(f"    {path}.{k}: dict with keys {list(val.keys())[:5]}")
                            else:
                                print(f"    {path}.{k}: {str(val)[:60]}")
                    for k, v in obj.items():
                        find_interesting_data(v, f"{path}.{k}" if path else k, depth + 1)
                elif isinstance(obj, list) and len(obj) > 0:
                    find_interesting_data(obj[0], f"{path}[0]", depth + 1)

            print(f"\n    Interesting fields found:")
            find_interesting_data(data)
        else:
            print(f"    Error: {resp.text[:300]}")


if __name__ == "__main__":
    main()
