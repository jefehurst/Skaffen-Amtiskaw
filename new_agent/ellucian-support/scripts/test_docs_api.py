#!/usr/bin/env python3
"""Test the docs API with various auth approaches."""

import os
import sys
from pathlib import Path

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


DOCS_API = "https://resources-admin.elluciancloud.com"


def test_no_auth():
    """Test API with no authentication."""
    print("=== Test 1: No auth ===")
    with httpx.Client(timeout=30.0) as client:
        # Try to get a page
        resp = client.get(
            f"{DOCS_API}/api/bundle/ellucian_forms/page/c_forms_overview.html",
            headers={"Accept": "application/json"},
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Got page: {data.get('title', 'N/A')}")
            html = data.get("topic_html", "")[:200]
            print(f"Content preview: {html}...")
        else:
            print(f"Error: {resp.text[:200]}")
    print()


def test_with_servicenow_cookies():
    """Test API with ServiceNow session cookies."""
    print("=== Test 2: With ServiceNow cookies ===")

    from ellucian_support.auth import AuthSession

    session = AuthSession.load()
    if not session:
        print("No ServiceNow session")
        return

    with httpx.Client(timeout=30.0) as client:
        # Set ServiceNow cookies
        for name, value in session.cookies.items():
            client.cookies.set(name, value)

        resp = client.get(
            f"{DOCS_API}/api/bundle/ellucian_forms/page/c_forms_overview.html",
            headers={"Accept": "application/json"},
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Got page: {data.get('title', 'N/A')}")
        else:
            print(f"Error: {resp.text[:200]}")
    print()


def test_toc():
    """Test getting table of contents."""
    print("=== Test 3: Get TOC (no auth) ===")
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{DOCS_API}/api/bundle/ellucian_forms/toc",
            headers={"Accept": "application/json"},
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"TOC entries: {len(data)}")
            for entry in data[:5]:
                print(f"  - {entry.get('title', 'N/A')}")
        else:
            print(f"Error: {resp.text[:200]}")
    print()


def test_bundlelist():
    """Test getting bundle list."""
    print("=== Test 4: Get bundle list (no auth) ===")
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{DOCS_API}/api/bundlelist",
            headers={"Accept": "application/json"},
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            bundles = data.get("bundle_list", [])
            print(f"Total bundles: {len(bundles)}")
            for b in bundles[:5]:
                print(f"  - {b.get('name')}: {b.get('title')}")
        else:
            print(f"Error: {resp.text[:200]}")
    print()


def main():
    test_no_auth()
    test_with_servicenow_cookies()
    test_toc()
    test_bundlelist()


if __name__ == "__main__":
    main()
