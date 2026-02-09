#!/usr/bin/env python3
"""Analyze the Ellucian docs site HAR to find content API."""

import json
from pathlib import Path
from urllib.parse import urlparse


def main():
    har_path = Path(__file__).parent.parent.parent / "tmp" / "ellucian_doc_site_navigation.har"
    har = json.loads(har_path.read_text())
    entries = har["log"]["entries"]

    print("=== Ellucian Docs HAR Analysis ===")
    print(f"Total entries: {len(entries)}\n")

    # Group by domain
    domains = {}
    for entry in entries:
        url = entry["request"]["url"]
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(entry)

    print("=== Domains ===")
    for domain, reqs in sorted(domains.items(), key=lambda x: -len(x[1])):
        print(f"  {domain}: {len(reqs)} requests")

    print("\n=== Interesting Endpoints (resources.elluciancloud.com) ===\n")

    # Look for content/API endpoints on the docs domain
    for entry in entries:
        url = entry["request"]["url"]
        if "resources.elluciancloud.com" not in url:
            continue

        parsed = urlparse(url)
        path = parsed.path
        method = entry["request"]["method"]
        status = entry["response"]["status"]
        content_type = ""
        for h in entry["response"]["headers"]:
            if h["name"].lower() == "content-type":
                content_type = h["value"]
                break

        # Skip static assets
        if any(ext in path for ext in [".css", ".js", ".png", ".jpg", ".svg", ".woff", ".ico"]):
            continue

        # Show interesting requests
        print(f"[{method}] {status} {path[:80]}")
        if content_type:
            print(f"    Content-Type: {content_type[:60]}")

        # Check response size
        resp = entry["response"]
        if "content" in resp and "size" in resp["content"]:
            size = resp["content"]["size"]
            if size > 1000:
                print(f"    Size: {size} bytes")
        print()

    print("\n=== JSON/API Responses ===\n")

    for i, entry in enumerate(entries):
        url = entry["request"]["url"]
        resp = entry["response"]

        content_type = ""
        for h in resp["headers"]:
            if h["name"].lower() == "content-type":
                content_type = h["value"]
                break

        if "json" in content_type.lower():
            parsed = urlparse(url)
            print(f"Entry {i}: [{entry['request']['method']}] {parsed.netloc}{parsed.path[:60]}")
            print(f"    Status: {resp['status']}, Type: {content_type[:40]}")

            # Show snippet of response
            if "content" in resp and "text" in resp["content"]:
                text = resp["content"]["text"][:200]
                print(f"    Preview: {text}...")
            print()


if __name__ == "__main__":
    main()
