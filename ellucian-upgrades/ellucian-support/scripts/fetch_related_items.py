#!/usr/bin/env python3
"""Fetch related defects/enhancements for a release."""

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


def get_related_ids_from_page(client, sys_id):
    """Extract related defect/enhancement IDs from SP page API."""
    sp_url = f"{SERVICENOW_BASE}/api/now/sp/page"
    params = {
        "id": "standard_ticket",
        "table": "ellucian_product_release",
        "sys_id": sys_id
    }
    resp = client.get(sp_url, params=params, headers={"Accept": "application/json"})

    if resp.status_code != 200:
        return None, None

    data = resp.json()
    defect_ids = []
    enhancement_ids = []

    # Navigate to Standard Ticket Tab widget
    containers = data.get('result', {}).get('containers', [])
    for container in containers:
        for row in container.get('rows', []):
            for col in row.get('columns', []):
                for widget in col.get('widgets', []):
                    w = widget.get('widget', {})
                    if w.get('name') == 'Standard Ticket Tab':
                        tabs = w.get('data', {}).get('tabs', [])
                        for tab in tabs:
                            name = tab.get('name', '')
                            nested = tab.get('widget', {}).get('data', {}).get('widget', {})
                            options = nested.get('options', {})
                            filter_str = options.get('filter', '')

                            # Extract sys_ids from filter like "sys_idINabc,def,ghi"
                            if filter_str.startswith('sys_idIN'):
                                ids = filter_str[8:].split(',')
                                if 'Defect' in name:
                                    defect_ids.extend(ids)
                                elif 'Enhancement' in name:
                                    enhancement_ids.extend(ids)

    return defect_ids, enhancement_ids


def fetch_defects(client, sys_ids):
    """Fetch defect details by sys_ids (individually to avoid 403 on query)."""
    results = []
    for sys_id in sys_ids:
        url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_defect/{sys_id}"
        resp = client.get(url, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            results.append(resp.json().get('result', {}))
    return results


def fetch_enhancements(client, sys_ids):
    """Fetch enhancement details by sys_ids (individually to avoid 403 on query)."""
    results = []
    for sys_id in sys_ids:
        url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_enhancement/{sys_id}"
        resp = client.get(url, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            results.append(resp.json().get('result', {}))
    return results


def main():
    session = AuthSession.load()
    if not session:
        print("No session - run 'ellucian-support login' first")
        return

    # Release with related items
    sys_id = "45cce3d283b20298c2649550ceaad3d8"

    with httpx.Client(timeout=30.0) as client:
        # Set cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value, domain="elluciansupport.service-now.com")

        # Get release info
        print("Release Info:")
        api_url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_release/{sys_id}"
        resp = client.get(api_url, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            result = resp.json().get("result", {})
            print(f"  {result.get('short_description', 'N/A')}")
            print(f"  Number: {result.get('number', 'N/A')}")
            print(f"  Date: {result.get('date_released', 'N/A')}")

        # Get related IDs from page
        print("\nExtracting related item IDs...")
        defect_ids, enhancement_ids = get_related_ids_from_page(client, sys_id)
        print(f"  Found {len(defect_ids)} defect IDs")
        print(f"  Found {len(enhancement_ids)} enhancement IDs")

        # Fetch defects
        if defect_ids:
            print("\n--- Related Defects ---")
            defects = fetch_defects(client, defect_ids)
            for d in defects:
                # Use 'summary' field for defects
                desc = d.get('summary', d.get('short_description', ''))[:70]
                version = d.get('ellucian_product_version', {})
                if isinstance(version, dict):
                    version = version.get('value', '')[:20] if version else ''
                print(f"  {d.get('number')}: {desc}")

        # Fetch enhancements
        if enhancement_ids:
            print("\n--- Related Enhancements ---")
            enhancements = fetch_enhancements(client, enhancement_ids)
            for e in enhancements:
                # Use 'summary' field for enhancements too
                desc = e.get('summary', e.get('short_description', ''))[:70]
                print(f"  {e.get('number')}: {desc}")


if __name__ == "__main__":
    main()
