#!/usr/bin/env python3
"""Find related defects/enhancements on release page."""

import json
import os
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

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

    # User-provided sys_id with related items
    sys_id = "483bb9bbc3139a9088a01d63e4013138"

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        # Set cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Fetch the HTML page
        print(f"[1] Fetching release page HTML...")
        page_url = f"{SERVICENOW_BASE}/customer_center?id=standard_ticket&table=ellucian_product_release&sys_id={sys_id}"
        resp = client.get(page_url)
        print(f"    Status: {resp.status_code}")
        print(f"    Size: {len(resp.text)} bytes")

        # Save HTML
        Path("/tmp/release_page.html").write_text(resp.text)
        print(f"    Saved to /tmp/release_page.html")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Look for related list sections
        print(f"\n[2] Looking for related list sections...")

        # Find elements with "defect" or "enhancement" in text/class/id
        for tag in soup.find_all(['div', 'section', 'h2', 'h3', 'span', 'a']):
            text = tag.get_text().lower()
            classes = ' '.join(tag.get('class', []))
            tag_id = tag.get('id', '')

            if any(x in text for x in ['related defect', 'related enhancement', 'defects', 'enhancements']):
                print(f"    Found: <{tag.name}> '{tag.get_text()[:50]}' class='{classes[:30]}'")

        # Look for tables that might contain defects/enhancements
        print(f"\n[3] Looking for data tables...")
        tables = soup.find_all('table')
        print(f"    Found {len(tables)} tables")

        for i, table in enumerate(tables[:5]):
            headers = [th.get_text().strip() for th in table.find_all('th')]
            rows = len(table.find_all('tr'))
            print(f"    Table {i}: {rows} rows, headers: {headers[:5]}")

        # Look for Angular/ServiceNow widget data
        print(f"\n[4] Looking for embedded widget data...")
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'related' in script.string.lower():
                # Find JSON-like structures
                matches = re.findall(r'"related[^"]*":\s*\[[^\]]*\]', script.string)
                for m in matches[:3]:
                    print(f"    Found: {m[:100]}...")

        # Try the related list API directly
        print(f"\n[5] Trying related list API...")
        # ServiceNow related list endpoint pattern
        rl_url = f"{SERVICENOW_BASE}/api/now/ui/related_list"
        params = {
            "table": "ellucian_product_release",
            "sys_id": sys_id
        }
        resp = client.get(rl_url, params=params, headers={"Accept": "application/json"})
        print(f"    Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            Path("/tmp/related_list_api.json").write_text(json.dumps(data, indent=2))
            print(f"    Saved to /tmp/related_list_api.json")
        else:
            print(f"    Response: {resp.text[:200]}")

        # Try GlideRecord-style query for related defects
        print(f"\n[6] Trying m2m relationship query...")
        # Look for release_defect or similar relationship table
        m2m_url = f"{SERVICENOW_BASE}/api/now/table/m2m_ellucian_release_defect"
        params = {"sysparm_query": f"release={sys_id}", "sysparm_limit": "10"}
        resp = client.get(m2m_url, params=params, headers={"Accept": "application/json"})
        print(f"    m2m_ellucian_release_defect: {resp.status_code}")

        if resp.status_code != 200:
            # Try alternative table names
            for table in ["ellucian_release_defect", "release_defect_m2m", "ellucian_product_release_defect"]:
                resp = client.get(f"{SERVICENOW_BASE}/api/now/table/{table}",
                                params=params, headers={"Accept": "application/json"})
                print(f"    {table}: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("result", [])
                    print(f"      Found {len(results)} records")
                    if results:
                        print(f"      Keys: {list(results[0].keys())}")
                    break


if __name__ == "__main__":
    main()
