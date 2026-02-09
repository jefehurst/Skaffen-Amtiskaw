#!/usr/bin/env python3
"""Test defect table API access."""

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

session = AuthSession.load()
SERVICENOW_BASE = "https://elluciansupport.service-now.com"

with httpx.Client(timeout=30.0) as client:
    for name, value in session.cookies.items():
        client.cookies.set(name, value, domain="elluciansupport.service-now.com")

    # Test defect table access with single ID
    defect_id = "3af4454d83075e94209676226daad3c4"
    url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_defect/{defect_id}"
    resp = client.get(url, headers={"Accept": "application/json"})
    print(f"Single defect GET: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json().get('result', {})
        print(f"  Number: {data.get('number')}")
        print(f"  Description: {data.get('short_description', '')[:80]}")
    else:
        print(f"  Error: {resp.text[:300]}")

    # Test with query
    print()
    query = f"sys_idIN{defect_id}"
    url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_defect"
    params = {"sysparm_query": query}
    resp = client.get(url, params=params, headers={"Accept": "application/json"})
    print(f"Query defects: {resp.status_code}")
    if resp.status_code == 200:
        results = resp.json().get('result', [])
        print(f"  Found: {len(results)}")
        for r in results:
            print(f"  - {r.get('number')}: {r.get('short_description', '')[:60]}")
    else:
        print(f"  Error: {resp.text[:300]}")
