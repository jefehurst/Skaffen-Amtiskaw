#!/usr/bin/env python3
"""Check what fields are returned for defects."""

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

session = AuthSession.load()
SERVICENOW_BASE = "https://elluciansupport.service-now.com"

with httpx.Client(timeout=30.0) as client:
    for name, value in session.cookies.items():
        client.cookies.set(name, value, domain="elluciansupport.service-now.com")

    defect_id = "3af4454d83075e94209676226daad3c4"
    url = f"{SERVICENOW_BASE}/api/now/table/ellucian_product_defect/{defect_id}"
    resp = client.get(url, headers={"Accept": "application/json"})

    if resp.status_code == 200:
        data = resp.json().get('result', {})
        print(f"Fields ({len(data)} total):")
        for key in sorted(data.keys()):
            val = data[key]
            if val and str(val).strip():
                val_str = str(val)[:60]
                print(f"  {key}: {val_str}")

        # Save full response
        Path("/tmp/defect_detail.json").write_text(json.dumps(data, indent=2))
        print(f"\nFull response saved to /tmp/defect_detail.json")
